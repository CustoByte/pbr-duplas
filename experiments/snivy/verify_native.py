"""Offline native PPC proof; no rendered game, persistence or battle claim."""
import argparse
import json
import struct
from pathlib import Path

from prepare_campaign_doubles import read_archive, sha
from verify_coop_draft import DraftReplay
from registry import RESOURCE, INTERNAL_ID, append_stats

LOAD = 0x803E052C
REFERENCE = 0x80625184
OBJECT, DATA, OUTPUT = 0x81B00000, 0x81810000, 0x81B01000


def verify(capture, dol_path, common_path):
    dol, common = dol_path.read_bytes(), common_path.read_bytes()
    if sha(dol) != 'da02a1232240e139ec14a26ee8b4c2818c56f3c2907f5c2391bd81e2dc0842f6':
        raise ValueError('Requires unchanged published test13 DOL')
    if sha(common) != 'a3667703d2bf2e6733c6d40e4709869982f98e45b9ad029a9f7d7d9fec883d57':
        raise ValueError('Requires unchanged published test13 common.fsys')
    old = dict(read_archive(common))[RESOURCE]
    new = append_stats(old)
    replay = DraftReplay(capture, dol)
    original_object = replay.get(REFERENCE)
    original_data = replay.get(original_object + 16)
    if bytes(replay.uc.mem_read(original_data, 501 * 52)) != old[48:48 + 501 * 52]:
        raise ValueError('Capture stats differ from audited baseline')

    def load(species):
        replay.uc.mem_write(OUTPUT, bytes(44))
        replay.call(LOAD, (species, OUTPUT))
        return bytes(replay.uc.mem_read(OUTPUT, 44))

    before = [load(s) for s in range(501)]
    obj = bytearray(replay.uc.mem_read(original_object, 48))
    rows = new[48:48 + 502 * 52]
    for offset, value in ((0, 502), (8, DATA), (16, DATA),
                          (20, len(rows)), (24, DATA + len(rows))):
        struct.pack_into('>I', obj, offset, value)
    replay.uc.mem_write(OBJECT, bytes(obj))
    replay.uc.mem_write(DATA, rows)
    replay.put(REFERENCE, OBJECT)
    assert [load(s) for s in range(501)] == before
    snivy = load(INTERNAL_ID)
    assert list(snivy[:8]) == [45, 45, 55, 63, 45, 55, 12, 12]
    assert snivy[22:24] == bytes((65, 0))
    replay.put(REFERENCE, original_object)
    assert [load(s) for s in range(501)] == before
    return {'kind': 'offline native PPC stats registration only',
            'national_id': 495, 'provisional_internal_id': INTERNAL_ID,
            'original_records_unchanged': 501, 'restoration_verified': True,
            'native_stats_output_hex': snivy.hex(),
            'dol_sha256': sha(dol), 'common_sha256': sha(common),
            'playable': False,
            'pending': ['global ID bounds audit', 'names and model registry',
                        'evolution eligibility', 'moves legality and learnset',
                        'PK4 and save roundtrip', 'models and animations',
                        'menus and actual Dolphin battles']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--dol', type=Path, required=True)
    parser.add_argument('--common', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.capture, args.dol, args.common)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
