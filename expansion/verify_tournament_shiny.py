"""Native verification of shiny rolls, identity, real PK4 and real stat recalculation.

Only heap allocation/free are fixtures for constructor/stat tests. No Pokemon
getter/setter, PID conversion, shiny predicate or stat calculation is stubbed.
No real Dolphin rendering, battle turn, trade eligibility or NAND save/load.
"""
import argparse,json,struct
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn import ppc_const as ppc
from prepare_campaign_doubles import sha
from verify_coop_draft import DraftReplay
from verify_sets import verify as construct

SRC=0x81D20000;PARTY=0x81D21000;TEMP=0x81D22000

def threshold(record,rank):
    if 31<=record<=38:rank=record-31
    maxrank=6 if record==29 else 7
    return 300+200*min(rank,maxrank)//maxrank

def draw(seed):
    while True:
        seed=(seed*214013+2531011)&0xffffffff
        value=seed>>16
        if value<60000:return value%10000,seed

def raw(pid,ot):return ((pid^(pid>>16)^ot^(ot>>16))&65535)<8

def letter(pid):return (((pid&0x3000000)>>18)|((pid&0x30000)>>12)|((pid&0x300)>>6)|(pid&3))%28

def verify(capture,base_dol,dol,deck,policy,manifest):
    symbols=manifest['symbols'];h=DraftReplay(capture,dol)
    # All normal ranks and each Masters set / Survival native tier.
    rates=[]
    for record in range(39):
        values=[]
        for rank in range(8):
            actual=h.call(symbols['shiny_threshold'],(record,rank));h.abi()
            assert actual==threshold(record,rank),(record,rank,actual)
            values.append(actual)
        rates.append(values)
    # Exact native RNG state transition, including rejection of biased tail.
    rng=h.call(0x802283B8);ctx=0x81B00000;rejections=0
    for private in (0,1):
        h.put(ctx+0xC,private)
        for seed in range(0,1000000,7919):
            address=ctx+0xA0 if private else rng
            h.put(address,seed);expected,state=draw(seed)
            if ((seed*214013+2531011)&0xffffffff)>>16>=60000:rejections+=1
            assert h.call(symbols['shiny_draw'],(ctx,))==expected
            assert h.get(address)==state;h.abi()
    # Snapshot a generated PK4 just before the real hook; no instruction skipped.
    snapshots=[];observed_shiny=0;sid_updates=0;stats=0;faint_checks=0
    old=DraftReplay(capture,base_dol);old_heap=[0x81C00000]
    def alloc(u,a,size,data):
        if a==0x801728E4:
            n=u.reg_read(ppc.UC_PPC_REG_4);assert n==44,n
            ret=old_heap[0];old_heap[0]+=(n+31)&~31
        else:ret=0
        u.reg_write(ppc.UC_PPC_REG_3,ret);u.reg_write(ppc.UC_PPC_REG_PC,u.reg_read(ppc.UC_PPC_REG_LR))
    for a in (0x801728E4,0x80172A14):old.uc.hook_add(UC_HOOK_CODE,alloc,begin=a,end=a)
    record=[None];installed=[False]
    def observer(machine,mon,species):
        nonlocal observed_shiny,sid_updates,stats,faint_checks
        prior=record[0];assert prior is not None
        before,expected,state=prior
        machine.uc.mem_write(TEMP,before)
        get=lambda pointer,field:machine.call(0x803DE52C,(pointer,field,0))
        pid0=get(TEMP,0);ot0=get(TEMP,7);pid=get(mon,0);ot=get(mon,7)
        assert raw(pid,ot)==expected,(species,hex(pid0),hex(ot0),hex(pid),hex(ot),expected,hex(state))
        assert pid==pid0 # Exact PID, shuffle, nature, gender and appearance retained.
        if species==201:assert letter(pid)==letter(pid0)
        if ot!=ot0:
            assert ot&65535==ot0&65535;sid_updates+=1
        for field in (5,6,0xA,0x70,*range(0xD,0x13),*range(0x36,0x46),*range(0x46,0x4C)):
            assert get(mon,field)==get(TEMP,field),(species,field)
        assert machine.get(0x81B00000+0xA0)==state
        observed_shiny+=expected
        payload=bytes(machine.uc.mem_read(mon,136))
        for m in (machine,old):
            m.uc.mem_write(SRC,payload);m.uc.mem_write(PARTY,bytes(0xA4))
        old_heap[0]=0x81C00000
        old.call(0x803DFD78,(SRC,PARTY),limit=3000000)
        machine.call(0x803DFD78,(SRC,PARTY),limit=3000000);machine.abi()
        fields=(0xA3,0xA4,0xA5,0xA7,0xA8,0xA6)
        values=lambda m:[m.call(0x803E100C,(PARTY,f,0)) for f in fields]
        normal=values(old);actual=values(machine);wanted=normal[:]
        if machine.call(0x803DF700,(SRC,)):
            winner=max(range(6),key=lambda n:normal[n]);wanted[winner]=normal[winner]*110//100
        assert actual==wanted,(species,normal,actual,wanted)
        for _ in range(2):
            machine.call(0x803DDEA8,(PARTY,),limit=3000000)
            assert values(machine)==wanted,(species,'bonus accumulated')
        assert machine.call(0x803E100C,(PARTY,0xA2,0))==wanted[0]
        if expected:
            machine.put(TEMP,0);machine.call(0x803DEB54,(PARTY,0xA2,TEMP))
            machine.call(0x803DDEA8,(PARTY,),limit=3000000)
            assert machine.call(0x803E100C,(PARTY,0xA2,0))==0
            faint_checks+=1
        stats+=1
    # The constructor fixture normally starts with ctx.C=0. Set a private RNG
    # in a narrow observation hook at function entry to make each case explicit.
    def capture_hook(u,a,size,data):
        if a==0x8017D750:
            ctx=u.reg_read(ppc.UC_PPC_REG_3)
            species_address=u.reg_read(ppc.UC_PPC_REG_5)+6
            species=int.from_bytes(u.mem_read(species_address,2),'big')
            u.mem_write(ctx+0xC,struct.pack('>I',1))
            u.mem_write(ctx+0xA0,struct.pack('>I',species*7919))
        else:
            ctx=u.reg_read(ppc.UC_PPC_REG_24);mon=u.reg_read(ppc.UC_PPC_REG_25)
            seed=int.from_bytes(u.mem_read(ctx+0xA0,4),'big');rank=int.from_bytes(u.mem_read(ctx+0x10,4),'big')
            col=int.from_bytes(u.mem_read(ctx+0x7C,4),'big');roll,state=draw(seed)
            record[0]=(bytes(u.mem_read(mon,136)),roll<threshold(col,rank),state)
    # verify_sets builds its own emulator; install the observer before the first
    # constructor through an explicit harness factory rather than replacing code.
    import verify_sets
    OriginalReplay=verify_sets.DraftReplay
    def factory(*args):
        machine=OriginalReplay(*args)
        for a in (0x8017D750,0x8017E218):machine.uc.hook_add(UC_HOOK_CODE,capture_hook,begin=a,end=a)
        return machine
    verify_sets.DraftReplay=factory
    try:construction=construct(capture,dol,deck,policy,constructed=observer)
    finally:verify_sets.DraftReplay=OriginalReplay
    return {'status':'passed-native-shiny-and-stat-construction','threshold_contexts':312,
            'rng_transition_cases':254,'tail_rejection_cases':rejections,'generated_species':493,
            'observed_shiny':observed_shiny,'secret_id_updates':sid_updates,
            'native_stat_comparisons':stats,'repeat_recalculations':stats*2,'no_resurrection_checks':faint_checks,
            'dol_sha256':sha(dol),'deck_sha256':sha(deck),'chance_basis_points_by_rank':rates[2],
            'limits':['Explicit generator rank/RNG context fixtures','Heap allocation/free are scratch fixtures',
                      'No real battle damage, model render, Trade UI eligibility or NAND save/load'],
            'dolphin_tested':False,'trade_save_tested':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('capture','base-dol','dol','deck','policy','payload','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=verify(a.capture,a.base_dol.read_bytes(),a.dol.read_bytes(),a.deck.read_bytes(),json.loads(a.policy.read_text()),json.loads(a.payload.read_text()))
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
