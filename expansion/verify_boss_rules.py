"""Run native fixed/variable CPU dispatch plus the boss roster rules.

Only archive lookup and allocation/free are fixtures. Original trainers,
selection, PK4 construction, setters/getters and mod boss rules execute.
"""
import argparse,json,struct,collections
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn import ppc_const as ppc
from verify_coop_draft import DraftReplay
from prepare_campaign_doubles import read_archive,word,sha
BASE=0x81800000;SESSION=0x81A00000;CTX=0x81B00000;PARTY=CTX+0x5000;TRAINER=CTX+0x6000;DEST=0x81D10000;ALT=0x81D30000;TEMP=0x81D60000

def verify(capture,dol,deck,common):
    resources=dict(read_archive(deck));rules=read_archive(common)[11][1];stats=read_archive(common)[8][1]
    h=DraftReplay(capture,dol);heap=[0x81C00000];before=[None];count=[0]
    def hook(u,a,size,data):
        if a==0x8017F474:
            party=u.reg_read(ppc.UC_PPC_REG_30)
            before[0]=[bytes(u.mem_read(int.from_bytes(u.mem_read(party+0x48+i*4,4),'big'),140)) for i in range(6)]
            return
        if a==0x801E00FC:
            key=u.reg_read(ppc.UC_PPC_REG_4);payload=resources[key];u.mem_write(BASE,payload);result=BASE
        elif a in (0x801728E4,0x801DF6B4):
            n=u.reg_read(ppc.UC_PPC_REG_4 if a==0x801728E4 else ppc.UC_PPC_REG_3)
            assert 0<n<65536;result=heap[0];heap[0]+=(n+31)&~31;assert heap[0]<0x81CF0000
        else:result=0
        u.reg_write(ppc.UC_PPC_REG_3,result);u.reg_write(ppc.UC_PPC_REG_PC,u.reg_read(ppc.UC_PPC_REG_LR))
    for a in (0x801E00FC,0x801728E4,0x801DF6B4,0x80172A14,0x801DF6FC,0x8017F474):h.uc.hook_add(UC_HOOK_CODE,hook,begin=a,end=a)
    rng=h.call(0x802283B8);results=[]
    def run(record,rank,boss=True,kind=1,seed=1):
        h.uc.mem_write(CTX,bytes(0x10000));h.uc.mem_write(SESSION,bytes(0x10000));heap[0]=0x81C00000
        h.call(0x8017C72C,(CTX,))
        for off,value in ((8,1),(0xC,1),(0x10,rank),(0x14,kind),(0x60,TRAINER),(0x6C,5 if kind==6 else 50),(0x7C,record)):
            h.put(CTX+off,value)
        h.uc.mem_write(CTX,bytes([int(boss)]));h.uc.mem_write(CTX+0x71,bytes([int(24<=record<=26)]))
        h.put(PARTY+0xC,1);h.put(PARTY+0x28,0x13572468)
        for i in range(6):
            h.put(PARTY+0x48+4*i,DEST+0x200*i);h.put(PARTY+0x30+4*i,ALT+0x200*i)
        at=48+record*92+(0 if boss else 16);trainer_key=word(rules,at+4);index=rules[at+3]
        row=resources[trainer_key][16+index*152:16+(index+1)*152]
        assert len(row)==152
        h.uc.mem_write(TRAINER,row);h.put(TRAINER+0xC,seed);h.put(rng,seed)
        assert h.call(0x8017F20C,(CTX,record,TRAINER,PARTY,SESSION),limit=20000000)==1
        h.abi();original=[];after=[];mew=[]
        for i,payload in enumerate(before[0]):
            h.uc.mem_write(TEMP,payload)
            original.append(h.call(0x803DE52C,(TEMP,5,0)) if payload[138]&128 else 0)
            mon=DEST+0x200*i
            after.append(h.call(0x803DE52C,(mon,5,0)) if h.uc.mem_read(mon+138,1)[0]&128 else 0)
            if after[-1]==150:
                moves=[h.call(0x803DE52C,(mon,f,0)) for f in range(0x36,0x3a)]
                pid=h.call(0x803DE52C,(mon,0,0));ot=h.call(0x803DE52C,(mon,7,0))
                mew.append({'moves':moves,'shiny':((pid^(pid>>16)^ot^(ot>>16))&65535)<8,'nature':pid%25})
        assert all(n<=max(collections.Counter(original)[s],1) for s,n in collections.Counter(after).items() if s),(record,rank,'introduced duplicate',original,after)
        effective=record-31 if 31<=record<=38 else rank
        if record<=4 and effective<7:assert 150 not in after,(record,rank,after)
        if kind==6:assert after==original,(record,'Little Battle changed')
        elif boss and effective>=5:
            if effective>=7:
                assert mew and all(x['shiny'] and x['nature']==10 for x in mew),(record,rank,after,mew)
                if record>4:assert mew[0]['moves']==[94,396,58,182]
            candidates=[i for i,s in enumerate(original) if s and not (effective>=7 and s==150)]
            weakest=min(candidates,key=lambda i:sum(stats[48+original[i]*52+30:48+original[i]*52+36]))
            legends={x['species'] for x in json.loads(Path(__file__).with_name('boss_sets.json').read_text())['legendary_sets']}
            assert after[weakest] in legends,(record,rank,weakest,original,after)
            assert after[weakest]!=original[weakest] or original[weakest] in legends
        elif not (record<=4 and 150 in original):assert after==original,(record,rank,original,after)
        r={'record':record,'rank':effective+1,'boss':boss,'little':kind==6,'before':original,'after':after,'mewtwo':mew}
        results.append(r);return r
    for record in (2,6,9,12,15,18,20,22,25,28,30):
        for rank in range(8):run(record,rank,kind=6 if record==20 else 1,seed=1+record*1009+rank*7919)
        print('verified record',record,flush=True)
    for record in range(31,39):run(record,0,kind=2,seed=record*7919)
    for rank in range(8):run(2,rank,boss=False,seed=rank*7919+123)
    # Targeted native Mewtwo path: rank gate, varied coverage and existing ace.
    manifest=json.loads(Path(__file__).with_name('shiny-payload.json').read_text())
    roster=manifest['symbols']['tournament_roster'];pool=resources[0x1DFA2800]
    def inject_mewtwo(slot=0,alternate=False):
        h.uc.mem_write(BASE,pool)
        index=next(i for i in range(word(pool,8)-1,-1,-1) if int.from_bytes(pool[16+i*56+6:16+i*56+8],'big')==150)
        mon=(ALT if alternate else DEST)+slot*0x200
        h.call(0x8017D750,(CTX,mon,BASE+16+index*56,PARTY,255),limit=3000000)
        return mon,BASE+16+index*56
    run(2,7,boss=False,seed=9981)
    mon,row=inject_mewtwo();variations=[]
    for rank in range(7):assert h.call(0x8017C564,(CTX,row,rank))==0
    assert h.call(0x8017C564,(CTX,row,7))==1
    for _ in range(32):
        h.call(roster,(CTX,PARTY),limit=3000000);h.abi()
        moves=tuple(h.call(0x803DE52C,(mon,f,0)) for f in range(0x36,0x3A))
        assert moves[0]==94 and moves[3]==182 and len(set(moves))==4
        assert set(moves[1:3])<={396,58,85,53,247,447}
        if variations:assert set(moves)!=set(variations[-1])
        variations.append(moves)
    assert len(set(variations))>=8
    run(9,7,boss=False,seed=7711);mon,_=inject_mewtwo();h.uc.mem_write(CTX,b'\1')
    h.call(roster,(CTX,PARTY),limit=3000000);h.abi()
    ids=[h.call(0x803DE52C,(DEST+i*0x200,5,0)) for i in range(6)]
    assert ids.count(150)==1 and len(set(ids))==6
    pid=h.call(0x803DE52C,(mon,0,0));ot=h.call(0x803DE52C,(mon,7,0))
    assert pid%25==10 and ((pid^(pid>>16)^ot^(ot>>16))&65535)<8
    assert [h.call(0x803DE52C,(mon,f,0)) for f in range(0x36,0x3A)]==[94,396,58,182]
    assert h.call(0x803DE52C,(mon,6,0))==270
    assert [h.call(0x803DE52C,(mon,f,0)) for f in range(0xD,0x13)]==[4,0,0,252,252,0]
    # Sunset: no duplicate Mewtwo when it was already in the reserve board.
    run(25,7,boss=False,seed=4321);inject_mewtwo(alternate=True);h.uc.mem_write(CTX,b'\1')
    h.call(roster,(CTX,PARTY),limit=3000000);h.abi()
    main=[h.call(0x803DE52C,(DEST+i*0x200,5,0)) for i in range(6)]
    alt=[h.call(0x803DE52C,(ALT+i*0x200,5,0)) for i in range(6)]
    assert main.count(150)==1 and 150 not in alt,(main,alt)
    return {'status':'passed-native-cpu-dispatch-and-boss-rules','dispatch_cases':len(results),'mewtwo_rank_gate_cases':8,'consecutive_mewtwo_sets_checked':32,'distinct_mewtwo_sets':len(set(variations)),
            'existing_mewtwo_and_sunset_reserve_cases':2,'results':results,
            'dol_sha256':sha(dol),'deck_sha256':sha(deck),
            'stubs':['Archive pointer lookup','Scratch allocation/free'],
            'limits':['Explicit rank, boss flag, trainer-index and RNG fixtures','No live battle, Trade UI or save/load'],
            'dolphin_tested':False}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('capture','dol','deck','common','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=verify(a.capture,a.dol.read_bytes(),a.deck.read_bytes(),a.common.read_bytes())
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='results'},indent=2))
