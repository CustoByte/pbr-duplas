"""Read-only FSYS inventory/extraction for the supplied PBR USA resources.

Usage: python inspect_fsys.py input.fsys output_directory
No repacking, patching or interpretation of gameplay fields is performed.
"""
import argparse
import hashlib
import json
import re
import struct
from pathlib import Path


def u32(data, offset):
    return struct.unpack_from('>I', data, offset)[0]


def decompress(data, expected):
    if data[:4] != b'LZSS':
        if len(data) != expected:
            raise ValueError('Uncompressed size mismatch')
        return data
    if len(data) < 16 or u32(data, 4) != expected or u32(data, 8) != len(data):
        raise ValueError('LZSS header mismatch')
    if expected > 64 * 1024 * 1024:
        raise ValueError('Resource exceeds analysis size limit')
    ring = bytearray(4096)
    cursor, source = 0xFEE, 16
    output = bytearray()
    while len(output) < expected:
        flags = data[source]
        source += 1
        for bit in range(8):
            if len(output) == expected:
                break
            if flags & (1 << bit):
                values = [data[source]]
                source += 1
                for value in values:
                    output.append(value)
                    ring[cursor] = value
                    cursor = (cursor + 1) & 4095
            else:
                first, second = data[source:source + 2]
                source += 2
                offset, length = first | ((second & 0xF0) << 4), (second & 15) + 3
                if len(output) + length > expected:
                    raise ValueError('Back-reference exceeds declared output')
                for index in range(length):
                    value = ring[(offset + index) & 4095]
                    output.append(value)
                    ring[cursor] = value
                    cursor = (cursor + 1) & 4095
    if source != len(data):
        raise ValueError('Trailing compressed bytes')
    return bytes(output)


def inspect(path, destination):
    data = path.read_bytes()
    if data[:4] != b'FSYS' or u32(data, 0x20) != len(data):
        raise ValueError('Invalid FSYS signature or size')
    count = u32(data, 0x0C)
    table = u32(data, u32(data, 0x18))
    if count > 10000 or table + count * 4 > len(data):
        raise ValueError('Invalid entry table')
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {'source': path.name, 'size': len(data),
                'sha256': hashlib.sha256(data).hexdigest(), 'entries': []}
    for index in range(count):
        header = u32(data, table + index * 4)
        identifier = u32(data, header)
        offset, expected, stored = (u32(data, header + n) for n in (4, 8, 0x14))
        name_offset = u32(data, header + 0x1C)
        name = None
        if name_offset:
            end = data.index(b'\0', name_offset)
            name = data[name_offset:end].decode('ascii', errors='replace')
        if offset + stored > len(data):
            raise ValueError('Payload outside archive')
        payload = decompress(data[offset:offset + stored], expected)
        safe = re.sub(r'[^A-Za-z0-9_.-]', '_', name or f'{identifier:08x}.bin')[:120]
        filename = f'{index:03d}_{safe}'
        target = destination / filename
        with target.open('xb') as stream:
            stream.write(payload)
        strings = [m.group().decode('ascii') for m in re.finditer(rb'[ -~]{6,}', payload)]
        (destination / (filename + '.strings.txt')).write_text('\n'.join(strings))
        manifest['entries'].append({'index': index, 'id': f'{identifier:08x}',
                                    'name': name, 'file': filename,
                                    'offset': offset, 'stored_size': stored,
                                    'decoded_size': len(payload),
                                    'magic_hex': payload[:4].hex(),
                                    'sha256': hashlib.sha256(payload).hexdigest()})
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(f'{path.name}: {count} entries decoded; {sum(e["decoded_size"] for e in manifest["entries"])} bytes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    inspect(args.input, args.output)
