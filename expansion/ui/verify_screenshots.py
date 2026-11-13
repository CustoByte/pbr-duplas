"""Validate the screenshot intake against native text metrics and field guards."""
import argparse,json,re
from pathlib import Path
from prepare_campaign_doubles import read_archive,sha
from translation.messages import read_messages,readable,TOKEN
from ui.apply_screenshot_review import validate
from ui.layout_text import preserve_alignment_breaks
from ui.font_ptbr import blocks,records
from ui.native_text import Metrics

def verify(capture,dol,original,baseline,candidate,plan):
    rid=0x27C10000;extract=lambda d:read_messages(dict(read_archive(d))[rid])[1]
    a,b,c=map(extract,(original,baseline,candidate));assert len(a)==len(b)==len(c)==9995
    entries=dict(read_archive(candidate));font=entries[0x27C00000]
    m=Metrics(capture,dol,font);m.verify_tildes();cases=[]
    budgets={6872:130,9218:160,7085:180,7649:112,7650:112,7651:112,7652:112,
             7653:112,7654:112,7655:112,7656:112,7661:112,7664:220,7665:100,
             7671:100,7673:220,7826:100,8055:100,9915:160,9916:150,9920:100,
             9924:160,9925:160,3178:220,3179:220,3180:220,3181:220,9433:380,8442:380}
    budgets.update({i:125 for i in range(3237,3255)});budgets.update({i:220 for i in range(8282,8307)})
    for i,budget in budgets.items():
        text=readable(c[i]);w,h=m(text)
        assert w<=budget,(i,w,budget,text)
        cases.append({'id':i,'width':w,'height':h,'review_budget':budget})
    protected_ranges=[(10,974),(1382,1482),(1991,2634),(2990,3114),(4760,5704),(6354,6731)]
    for lo,hi in protected_ranges:assert b[lo:hi]==c[lo:hi],(lo,hi)
    for i in range(8282,8307):
        original_name=TOKEN.sub('',readable(a[i])).split()[0]
        assert TOKEN.sub('',readable(c[i]))=='Natureza '+original_name+'.'
    fonts=[set(records(p)) for p in blocks(font)]
    changed=[]
    for i,(old,new) in enumerate(zip(b,c)):
        if old==new:continue
        target=readable(new);validate(a[i],target,i,plan)
        if str(i) not in plan.get('authorized_added_controls',{}):
            assert preserve_alignment_breaks(readable(a[i]),target)==target,('Lost line anchor',i)
        prefix=re.search(r'\{F00([0-9])\}',target);index=int(prefix[1]) if prefix else 1
        introduced=set(TOKEN.sub('',target))-set(TOKEN.sub('',readable(old)))
        assert all(ch.isspace() or ord(ch) in fonts[index] for ch in introduced),(i,introduced-fonts[index])
        changed.append(i)
    expected={3238:'LUTADOR',3239:'VOADOR',3241:'TERRESTRE',3242:'PEDRA',3243:'INSETO',3245:'AÇO',3252:'GELO',3253:'DRAGÃO',3254:'SOMBRIO'}
    for i,label in expected.items():assert TOKEN.sub('',readable(c[i]))==label
    date=readable(c[8307]);assert '{0061} {0060} {005F}\n{0062}\n' in date
    assert '{0003:0002}' not in readable(c[8442]) and 'Não há' in readable(c[8442])
    assert re.search(r'\} +Não há',readable(c[8442]))
    assert 'é plantada' in readable(c[3328]) and 'usuário' in readable(c[3328])
    assert 'piscar' not in readable(c[3178]) and '1/3' in readable(c[3178])
    return {'status':'passed-source-fields-glyphs-and-native-metric-budgets','changed_ids':changed,
            'changed_count':len(changed),'native_cases':cases,'candidate_sha256':sha(candidate),
            'protected_name_ranges_unchanged':True,'all_25_nature_names_preserved':True,
            'other_common_resources_unchanged':all(v==entries[k] for k,v in dict(read_archive(baseline)).items() if k!=rid),
            'dolphin_visual_tested':False,'limits':['Review budgets are conservative checks, not a live render of the reported frames.','The requested Storage caption uses source-bounded spacing; actual position needs Dolphin.']}
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('capture','dol','original','baseline','candidate','plan','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=verify(a.capture,a.dol.read_bytes(),a.original.read_bytes(),a.baseline.read_bytes(),a.candidate.read_bytes(),json.loads(a.plan.read_text()));a.output.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print('Verified changed message IDs:',r['changed_count'])
