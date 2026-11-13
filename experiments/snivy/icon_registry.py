"""Append independent Snivy icon mappings, preserving sentinels and forms."""

import struct

FACE_TABLE = 0x007D0200
BODY_TABLE = 0x16410200
ICON_TABLE = 0x1D9D0200
ICON_INDEX = 562
FACE_ID = 0x7BEA0C00
BODY_ID = 0x6BEA0C00


def extend_table(data, expected_count, stride, added_rows):
    if len(data) < 48 or struct.unpack_from(">II", data) != (expected_count, stride):
        raise ValueError("Unexpected original icon mapping table")
    start, length, total = struct.unpack_from(">III", data, 16)
    if (start, length, total) != (48, expected_count * stride, len(data)):
        raise ValueError("Unexpected icon mapping lengths")
    if any(len(row) != stride for row in added_rows):
        raise ValueError("Invalid icon mapping row size")
    end = start + length
    added = b"".join(added_rows)
    output = bytearray(data[:end] + added + data[end:])
    struct.pack_into(">I", output, 0, expected_count + len(added_rows))
    struct.pack_into(">II", output, 20, length + len(added), len(output))
    assert output[48:end] == data[48:end] and output[end + len(added):] == data[end:]
    return bytes(output)


def prepare(resources):
    faces = resources[FACE_TABLE]
    bodies = resources[BODY_TABLE]
    icons = resources[ICON_TABLE]
    for table, count, stride in ((faces, 495, 8), (bodies, 495, 12), (icons, 562, 16)):
        extend_table(table, count, stride, [])
    old_ids = set(struct.unpack_from(">" + "I" * (562 * 4), icons, 48))
    if FACE_ID in old_ids or BODY_ID in old_ids:
        raise ValueError("Reserved portrait resource IDs collide")
    # No sexual dimorphism; both sexes use the same own Snivy atlases.
    icon = struct.pack(">4I", FACE_ID, BODY_ID, FACE_ID, BODY_ID)
    # Native indices 495..500 remain empty; 501 is the independent new species.
    # Face flags: one form << 1, plus has-evolution bit 0 for Little Battle.
    face = struct.pack(">IHH", 501, ICON_INDEX, 3)
    body = struct.pack(">IHHHH", 501, ICON_INDEX, 1, 0, 0)
    return {
        FACE_TABLE: extend_table(faces, 495, 8, [bytes(8)] * 6 + [face]),
        BODY_TABLE: extend_table(bodies, 495, 12, [bytes(12)] * 6 + [body]),
        ICON_TABLE: extend_table(icons, 562, 16, [icon]),
    }
