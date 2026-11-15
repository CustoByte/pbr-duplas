"""Prepare a private review queue; never marks drafts as approved."""
import argparse,json,re
from pathlib import Path
from translation.messages import read_messages,readable,RESOURCE,TOKEN
from prepare_campaign_doubles import read_archive

def select(battle,common,approval,drafts):
    rows=read_messages(dict(read_archive(battle))[RESOURCE])[1]
    used={rows[i] for b in approval['batches'] for e in b['entries'] for i in e['ids']}
    used.update(rows[i] for i in (3923,3925,4359,4361,4362,4375,4377,4378))
    pending=[]
    for source,draft in drafts.items():
        for index in draft['ids']:
            if rows[index] not in used:
                pending.append({'archive':'menu_fight_s.fsys','id':index,
                                'source':readable(rows[index]),'draft':draft['target'],
                                'status':'awaiting-editorial-and-layout-review'})
    # Menu and campaign text from the common resource. Name and description
    # tables are deliberately outside this initial selection range.
    common_rows=read_messages(dict(read_archive(common))[0x27C10000])[1]
    for index,row in enumerate(common_rows):
        if index<7000:continue
        text=readable(row);body=TOKEN.sub('',text)
        if len(body.split())<4 or not re.search('[a-z]',body):continue
        pending.append({'archive':'mes_common.fsys','id':index,'source':text,
                        'status':'awaiting-scope-protected-name-and-translation-review'})
    assert len(pending)>=2000
    return {'requested_new_messages':2000,'translated_and_validated':0,
            'publication_allowed':False,'entries':pending[:2000]}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('battle','common','approval','drafts','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    result=select(a.battle.read_bytes(),a.common.read_bytes(),json.loads(a.approval.read_text()),json.loads(a.drafts.read_text()))
    a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print('Queued:',len(result['entries']),'messages; not yet approved or applied')
