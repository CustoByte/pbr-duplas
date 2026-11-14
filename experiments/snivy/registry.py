"""Isolated data experiment, deliberately not imported by the release builder.

National IDs are not native table indices. Native 494/495 are egg sentinels;
496..500 contain alternate-form data. No model/name/evolution entry is supplied.
"""

import struct

RESOURCE = 0x00810200
NATIONAL_ID = 495
INTERNAL_ID = 501
RESERVED_NATIVE = frozenset(range(494, 501))


def internal_id(national):
    if 1 <= national <= 493:
        return national
    if national == NATIONAL_ID:
        return INTERNAL_ID
    raise ValueError("National species is not registered (including Victini 494)")


def experimental_row():
    # Only the fields required by the request and verified in the USA loader.
    # Zeros in all other fields are unresolved, NOT production defaults.
    row = bytearray(52)
    row[30:36] = bytes((45, 45, 55, 63, 45, 55))  # HP/Atk/Def/Spe/SpA/SpD
    row[36:38] = bytes((12, 12))  # Grass/Grass
    row[48] = 65  # Overgrow
    return bytes(row)


def append_stats(table, row=None):
    if len(table) < 48:
        raise ValueError("Truncated table")
    count, stride = struct.unpack_from(">II", table)
    start = struct.unpack_from(">I", table, 16)[0]
    if (count, stride, start, len(table)) != (501, 52, 48, 26112):
        raise ValueError("Only the audited RPBE01 stats layout is supported")
    if struct.unpack_from(">II", table, 20) != (count * stride, len(table)):
        raise ValueError("Unexpected data/total lengths")
    end = start + count * stride
    row = experimental_row() if row is None else row
    if not isinstance(row, bytes) or len(row) != stride:
        raise ValueError("Expected a complete 52-byte stats row")
    result = bytearray(table[:end] + row + table[end:])
    struct.pack_into(">I", result, 0, count + 1)
    struct.pack_into(">II", result, 20, (count + 1) * stride, len(result))
    assert result[48:end] == table[48:end]
    assert result[end + 52 :] == table[end:]
    return bytes(result)
