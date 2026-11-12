"""Run complete native trainer-pool generation (8017ec70) and PK4 creation.

Original trainer records and common-table deck resolution execute natively.
Resource lookup returns the locally expanded DCKP, allocation/free use scratch
memory. Rank/format/level/RNG contexts are fixtures. No combat/trade/save UI.
"""
import argparse,json
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn import ppc_const as ppc
from prepare_campaign_doubles import read_archive,word,sha
from verify_coop_draft import DraftReplay

BASE=0x81800000;CTX=0x81B00000;PARTY=CTX+0x5000;TRAINER=CTX+0x6000;DEST=0x81D10000

def verify(capture,dol,original_deck,expanded_deck,reference=None):
    original=dict(read_archive(original_deck));expanded=dict(read_archive(expanded_deck))
    h=DraftReplay(capture,dol);heap=[0x81C00000];resource=[None];alloc=[]
    def hook(u,a,size,data):
        if a==0x801E00FC:
            key=u.reg_read(ppc.UC_PPC_REG_4);assert key==resource[0],hex(key);ret=BASE
        elif a in (0x801728E4,0x801DF6B4):
            n=u.reg_read(ppc.UC_PPC_REG_4 if a==0x801728E4 else ppc.UC_PPC_REG_3)
            assert 0<n<65536
            ret=heap[0];heap[0]+=(n+31)&~31;assert heap[0]<0x81CF0000;alloc.append(n)
        else:ret=0
        u.reg_write(ppc.UC_PPC_REG_3,ret);u.reg_write(ppc.UC_PPC_REG_PC,u.reg_read(ppc.UC_PPC_REG_LR))
    for a in (0x801E00FC,0x801728E4,0x801DF6B4,0x80172A14,0x801DF6FC):h.uc.hook_add(UC_HOOK_CODE,hook,begin=a,end=a)
    results=[];rng=h.call(0x802283B8)
    for record,deck_key,trainer_key in ((2,0x1DFA2800,0x1DDB2A00),(9,0x1DF52800,0x1DDF2A00)):
        pool=expanded[deck_key];trainers=original[trainer_key];resource[0]=deck_key
        h.uc.mem_write(BASE,pool);h.uc.mem_write(CTX,bytes(0x10000));heap[0]=0x81C00000
        h.call(0x8017C72C,(CTX,));heap_base=heap[0]
        for off,val in ((8,1),(0xC,1),(0x14,1),(0x10,7),(0x6C,50),(0x60,TRAINER),(0x7C,record)):
            h.put(CTX+off,val)
        h.put(PARTY+0x28,0x13572468)
        for i in range(6):h.put(PARTY+0x48+4*i,DEST+0x200*i)
        seen=set();witness={};built=0
        attempts=range(1,2401) if reference is None else sorted({v['attempt'] for x in reference['results'] if x['colosseum_record']==record for v in x['first_native_generation_witness'].values()})
        generated=0
        for attempt in attempts:
            trainer_index=(attempt-1)%word(trainers,8)
            row=trainers[16+trainer_index*152:16+(trainer_index+1)*152]
            h.uc.mem_write(TRAINER,row);h.put(rng,attempt*7919);h.put(CTX+0xA0,attempt*7919)
            heap[0]=heap_base
            assert h.call(0x8017EC70,(CTX,record,TRAINER+0x64,PARTY),limit=10000000)==1
            ids=[]
            for i in range(6):
                mon=DEST+0x200*i;s=h.call(0x803DE52C,(mon,5,0));ids.append(s)
                assert 1<=s<=493
                exp=h.call(0x803DE52C,(mon,8,0));assert exp==h.call(0x803DF14C,(s,50))
                moves=[h.call(0x803DE52C,(mon,f,0)) for f in range(0x36,0x3A)]
                assert all(0<=m<=467 for m in moves) and any(moves)
                if s not in seen:witness[s]={'attempt':attempt,'trainer_record':trainer_index}
                seen.add(s)
            assert len(set(ids))==6,(record,trainer_index,ids)
            built+=6;generated+=1
            if len(seen)==493:break
            if attempt%400==0:print(f'record {record}: {attempt} teams / {len(seen)} species',flush=True)
        assert seen==set(range(1,494)),(record,sorted(set(range(1,494))-seen))
        results.append({'colosseum_record':record,'pokemon_deck':f'{deck_key:08x}',
                        'trainer_deck':f'{trainer_key:08x}','teams_generated':generated,'native_pokemon_built':built,
                        'species_reached':len(seen),'first_native_generation_witness':witness})
        print(f'record {record}: all 493 species generated as native PK4',flush=True)
    return {'status':'passed-native-trainer-generation-fixtures','native_trainer_generator':'8017ec70',
            'native_pokemon_constructor':'8017d750','pool_and_pk4_selection_stubs':[],
            'resource_and_allocation_stubs':['801e00fc expanded DCKP pointer','801728e4/801df6b4 allocation','80172a14/801df6fc free'],
            'results':results,'dol_sha256':sha(dol),'deck_sha256':sha(expanded_deck),
            'limits':['Explicit rank 8 / level 50 / native Level 30 Open / format and RNG seed fixtures','Trainer index selected from original DCKT records by harness',
                      'No real opponent UI/AI/damage/render, Trade eligibility or save/load'],
            'dolphin_tested':False,'trade_save_tested':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('capture','dol','original-deck','expanded-deck','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--witness-report',type=Path)
    a=p.parse_args();r=verify(a.capture,a.dol.read_bytes(),a.original_deck.read_bytes(),a.expanded_deck.read_bytes(),json.loads(a.witness_report.read_text()) if a.witness_report else None)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='results'},indent=2))
