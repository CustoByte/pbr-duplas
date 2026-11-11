"""Execute the shiny wrapper and real PK4 getters in PPC; no getter stubs.

Synthetic fixtures exercise identities, all shuffle variants, ABI, copies,
pass scope and unchanged bytes. Optional private memory replays existing passes.
This does not render Dolphin or persist a save.
"""
import argparse,json,struct
from pathlib import Path
from unicorn import ppc_const as ppc
from verify_native_doubles import Native
from prepare_campaign_doubles import file_offset,read_archive,sha
from prepare_rental_shiny import prepare_shiny
from rental_shiny_asm import assemble,WRAPPER,PASS_BASE_GLOBAL,PASS_STRIDE,POKEMON_OFFSET

BASE=0x80910000
QUERY=0x80980000

class Harness:
    def __init__(self,dol,common):self.n=Native(dol,read_archive(common)[11][1]);self.u=self.n.uc
    def call(self,pc,args=()):
        regs={i:0xABC00000+i for i in range(14,32)}
        regs.update({2:0x806308E0,13:0x8062D600})
        result=self.n.run(pc,args,registers=regs,instruction_limit=100000)
        for i in range(14,32):
            if self.u.reg_read(getattr(ppc,f'UC_PPC_REG_{i}'))!=regs[i]:raise AssertionError(f'ABI register r{i} changed')
        if self.u.reg_read(ppc.UC_PPC_REG_1)!=0x80EF0000:raise AssertionError('Stack not restored')
        return result
    def put(self,a,w):self.u.mem_write(a,struct.pack('>I',w))
    def pokemon(self,a,pid,tid,species=394):
        self.u.mem_write(a,bytes(0x8C));self.put(a,pid)
        block=self.call(0x803E07E8,(a,pid,0))
        self.u.mem_write(block,struct.pack('>HHII',species,0,tid,125000))
        data=bytes(self.u.mem_read(a+8,128));checksum=sum(struct.unpack('>64H',data))&0xFFFF
        self.u.mem_write(a+6,struct.pack('>H',checksum));self.u.mem_write(a+0x8A,b'\x80')
        assert self.call(0x803DE52C,(a,7,0))==tid
        assert self.call(0x803DE52C,(a,5,0))==species
    def shiny(self,a):return self.call(WRAPPER,(a,))

def vanilla(pid,tid):return int(((pid>>16)^(pid&65535)^(tid>>16)^(tid&65535))<8)

def verify(v7,changed,common,diagnostics=None):
    expected,_=prepare_shiny(v7)
    if changed!=expected:
        from monferno_build import prepare_build
        expected,_=prepare_build(expected)
    if changed!=expected:raise AssertionError('Shiny DOL is not reproducible')
    before=Harness(v7,common);after=Harness(changed,common)
    fixtures=0;checks=0
    for base in (BASE,0x90010000):
        for h in (before,after):
            if base>=0x90000000:h.u.mem_map(0x90000000,0x200000)
            h.put(PASS_BASE_GLOBAL,base)
        for shuffle in range(32):
            for h in(before,after):h.u.mem_write(base+37*PASS_STRIDE,bytes(3*PASS_STRIDE))
            for index in range(12):
                pid=0xC3000000|(shuffle<<13)|((index+1)*37)
                tid=0x13572468+index
                assert not vanilla(pid,tid)
                a=base+(37+index//6)*PASS_STRIDE+POKEMON_OFFSET+(index%6)*0x8C
                for h in(before,after):h.pokemon(a,pid,tid)
                original=bytes(after.u.mem_read(a,0x8C))
                assert before.shiny(a)==0 and after.shiny(a)==1
                after.u.mem_write(QUERY,original)
                assert after.shiny(QUERY)==1
                assert bytes(after.u.mem_read(a,0x8C))==original==bytes(after.u.mem_read(QUERY,0x8C))
                # Same species, same PID, different trainer remains native.
                after.pokemon(QUERY,pid,tid^0x8000)
                assert after.shiny(QUERY)==vanilla(pid,tid^0x8000)==0
                # Same trainer/species, different PID remains native.
                after.pokemon(QUERY,pid^0x40000000,tid)
                assert after.shiny(QUERY)==vanilla(pid^0x40000000,tid)==0
                fixtures+=1;checks+=5
        # Duplicate PID with differing trainers: continue past the wrong match.
        pid=0x81234567;tid=0x13572468
        after.pokemon(base+37*PASS_STRIDE+POKEMON_OFFSET,pid,tid^0x8000)
        after.pokemon(base+38*PASS_STRIDE+POKEMON_OFFSET+5*0x8C,pid,tid)
        after.pokemon(QUERY,pid,tid);assert after.shiny(QUERY)==1;checks+=1
        after.pokemon(base+39*PASS_STRIDE+POKEMON_OFFSET,0xAB123456,tid)
        after.pokemon(QUERY,0xAB123456,tid);assert after.shiny(QUERY)==0;checks+=1
        # Preserve naturally shiny Pokemon outside the two rental passes.
        pid=(tid>>16)^(tid&65535)
        after.pokemon(QUERY,pid,tid);assert after.shiny(QUERY)==1;checks+=1
        # A missing/unloaded pass array uses the original PID/TID formula.
        after.put(PASS_BASE_GLOBAL,0)
        after.pokemon(QUERY,0xAB123456,tid);assert after.shiny(QUERY)==0
        after.pokemon(QUERY,pid,tid);assert after.shiny(QUERY)==1;checks+=2
    private=None
    if diagnostics:
        from verify_vm_wait import Replay
        machines=[Replay(diagnostics),Replay(diagnostics)]
        for a in assemble():
            off=file_offset(changed,a);machines[1].uc.mem_write(a,changed[off:off+4])
        base=machines[0].get(PASS_BASE_GLOBAL)
        saved=bytes(machines[1].uc.mem_read(base,159*PASS_STRIDE))
        species=[];rental=0;copies=0;opponents=0
        for p in(37,38):
            row=[]
            for s in range(6):
                a=base+p*PASS_STRIDE+POKEMON_OFFSET+s*0x8C
                row.append(machines[0].call(0x803DE52C,(a,5,0)))
                assert machines[0].call(WRAPPER,(a,))==0
                assert machines[1].call(WRAPPER,(a,))==1;rental+=1
            species.append(row)
        assert species==[[2,5,8,148,111,18],[388,391,394,404,444,397]]
        for slot in range(4):
            a=0x9194F46C+0x648+slot*0x8C
            assert machines[0].call(WRAPPER,(a,))==0 and machines[1].call(WRAPPER,(a,))==1;copies+=1
        for slot in range(6):
            a=0x9194F46C+0x1420+slot*0x8C
            assert machines[0].call(WRAPPER,(a,))==machines[1].call(WRAPPER,(a,));opponents+=1
        assert bytes(machines[1].uc.mem_read(base,159*PASS_STRIDE))==saved
        private={'rental_pokemon_existing_memory':rental,'selected_battle_copies':copies,
            'opponents_unchanged':opponents,'entire_pass_array_unchanged':True,
            'source':'Private user-provided decoded Dolphin state; not distributed'}
    return {'status':'passed','identity_fixtures':fixtures,'checks':checks,'shuffle_variants':32,
        'allocation_banks':['MEM1','MEM2'],'native_getter_stubs':[],
        'abi_nonvolatile_registers_and_stack':'passed','pokemon_bytes_unchanged':True,
        'private_existing_memory_replay':private,'main_dol_sha256':sha(changed),
        'limits':['No Dolphin rendering/gameplay test','No save-file persistence test',
                  'Shiny appearance is active while using this mod; saved identities are unchanged']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in('v7','changed','common','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--diagnostics',type=Path);a=p.parse_args()
    report=verify(a.v7.read_bytes(),a.changed.read_bytes(),a.common.read_bytes(),a.diagnostics)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
