"""Narrow non-contiguous species guards: admit 501, preserve every other value.

This is not a blanket 493->501 replacement and does not register table rows.
"""

import struct

from prepare_campaign_doubles import word, file_offset, sha
from team_series_asm import branch, d

BASE = 0x80646200
END = 0x80647200
SOURCE_SHA = "bbbb63e9f958f8ff4b36da7e0948fff335cb2b87b5607fec0d90eda7b2bb7fb5"
SITES = (
    0x800124A0, 0x80013E1C, 0x80013FF4, 0x80014084,
    0x80014330, 0x80014370, 0x80014438, 0x800144A8,
    0x80015608, 0x80015670, 0x800156D8, 0x80015740,
    0x800157A8, 0x8001B938, 0x8001EE34, 0x800218C0,
    0x800219D0, 0x80021AE0, 0x80021BF0, 0x80021D00,
    0x80021E10, 0x80021F08, 0x80023BB4, 0x80023C28,
    0x80023C9C, 0x80023D10, 0x80023D84, 0x80026F40,
    0x80026FCC, 0x80027098,
    0x80058C6C,  # Native menu Pokémon-presence predicate, original limit 495.
)


def patch_dol(dol):
    if sha(dol) != SOURCE_SHA:
        raise ValueError("Requires the exact verified Snivy name-stage DOL")
    slot = 6
    if any(word(dol, base + slot * 4) for base in (0, 0x48, 0x90)):
        raise ValueError("Guard section slot is occupied")
    for count, ao, so in ((7, 0x48, 0x90), (11, 0x64, 0xAC)):
        for i in range(count):
            start, size = word(dol, ao + i * 4), word(dol, so + i * 4)
            if size and start < END and BASE < start + size:
                raise ValueError("Guard section overlaps existing data/code")
    if word(dol, 0xD8) + word(dol, 0xDC) > BASE:
        raise ValueError("Guard section overlaps BSS")
    output, code, cases = bytearray(dol), bytearray(), []
    for site in SITES:
        at = file_offset(dol, site)
        compare, following = word(dol, at), word(dol, at + 4)
        if (compare >> 26 not in (10, 11) or (compare >> 23) & 7
                or compare & 65535 not in (493, 495)):
            raise ValueError(f"Unexpected original species compare at {site:08x}")
        if following >> 26 != 16 or (following >> 16) & 31 != 1 or (following >> 21) & 31 not in (4, 12):
            raise ValueError(f"Expected bgt/ble following compare at {site:08x}")
        entry = BASE + len(code)
        # EQ is an accepted result for the existing <= upper-bound branch.
        # Values other than 501 execute the exact original compare. GPRs,
        # LR, CTR, XER, CR1..7 and stack are never modified by this bridge.
        words = ((compare & 0xFFFF0000) | 501, 0x41820008, compare,
                 branch(entry + 12, site + 4))
        code.extend(b"".join(struct.pack(">I", w) for w in words))
        struct.pack_into(">I", output, at, branch(site, entry))
        cases.append(dict(site=f"{site:08x}", register=(compare >> 16) & 31,
                          old_limit=compare & 65535, thunk=f"{entry:08x}"))
    if len(code) > END - BASE:
        raise ValueError("Species bridges exceed their reservation")
    clamp_at = file_offset(dol, 0x8063C704)
    if word(dol, clamp_at) != d(14, 4, 4, 0x6200):
        raise ValueError("Unexpected name-stage arena clamp")
    struct.pack_into(">I", output, clamp_at, d(14, 4, 4, 0x7200))
    offset = (len(output) + 31) & ~31
    output.extend(bytes(offset - len(output)))
    output.extend(code + bytes(END - BASE - len(code)))
    for base, value in ((0, offset), (0x48, BASE), (0x90, END - BASE)):
        struct.pack_into(">I", output, base + slot * 4, value)
    return bytes(output), cases
