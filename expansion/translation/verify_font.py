"""Native font metrics for approved text; no GPU/balloon-layout validation."""
import argparse, json
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn import ppc_const as ppc
from verify_coop_draft import DraftReplay
from translation.messages import encoded, readable, read_messages, RESOURCE
from prepare_campaign_doubles import read_archive, sha


def verify(capture, dol, original, translated):
    h = DraftReplay(capture, dol)
    pointer = 0x81AC0000
    message_id = 0x70000001
    def lookup(u, address, size, data):
        if u.reg_read(ppc.UC_PPC_REG_4) == message_id:
            u.reg_write(ppc.UC_PPC_REG_3, pointer)
            u.reg_write(ppc.UC_PPC_REG_PC, u.reg_read(ppc.UC_PPC_REG_LR))
    h.uc.hook_add(UC_HOOK_CODE, lookup, begin=0x8024FB34, end=0x8024FB34)
    before = read_messages(dict(read_archive(original))[RESOURCE])[1]
    after = read_messages(dict(read_archive(translated))[RESOURCE])[1]
    approval = json.loads(Path(__file__).with_name('approved.json').read_text())
    canonical = {}
    for batch in approval['batches']:
        if batch['status'] in ('approved-by-user', 'approved-by-user-delegation'):
            for entry in batch['entries']:
                for index in entry['ids']:
                    canonical.setdefault(before[index], index)
    references = {index: entry['layout_reference_id']
                  for batch in approval['batches'] if batch['status'] in ('approved-by-user', 'approved-by-user-delegation')
                  for entry in batch['entries'] if 'layout_reference_id' in entry
                  for index in entry['ids']}
    from translation.trainer_names import approved_entries
    trainer_frames = {index: entry['battle_dialogue_layout_reference_id']
                      for entry in approved_entries() if 'battle_dialogue_layout_reference_id' in entry
                      for index in entry.get('battle_dialogue_reference_ids', [])}
    for index, source in enumerate(before):
        first = canonical.get(source)
        if first in references:
            references.setdefault(index, references[first])
    cases = []
    def fixture_text(row, name):
        return readable(row).replace('{0025}', name).replace('{0015}', name).replace('▼', '')
    for index, (a, b) in enumerate(zip(before, after)):
        if a == b:
            continue
        for name in ('Pikachu', 'Feraligatr', 'WWWWWWWWWWWW'):
            measures = []
            for row in (a, b):
                text = fixture_text(row, name)
                h.uc.mem_write(pointer, encoded(text))
                result = h.call(0x8024FBBC, (0x8048062C, message_id, 1, 0), limit=3000000)
                h.abi()
                measures.append({'width': result & 65535, 'height': result >> 16})
            reference_height = measures[0]['height']
            width_budget = 240
            if index in references:
                text = fixture_text(before[references[index]], name)
                h.uc.mem_write(pointer, encoded(text))
                result = h.call(0x8024FBBC, (0x8048062C, message_id, 1, 0), limit=3000000)
                h.abi()
                reference_height = max(reference_height, result >> 16)
            if index in trainer_frames:
                text = readable(before[trainer_frames[index]])
                h.uc.mem_write(pointer, encoded(text))
                result = h.call(0x8024FBBC, (0x8048062C, message_id, 1, 0), limit=3000000)
                h.abi()
                width_budget = max(width_budget, result & 65535)
                reference_height = max(reference_height, result >> 16)
            assert measures[1]['height'] <= reference_height
            assert measures[1]['width'] <= width_budget, (index, measures[1], width_budget)
            cases.append({'id': index, 'name_characters': len(name), 'source': measures[0], 'target': measures[1],
                          'layout_reference_id': references.get(index, trainer_frames.get(index)),
                          'allowed_reference_height': reference_height, 'width_budget': width_budget})
    return {'status': 'passed-native-font-metric-fixtures', 'case_count': len(cases),
            'cases': cases, 'native_font_unchanged': True,
            'height_not_increased': all(c['target']['height']<=c['source']['height'] for c in cases),
            'paired_native_message_height_respected': True,
            'translated_archive_sha256': sha(translated), 'dol_sha256': sha(dol),
            'limits': ['240-pixel width is a conservative test budget, not a verified live balloon boundary',
                       'Trainer-name references additionally use the original widest referenced trainer line as a font-metric envelope; live frame unverified',
                       'Where specified, wrapping uses the original equivalent two-line message as a height reference; live layout still unverified',
                       'Message lookup returns test text; native font measurement executes without GPU',
                       'Actual battle balloon layout and rendering still need Dolphin'],
            'dolphin_visual_tested': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for n in ('capture', 'dol', 'original', 'translated', 'output'):
        p.add_argument('--' + n, type=Path, required=True)
    a = p.parse_args()
    report = verify(a.capture, a.dol.read_bytes(), a.original.read_bytes(), a.translated.read_bytes())
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'}, indent=2))
