"""Replay native command UIs from two private Dolphin captures.

Controller caches/connection fields and the owner table are explicit fixtures.
Only UI feedback sounds are stubbed; four paired-single context instructions
are skipped. No input, actor getter, cursor or UI transition is substituted.
"""
import argparse
import json
import struct
from pathlib import Path

from unicorn import UC_HOOK_CODE
from unicorn import ppc_const as ppc

from coop_actor_bridge import BEGIN_HOOK, REGISTRY, UI, automatic_state, prepare_actor_bridge
from coop_input_router import ENTRY, STATE
from prepare_campaign_doubles import sha
from verify_coop_capture import verify_loaded_text
from verify_coop_input import CURSOR_CONTEXT_PSQ, allow_cursor_context
from verify_vm_wait import Replay, STOP


class CommandReplay(Replay):
    def __init__(self, diagnostics, dol):
        super().__init__(diagnostics)
        # Overlay text only: runtime objects, rosters, BSS and globals stay live.
        for index in range(7):
            off,address,size=(struct.unpack_from('>I',dol,base+4*index)[0] for base in (0,0x48,0x90))
            if size:self.uc.mem_write(address,dol[off:off+size])
        allow_cursor_context(self)
        self.input_args=[];self.feedback_sounds=[];self.stop_at_begin=False
        self.uc.hook_add(UC_HOOK_CODE,self.observe)
        self.manager=self.call(0x802492D8)
        assert self.call(0x80249310)==2
        self.session=self.call(0x8011F458)
        self.battle_data=self.call(0x803B0028,(self.call(0x803B0008),))
        self.slot=int.from_bytes(self.uc.mem_read(UI+0x64,2),'big')
        handle=self.get(0x8062D600-0x7E1C)
        self.callback=self.get(REGISTRY+0x2C+4*handle)
        assert self.callback in (0x80061598,0x80061C98)

    def observe(self,u,address,size,data):
        if address==0x8005C04C:
            sound=u.reg_read(ppc.UC_PPC_REG_3)
            if sound not in (1,2,3):raise AssertionError('Unexpected feedback sound')
            self.feedback_sounds.append(sound)
            u.reg_write(ppc.UC_PPC_REG_PC,u.reg_read(ppc.UC_PPC_REG_LR))
        if address==ENTRY+4:
            self.input_args.append(tuple(u.reg_read(getattr(ppc,f'UC_PPC_REG_{i}')) for i in (3,4,5)))
        if self.stop_at_begin and address==BEGIN_HOOK+4:u.emu_stop()

    def seed(self,p0,p1):
        for port,mask in enumerate((p0,p1)):
            address=self.manager+0x38+port*0x928
            for offset,value in [(0x1C,mask),(0x20,mask),(0x3C,0),(0x40,3)]:self.put(address+offset,value)
            self.uc.mem_write(address+0xA1,b'\0')

    def enable(self,owners=(0,1,0,1,255,255)):
        self.uc.mem_write(STATE,automatic_state(self.session,owners))

    def tick(self,p0=0,p1=0):
        self.seed(p0,p1);self.input_args.clear();self.call(self.callback)
        assert self.uc.reg_read(ppc.UC_PPC_REG_1)==0x81F00000
        for i in range(14,32):assert self.uc.reg_read(getattr(ppc,f'UC_PPC_REG_{i}'))==0

    def ui_state(self):
        return (bytes(self.uc.mem_read(UI+0x64,0x54)),
                bytes(self.uc.mem_read(0x8062D600-0x6730,0x18)))

    def open_epoch(self,mode):
        self.stop_at_begin=True
        try:self.call(BEGIN_HOOK,(0,mode,15,0))
        except AssertionError as error:
            assert str(error)=='Native replay instruction limit'
        else:raise AssertionError('Expected to stop at native UI prologue')
        finally:self.stop_at_begin=False
        assert self.uc.reg_read(ppc.UC_PPC_REG_PC)==BEGIN_HOOK+4
        assert self.uc.reg_read(ppc.UC_PPC_REG_1)==0x81F00000-0x40
        assert self.uc.reg_read(ppc.UC_PPC_REG_LR)==STOP
        assert tuple(self.uc.reg_read(getattr(ppc,f'UC_PPC_REG_{i}')) for i in range(3,7))==(0,mode,15,0)


def verify(source,captures):
    changed=prepare_actor_bridge(source)
    assert len(changed)==len(source)
    observations=[];disabled=0;confirmed=0;cancelled=0;logical=0;guards=0;epochs=0;survivor=0
    for folder in captures:
        verify_loaded_text(source,(folder/'mem1.bin').read_bytes())
        fresh=lambda dol=changed:CommandReplay(folder,dol)
        probe=fresh()
        observations.append({'mode':probe.uc.mem_read(0x8062D600-0x671C,1)[0],
                             'active_position':probe.slot,'callback':f'{probe.callback:08x}'})
        # Disabled trampoline must preserve native UI behavior, not just raw reads.
        for mask in (0,1,2,4,8,0x800,0x400):
            before,after=fresh(source),fresh()
            before.tick(mask,0);after.tick(mask,0)
            assert before.ui_state()==after.ui_state()
            assert before.input_args==after.input_args
            disabled+=1

        owner=probe.slot
        for event in (0x800,0x400):
            native,test=fresh(source),fresh();test.enable()
            original_state=test.ui_state()
            # Wrong player's buttons cannot move or confirm/cancel this UI.
            for wrong_mask in (1,2,4,8,0x800,0x400):
                test.tick(wrong_mask if owner==1 else 0,wrong_mask if owner==0 else 0)
                assert test.ui_state()==original_state
                assert all(args[2]==owner for args in test.input_args)
                guards+=1
            # Held button at the start of a choice is blocked until released.
            test=fresh();test.enable()
            test.tick(event if owner==0 else 0,event if owner==1 else 0)
            assert test.ui_state()==original_state and not test.input_args
            test.tick()
            test.tick(event if owner==0 else 0,event if owner==1 else 0)
            native.tick(event,0)
            assert test.ui_state()==native.ui_state()!=original_state
            assert test.input_args and test.input_args[-1][2]==owner
            assert test.input_args[-1][:2]==native.input_args[-1][:2]
            if event==0x800:confirmed+=1
            else:cancelled+=1

        # Resolve ownership through the game's active->logical-party getter.
        # These are explicit mapping fixtures, not simulated faint events.
        for owners in ((0,1,0,1,255,255),(1,0,1,0,255,255)):
            for selected in range(4):
                test=fresh();test.enable(owners)
                test.uc.mem_write(test.battle_data+0x312C+test.slot,bytes([selected]))
                expected=owners[selected]
                test.tick();test.tick(0x800 if expected==0 else 0,0x800 if expected==1 else 0)
                assert test.input_args[-1][2]==expected
                assert test.uc.mem_read(STATE+6,1)[0]==expected
                logical+=1

        # Use the original game's mapping-reorder function, rather than raw
        # RAM writes, to place two members of one owner in the active slots.
        # This exercises survivor routing; HP/faint events are not simulated.
        for remaining_owner in (0,1):
            test=fresh();test.enable()
            client,selected=(2,2) if remaining_owner==0 else (0,3)
            test.call(0x803C96D4,(test.call(0x803B0008),test.battle_data,client,selected))
            for slot in (0,1):
                member=test.call(0x803CC838,(0,slot))
                assert (0,1,0,1)[member]==remaining_owner
            test.tick();test.tick(0x800 if remaining_owner==0 else 0,0x800 if remaining_owner==1 else 0)
            assert test.input_args[-1][2]==remaining_owner
            survivor+=1

        for corrupt in ('missing_draft','different_session','slot','mode','empty_owner','bad_party_index'):
            test=fresh();test.enable()
            if corrupt=='missing_draft':test.uc.mem_write(STATE+9,b'\0')
            if corrupt=='different_session':test.put(STATE+0x1C,test.session+4)
            if corrupt=='slot':test.uc.mem_write(UI+0x64,b'\0\2')
            if corrupt=='mode':test.uc.mem_write(0x8062D600-0x671C,b'\x08')
            if corrupt=='empty_owner':test.uc.mem_write(STATE+10+test.slot,b'\xff')
            if corrupt=='bad_party_index':test.uc.mem_write(test.battle_data+0x312C+test.slot,b'\xff')
            original_state=test.ui_state();test.tick();test.tick(0x800,0x800)
            assert test.ui_state()==original_state and not test.input_args
            guards+=1

        # Every UI-open event gets a new epoch even for the same owner/mode.
        test=fresh();test.enable();mode=observations[-1]['mode']
        for _ in range(2):
            old=test.get(STATE+0x10);test.open_epoch(mode)
            assert test.get(STATE+0x10)==(old+1)&0xFFFFFFFF
            original_state=test.ui_state()
            test.tick(0x800 if owner==0 else 0,0x800 if owner==1 else 0)
            assert test.ui_state()==original_state and not test.input_args
            test.tick();epochs+=1
        # Campaign/other UI calls do not inherit the last actor's controller.
        test=fresh();test.enable();test.seed(0x800,0x400)
        assert test.call(ENTRY,(0x80000000,0,0,0))==0x800
        guards+=1
        for flag_offset in (0,4,8):
            test=fresh();test.enable();test.uc.mem_write(STATE+flag_offset,b'\0')
            old=test.get(STATE+0x10);test.open_epoch(mode)
            assert test.get(STATE+0x10)==old
            guards+=1
        test=fresh();test.enable();test.put(STATE+0x10,0xFFFFFFFF)
        test.open_epoch(mode);assert test.get(STATE+0x10)==0;epochs+=1

    assert {x['active_position'] for x in observations}=={0,1}
    return {'status':'passed','captured_interfaces':observations,
            'disabled_native_ui_comparisons':disabled,'native_ui_confirm_transitions':confirmed,
            'native_ui_cancel_transitions':cancelled,'logical_party_ownership_cases':logical,
            'guard_cases':guards,'same_actor_new_decision_epochs':epochs,
            'native_party_reorder_survivor_cases':survivor,
            'cursor_and_nonvolatile_registers_preserved':True,
            'native_actor_mapping_getter':'803cc838','input_stubs':[],
            'native_party_reorder_function':'803c96d4',
            'ui_feedback_sound_stub':'8005c04c (feedback ids 1, 2, 3 only)',
            'paired_single_context_instructions_skipped':[f'{x:08x}' for x in CURSOR_CONTEXT_PSQ],
            'dol_bytes_added':len(changed)-len(source),'prototype_dol_sha256':sha(changed),
            'activation':'Disabled at boot; explicit test owner table required',
            'limits':['Only the two registered command UI families captured here are routed automatically',
                      'Button caches, connection values and owner table are explicit test fixtures',
                      'Alternate mappings include fixtures and native reorder calls; no HP/faint simulation',
                      'Draft ownership, reserve restrictions, targets and battle lifecycle are unfinished',
                      'No physical-controller Dolphin test or NetPlay test; not a playable coop release'],
            'privacy':'No private state, RAM or roster included'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--captures',type=Path,nargs=2,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=verify(args.source.read_bytes(),args.captures)
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
