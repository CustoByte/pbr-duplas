"""Audit every already changed MESG row; never translate previously untouched IDs.

Requires private original files and a RAM capture for real native-font metrics.
Writes private candidates and a reproducible source-gated review plan. It does
not update player packages/feeds or declare unmeasured UI frames verified.
"""
import argparse
import json
import re
from pathlib import Path

from prepare_campaign_doubles import read_archive, sha
from encounter_expansion import rebuild_archive
from translation.messages import TOKEN, read_messages, readable, write_messages
from ui.dialogue_layout import reflow, validate_layout
from ui.dialogue_editorial import concise, eligible, validate_editorial

RESOURCES = {'common': ('mes_common.fsys',0x27C10000), 'battle': ('menu_fight_s.fsys',0x27C31800),
             'names': ('mes_name_e.fsys',0x27C51800), 'tutorial': ('menu_btutorial.fsys',0x2A431800)}
ALIASES = {'battle': ('mes_fight_e.fsys','mes_bpass_e.fsys','menu_bpass2.fsys'),
           'names': ('menu_name2.fsys','mes_bpass_e.fsys','menu_bpass2.fsys')}


def protected_names(common):
    names = set()
    for lo,hi in ((10,974),(1382,1482),(1991,2634),(2990,3114),(4760,5704),(6354,6731)):
        for row in common[lo:hi]:
            name = TOKEN.sub('', readable(row)).strip()
            if len(name)>2 and '\n' not in name and not re.search('[\u3040-\u30ff\u4e00-\u9fff]',name):
                names.add(name)
    return names


def review(originals, baseline, metrics, output):
    if output.exists():
        raise ValueError('Use a new output directory; never overwrite a prior review')
    output.mkdir(parents=True)
    common = read_messages(dict(read_archive(originals['common']))[RESOURCES['common'][1]])[1]
    names = protected_names(common)
    from ui.verify_dialogue_paging import verify as verify_paging
    report = dict(checked=0, resources=[], changed=[], pending=[], native_paging=verify_paging(metrics),
                  new_translations=0, dolphin_visual_tested=False, published=False,
                  limits=['Original text dimensions are conservative references, not the measured physical frame.',
                          'Pending entries are review flags, not confirmed on-screen overflows.',
                          'No whole-game visual validation; no player feed changed.'])
    plan = dict(status='review-in-progress-not-published', resources={})
    changed_resources = {}
    manual = json.loads(Path(__file__).with_name('dialogue-menu-editorial.json').read_text())
    for kind,(filename,rid) in RESOURCES.items():
        old = dict(read_archive(originals[kind])); current = dict(read_archive(baseline[filename]))
        _,source_rows = read_messages(old[rid]); header,rows = read_messages(current[rid])
        if len(rows) < len(source_rows):
            raise ValueError('Baseline lost message IDs')
        targets = {}; rewritten = list(rows)
        for index,(original,translated) in enumerate(zip(source_rows,rows)):
            if original == translated:
                continue
            report['checked'] += 1
            source,before = readable(original),readable(translated)
            after,case = reflow(kind,index,source,before,metrics,names)
            editorial = []
            if case['status'] != 'bounded' and eligible(kind,index):
                shorter,rules = concise(before)
                if rules:
                    validate_editorial(before,shorter,names)
                    candidate,newcase = reflow(kind,index,source,shorter,metrics,names)
                    if newcase['status'] == 'bounded':
                        after,case,editorial = candidate,newcase,rules
            manual_text = manual.get(kind,{}).get(str(index))
            if case['status'] != 'bounded' and manual_text:
                validate_editorial(before,manual_text,names)
                candidate,newcase = reflow(kind,index,source,manual_text,metrics,names)
                if newcase['status'] == 'bounded':
                    after,case,editorial = candidate,newcase,['explicit reviewed menu rephrase']
            record = dict(resource=kind,id=index,before=before,after=after,editorial_rules=editorial,**case)
            if after != before and case['status'] == 'bounded':
                rewritten[index] = (validate_editorial(before,after,names) if editorial else
                                    validate_layout(before,after,case.get('pagination_allowed',False)))
                targets[str(index)] = dict(source_sha256=sha(translated), target=after,
                    editorial_rules=editorial, extra_pages=case.get('extra_pages',0), status=case['status'])
                report['changed'].append(record)
            if case['status'] != 'bounded':
                report['pending'].append(record)
        resource = write_messages(header,rewritten)
        result = rebuild_archive(baseline[filename],{rid:resource}) if targets else baseline[filename]
        assert all(row == rewritten[index] for index,row in enumerate(read_messages(resource)[1]))
        assert all(rewritten[index] == row for index,row in enumerate(rows) if str(index) not in targets)
        (output/filename).write_bytes(result)
        changed_resources[kind] = resource
        plan['resources'][filename] = dict(base_sha256=sha(baseline[filename]),resource=hex(rid),
                target_sha256=sha(result),targets_by_id=targets,kind=kind)
        report['resources'].append(dict(kind=kind,changed=len(targets),message_count=len(rows),
            already_changed=sum(a!=b for a,b in zip(source_rows,rows)),extra_ids_preserved=len(rows)-len(source_rows)))
        print(kind, 'checked; changed:',len(targets),flush=True)
    # Shared MESG tables must remain byte-identical in every installed copy.
    results = {}
    for kind,filenames in ALIASES.items():
        rid = RESOURCES[kind][1]
        for filename in filenames:
            if filename not in baseline:
                raise ValueError('Missing synchronized archive: '+filename)
            data = results.get(filename,baseline[filename])
            existing = dict(read_archive(data))
            if existing[rid] != dict(read_archive(baseline[RESOURCES[kind][0]]))[rid]:
                raise ValueError('Shared message baseline differs: '+filename)
            results[filename] = (rebuild_archive(data,{rid:changed_resources[kind]})
                                 if existing[rid] != changed_resources[kind] else data)
    for filename,data in results.items():
        (output/filename).write_bytes(data)
    plan['aliases'] = {name:dict(base_sha256=sha(baseline[name]),target_sha256=sha(data)) for name,data in results.items()}
    report['changed_count'] = len(report['changed'])
    report['pending_count'] = len(report['pending'])
    report['extra_pages'] = sum(row.get('extra_pages',0) for row in report['changed'])
    for name,value in (('plan.json',plan),('audit.json',report)):
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original-directory',type=Path,required=True)
    p.add_argument('--baseline-directory',type=Path,required=True)
    p.add_argument('--common-baseline',type=Path)
    for name in ('capture','dol','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a = p.parse_args()
    originals = {}
    for kind,(filename,rid) in RESOURCES.items():
        matches = list(a.original_directory.rglob(filename))
        unique = {sha(path.read_bytes()):path for path in matches}
        if len(unique) != 1:
            raise ValueError('Provide one unambiguous original '+filename)
        originals[kind] = next(iter(unique.values())).read_bytes()
    required = {filename for filename,rid in RESOURCES.values()} | {n for values in ALIASES.values() for n in values}
    baseline = {name:(a.baseline_directory/name).read_bytes() for name in required}
    if a.common_baseline:
        baseline['mes_common.fsys'] = a.common_baseline.read_bytes()
    entries = dict(read_archive(baseline['mes_common.fsys']))
    from ui.native_text import Metrics
    metrics = Metrics(a.capture,a.dol.read_bytes(),entries[0x27C00000])
    metrics.verify_tildes()
    report = review(originals,baseline,metrics,a.output)
    print('Audited:',report['checked'],'changed:',report['changed_count'],'pending:',report['pending_count'],flush=True)


if __name__ == '__main__':
    main()
