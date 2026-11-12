"""Execute cooperative draft code with native predicates and real rental data.

The selection UI object/registration are reconstructed because supplied states
were captured during battle. No eligibility, Pokemon getter, selection marking
or packing routine is stubbed. This is not a rendered/live selection test.
"""
import argparse,itertools,json,struct
from pathlib import Path

from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn import ppc_const as ppc

from coop_actor_bridge import REGISTRY
from coop_input_router import ENTRY,STATE
from coop_policy import CoopPolicy
from prepare_campaign_doubles import file_offset,sha,word
from prepare_coop_draft import DRAFT,END,PAYLOAD,prepare_draft
from verify_coop_capture import verify_loaded_text
from verify_coop_input import CURSOR_CONTEXT_PSQ
from verify_vm_wait import Replay,STOP

RESET=0x80159B6C
CHOOSE=0x80159DB8
PACK=0x8015A1C4


class DraftReplay(Replay):
    def __init__(self,capture,dol):
        # No script VM runs in these isolated native calls. Use narrowly scoped
        # observation hooks rather than the VM replay's per-instruction hook.
        self.uc=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
        for name,base in (('mem1.bin',0x80000000),('mem2.bin',0x90000000)):
            data=(capture/name).read_bytes();self.uc.mem_map(base,len(data));self.uc.mem_write(base,data)
        self.uc.reg_write(ppc.UC_PPC_REG_MSR,0x2000)
        for i in range(7):
            off,address,size=(word(dol,j+4*i) for j in (0,0x48,0x90))
            if size:self.uc.mem_write(address,dol[off:off+size])
        self.sound_ids=[];self.reads=[];self.stop_address=None;self.stopped_at=None
        for address in (0x8005C04C,0x8000AEB0,ENTRY+4,*CURSOR_CONTEXT_PSQ):
            self.uc.hook_add(UC_HOOK_CODE,self.observe,begin=address,end=address)
        def code_write(u,access,address,size,value,data):
            raise AssertionError(f'Native write over draft code at {address:08x}')
        self.uc.hook_add(UC_HOOK_MEM_WRITE,code_write,begin=PAYLOAD,end=DRAFT-1)
        self.ui=self.get(0x806258C8);self.session=self.call(0x8011F458)
        self.manager=self.call(0x802492D8)
        # Obtain the actual current rental through its native, migration-aware accessor.
        rental=self.call(0x800E8594,(38,))
        self.pool=bytes(self.uc.mem_read(rental,0x6EC))
        self.original_enemy=bytes(self.uc.mem_read(self.session+0x2DD4,0x6EC))
        self.original_ready=bytes(self.uc.mem_read(self.session+0x44C,0x6EC))
        self.original_enemy_ready=bytes(self.uc.mem_read(self.session+0x1224,0x6EC))
        self.code=bytes(self.uc.mem_read(PAYLOAD,DRAFT-PAYLOAD))
        assert self.get(0x8063C800)==0x45585048 # Captured SDK EXPHeap header.

    def observe(self,u,address,size,data):
        if address in CURSOR_CONTEXT_PSQ:
            u.reg_write(ppc.UC_PPC_REG_PC,address+4);return
        if address==0x8005C04C:
            value=u.reg_read(ppc.UC_PPC_REG_3)
            assert value in (1,2,3)
            self.sound_ids.append(value)
            u.reg_write(ppc.UC_PPC_REG_PC,u.reg_read(ppc.UC_PPC_REG_LR))
        if address==0x8000AEB0:
            # UI pick feedback only; direct selection tests request no sound.
            assert u.reg_read(ppc.UC_PPC_REG_3)==0x21F
            self.sound_ids.append(0x21F)
            u.reg_write(ppc.UC_PPC_REG_PC,u.reg_read(ppc.UC_PPC_REG_LR))
        if address==ENTRY+4:
            self.reads.append(tuple(u.reg_read(getattr(ppc,f'UC_PPC_REG_{i}')) for i in (3,4,5)))
        if self.stop_address and address in self.stop_address:
            self.stopped_at=address;u.reg_write(ppc.UC_PPC_REG_PC,STOP)

    def setup(self,enabled=True):
        self.uc.mem_write(self.session+0x1FFC,self.pool)
        self.uc.mem_write(self.session+0x44C,self.original_ready)
        self.uc.mem_write(self.session+0x1224,self.original_enemy_ready)
        self.uc.mem_write(self.session+0x19,b'\4')
        self.put(self.ui+0xD8,self.session)
        self.uc.mem_write(self.ui+0x140,b'\0\0')
        self.put(self.ui+0xC0,30)
        self.put(REGISTRY+0x2C+30*4,0x80156414)
        self.uc.mem_write(REGISTRY+0x12C+30,b'\1')
        self.uc.mem_write(DRAFT,struct.pack('>I',0x44524654)+bytes([int(enabled)])+bytes(27))
        self.call(RESET)
        self.abi()

    def abi(self):
        assert self.uc.reg_read(ppc.UC_PPC_REG_1)==0x81F00000
        assert self.uc.reg_read(ppc.UC_PPC_REG_2)==0x806308E0
        assert self.uc.reg_read(ppc.UC_PPC_REG_13)==0x8062D600
        for i in range(14,32):assert self.uc.reg_read(getattr(ppc,f'UC_PPC_REG_{i}'))==0
        assert not self.uc.reg_read(ppc.UC_PPC_REG_CR)&0x00FFF000

    def ranks(self):return list(self.uc.mem_read(self.ui+0xDC,6))
    def owner(self):return self.uc.mem_read(DRAFT+6,1)[0]
    def choose(self,slot):
        if self.uc.mem_read(DRAFT+5,1)==b'\1':self.query()
        result=self.call(CHOOSE,(slot,0,0,0));self.abi();return result
    def event(self,address,args,stops):
        self.stop_address=set(stops);self.stopped_at=None
        hooks=[self.uc.hook_add(UC_HOOK_CODE,self.observe,begin=stop,end=stop) for stop in stops]
        try:result=self.call(address,args)
        finally:
            self.stop_address=None
            for hook in hooks:self.uc.hook_del(hook)
        self.abi();return result,self.stopped_at
    def undo(self,slot):
        self.query()
        return self.event(0x80157770,(slot,0,0,0),(0x80157774,))[0]
    def pack_event(self):
        if self.uc.mem_read(DRAFT+5,1)==b'\1':self.query()
        return self.event(0x80157488,(1,),(0x8015748C,0x80157B58))
    def packed(self,side=0):
        base=self.session+(0x44C if side==0 else 0x1224)
        return [bytes(self.uc.mem_read(base+0x1FC+i*0x8C,0x88)) for i in range(6)
                if self.uc.mem_read(base+0x286+i*0x8C,1)[0]&0x80]
    def seed(self,p0,p1):
        for index,mask in enumerate((p0,p1)):
            base=self.manager+0x38+index*0x928
            for off,value in ((0x1C,mask),(0x20,mask),(0x3C,0),(0x40,3)):self.put(base+off,value)
            self.uc.mem_write(base+0xA1,b'\0')
    def query(self,p0=0,p1=0,raw=False):
        self.seed(p0,p1);self.reads.clear()
        for off in (-0x6768,-0x6764,-0x6760):self.put(0x8062D600+off,0)
        args=(0x80000000,0,0,0) if raw else (0x28,0x33,0,0)
        return self.event(0x80156454 if raw else 0x801570B0,args,
                          (0x80156458,) if raw else (0x801570B4,))[0]
    def intact(self):
        assert bytes(self.uc.mem_read(PAYLOAD,DRAFT-PAYLOAD))==self.code
        assert self.get(0x8063C800)==0x45585048
        assert bytes(self.uc.mem_read(self.session+0x1FFC,0x6EC))==self.pool
        assert bytes(self.uc.mem_read(self.session+0x2DD4,0x6EC))==self.original_enemy


def verify(source,changed,payload,manifest,captures):
    assert prepare_draft(source,payload,manifest)==changed
    assert word(changed,0x50)==0x8063C000 and word(changed,0x98)==0x800
    assert word(changed,0x54)==PAYLOAD and PAYLOAD+word(changed,0x9C)==END
    for base in (STATE,DRAFT):assert bytes(32)==changed[file_offset(changed,base):file_offset(changed,base)+32]
    counts={'four_pick_orders':0,'wrong_owner_selected_slots_blocked':0,'incomplete_confirmation_blocked':0,
            'native_undo_transitions':0,'cursor_and_raw_owner_queries':0,'native_command_after_draft':0,
            'disabled_comparisons':0,'arena_clamp_cases':0,'cleanup_cases':0,'release_barrier_guard_cases':0}
    for capture in captures:
        verify_loaded_text(source,(capture/'mem1.bin').read_bytes())
        h=DraftReplay(capture,changed)
        originals=[h.pool[0x1FC+i*0x8C:0x1FC+i*0x8C+0x88] for i in range(6)]
        for order in itertools.permutations(range(6),4):
            h.setup()
            assert h.owner()==0
            for index,slot in enumerate(order):
                assert h.owner()==(0 if index<2 else 1)
                assert h.choose(slot)==1
                if index==1:
                    before=h.ranks();assert h.choose(order[0])==0 and h.ranks()==before
                    counts['wrong_owner_selected_slots_blocked']+=1
            assert h.owner()==0
            _,at=h.pack_event();assert at==0x8015748C
            expected=CoopPolicy.selected(order[:2],order[2:]).selection
            assert h.packed()==[originals[i] for i in expected]
            assert list(h.uc.mem_read(STATE+10,6))==[0,1,0,1,255,255]
            assert h.uc.mem_read(STATE+9,1)==b'\1'
            counts['four_pick_orders']+=1
        print(f'{capture.name}: 360 native draft orders passed',flush=True)
        h.intact()
        # Native automatic/batched selection cannot cross a new choice epoch
        # without a fresh input read releasing the incoming owner's buttons.
        for picks in ((),(0,),(0,1),(0,1,2,3)):
            h.setup()
            for slot in picks:h.choose(slot)
            before=h.ranks()
            if len(picks)<4:
                assert h.call(CHOOSE,(5,0,0,0))==0
            else:
                assert h.event(0x80157488,(1,),(0x8015748C,0x80157B58))[1]==0x80157B58
            assert h.ranks()==before
            counts['release_barrier_guard_cases']+=1
        baseline=DraftReplay(capture,source)
        for order in ((0,1,2,3),(5,4,3,2)):
            baseline.setup(False);h.setup(False)
            for slot in order:
                assert baseline.choose(slot)==h.choose(slot)
                assert baseline.ranks()==h.ranks()
                counts['disabled_comparisons']+=1
            baseline.call(PACK);h.call(PACK)
            assert baseline.packed()==h.packed()
            counts['disabled_comparisons']+=1
        # Existing native confirmation callers must not leave an incomplete draft.
        for selected in range(4):
            h.setup()
            for slot in range(selected):h.choose(slot)
            before=h.ranks();_,at=h.pack_event()
            assert at==0x80157B58 and h.ranks()==before and h.uc.mem_read(STATE+9,1)==b'\0'
            counts['incomplete_confirmation_blocked']+=1
        # Back before P2 has a pick returns to P1; Back after all four returns to P2.
        for picks,last,expected_owner in [((0,1),1,0),((0,1,2,3),3,1)]:
            h.setup()
            for slot in picks:h.choose(slot)
            assert h.undo(last)==1 and h.owner()==expected_owner
            assert h.ranks()[last]==0
            counts['native_undo_transitions']+=1
        # Editing an earlier P1 pick after P2's choices preserves each owner's order.
        h.setup()
        for slot in (0,1,2,3):h.choose(slot)
        assert h.choose(0)==1 and h.owner()==0
        assert h.choose(4)==1
        h.pack_event();assert h.packed()==[originals[i] for i in (1,2,4,3)]
        counts['native_undo_transitions']+=1
        # Actual native callsites enter the input router with the new draft owner.
        for owner in (0,1):
            for raw in (False,True):
                h.setup()
                if owner:
                    h.choose(0);h.choose(1)
                h.query(raw=raw)
                wrong=h.query(0x800 if owner else 0,0x800 if not owner else 0,raw=raw)
                # The native cursor API may report initial focus without a
                # button press; the high confirmation bit must remain clear.
                assert wrong==0 if raw else wrong in (0,0x33)
                value=h.query(0x800 if not owner else 0,0x800 if owner else 0,raw=raw)
                assert value==(0x800 if raw else 0x80000033)
                assert h.reads[-1][2]==owner
                if not raw:assert h.reads[-1][1]==0x33
                counts['cursor_and_raw_owner_queries']+=1
        # Committing installs the ownership consumed by the existing actor bridge.
        h.setup()
        for slot in (0,1,2,3):h.choose(slot)
        h.pack_event();h.seed(0,0)
        actor=0 if capture.name=='diagnostics-command' else 1
        callback=0x80061C98 if actor==0 else 0x80061598
        for off in (-0x6768,-0x6764,-0x6760):h.put(0x8062D600+off,0)
        before=bytes(h.uc.mem_read(0x8062D600-0x672C,2))
        h.call(callback);h.seed(0x800 if actor==0 else 0,0x800 if actor==1 else 0)
        h.reads.clear();h.call(callback)
        assert h.reads[-1][2]==actor and bytes(h.uc.mem_read(0x8062D600-0x672C,2))!=before
        counts['native_command_after_draft']+=1
        for committed in (False,True):
            h.setup()
            for slot in ((0,1,2,3) if committed else (0,)):h.choose(slot)
            if committed:h.pack_event()
            h.call(0x80156364);h.abi()
            assert h.uc.mem_read(STATE+9,1)==bytes([int(committed)])
            assert h.uc.mem_read(STATE+5,2)==bytes(2)
            assert h.uc.mem_read(DRAFT+5,1)==b'\0'
            counts['cleanup_cases']+=1
        # Both MEM1 ArenaLo setter aliases reserve the new section, while
        # preserving a caller's larger requested value.
        for setter in (0x8026EABC,0x8026EACC):
            for requested in (0,0x8063C800,0x8063D2C0,END-4,END,END+0x1000,0x81700000):
                h.call(setter,(requested,));assert h.call(0x8026EA8C)==max(END,requested)
                counts['arena_clamp_cases']+=1
        h.intact()
    return {'status':'passed',**counts,'selection_predicate_stubs':[],'pokemon_getter_stubs':[],
            'native_marking':'80159db8','native_packing':'8015a1c4','native_legality':'80154e0c',
            'input_and_ui_fixtures':'Reconstructed selection object/registration; seeded button caches',
            'audio_stubs':['8005c04c feedback ids 1/2/3','8000aeb0 selection feedback 0x21f'],
            'sdk_heap_header_preserved':'8063c800 EXPHeap','reserved_mem1_end':f'{END:08x}',
            'prototype_sha256':sha(changed),'enabled_at_boot':False,'private_data_published':False,
            'limits':['No rendered selection screen or physical controllers','No full battle startup, faint/replacement or NetPlay test',
                      'Capture heap allocation is not replayed; fresh-boot arena reservation is checked separately',
                      'Owner/turn display and remaining battle interfaces still need integration']}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','changed','payload','manifest','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--captures',type=Path,nargs=2,required=True)
    a=parser.parse_args();result=verify(a.source.read_bytes(),a.changed.read_bytes(),a.payload.read_bytes(),json.loads(a.manifest.read_text()),a.captures)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
