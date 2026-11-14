"""Run the native reserve candidate sampler over expanded pools.

This establishes reachability in 8017e968 under explicit rank/level/exclusion
fixtures. It does not substitute for full trainer dispatch, combat, trade/save.
"""
import argparse,json,struct
from pathlib import Path
from prepare_campaign_doubles import read_archive,word,sha
from verify_coop_draft import DraftReplay

BASE=0x81800000;CTX=0x81B00000;EXCLUDED=CTX+0x1000;DUMMY=CTX+0x2000;OUT=CTX+0x3000;TRAINER=CTX+0x4000

def verify(capture,dol,deck,policy):
    h=DraftReplay(capture,dol);rng=h.call(0x802283B8)
    all_targets=[];native_rows=dict(read_archive(deck));global_seen=set();low_legend=0;teams=0;results=[]
    for key in (0x1DFA2800,0x1DF52800): # Gateway doubles and another shared campaign pool.
        pool=native_rows[key];count=word(pool,8)
        h.uc.mem_write(BASE,pool);h.uc.mem_write(CTX,bytes(0x5000));h.put(CTX+0x10,7);h.put(CTX+0x6C,50);h.put(CTX+0x60,TRAINER)
        h.uc.mem_write(CTX+0xC,b'\1')
        for i in range(6):h.put(EXCLUDED+4*i,DUMMY)
        seen=set();witnesses={};hist={};advanced=0
        for seed in range(1,6001):
            h.put(rng,seed);h.put(TRAINER+12,seed)
            assert h.call(0x8017E968,(CTX,BASE,EXCLUDED,OUT,6,6,count),limit=1000000)==1
            ids=[]
            for slot in range(6):
                pointer=h.get(OUT+4*slot)
                assert BASE+16<=pointer<BASE+len(pool) and (pointer-BASE-16)%56==0
                species=int.from_bytes(h.uc.mem_read(pointer+6,2),'big');assert 1<=species<=493
                ids.append(species);hist[species]=hist.get(species,0)+1
                if species not in seen:witnesses[species]=seed
                seen.add(species)
            assert len(set(ids))==6
            teams+=1;advanced+=1
            if len(seen)==493:break
        results.append({'pool':f'{key:08x}','rank':8,'species_selected':len(seen),'teams_sampled':advanced,
                        'missing_species':sorted(set(range(1,494))-seen),'first_selection_seed':witnesses})
        assert seen==set(range(1,494)),results[-1]['missing_species']
        global_seen|=seen
        # Low-rank native window must not admit any legendary or mythical row.
        from encounter_expansion import MYTHICAL_LEGENDARY
        h.put(CTX+0x10,0)
        for seed in range(1,101):
            h.put(rng,seed);h.put(TRAINER+12,seed)
            assert h.call(0x8017E968,(CTX,BASE,EXCLUDED,OUT,6,6,count),limit=1000000)==1
            ids=[int.from_bytes(h.uc.mem_read(h.get(OUT+4*i)+6,2),'big') for i in range(6)]
            assert not set(ids)&MYTHICAL_LEGENDARY;low_legend+=1;teams+=1
    return {'status':'passed-native-sampler-fixtures','native_sampler':'8017e968','native_rank_filter':'8017c564',
            'actual_species_selected':len(global_seen),'native_team_samples':teams,'low_rank_no_legendary_cases':low_legend,
            'pool_results':results,'dol_sha256':sha(dol),'deck_sha256':sha(deck),'rng_or_sampler_stubs':[],
            'fixtures':['Native rank 7 / level 50','Six empty exclusion records','Explicit RNG seeds',
                        'Sampler context/trainer RNG seed; direct entry, not full trainer dispatch'],
            'limits':['Not a full trainer-generation or Trade Battle path proof','No rendered models, battle, trade eligibility or save/load validation'],
            'dolphin_tested':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('capture','dol','deck','policy','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=verify(a.capture,a.dol.read_bytes(),a.deck.read_bytes(),json.loads(a.policy.read_text()))
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='pool_results'},indent=2))
