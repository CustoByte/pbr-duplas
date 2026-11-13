"""Replay the real USA FSYS catalog lookup against an appended disk catalog."""

import argparse
import hashlib
import json
from pathlib import Path

from catalog import append_archive, entries, relocate, SNIVY_ARCHIVE_ID
from verify_coop_draft import DraftReplay

LOOKUP = 0x8024C32C
POINTER = 0x80627B5C
BASE = 0x81B40000


def verify(capture, dol_path, catalog_path):
    source = catalog_path.read_bytes()
    dol = dol_path.read_bytes()
    digest = lambda data: hashlib.sha256(data).hexdigest()
    if digest(source) != "da886839e93a719a04833795f2407417cccded696d7e92e49087065dbf3ee26e":
        raise ValueError("Requires the supplied audited original catalog")
    if digest(dol) != "da02a1232240e139ec14a26ee8b4c2818c56f3c2907f5c2391bd81e2dc0842f6":
        raise ValueError("Requires unchanged test13 DOL")
    patched = append_archive(source)
    h = DraftReplay(capture, dol)
    original_pointer = h.get(POINTER)
    original_start, original = entries(source)
    new_start, new = entries(patched)
    before = [h.call(LOOKUP, (row[0],)) for row in original]
    assert before == [original_pointer + original_start + 16 * i for i in range(len(original))]
    assert h.call(LOOKUP, (SNIVY_ARCHIVE_ID,)) == 0
    h.uc.mem_write(BASE, relocate(patched, BASE))
    h.put(POINTER, BASE)
    try:
        for index, (identity, name, name_offset, cache, _) in enumerate(new):
            address = h.call(LOOKUP, (identity,))
            assert address == BASE + new_start + 16 * index
            assert h.get(address + 4) == BASE + name_offset
            assert bytes(h.uc.mem_read(BASE + name_offset, len(name) + 1)) == name.encode() + b"\0"
            assert h.get(address + 8) == cache
            assert h.get(address + 12) == 0
        assert h.call(LOOKUP, (0xFFFFFFFF,)) == 0
    finally:
        h.put(POINTER, original_pointer)
    assert [h.call(LOOKUP, (row[0],)) for row in original] == before
    return dict(
        kind="offline native catalog lookup; no archive loading or rendering",
        passed=True, original_entries_preserved=len(original),
        added_id=SNIVY_ARCHIVE_ID, added_name=new[-1][1],
        source_sha256=digest(source), target_sha256=digest(patched),
        original_bytes=len(source), target_bytes=len(patched),
        native_lookup=f"{LOOKUP:08x}", restoration_verified=True,
        playable=False, published_in_updater=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("capture", "dol", "catalog", "report"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.capture, args.dol, args.catalog)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
