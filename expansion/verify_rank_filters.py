"""Execute native rank/level-rule candidate filtering across all expanded pools.

The trainer type context accepts all types so this audits rank, minimum level,
Level 30 Open / Level 50 All / Little flags and list capacity. Full trainer
selection is separately covered by verify_trainers; no battle/trade/save test.
"""
import argparse,json,struct
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn import ppc_const as ppc
from prepare_campaign_doubles import read_archive,word,sha
from verify_coop_draft import DraftReplay
from encounter_expansion import MYTHICAL_LEGENDARY

BASE=0x81800000;CTX=0x81B00000;TRAINER=CTX+0x6000;LIST=CTX+0x7000;ITEMS=0x81D00000

def verify(capture,dol,original_deck,expanded_deck):
    original=dict(read_archive(original_deck));expanded=dict(read_archive(expanded_deck))
    h=DraftReplay(capture,dol);heap=[0x81C00000]
    def alloc(u,a,size,data):
        if a==0x801DF6B4:
            n=u.reg_read(ppc.UC_PPC_REG_3);assert n==8192,n
            result=heap[0];heap[0]+=n;assert heap[0]<=0x81C10000
        else:result=0
        u.reg_write(ppc.UC_PPC_REG_3,result);u.reg_write(ppc.UC_PPC_REG_PC,u.reg_read(ppc.UC_PPC_REG_LR))
    for a in (0x801DF6B4,0x801DF6FC):h.uc.hook_add(UC_HOOK_CODE,alloc,begin=a,end=a)
    h.uc.mem_write(CTX,bytes(0x10000));h.put(CTX+0x60,TRAINER)
    h.uc.mem_write(TRAINER+0x60,b'\xff'*4)
    results=[];maximum=0
    for key,pool in expanded.items():
        if pool==original[key] or pool[:4]!=b'DCKP':continue
        h.uc.mem_write(BASE,pool);old_end=BASE+len(original[key]);cases=[]
        for mode,level in ((1,50),(2,50),(6,5)):
            h.put(CTX+0x14,mode);h.put(CTX+0x6C,level)
            for rank in range(8):
                heap[0]=0x81C00000
                h.uc.mem_write(LIST,struct.pack('>III',2048,0,ITEMS))
                h.call(0x8017E32C,(CTX,rank,BASE+16,BASE+len(pool),LIST),limit=3000000);h.abi()
                count=h.get(LIST+4);assert count<2048,(key,mode,rank,count)
                maximum=max(maximum,count)
                pointers=[h.get(ITEMS+4*i) for i in range(count)]
                assert len(set(pointers))==len(pointers)
                assert all(BASE+16<=p<BASE+len(pool) and (p-BASE-16)%56==0 for p in pointers)
                species={int.from_bytes(h.uc.mem_read(p+6,2),'big') for p in pointers}
                added=[p for p in pointers if p>=old_end]
                new_legend={int.from_bytes(h.uc.mem_read(p+6,2),'big') for p in added}&MYTHICAL_LEGENDARY
                if mode==6:assert not added,(key,rank,'appended species admitted to Little Battle')
                if mode in (1,2) and rank==7:assert species==set(range(1,494)),(key,mode,sorted(set(range(1,494))-species))
                if rank<6:assert not new_legend,(key,mode,rank,new_legend)
                cases.append({'level_rule':mode,'rank':rank+1,'candidates':count,'species':len(species),
                              'appended_candidates':len(added),'appended_legendary_species':len(new_legend)})
        results.append({'deck':f'{key:08x}','cases':cases})
    assert len(results)==6
    for key in (0x20712800,0x20722800):assert expanded[key]==original[key]
    return {'status':'passed-native-rank-and-level-filters','native_filter':'8017e32c',
            'cases':sum(len(x['cases']) for x in results),'maximum_candidates':maximum,
            'all493_at_rank8_in_both_normal_level_rules':True,
            'dedicated_little_pools_unchanged':True,'results':results,
            'dol_sha256':sha(dol),'deck_sha256':sha(expanded_deck),
            'stubs':['Scratch allocation/free only at 801df6b4/801df6fc'],
            'limits':['All-types trainer fixture; full trainer generation tested separately',
                      'No actual tournament dispatch, battle, Trade UI or save/load'],
            'dolphin_tested':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('capture','dol','original-deck','expanded-deck','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=verify(a.capture,a.dol.read_bytes(),a.original_deck.read_bytes(),a.expanded_deck.read_bytes())
    a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:v for k,v in r.items() if k!='results'},indent=2))
