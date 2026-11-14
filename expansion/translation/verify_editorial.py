"""Check an editorial subset against real message controls and native metrics."""
import argparse,json,re
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn import ppc_const as ppc
from verify_coop_draft import DraftReplay
from prepare_campaign_doubles import read_archive
from translation.messages import RESOURCE,read_messages,readable,validate_target,encoded

def verify(capture,dol,battle,review,common=False):
    rows=read_messages(dict(read_archive(battle))[0x27C10000 if common else RESOURCE])[1]
    h=DraftReplay(capture,dol);pointer=0x81AC0000;gid=0x70000001
    def lookup(u,address,size,data):
        if u.reg_read(ppc.UC_PPC_REG_4)==gid:
            u.reg_write(ppc.UC_PPC_REG_3,pointer)
            u.reg_write(ppc.UC_PPC_REG_PC,u.reg_read(ppc.UC_PPC_REG_LR))
    h.uc.hook_add(UC_HOOK_CODE,lookup,begin=0x8024FB34,end=0x8024FB34)
    failures=[];cases=[]
    targets=review['targets_by_id'] if common else review['battle_targets_by_id']
    for index,body in targets.items():
        index=int(index);source=readable(rows[index])
        prefix=re.match(r'^(?:\{F[0-9A-F]{3}\})+',source)[0]
        target=prefix+body
        validate_target(rows[index],target)
        for name in ('Pikachu','WWWWWWWWWWWW'):
            fixture=target
            if common:
                from translation.messages import TOKEN
                fixture=TOKEN.sub(lambda m:m[0] if m[0].startswith('{F') else name if m[0] in ('{0015}','{0021}','{0020}','{000F}') else '',fixture)
            else:
                fixture=fixture.replace('{0015}',name).replace('{0025}',name)
            h.uc.mem_write(pointer,encoded(fixture))
            result=h.call(0x8024FBBC,(0x8048062C,gid,1,0),limit=3000000);h.abi()
            case={'id':index,'width':result&65535,'height':result>>16}
            cases.append(case)
            if common:
                original=TOKEN.sub(lambda m:m[0] if m[0].startswith('{F') else name if m[0] in ('{0015}','{0021}','{0020}','{000F}') else '',source)
                h.uc.mem_write(pointer,encoded(original))
                limit=h.call(0x8024FBBC,(0x8048062C,gid,1,0),limit=3000000);h.abi()
                case['source_width']=limit&65535;case['source_height']=limit>>16
                if 1047<=index<=1053:
                    # These are inserted condition names, not fixed-size
                    # menu labels. Check the same native battle text envelope.
                    case['dynamic_condition_value']=True
                    if case['width']>240 or case['height']>25:failures.append(case)
                elif case['width']>case['source_width'] or case['height']>case['source_height']:failures.append(case)
            elif case['width']>240 or case['height']>50:failures.append(case)
    return {'reviewed_concepts':len(targets),
            'native_font_cases':len(cases),'failures':failures,
            'controls_preserved':True,'dolphin_visual_tested':False,
            'status':'passed-native-editorial-subset' if not failures else 'needs-layout-revision'}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--common',action='store_true')
    for n in ('capture','dol','battle','review','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();report=verify(a.capture,a.dol.read_bytes(),a.battle.read_bytes(),json.loads(a.review.read_text()),common=a.common)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
