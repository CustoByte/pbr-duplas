"""Check auxiliary input, native result lifecycle and native prompt prefixes.

Private captures supply actual code/data. Auxiliary registrations/details
objects and widget-ready state are explicit fixtures. Result state is supplied
at the original manager; no real battle damage, renderer or networking runs.
"""
import argparse,json,struct
from pathlib import Path
from coop_actor_bridge import UI,REGISTRY
from coop_input_router import STATE,ENTRY
from prepare_coop_draft import AUX_CALLS,DRAFT
from prepare_campaign_doubles import sha
from verify_coop_target import TargetReplay
from verify_coop_draft import DraftReplay,CHOOSE

class FinishReplay(TargetReplay):
    def register_aux(self,details=False):
        if details:
            context=self.get(0x80625860)
            handle=self.get(context+0x64)
            # Captured details object exists, but its callback isn't active.
            if handle>=32:handle=29;self.put(context+0x64,handle)
            callback=0x800FC1B4
        else:handle=self.get(0x806257E8);callback=0x8006B468
        assert handle<32
        self.put(REGISTRY+0x2C+4*handle,callback)
        self.uc.mem_write(REGISTRY+0x12C+handle,b'\1')

    def aux(self,callsite,p0=0,p1=0,pad=0):
        self.seed(p0,p1);self.reads.clear()
        for off in (-0x6768,-0x6764,-0x6760):self.put(0x8062D600+off,0)
        if callsite in (0x8006B4D8,0x8006B510):args=(0x40000000,pad,0,1)
        elif callsite in (0x8006B4F0,0x8006B52C):args=(0x80000000,pad,0,1)
        else:args=(0x29 if callsite>=0x800FC000 else 0,2,pad,1)
        return self.event(callsite,args,(callsite+4,))[0]

    def text(self,id):return self.call(0x8024FB34,(0x8048062C,id))
    def message_bytes(self,p):
        out=bytearray()
        for i in range(126):
            raw=bytes(self.uc.mem_read(p+2*i,2));out.extend(raw)
            if len(out)>=4 and out[-4:]==b'\xff'*4:return bytes(out)
        raise AssertionError('Unterminated text')


def verify(source,changed,captures):
    counts={k:0 for k in ('auxiliary_callsite_owner_cases','disabled_auxiliary_comparisons',
        'auxiliary_guard_cases','native_auxiliary_callback_cases','draft_details_cases',
        'native_result_intake_cases','native_result_readout_cases','menu_p1_cases',
        'prompt_prefix_cases','unchanged_message_cases','repeated_finish_cases')}
    for capture in captures:
        baseline=FinishReplay(capture,source);h=FinishReplay(capture,changed)
        for pos in (0,1):
            for family in (0,1,2,3):
                # Reserve UI uses the separate native opening; aux scope still
                # resolves the position through the same actual battle context.
                if family==3:
                    h.enable();h.health(15);h.mapping((0,1));h.open(pos)
                else:h.health(15);h.mapping((0,1));h.open_choice(family,pos)
                for call in AUX_CALLS:
                    h.register_aux(call>=0x800FC000)
                    for pad in (0,1):
                        h.aux(call,pad=pad)
                        assert not h.aux(call,0x800 if pos else 0,0x800 if not pos else 0,pad)&0x80000000
                        value=h.aux(call,0x800 if not pos else 0,0x800 if pos else 0,pad)
                        assert value==(0x800 if call in AUX_CALLS[:4] else 0x80000002),(family,pos,hex(call),hex(value))
                        assert h.reads[-1][2]==pos
                        counts['auxiliary_callsite_owner_cases']+=1
        for call in AUX_CALLS:
            for machine in (baseline,h):
                machine.health(15);machine.mapping((0,1));machine.open_choice(1,0,enabled=False)
                machine.register_aux(call>=0x800FC000)
            for mask in (0,1,0x800,0x400):
                assert h.aux(call,mask)==baseline.aux(call,mask)
                counts['disabled_auxiliary_comparisons']+=1
        for corrupt in ('session','owner','missing_table','actor','mode'):
            h.health(15);h.mapping((0,1));h.open_choice(1,0);h.register_aux()
            if corrupt=='session':h.put(STATE+0x1C,h.session+4)
            if corrupt=='owner':h.uc.mem_write(STATE+10,b'\xff')
            if corrupt=='missing_table':h.uc.mem_write(STATE+9,b'\0')
            if corrupt=='actor':h.uc.mem_write(UI+0x64,b'\0\2')
            if corrupt=='mode':h.uc.mem_write(0x80626EE4,b'\x16')
            assert h.aux(AUX_CALLS[1],0x800,0x800)==0
            counts['auxiliary_guard_cases']+=1
        # Run the real secondary callback; only its registration/ready phase
        # are prepared, not replaced by a Python implementation.
        for pos in (0,1):
            h.health(15);h.mapping((0,1));h.open_choice(1,pos);h.register_aux()
            for p0,p1 in ((0,0),(0,0),(0x800 if pos else 0,0x800 if not pos else 0),
                          (0x800 if not pos else 0,0x800 if pos else 0)):
                h.seed(p0,p1);h.reads.clear();h.uc.mem_write(UI+0x90,b'\0\3')
                h.call(0x8006B468);h.abi()
                assert all(read[2]==pos for read in h.reads)
                counts['native_auxiliary_callback_cases']+=1
        # Details while assigning the shared pass also use that pick's owner.
        for owner in (0,1):
            h.setup()
            if owner:
                for slot in (0,1):
                    DraftReplay.query(h)
                    assert h.call(CHOOSE,(slot,0,0,0))==1
            h.register_aux(True)
            h.aux(AUX_CALLS[-1]);h.aux(AUX_CALLS[-1])
            result=h.aux(AUX_CALLS[-1],0x800 if owner==0 else 0,0x800 if owner==1 else 0)
            assert result==0x80000002 and h.reads[-1][2]==owner
            counts['draft_details_cases']+=1
        # setup() deliberately reconstructs the selection pool from the real
        # rental accessor. Subsequent lifecycle/text tests must preserve that
        # explicit fixture, rather than the pre-setup captured pool.
        assert bytes(h.uc.mem_read(h.session+0x1FFC,0x6EC))==h.pool
        h.pass_before=h.pool
        manager=h.get(0x806257F8)
        for raw in (0,1,2,0x80):
            for machine in (baseline,h):
                machine.enable();machine.uc.mem_write(STATE+5,b'\2\1')
                machine.call(0x800754C8,(raw,));machine.abi()
            assert h.get(manager+0x28)==baseline.get(manager+0x28)==raw
            assert h.uc.mem_read(STATE+5,2)==bytes(2)
            assert h.uc.mem_read(STATE+9,1)==bytes([raw!=0x80])
            h.seed(0x800,0x400)
            assert h.call(ENTRY,(0x80000000,0,0,0))==0x800
            counts['menu_p1_cases']+=1;counts['native_result_intake_cases']+=1
        for state in (0,4,5,6):
            for winner in (0,1,2,3):
                for machine in (baseline,h):
                    machine.enable();machine.put(manager+12,state)
                    machine.uc.mem_write(manager+0x52A,bytes([winner]))
                expected=baseline.call(0x80075394);result=h.call(0x80075394);h.abi()
                assert result==expected
                assert h.uc.mem_read(STATE+9,1)==bytes([result>2])
                epoch=h.get(STATE+0x10);assert h.call(0x80075394)==result
                assert h.get(STATE+0x10)==epoch
                counts['native_result_readout_cases']+=1;counts['repeated_finish_cases']+=1
        # Prefix retains every original command/placeholder/terminator byte.
        for pos in (0,1):
            for family in range(4):
                h.health(15);h.mapping((0,1))
                if family==3:h.enable();h.open(pos)
                else:h.open_choice(family,pos)
                for id in (0x2ECB,0x2ECC,0x3123,0x3124):
                    p=baseline.text(id);original=baseline.message_bytes(p)
                    changed_text=h.message_bytes(h.text(id));head=14 if id in (0x2ECB,0x2ECC) else 8
                    prefix=f'P{pos+1}: '.encode('utf-16-be')
                    assert changed_text==original[:head]+prefix+original[head:]
                    assert baseline.message_bytes(p)==original
                    counts['prompt_prefix_cases']+=1
                for id in (0x2ECD,0x3125,1):
                    assert h.text(id)==baseline.text(id);counts['unchanged_message_cases']+=1
        h.intact_switch()
        print(f'{capture.name}: auxiliary/lifecycle/prompt checks passed',flush=True)
    return {'status':'passed',**counts,'prototype_sha256':sha(changed),'enabled_at_boot':False,
        'auxiliary_native_input_calls':[f'{a:08x}' for a in AUX_CALLS],
        'native_result_intake':'800754c8','native_result_readout':'80075394','native_text_accessor':'8024fb34',
        'prompt_ids':['2ecb','2ecc','3123','3124'],'reserved_end':'80641000',
        'fixtures':['Auxiliary callback registration/details object; widget-ready phase',
                    'Synthetic result manager phase/winner; native result functions execute',
                    'Owner, mapping, HP and controller caches as in prior suites'],
        'limits':['Prompt bytes verified, but layout/refresh/rendering not tested',
                  'No real battle outcome, full campaign, physical controllers or NetPlay test',
                  'Special tournament paths and full summary navigation remain to be checked in Dolphin'],
        'private_data_published':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','changed','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--captures',type=Path,nargs=2,required=True)
    a=p.parse_args();report=verify(a.source.read_bytes(),a.changed.read_bytes(),a.captures)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
