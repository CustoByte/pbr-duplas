"""Construct the appended species through native 8017d750 and read PK4 fields.

Only allocation/free are scratch fixtures. No Pokemon constructor, getter,
move resolver, ability resolver, EXP or checksum routine is substituted.
No rendering, real trainer dispatch, trade or save persistence is exercised.
"""
import argparse,json
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn import ppc_const as ppc
from prepare_campaign_doubles import read_archive,word,sha
from verify_coop_draft import DraftReplay


def verify(capture,dol,deck,policy,constructed=None):
    h=DraftReplay(capture,dol);pool=dict(read_archive(deck))[0x1DFA2800]
    base=0x81800000;ctx=0x81B00000;party=ctx+0x5000;trainer=ctx+0x6000;dest=0x81D10000
    h.uc.mem_write(base,pool);h.uc.mem_write(ctx,bytes(0x10000));h.put(ctx+0x10,7);h.put(ctx+0x6C,50)
    h.put(ctx+0x60,trainer);h.put(party+0x28,0x13572468);h.uc.mem_write(party+0xC,b'\1')
    allocation=[0x81C00000];allocations=[]
    def hook(u,a,size,data):
        if a in (0x801728E4,0x801DF6B4):
            n=u.reg_read(ppc.UC_PPC_REG_4 if a==0x801728E4 else ppc.UC_PPC_REG_3)
            assert 0<n<65536
            ret=allocation[0];allocation[0]+=(n+31)&~31;allocations.append(n)
            assert allocation[0]<0x81C10000
        else:ret=0
        u.reg_write(ppc.UC_PPC_REG_3,ret);u.reg_write(ppc.UC_PPC_REG_PC,u.reg_read(ppc.UC_PPC_REG_LR))
    for a in (0x801728E4,0x801DF6B4,0x80172A14,0x801DF6FC):h.uc.hook_add(UC_HOOK_CODE,hook,begin=a,end=a)
    rows={}
    for i in range(word(pool,8)-1,-1,-1):
        row=pool[16+i*56:72+i*56];s=int.from_bytes(row[6:8],'big')
        if s not in rows:rows[s]=base+16+i*56
    results={};fail=[]
    for species in range(1,494):
        allocation[0]=0x81C00000;h.uc.mem_write(dest,bytes(0xA4))
        h.call(0x8017D750,(ctx,dest,rows[species],party,255),limit=3000000);h.abi()
        get=lambda f:h.call(0x803DE52C,(dest,f,0))
        actual=get(5);moves=[get(f) for f in range(0x36,0x3A)];ability=get(0xA)
        exp=get(8);expected=h.call(0x803DF14C,(species,50))
        ivs=[get(f) for f in range(0x46,0x4C)];evs=[get(f) for f in range(0xD,0x13)]
        assert all(0<=v<=31 for v in ivs), (species,ivs)
        assert all(0<=v<=255 for v in evs) and sum(evs)<=510,(species,evs)
        if actual!=species or any(m>467 for m in moves) or not any(moves) or not 1<=ability<=123 or exp!=expected:
            fail.append({'species':species,'actual':actual,'moves':moves,'ability':ability,'exp':exp,'expected_exp':expected})
        results[species]={'moves':moves,'ability':ability,'exp_matches_level_50':exp==expected,'ivs':ivs,'evs':evs}
        if constructed is not None:constructed(h,dest,species)
    assert not fail,fail[:10]
    return {'status':'passed-native-construction','native_constructed_species':493,'native_constructor':'8017d750',
            'native_box_getter':'803de52c','level_50_exp_checks':493,'invalid_constructions':fail,
            'new_species_checks':{str(s):results[s] for s in (251,489,491,492,493)},
            'stubs':['Scratch allocation/free at 801728e4,801df6b4,80172a14,801df6fc'],
            'pokemon_or_move_ability_exp_getter_stubs':[],
            'dol_sha256':sha(dol),'deck_sha256':sha(deck),
            'limits':['No model render, real battle damage, trade eligibility, Rental Pass save/load'],
            'dolphin_tested':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('capture','dol','deck','policy','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=verify(a.capture,a.dol.read_bytes(),a.deck.read_bytes(),json.loads(a.policy.read_text()))
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
