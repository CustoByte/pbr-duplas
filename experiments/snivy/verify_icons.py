"""Native face/body atlas dispatch, including NFE metadata; no rendered UI."""

import argparse
import json
from pathlib import Path
import struct

from prepare_campaign_doubles import read_archive, sha
from verify_coop_draft import DraftReplay
from icon_registry import prepare, FACE_TABLE, BODY_TABLE, ICON_TABLE, FACE_ID, BODY_ID, ICON_INDEX


def verify(capture, dol_path, common_path, face_path, body_path):
    dol, common = dol_path.read_bytes(), common_path.read_bytes()
    if sha(dol) != "da02a1232240e139ec14a26ee8b4c2818c56f3c2907f5c2391bd81e2dc0842f6" or sha(common) != "a3667703d2bf2e6733c6d40e4709869982f98e45b9ad029a9f7d7d9fec883d57":
        raise ValueError("Requires exact test13 baseline")
    resources = dict(read_archive(common))
    targets = prepare(resources)
    h = DraftReplay(capture, dol)
    refs = {FACE_TABLE: 0x80625178, BODY_TABLE: 0x806251C0, ICON_TABLE: 0x806251D8}
    getters = {FACE_TABLE: 0x80395600, BODY_TABLE: 0x8039A570, ICON_TABLE: 0x8039C124}
    originals = {rid: h.get(ref) for rid, ref in refs.items()}
    for slot, rid in enumerate(refs):
        source, target = resources[rid], targets[rid]
        old_count, stride = struct.unpack_from(">II", source)
        old_data = h.get(originals[rid] + 16)
        assert bytes(h.uc.mem_read(old_data, old_count * stride)) == source[48:48 + old_count * stride]
        obj = bytearray(h.uc.mem_read(originals[rid], 48))
        count = struct.unpack_from(">I", target)[0]
        rows = target[48:48 + count * stride]
        object_at, data_at = 0x81B00000 + slot * 0x100, 0x81810000 + slot * 0x10000
        for offset, value in ((0, count), (8, data_at), (16, data_at),
                              (20, len(rows)), (24, data_at + len(rows))):
            struct.pack_into(">I", obj, offset, value)
        h.uc.mem_write(object_at, bytes(obj))
        h.uc.mem_write(data_at, rows)
        h.put(refs[rid], object_at)
        for index in range(old_count):
            pointer = h.call(getters[rid], (refs[rid], index))
            assert bytes(h.uc.mem_read(pointer, stride)) == source[48 + index * stride:48 + (index + 1) * stride]
    try:
        face_index = h.call(0x80395634, (refs[FACE_TABLE], 501))
        body_index = h.call(0x8039A5A4, (refs[BODY_TABLE], 501))
        assert face_index == body_index == ICON_INDEX
        assert h.call(0x80395668, (refs[FACE_TABLE], 501)) == 1
        assert h.call(0x803956A0, (refs[FACE_TABLE], 501)) == 1
        assert h.call(0x8039A5D8, (refs[BODY_TABLE], 501)) == 1
        ids = [h.call(getter, (refs[ICON_TABLE], ICON_INDEX))
               for getter in (0x8039C158, 0x8039C18C, 0x8039C1C0, 0x8039C1F4)]
        assert ids == [FACE_ID, BODY_ID, FACE_ID, BODY_ID]
        h.abi()
        face = dict(read_archive(face_path.read_bytes()))[FACE_ID]
        body = dict(read_archive(body_path.read_bytes()))[BODY_ID]
        assert struct.unpack_from(">HH", face) == (96, 96)
        assert struct.unpack_from(">HH", body) == (54, 108)
    finally:
        for rid, pointer in originals.items():
            h.put(refs[rid], pointer)
    return dict(
        kind="offline native portrait table lookup and private archive structure",
        passed=True, original_face_rows_preserved=495, original_body_rows_preserved=495,
        original_icon_rows_preserved=562, new_icon_index=ICON_INDEX,
        face_resource=f"{FACE_ID:08x}", body_resource=f"{BODY_ID:08x}",
        gender_references_verified=4, native_form_count=1, native_has_evolution=True,
        face_atlas_dimensions=[96, 96], body_atlas_dimensions=[54, 108],
        face_texture_sha256=sha(face), body_texture_sha256=sha(body),
        limits=["No actual UI render or FSYS loading in Dolphin",
                "NFE flag is not a complete Little Battle eligibility test",
                "No player pass delivery or save/load"],
        playable=False, published_in_updater=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("capture", "dol", "common", "face", "body", "report"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.capture, args.dol, args.common, args.face, args.body)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
