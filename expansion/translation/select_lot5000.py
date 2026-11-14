"""Inventory genuinely untranslated text without selecting protected name tables."""
import argparse,json,re
from pathlib import Path
from translation.messages import RESOURCE,TOKEN,read_messages,readable
from prepare_campaign_doubles import read_archive,sha

# Includes duplicate/debug move names, berry/ribbon names, clothing names,
# primary trainer names, and the composite nature-name table.
COMMON_PROTECTED=((0,974),(1054,1523),(1990,2634),(2989,3114),
                  (4570,5744),(6354,6731),(8282,8307))

def inventory(common,battle,current_common,current_battle,trainer_indices):
    result=[];counts={};protected_trainers={(x['version'],x['index']) for x in trainer_indices}
    translated={}
    for name,version,rid,source,current in (
        ('mes_common.fsys',1,0x27C10000,common,current_common),
        ('menu_fight_s.fsys',2,RESOURCE,battle,current_battle)):
        before=read_messages(dict(read_archive(source))[rid])[1]
        after=read_messages(dict(read_archive(current))[rid])[1]
        assert len(before)==len(after)
        for a,b in zip(before,after):
            if a!=b:translated.setdefault(re.sub(r'\s+',' ',TOKEN.sub('',readable(a))).strip(),readable(b))
        candidates=[]
        for i,(a,b) in enumerate(zip(before,after)):
            if a!=b or (version,i) in protected_trainers:continue
            if version==1 and any(lo<=i<hi for lo,hi in COMMON_PROTECTED):continue
            text=readable(a);body=TOKEN.sub('',text).strip()
            if not re.search('[A-Za-z]',body):continue
            if re.fullmatch(r'[A-Z0-9 #_.-]{1,3}',body):continue
            if re.search(r'\b[Dd]ummy\b|#PBLOCK|ZXQ',body):continue
            if not re.match(r'^(?:\{F[0-9A-F]{3}\})+',text):continue
            # Sentences first, followed by real UI labels and geographic text.
            priority=0 if len(body.split())>=4 else 1
            candidates.append({'archive':name,'resource':hex(rid),'id':i,
                               'source':text,'source_sha256':sha(a),
                               'priority':priority,'status':'awaiting-translation-and-review'})
        counts[name]=len(candidates);result.extend(candidates)
    result.sort(key=lambda e:(e['priority'],e['archive']!='menu_fight_s.fsys',e['id']))
    assert len(result)>=5000,counts
    return {'requested_new_messages':5000,'candidate_count':len(result),
            'candidates_by_archive':counts,'original_common_sha256':sha(common),
            'original_battle_sha256':sha(battle),'publication_allowed':False,
            'entries':result}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('common','battle','current-common','current-battle','trainers','output'):
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    q=inventory(a.common.read_bytes(),a.battle.read_bytes(),a.current_common.read_bytes(),
                a.current_battle.read_bytes(),json.loads(a.trainers.read_text()))
    a.output.write_text(json.dumps(q,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in q.items() if k!='entries'},indent=2))
