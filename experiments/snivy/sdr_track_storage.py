"""Compact storage for immutable SDR float/time arrays.

Each curve retains an independent writable 32-byte header/cache. Only identical
float32 value arrays and immutable frame records share file offsets. Values
are rounded to six decimals and repeated adjacent samples are collapsed; the
full pose/skin roundtrip must pass before any private package is accepted.
"""
import struct


def writer(frame_rate=30):
    def write(file, address, keyframes, scale):
        if not keyframes or len(keyframes) > 65535:
            raise ValueError('Invalid native track length')
        if scale != 1:
            raise ValueError('Compact tracks require the audited float32 format')
        compact = []
        for frame, value in keyframes:
            value = round(value, 6)
            if value == 0:
                value = 0.0
            if not compact or struct.pack('>f', value) != struct.pack('>f', compact[-1][1]):
                compact.append((frame, value))
        keyframes = compact
        cache = getattr(file, '_snivy_arrays', None)
        if cache is None:
            cache = file._snivy_arrays = {}
        arrays = (
            ('values', b''.join(struct.pack('>f', value) for _, value in keyframes)),
            ('frames', b''.join(struct.pack('>HHIf', 0, i, 0, frame / frame_rate)
                               for i, (frame, _) in enumerate(keyframes))),
        )
        next_address = address + 32
        pointers = []
        for kind, data in arrays:
            key = (kind, data)
            at = cache.get(key)
            if at is None:
                at = next_address
                file.file.seek(at)
                file.file.write(data)
                cache[key] = at
                next_address += len(data)
            pointers.append(at)
        header = bytearray(32)
        struct.pack_into('>I', header, 0, pointers[0])
        struct.pack_into('>H', header, 8, len(keyframes))
        struct.pack_into('>f', header, 12, keyframes[-1][0] / frame_rate)
        struct.pack_into('>I', header, 16, pointers[1])
        struct.pack_into('>H', header, 20, len(keyframes))
        struct.pack_into('>f', header, 24, -1234567.0)
        file.file.seek(address)
        file.file.write(header)
        return next_address
    return write
