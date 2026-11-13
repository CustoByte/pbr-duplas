"""Independent Snivy name registration, isolated from the public updater.

Global message IDs differ from MESG row indices. Append both tables, preserving
all old entries and the exact old name behavior for eggs and alternate forms.
"""

import struct

from prepare_campaign_doubles import file_offset, sha, word
from team_series_asm import branch, d
from translation.messages import read_messages, write_messages, encoded, readable

MAP_RESOURCE = 0x008B0000
MESSAGE_RESOURCE = 0x27C10000
NAME_HOOK = 0x803E3478
NAME_CODE = 0x80646000
RESERVED_END = NAME_CODE + 0x200
DOL_SHA = "da02a1232240e139ec14a26ee8b4c2818c56f3c2907f5c2391bd81e2dc0842f6"


def append_name(mapping, messages):
    if len(mapping) < 8:
        raise ValueError("Truncated global message map")
    stride, count = struct.unpack_from(">II", mapping)
    if stride != 4 or len(mapping) != 8 + count * stride or count >= 32767:
        raise ValueError("Unsupported global message map layout")
    header, rows = read_messages(messages)
    if any(readable(row) == "{F001}{F101}SNIVY" for row in rows):
        raise ValueError("Snivy name is already registered")
    if len(rows) >= 65535:
        raise ValueError("MESG local index exceeds uint16")
    new_header = bytearray(header)
    struct.pack_into(">I", new_header, 4, len(rows) + 1)
    new_messages = write_messages(bytes(new_header), rows + [encoded("{F001}{F101}SNIVY")])
    new_map = bytearray(mapping + struct.pack(">HH", 1, len(rows) + 1))
    struct.pack_into(">I", new_map, 4, count + 1)
    assert new_map[8:-4] == mapping[8:]
    assert read_messages(new_messages)[1][:-1] == rows
    return bytes(new_map), new_messages, count + 1


def name_thunk(global_id):
    if not 0 < global_id <= 32767:
        raise ValueError("Name ID does not fit signed immediate")
    # Preserve r0, CR and SP. No function calls and no LR/CTR changes.
    words = [
        d(37, 1, 1, -0x20), d(36, 0, 1, 8), 0x7C000026,
        d(36, 0, 1, 12), d(11, 0, 4, 501),
        0x4082000C, d(14, 3, 0, global_id), 0x48000008,
        d(14, 3, 4, 10), d(32, 0, 1, 12), 0x7C0FF120,
        d(32, 0, 1, 8), d(14, 1, 1, 0x20),
    ]
    words.append(branch(NAME_CODE + len(words) * 4, NAME_HOOK + 4))
    return b"".join(struct.pack(">I", w) for w in words)


def patch_dol(dol, global_id):
    if sha(dol) != DOL_SHA:
        raise ValueError("Name hook requires exact published test13 DOL")
    slot = 3
    if any(word(dol, base + slot * 4) for base in (0, 0x48, 0x90)):
        raise ValueError("Name section slot is occupied")
    if word(dol, file_offset(dol, NAME_HOOK)) != 0x3864000A:
        raise ValueError("Unexpected native species name instruction")
    for count, ao, so in ((7, 0x48, 0x90), (11, 0x64, 0xAC)):
        for index in range(count):
            start, size = word(dol, ao + index * 4), word(dol, so + index * 4)
            if size and start < RESERVED_END and NAME_CODE < start + size:
                raise ValueError("Name section overlaps an existing section")
    if word(dol, 0xD8) + word(dol, 0xDC) > NAME_CODE:
        raise ValueError("Name section overlaps BSS")
    output = bytearray(dol)
    struct.pack_into(">I", output, file_offset(dol, NAME_HOOK), branch(NAME_HOOK, NAME_CODE))
    # Extend the existing shared MEM1 arena clamp, retaining all older mods.
    for address, before, after in (
        (0x8063C700, d(15, 4, 0, 0x8064), d(15, 4, 0, 0x8064)),
        (0x8063C704, d(14, 4, 4, 0x6000), d(14, 4, 4, 0x6200)),
    ):
        offset = file_offset(dol, address)
        if word(dol, offset) != before:
            raise ValueError("Unexpected existing MEM1 arena clamp")
        struct.pack_into(">I", output, offset, after)
    offset = (len(output) + 31) & ~31
    output.extend(bytes(offset - len(output)))
    body = name_thunk(global_id)
    if len(body) > RESERVED_END - NAME_CODE:
        raise ValueError("Name hook exceeds its section")
    output.extend(body + bytes(RESERVED_END - NAME_CODE - len(body)))
    for base, value in ((0, offset), (0x48, NAME_CODE), (0x90, RESERVED_END - NAME_CODE)):
        struct.pack_into(">I", output, base + slot * 4, value)
    return bytes(output)
