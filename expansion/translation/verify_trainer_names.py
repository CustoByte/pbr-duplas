"""Native global message lookup and font metrics over the reviewed archives.

Loads the actual new MESG resources into scratch RAM and changes only the
captured resource registration pointers. The message map, lookup and font
measurements execute the original game code. No GPU, NAND or game UI runs.
"""
import argparse, json, struct
from pathlib import Path
from verify_coop_draft import DraftReplay
from prepare_campaign_doubles import read_archive, sha
from translation.messages import read_messages, readable
from translation.trainer_names import plan, approved_entries


def verify(capture, dol, original_common, translated_common, original_battle, translated_battle):
    h = DraftReplay(capture, dol)
    context = 0x8048062C
    count = h.get(context + 0xD34)
    mapping = bytes(h.uc.mem_read(h.get(context + 0xD38), count * 4))
    global_ids = {}
    for i in range(count):
        key = struct.unpack_from('>HH', mapping, i*4)
        global_ids.setdefault(key, []).append(i+1)
    data = []
    for slot, resource_id, original, translated, scratch in (
        (0, 0x27C10000, original_common, translated_common, 0x92C00000),
        (1, 0x27C31800, original_battle, translated_battle, 0x92D00000),
    ):
        source = dict(read_archive(original))[resource_id]
        target = dict(read_archive(translated))[resource_id]
        captured = h.get(context + 0x64F34 + 4*slot)
        assert bytes(h.uc.mem_read(captured, len(source))) == source
        assert len(target) < 0x100000
        assert h.get(context + 0x64F54 + 4*slot) == slot+1
        source_rows = read_messages(source)[1]
        target_rows = read_messages(target)[1]
        assert len(source_rows) == len(target_rows)
        h.uc.mem_write(scratch, target)
        h.put(context + 0x64F34 + 4*slot, scratch)
        data.append((source_rows, target_rows))
    common_before, common_after = data[0]
    battle_before, battle_after = data[1]
    # Every common row passes through the native global ID/resource map. This
    # checks shifted offsets for names, items, moves, species and other text.
    lookup_cases = 0
    for index, row in enumerate(common_after):
        identifiers = global_ids.get((1, index+1), [])
        assert identifiers, ('Unmapped common message', index)
        for gid in identifiers:
            pointer = h.call(0x8024FB34, (context, gid))
            h.abi()
            assert bytes(h.uc.mem_read(pointer, len(row))) == row, (index, gid)
            lookup_cases += 1
    cases = []
    for entry in approved_entries():
        index = entry['common_message_index']
        gid = entry['native_message_id']
        assert gid in global_ids[(1, index+1)]
        assert readable(common_after[index]) == '{F001}{F101}' + entry['replacement']
        result = h.call(0x8024FBBC, (context, gid, 1, 0), limit=3000000)
        h.abi()
        assert result & 65535 <= 150 and result >> 16 == 25
        cases.append({'original': entry['original'], 'replacement': entry['replacement'],
                      'native_message_id': gid, 'width': result & 65535, 'height': result >> 16})
    reference_cases = 0
    battle_lookup_cases = 0
    for index, (source, target) in enumerate(zip(battle_before, battle_after)):
        if source == target:
            continue
        identifiers = global_ids.get((2, index+1), [])
        assert identifiers, ('Unmapped changed battle message', index)
        for gid in identifiers:
            pointer = h.call(0x8024FB34, (context, gid))
            h.abi()
            assert bytes(h.uc.mem_read(pointer, len(target))) == target
            battle_lookup_cases += 1
    for entry in approved_entries():
        for index in entry.get('battle_dialogue_reference_ids', []):
            gid = global_ids[(2, index+1)][0]
            pointer = h.call(0x8024FB34, (context, gid))
            row = battle_after[index]
            assert bytes(h.uc.mem_read(pointer, len(row))) == row
            assert entry['replacement'] in readable(row)
            reference_cases += 1
    for index in (5890, 6372, 6466, 6521, 6735, 8108):
        assert common_before[index] == common_after[index]
    # The records label at 7842 is now legitimately translated; preserve
    # the place name itself rather than freezing the surrounding sentence.
    assert readable(common_before[7842]).count('Crystal Colosseum') == readable(common_after[7842]).count('Crystal Colosseum') == 1
    for index in (9294,):
        gid = global_ids[(1, index+1)][0]
        result = h.call(0x8024FBBC, (context, gid, 1, 0), limit=3000000)
        assert readable(common_after[index]) == "{F001}{F101}Pedro's Groupie"
        assert result & 65535 <= 240 and result >> 16 == 25
    return {'status': 'passed-native-trainer-labels-and-reference-lookup',
            'native_common_message_lookups': lookup_cases, 'reviewed_names': len(cases),
            'renamed_names': sum(c['original']!=c['replacement'] for c in cases),
            'native_battle_reference_lookups': reference_cases, 'name_font_cases': cases,
            'native_changed_battle_message_lookups': battle_lookup_cases,
            'Marina_Joel_Joey_Crystal_Colosseum_Sierra_Leone_preserved': True,
            'original_global_message_mapping_preserved': True,
            'common_sha256': sha(translated_common), 'battle_sha256': sha(translated_battle),
            'dol_sha256': sha(dol), 'dolphin_visual_tested': False,
            'limits': ['New MESG resources injected into captured registrations; no archive loading in Dolphin',
                       'Native lookup and metrics do not validate the real UI frame or rendering',
                       'No full battle, save/load or changed trainer appearance test']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('capture','dol','original-common','translated-common','original-battle','translated-battle','output'):
        p.add_argument('--'+n, type=Path, required=True)
    a = p.parse_args()
    report = verify(a.capture, a.dol.read_bytes(), a.original_common.read_bytes(), a.translated_common.read_bytes(),
                    a.original_battle.read_bytes(), a.translated_battle.read_bytes())
    a.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='name_font_cases'}, indent=2))
