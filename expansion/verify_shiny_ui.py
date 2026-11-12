"""Check native-font measurements and status annotation without a GPU render.

Native PK4 setter/getter, shiny appearance predicate, message lookup, font
metrics and mod UI/bonus code execute. Only allocation/free and final queued
text draw are fixtures. Live layouts and screenshots still need Dolphin.
"""
import argparse,json,struct
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn import ppc_const as ppc
from verify_coop_draft import DraftReplay
from prepare_campaign_doubles import sha
from tournament_shiny import UI_BRIDGES

PARTY=0x81D10000;VALUE=0x81D20000;UI=0x81E10000
OFFSETS=(0x90,0x92,0x94,0x98,0x9A,0x96)

def verify(capture,dol,manifest):
    h=DraftReplay(capture,dol);symbols=manifest['symbols'];calls=[]
    def hook(u,a,size,data):
        if a==0x801728E4:
            assert u.reg_read(ppc.UC_PPC_REG_4)==44;ret=0x81C00000
        elif a==0x80172A14:ret=0
        else:
            calls.append([u.reg_read(getattr(ppc,f'UC_PPC_REG_{i}')) for i in range(3,9)]);ret=1
        u.reg_write(ppc.UC_PPC_REG_3,ret);u.reg_write(ppc.UC_PPC_REG_PC,u.reg_read(ppc.UC_PPC_REG_LR))
    for a in (0x801728E4,0x80172A14,0x80254C6C):h.uc.hook_add(UC_HOOK_CODE,hook,begin=a,end=a)
    h.call(0x803DFD78,(h.session+0x648,PARTY),limit=3000000)
    h.put(0x80625860,UI);h.put(UI+0x80,PARTY)
    pid=h.call(0x803DE52C,(PARTY,0,0));ot=h.call(0x803DE52C,(PARTY,7,0))
    def set_ot(wanted):
        sid=(ot^pid^(pid>>16))&65535
        target=(ot&65535)|((sid if wanted else sid^0x8000)<<16)
        h.put(VALUE,target);h.call(0x803DEB54,(PARTY,7,VALUE))
        assert h.call(0x803DF700,(PARTY,))==wanted
    cases=[];bonus_cases=0
    def decode(at):
        out=[]
        for i in range(32):
            c=int.from_bytes(h.uc.mem_read(at+2*i,2),'big')
            if c==0xffff and i>=4:break
            if i>=4:out.append(chr(c))
        return ''.join(out)
    for shiny in (False,True):
        set_ot(int(shiny))
        for winner in range(6):
            for i,off in enumerate(OFFSETS):h.uc.mem_write(PARTY+off,struct.pack('>H',100 if i==winner else 90))
            h.put(VALUE,100 if winner==0 else 90)
            snapshot=bytes(h.uc.mem_read(PARTY,136))
            h.call(symbols['shiny_bonus'],(PARTY,VALUE));h.abi()
            actual=[int.from_bytes(h.uc.mem_read(PARTY+off,2),'big') for off in OFFSETS]
            wanted=[100 if i==winner else 90 for i in range(6)]
            if shiny:wanted[winner]=110
            assert actual==wanted,(shiny,winner,actual,wanted)
            assert bytes(h.uc.mem_read(PARTY,136))==snapshot
            assert h.get(VALUE)==(110 if shiny and winner==0 else (100 if winner==0 else 90))
            bonus_cases+=1
            for width,height in ((320,30),(78,30),(73,30),(30,30),(320,15)):
                for field in range(6):
                    h.uc.mem_write(PARTY+0x8E,struct.pack('>H',actual[0]))
                    before=bytes(h.uc.mem_read(PARTY,0xA4));msg=0xEA1 if not field else 0xEAE
                    args=(msg,480,200,width,height,0xFFFFFFFF)
                    h.call(UI_BRIDGES+8*field,args,limit=3000000);h.abi();call=calls[-1]
                    assert call[1:]==list(args[1:]),'Original bounds/color changed'
                    assert bytes(h.uc.mem_read(PARTY,0xA4))==before
                    annotation=call[0]>=0x7FFF0000
                    if annotation:
                        assert shiny and field==winner
                        at=h.call(0x8024FB34,(0x8048062C,call[0]));text=decode(at)
                        wh=h.call(0x8024FBBC,(0x8048062C,call[0],1,0),limit=3000000)
                        assert wh&65535<=width and wh>>16<=height
                        assert text in (('110/100 (+10)','110/100(+10)') if not field else ('100 (+10)','100(+10)')),(field,text)
                    else:
                        assert call[0]==msg
                        if shiny and field==winner and width==320 and height==30:raise AssertionError('Wide row omitted bonus')
                    cases.append({'shiny':shiny,'highest_stat':winner,'displayed_stat':field,'width':width,'height':height,'annotation':annotation})
    # Original message lookup must stay unchanged for normal IDs.
    stock=h.call(0x8024FB34,(0x8048062C,0xEAE))
    assert bytes(h.uc.mem_read(stock,8))==bytes.fromhex('fffff001fffff101')
    return {'status':'passed-native-status-text-and-font-metrics','bonus_winner_cases':bonus_cases,
            'display_cases':len(cases),'annotated_cases':sum(x['annotation'] for x in cases),
            'original_font_color_and_bounds_preserved':True,'font_never_shrunk':True,
            'compact_space_fallback':True,'narrow_or_short_bounds_keep_original_effective_value':True,
            'no_pokemon_mutation_by_ui':True,'dol_sha256':sha(dol),
            'stubs':['Scratch allocation/free','Final text draw (record arguments, no GPU)'],
            'limits':['Synthetic width/height cases; live resource layouts not loaded',
                      'Visual appearance outside/inside battle still needs Dolphin screenshots'],
            'dolphin_tested':False}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('capture','dol','payload','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=verify(a.capture,a.dol.read_bytes(),json.loads(a.payload.read_text()))
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
