"""Native PPC migration tests; no native Pokemon getter/setter stubs."""
import argparse,json,struct
from pathlib import Path
from unicorn import ppc_const as ppc
from monferno_build import prepare_build,CODE,RESERVED_END,HOOKS,CARRY,CARRY_HOOK
from verify_rental_shiny import Harness,BASE,QUERY
from prepare_campaign_doubles import sha,file_offset,word

FIELDS=(0,5,6,0xA,0x36,0x37,0x38,0x39,0x3C,0x3D,0x40,0x41)

def verify(v8,v9,common,diagnostics=None):
    expected,_=prepare_build(v8)
    if expected!=v9:raise AssertionError('V9 is not reproducible')
    h=Harness(v9,common);base=BASE;h.put(0x80453184,base)
    mon=base+38*0x6EC+0x288
    def get(m,f):return h.call(0x803DE52C,(m,f,0))
    def setfield(m,f,value):
        h.put(QUERY+0x400,value);h.call(0x803DECA8,(m,f,QUERY+0x400))
    def fixture(pid,species=391):
        h.pokemon(mon,pid,0x13572468,species)
        for f,v in [(6,301),(0xA,66),(0x36,7),(0x37,183),(0x38,447),(0x39,241),(0x3C,17),(0x3D,7),(0x40,2),(0x41,1)]:setfield(mon,f,v)
    def check():
        pid=get(mon,0);assert pid%25==3
        assert [get(mon,f) for f in(6,0x36,0x37,0x38,0x39,0x3C,0x3D,0x40,0x41)]==[157,7,183,299,370,10,5,0,0]
    cases=0
    # All shuffle layouts, all old nature classes and wrap-around PID cases.
    for shuffle in range(32):
        for nature in range(25):
            pid=(0xFEE00000|(shuffle<<13)|0x105)+nature
            fixture(pid);original=bytes(h.u.mem_read(mon,0x8C))
            returned=h.call(0x800E8594,(38,));assert returned==base+38*0x6EC
            check();assert get(mon,0)&0xFFFFF==pid&0xFFFFF
            assert get(mon,0xA)==66 and get(mon,7)==0x13572468
            after=bytes(h.u.mem_read(mon,0x8C))
            assert h.call(0x800E88B0,(1,38))==mon
            assert bytes(h.u.mem_read(mon,0x8C))==after
            assert h.call(0x803DF31C,(mon,))==3 # Actual native nature getter.
            assert h.shiny(mon)==1
            # PP already consumed after migration remains consumed on access.
            setfield(mon,0x3C,4);setfield(mon,0x3D,2)
            h.call(0x800E8594,(38,));assert get(mon,0x3C)==4 and get(mon,0x3D)==2
            # A battle copy is not migrated/replenished by the new helper.
            h.u.mem_write(QUERY,bytes(h.u.mem_read(mon,0x8C)));setfield(QUERY,6,0)
            copy=bytes(h.u.mem_read(QUERY,0x8C));h.call(CODE,(QUERY,));assert bytes(h.u.mem_read(QUERY,0x8C))==copy
            cases+=1
    # Pass/slot/species boundaries and current-pass (-1/255) accessor forms.
    fixture(0xFFFA8123);h.u.mem_write(0x80453190,b'\x26')
    assert h.call(0x800E8594,(0xFFFFFFFF,))==base+38*0x6EC;check()
    fixture(0xFFFA8123);assert h.call(0x800E88B0,(1,255))==mon;check()
    fixture(0xFFFA8123,394);saved=bytes(h.u.mem_read(mon,0x8C));h.call(0x800E8594,(38,));assert saved==bytes(h.u.mem_read(mon,0x8C))
    fixture(0xFFFA8123);saved=bytes(h.u.mem_read(mon,0x8C));h.call(0x800E8594,(37,));assert saved==bytes(h.u.mem_read(mon,0x8C))
    # Consecutive fights: consumption stays visible throughout a fight. Only
    # the next-party carryover restore supplies the next Lum Berry.
    fixture(0xFFFA8123);h.call(0x800E8594,(38,))
    h.u.mem_write(QUERY,bytes(h.u.mem_read(mon,0x8C))+bytes(0x20))
    berry_cycles=0
    for _ in range(3):
        setfield(QUERY,6,0);assert get(QUERY,6)==0
        h.call(CODE,(QUERY,));assert get(QUERY,6)==0
        h.put(QUERY+0x400,0)
        h.call(CARRY,(QUERY,6,QUERY+0x400));assert get(QUERY,6)==157
        assert word(h.u.mem_read(QUERY+0x400,4),0)==0
        berry_cycles+=1
    # Another trainer's same-PID Pokemon must keep its consumed item.
    pid=get(mon,0);h.pokemon(QUERY,pid,0x24681357,391);h.put(QUERY+0x400,0)
    h.call(CARRY,(QUERY,6,QUERY+0x400));assert get(QUERY,6)==0
    # Both aliases clamp arbitrary loader values below the section; normal
    # default and later heap allocations retain their exact requested value.
    for setter in(0x8026EABC,0x8026EACC):
        for value in(0,0x80004000,0x8063B2B0,0x8063C000,RESERVED_END,0x8063D2C0,0x81000000):
            h.call(setter,(value,));stored=word(h.u.mem_read(0x8062D600-0x7870,4),0)
            assert stored==max(value,RESERVED_END)
    # Exhaust all upper-PID combinations: the nature search terminates even
    # when incrementing across the 32-bit boundary.
    bound=0
    for top in range(4096):
        p=top<<20|0xABCDE;n=0
        while p%25!=3:
            p=(p+0x100000)&0xFFFFFFFF;n+=1
            assert n<=49
        bound=max(bound,n)
    private=None
    if diagnostics:
        from verify_vm_wait import Replay
        replay=Replay(diagnostics)
        # Apply each section: the new text section is absent in an older state.
        from disassemble import sections
        for off,a,size in sections(v9):
            if a==CODE:replay.uc.mem_write(a,v9[off:off+size])
        for a in(*HOOKS,0x8026EABC,0x8026EACC,CARRY_HOOK):
            off=file_offset(v9,a);replay.uc.mem_write(a,v9[off:off+4])
        base=replay.get(0x80453184);mon=base+38*0x6EC+0x288
        before=bytes(replay.uc.mem_read(base,159*0x6EC))
        old_pid=replay.call(0x803DE52C,(mon,0,0))
        old_attrs={f:replay.call(0x803DE52C,(mon,f,0)) for f in(*range(0xD,0x13),*range(0x46,0x4C),7,0xA)}
        assert replay.call(0x800E8594,(38,))==base+38*0x6EC
        now={f:replay.call(0x803DE52C,(mon,f,0)) for f in FIELDS}
        assert now[0]%25==3 and now[0]&0xFFFFF==old_pid&0xFFFFF
        assert [now[f] for f in(5,6,0xA,0x36,0x37,0x38,0x39,0x3C,0x3D)]==[391,157,66,7,183,299,370,10,5]
        assert old_attrs=={f:replay.call(0x803DE52C,(mon,f,0)) for f in old_attrs}
        after=bytes(replay.uc.mem_read(base,159*0x6EC));start=38*0x6EC+0x288
        assert before[:start]==after[:start] and before[start+0x88:]==after[start+0x88:]
        assert replay.call(0x803DF31C,(mon,))==3
        once=after;replay.call(0x800E88B0,(1,38));assert bytes(replay.uc.mem_read(base,len(after)))==once
        private={'existing_state_migrated':True,'nature':'Adamant','moves':[7,183,299,370],'item_id':157,
            'other_pokemon_and_pass_data_unchanged':True,'ivs_evs_ability_trainer_id_preserved':True,'idempotent':True}
    return {'status':'passed','identity_nature_fixtures':cases,'native_getter_setter_stubs':[],
        'maximum_nature_search_iterations':bound,'arena_reservation_cases':14,'consecutive_berry_consumption_restore_cycles':berry_cycles,
        'scope_and_consumed_pp_and_battle_item_checks':'passed','abi_nonvolatile_registers_and_stack':'passed',
        'private_existing_memory_replay':private,'main_dol_sha256':sha(v9),
        'limits':['No Dolphin boot/rendering/gameplay execution','No actual save-file persistence test',
            'Modified rental data may be persisted when the game saves normally; applicator does not edit save files']}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in('v8','v9','common','output'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--diagnostics',type=Path);a=p.parse_args()
    r=verify(a.v8.read_bytes(),a.v9.read_bytes(),a.common.read_bytes(),a.diagnostics)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
