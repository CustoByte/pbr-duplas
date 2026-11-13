"""Read-only BRRES resource inventory. Does not convert or distribute assets."""
import argparse
import hashlib
import json
import struct
from pathlib import Path


def inspect(data):
    def bounds(offset, size):
        if offset < 0 or size < 0 or offset + size > len(data):
            raise ValueError('Reference outside BRRES')
    def u32(offset):
        bounds(offset, 4)
        return struct.unpack_from('>I', data, offset)[0]
    def name(offset):
        bounds(offset, 1)
        end = data.find(b'\0', offset)
        if end < 0 or end - offset > 4096:
            raise ValueError('Invalid resource name')
        return data[offset:end].decode('utf-8')
    def group(offset):
        size, count = u32(offset), u32(offset + 4)
        bounds(offset, size)
        if size < 8 + (count + 1) * 16:
            raise ValueError('Truncated resource dictionary')
        result = []
        for i in range(count):
            entry = offset + 8 + (i + 1) * 16
            result.append((name(offset + u32(entry + 8)), offset + u32(entry + 12)))
        return result
    if len(data) < 24 or data[:6] != b'bres\xfe\xff':
        raise ValueError('Expected big-endian BRRES')
    if u32(8) != len(data):
        raise ValueError('BRRES length mismatch')
    root = struct.unpack_from('>H', data, 12)[0]
    bounds(root, 8)
    if data[root:root + 4] != b'root':
        raise ValueError('Missing root section')
    bounds(root, u32(root + 4))
    folders = {}
    total = 1  # root is included in BRRES section count
    for folder, offset in group(root + 8):
        resources = []
        for resource, at in group(offset):
            bounds(at, 16)
            size, version = u32(at + 4), u32(at + 8)
            bounds(at, size)
            if size < 16:
                raise ValueError('Invalid section size')
            item = dict(name=resource, format=data[at:at + 4].decode('ascii'),
                        offset=at, size=size, version=version)
            if item['format'] in ('CHR0', 'SRT0') and version == 5:
                bounds(at, 40)
                item.update(frames=struct.unpack_from('>H', data, at + 32)[0],
                            tracks=struct.unpack_from('>H', data, at + 34)[0],
                            loop=bool(u32(at + 36)))
            resources.append(item)
            total += 1
        folders[folder] = resources
    if total != struct.unpack_from('>H', data, 14)[0]:
        raise ValueError('Section count mismatch')
    return dict(sha256=hashlib.sha256(data).hexdigest(), size=len(data),
                section_count=total, folders=folders,
                converted_to_pbr=False, visually_verified=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    result = inspect(args.source.read_bytes())
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    for folder, resources in result['folders'].items():
        print(f'{folder}: {len(resources)}')
        if folder == 'AnmChr(NW4R)':
            for item in resources:
                if item['name'] in ('NorIdle0', 'Faint0', 'Atk0_0', 'DamF0'):
                    print(item)
