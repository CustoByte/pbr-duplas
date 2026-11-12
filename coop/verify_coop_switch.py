"""Native PPC replay of cooperative party input and switch validation.

Private battle captures supply real party data and functions. HP is changed
through the native setter; selector/display-party objects, row permutations,
button caches and owner tables are explicit fixtures. No battle damage engine,
rendered replacement sequence, controller hardware or networking runs here.
"""
import argparse,itertools,json,struct
from pathlib import Path
from unicorn import UC_HOOK_MEM_WRITE

from coop_actor_bridge import UI,automatic_state
from coop_input_router import STATE
from coop_policy import CoopPolicy
from prepare_campaign_doubles import sha
from verify_coop_capture import verify_loaded_text
from verify_coop_draft import DraftReplay

VALIDATE=0x801722BC
ORIGINAL=0x8063EB50
SELECTOR=0x81D00000
PARTY=0x81D01000
VALUE=0x81D02000

class SwitchReplay(DraftReplay):
    def __init__(self,capture,dol):
        super().__init__(capture,dol)
        self.ctx=self.call(0x803B0008)
        self.data=self.call(0x803B0028,(self.ctx,))
        self.mons=[self.call(0x803B0184,(self.ctx,0,i)) for i in range(4)]
        self.hp=[self.call(0x803E100C,(mon,0xA2,0)) for mon in self.mons]
        assert all(self.hp) and self.call(0x803B00E0,(self.ctx,0))==4
        self.extra_code=bytes(self.uc.mem_read(0x8063EB40,0x18))
        self.pass_before=bytes(self.uc.mem_read(self.session+0x1FFC,0x6EC))
        def guard(*args):raise AssertionError('Write over switch trampolines')
        self.uc.hook_add(UC_HOOK_MEM_WRITE,guard,begin=0x8063EB40,end=0x8063EB57)

    def enable(self,owners=(0,1,0,1,255,255)):
        self.uc.mem_write(STATE,automatic_state(self.session,owners))

    def mapping(self,active):
        order=tuple(active)+tuple(i for i in range(6) if i not in active)
        self.uc.mem_write(self.data+0x312C,bytes(order))
        return order

    def health(self,mask):
        for i,mon in enumerate(self.mons):
            self.put(VALUE,self.hp[i] if mask&(1<<i) else 0)
            self.call(0x803DEB54,(mon,0xA2,VALUE));self.abi()
            assert bool(self.call(0x803E100C,(mon,0xA2,0)))==bool(mask&(1<<i))

    def selector(self,order,active,position,pending=6,trap=0):
        self.uc.mem_write(PARTY,bytes(8+6*0xA4))
        self.put(PARTY,6);self.put(PARTY+4,4)
        for row,member in enumerate(order):
            if member<4:self.uc.mem_write(PARTY+8+row*0xA4,bytes(self.uc.mem_read(self.mons[member],0xA4)))
        self.uc.mem_write(SELECTOR,bytes(0x40))
        self.put(SELECTOR,PARTY);self.put(SELECTOR+4,self.ctx)
        self.uc.mem_write(SELECTOR+9,bytes((pending,*active,active[position])))
        self.uc.mem_write(SELECTOR+0x1A,struct.pack('>H',trap))
        self.put(SELECTOR+0x1C,position*2)
        self.uc.mem_write(SELECTOR+0x20,bytes(order))

    def open(self,position):
        self.call(0x8005F320,(0,3+5*position,0,0),limit=1000000);self.abi()
        assert self.uc.mem_read(0x80626EE4,1)==bytes([3+5*position])

    def query(self,row,p0=0,p1=0):
        self.seed(p0,p1);self.reads.clear()
        for off in (-0x6768,-0x6764,-0x6760):self.put(0x8062D600+off,0)
        return self.event(0x80063240,(1,row+1,0,1),(0x80063244,))[0]

    def tick(self,row,p0=0,p1=0):
        # Advance the real party callback from its input-ready phase. Widget
        # animation completion is not simulated: state 24/focus are fixtures.
        self.uc.mem_write(0x80626ED4,struct.pack('>H',24))
        self.uc.mem_write(0x80626EE2,struct.pack('>H',row+1))
        for off in (-0x6768,-0x6764,-0x6760):self.put(0x8062D600+off,0)
        self.seed(p0,p1);self.reads.clear();self.call(0x80062B50);self.abi()
        return int.from_bytes(self.uc.mem_read(0x80626ED4,2),'big')

    def intact_switch(self):
        assert bytes(self.uc.mem_read(self.session+0x1FFC,0x6EC))==self.pass_before
        assert bytes(self.uc.mem_read(self.session+0x2DD4,0x6EC))==self.original_enemy
        assert bytes(self.uc.mem_read(0x8063D400,0x8063EB00-0x8063D400))==self.code
        assert self.get(0x8063C800)==0x45585048
        assert bytes(self.uc.mem_read(0x8063EB40,0x18))==self.extra_code


def verify(source,changed,captures):
    counts={k:0 for k in ('policy_legality_cases','preserved_native_rejections','native_party_input_cases',
        'native_callback_transitions','disabled_validation_comparisons','native_reorder_survivor_cases',
        'guard_cases','cancel_cases','disconnected_owner_cases','disabled_input_comparisons',
        'release_barrier_cases')}
    for capture in captures:
        verify_loaded_text(source,(capture/'mem1.bin').read_bytes())
        h=SwitchReplay(capture,changed)
        for owners in ((0,1,0,1),(1,0,1,0)):
            h.enable((*owners,255,255))
            for mask in range(16):
                h.health(mask)
                for active in itertools.permutations(range(4),2):
                    order=h.mapping(active)
                    policy=CoopPolicy(tuple(range(4)),owners=owners)
                    policy.active=list(active)
                    for member in range(4):
                        if not mask&(1<<member):policy.faint(member)
                    for position in (0,1):
                        h.selector(order,active,position)
                        if policy.active[position] is None:allowed=policy.replacements(position)
                        else:allowed=policy.switches(position,owners[active[position]])
                        for row,member in enumerate(order):
                            native=h.call(ORIGINAL,(row,SELECTOR));h.abi()
                            expected=native or (0 if member in allowed else 0x505A)
                            result=h.call(VALIDATE,(row,SELECTOR));h.abi()
                            assert result==expected,(capture.name,owners,mask,active,position,row,result,expected)
                            counts['policy_legality_cases']+=1
                            if native:counts['preserved_native_rejections']+=1
        # Native pending-choice/trapping reasons remain authoritative.
        h.enable();h.health(15);order=h.mapping((0,1))
        for pending,trap,error in ((2,0,0x2ED3),(6,1,0x30BB)):
            h.selector(order,(0,1),0,pending,trap)
            assert h.call(ORIGINAL,(2,SELECTOR))==error
            assert h.call(VALIDATE,(2,SELECTOR))==error
            counts['preserved_native_rejections']+=1
        # Disabled entry is equivalent for every row, native rejection and client.
        for pending,trap in ((6,0),(2,0),(6,1)):
            for client in range(4):
                h.selector(order,(0,1),client//2,pending,trap);h.put(SELECTOR+0x1C,client)
                for row in range(6):
                    h.uc.mem_write(STATE+4,b'\0');before=h.call(ORIGINAL,(row,SELECTOR))
                    after=h.call(VALIDATE,(row,SELECTOR));assert before==after
                    counts['disabled_validation_comparisons']+=1
        h.enable();h.selector(order,(0,1),0)
        for client in (1,3):
            h.put(SELECTOR+0x1C,client)
            for row in range(6):
                assert h.call(VALIDATE,(row,SELECTOR))==h.call(ORIGINAL,(row,SELECTOR))
                counts['guard_cases']+=1
        for corrupt in ('owners','session','selector_context','missing_table','oversized_row'):
            h.enable();h.selector(order,(0,1),0)
            if corrupt=='owners':h.uc.mem_write(STATE+10,b'\xff')
            if corrupt=='session':h.put(STATE+0x1C,h.session+4)
            if corrupt=='selector_context':h.put(SELECTOR+4,h.ctx+4)
            if corrupt=='missing_table':h.uc.mem_write(STATE+9,b'\0')
            row=6 if corrupt=='oversized_row' else 2
            assert h.call(VALIDATE,(row,SELECTOR))==0x505A
            counts['guard_cases']+=1
        h.enable();h.health(15);h.mapping((0,1));h.open(0)
        h.uc.mem_write(STATE+4,b'\0')
        for row in range(6):
            for mask in (0,1,2,4,8,0x800,0x400):
                h.seed(mask,0)
                for off in (-0x6768,-0x6764,-0x6760):h.put(0x8062D600+off,0)
                native=h.call(0x8005B5EC,(1,row+1,0,1))
                assert h.query(row,mask,0)==native
                counts['disabled_input_comparisons']+=1
        # Controller routing and confirmation filtering with actual core HP.
        for position,mask,expected_owner,valid_member in (
            (0,15,0,2),(1,15,1,3), # voluntary switch
            (0,14,0,2),(1,13,1,3), # active faints, own reserve remains
            (0,10,1,3),(1,5,0,2)): # both owned members faint, partner fills vacancy
            h.enable();h.health(mask);order=h.mapping((0,1));h.open(position)
            valid_row=order.index(valid_member)
            assert not h.query(valid_row,0x800 if expected_owner==0 else 0,0x800 if expected_owner==1 else 0)&0x80000000
            counts['release_barrier_cases']+=1
            h.query(valid_row)
            assert h.uc.mem_read(STATE+6,1)==bytes([expected_owner])
            assert h.uc.mem_read(STATE+5,1)==bytes([4 if mask&(1<<position) else 5])
            assert not h.query(valid_row,0x800 if expected_owner==1 else 0,0x800 if expected_owner==0 else 0)&0x80000000
            assert h.reads and h.reads[-1][2]==expected_owner
            for row,member in enumerate(order):
                h.query(row)
                result=h.query(row,0x800 if expected_owner==0 else 0,0x800 if expected_owner==1 else 0)
                allowed=member==valid_member
                assert bool(result&0x80000000)==allowed,(position,mask,row,hex(result))
                assert h.reads[-1]==(1,row+1,expected_owner)
                counts['native_party_input_cases']+=1
                h.tick(row)
                state=h.tick(row,0x800 if expected_owner==0 else 0,0x800 if expected_owner==1 else 0)
                assert state==(27 if allowed else 24)
                if allowed:assert int.from_bytes(h.uc.mem_read(UI+0x66,2),'big')==row
                counts['native_callback_transitions']+=1
            # B/cancel remains native and owned, rather than being treated as a member.
            h.query(valid_row)
            result=h.query(valid_row,0x400 if expected_owner==0 else 0,0x400 if expected_owner==1 else 0)
            assert result&0x80000000 and result&0xFFFF in (30,65535)
            counts['cancel_cases']+=1
            h.query(valid_row)
            port=h.manager+0x38+expected_owner*0x928
            h.put(port+0x3C,1)
            # query() seeds connection, so use the callsite directly.
            result=h.event(0x80063240,(1,valid_row+1,0,1),(0x80063244,))[0]
            assert result==0
            counts['disconnected_owner_cases']+=1
        # Native reorder after a replacement makes both command positions
        # belong to the surviving player. Damage/faint animation is not run.
        for owner in (0,1):
            h.enable();h.health(5 if owner==0 else 10);h.mapping((0,1))
            client,member=(2,2) if owner==0 else (0,3)
            h.call(0x803C96D4,(h.ctx,h.data,client,member))
            for position in (0,1):
                active=h.call(0x803CC838,(0,position));assert active%2==owner
                h.open(position);h.query(2)
                assert h.uc.mem_read(STATE+6,1)==bytes([owner])
                h.query(2,0x800 if owner==0 else 0,0x800 if owner==1 else 0)
                assert h.reads[-1][2]==owner
                counts['native_reorder_survivor_cases']+=1
        h.intact_switch()
        print(f'{capture.name}: native cooperative switch checks passed',flush=True)
    return {'status':'passed',**counts,'prototype_sha256':sha(changed),'enabled_at_boot':False,
        'native_validation':'801722bc','native_party_callback':'80062b50','native_hp_setter':'803deb54',
        'native_hp_getter':'803e100c field 0xa2','native_party_reorder':'803c96d4',
        'input_validation_hp_or_party_getter_stubs':[],
        'fixtures':['Owner table and controller caches','HP through native setter, not battle damage',
                    'Selector/display party and row permutations','Party callback input-ready phase and focus'],
        'audio_and_psq_exceptions':'Same narrow feedback stubs and four context PSQ skips as verify_coop_draft',
        'limits':['No physical controllers, rendered replacement battle or NetPlay test',
                  'Selector layout inferred from native validator; not captured during a real replacement',
                  'Native 0x505a rejection text has not been checked visually',
                  'Secondary interfaces, special tournament screens, turn indicator and battle lifecycle remain unfinished'],
        'private_data_published':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','changed','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--captures',type=Path,nargs=2,required=True)
    a=p.parse_args();report=verify(a.source.read_bytes(),a.changed.read_bytes(),a.captures)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
