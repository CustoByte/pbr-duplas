"""Promote exactly 5000 non-overlapping, verified new message IDs."""
import argparse,collections,json,re
from pathlib import Path
from translation.messages import TOKEN

def promote(report,root,replace=False):
    passed=report['passed']
    if len(passed)<5000:raise ValueError('Fewer than 5000 layout-checked new texts')
    selected=list(passed[:5000]);keys={(e['archive'],e['id']) for e in selected}
    # Complete the month abbreviations and active summary/cancel controls,
    # prioritizing them over optional geographic-name localization.
    wanted={9951,9952,9954,9956,9959,9961,9962,9993}
    for entry in passed[5000:]:
        key=entry['archive'],entry['id']
        if entry['archive']=='mes_common.fsys' and entry['id'] in wanted and key not in keys:
            remove=next((i for i in range(len(selected)-1,-1,-1)
                         if selected[i]['archive']=='mes_common.fsys' and 5744<=selected[i]['id']<6354),None)
            if remove is None:raise ValueError('Cannot replace optional geography entry')
            keys.remove((selected[remove]['archive'],selected[remove]['id']))
            selected[remove]=entry;keys.add(key)
    assert len(selected)==len(keys)==5000
    p=root/'approved.json';approved=json.loads(p.read_text())
    if any(b['batch']==14 for b in approved['batches']):
        if not replace:raise ValueError('Lot already promoted')
        approved['batches']=[b for b in approved['batches'] if b['batch']!=14]
    battle=[];common={};cases=[]
    for e in selected:
        source=e['source'];target=e['target'];prefix=re.match(r'^(?:\{F[0-9A-F]{3}\})+',source)[0]
        assert re.sub(r'\s+',' ',TOKEN.sub('',source)).strip()!=re.sub(r'\s+',' ',TOKEN.sub('',target)).strip()
        if e['archive']=='menu_fight_s.fsys':
            battle.append({'ids':[e['id']],'target':target,'glyph_policy':'prepared-ascii-with-original-names'})
        else:common[str(e['id'])]=target[len(prefix):]
        cases.append({'archive':e['archive'],'id':e['id'],'source_sha256':e['source_sha256'],**e['font_metrics']})
    approved['batches'].append({'batch':14,'status':'approved-by-user-delegation',
                               'category':'full-game-lot-5000','propagate_exact_duplicates':False,'entries':battle})
    p.write_text(json.dumps(approved,ensure_ascii=False,indent=2)+'\n')
    (root/'review-common-lot5000.json').write_text(json.dumps({'status':'approved-by-user-delegation','glyph_policy':'prepared-ascii-with-original-names','targets_by_id':common},ensure_ascii=False,indent=2)+'\n')
    return {'status':'passed-native-font-and-source-family-envelopes','new_message_count':5000,
            'by_archive':dict(collections.Counter(e['archive'] for e in selected)),
            'cases':cases,'font_size_changed':False,'dolphin_visual_tested':False,
            'limits':report['limits']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--replace',action='store_true')
    a=p.parse_args();r=promote(json.loads(a.report.read_text()),Path(__file__).parent,a.replace)
    a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(r['by_archive'])
