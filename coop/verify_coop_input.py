"""Replay native PBR input reads in private memory; hardware polling isn't run.

Controller-cache masks and connection fields are explicit test inputs. The
original game read, manager accessor and router execute in PPC without stubs.
"""
import argparse,json,struct,unittest
from pathlib import Path
from unicorn import UC_HOOK_CODE
from unicorn import ppc_const as ppc
from prepare_campaign_doubles import file_offset,sha
from verify_vm_wait import Replay
from coop_input_router import prepare_router,assemble,CODE,STATE,ENTRY,state_bytes
from test_coop_policy import PolicyTests

# Paired-single stack saves/restores in the cursor-coordinate helper. Scalar
# f30/f31 are separately saved/restored by the native stfd/lfd instructions.
# No cursor computation, game input, audio or controller getter is stubbed.
CURSOR_CONTEXT_PSQ=(0x8000AD80,0x8000AD88,0x8000AE88,0x8000AE90)

def allow_cursor_context(vm):
    def hook(u,a,size,data):
        if a in CURSOR_CONTEXT_PSQ:
            u.reg_write(ppc.UC_PPC_REG_PC,a+4)
    vm.uc.hook_add(UC_HOOK_CODE,hook)

def verify(source,changed,diagnostics):
    if changed!=prepare_router(source):raise AssertionError('Router is not reproducible')
    before,after=Replay(diagnostics,source),Replay(diagnostics,source)
    after.uc.mem_write(CODE,assemble());off=file_offset(changed,ENTRY);after.uc.mem_write(ENTRY,changed[off:off+4])
    machines=(before,after);manager=before.call(0x802492D8)
    for vm in machines:allow_cursor_context(vm)
    if before.call(0x80249310)!=2:raise AssertionError('Unexpected active pad count')
    def seed(p0,p1):
        for vm in machines:
            for port,mask in enumerate((p0,p1)):
                a=manager+0x38+port*0x928
                for offset,value in [(0x1C,mask),(0x20,mask),(0x3C,0),(0x40,3)]:vm.put(a+offset,value)
                vm.uc.mem_write(a+0xA1,b'\0')
    def read(vm,flags=0x80000000,port=0):
        value=vm.call(ENTRY,(flags,port,port,0))
        if vm.uc.reg_read(ppc.UC_PPC_REG_1)!=0x81F00000:raise AssertionError('Input router failed to restore stack')
        for i in range(14,32):
            if vm.uc.reg_read(getattr(ppc,f'UC_PPC_REG_{i}'))!=0:raise AssertionError('Input router broke PPC ABI')
        return value
    masks=(0,1,2,4,8,0x400,0x800,0x1000,0x8000,0xC00,0x1801)
    disabled=0;menus=0;owner_cases=0
    for p0 in masks:
        for p1 in masks:
            seed(p0,p1);after.uc.mem_write(STATE,bytes(32))
            for flags in(0x80000000,0x40000000):
                assert read(before,flags)==read(after,flags);disabled+=1
            after.uc.mem_write(STATE,state_bytes(enabled=1,phase=0,owner=1,epoch=1))
            assert read(after)==read(before);menus+=1
    for owner in(0,1):
        for phase in range(1,6):
            after.uc.mem_write(STATE,state_bytes(enabled=1,phase=phase,owner=owner,epoch=1))
            seed(0,0);assert read(after)==0
            for mask in masks:
                seed(mask if owner==0 else 0x400,mask if owner==1 else 0x800)
                for flags in(0x80000000,0x40000000):
                    assert read(after,flags)==read(before,flags,owner);owner_cases+=1
    # Handoff waits for release, including a second decision for the same
    # player after their partner has lost both Pokemon.
    after.uc.mem_write(STATE,state_bytes(enabled=1,phase=2,owner=1,epoch=10))
    seed(0x400,0x800);assert read(after)==0;assert read(after)==0
    seed(0x400,0);assert read(after)==0
    seed(0x400,0x800);assert read(after)==0x800
    after.put(manager+4,1);assert read(after)==0
    after.put(manager+4,2);assert read(after)==0
    seed(0x400,0);assert read(after)==0
    seed(0x400,0x800);assert read(after)==0x800
    after.put(STATE+0x10,11);assert read(after)==0
    seed(0x400,0);assert read(after)==0
    seed(0x400,0x800);assert read(after)==0x800
    # Disconnection doesn't give the choice to P1; reconnection requires release.
    other=manager+0x38+0x928;after.put(other+0x3C,0xFFFFFFFF)
    assert read(after)==0
    seed(0x400,0x800);assert read(after)==0
    seed(0x400,0);assert read(after)==0
    seed(0x400,0x800);assert read(after)==0x800
    # Leaving battle returns the same logical pad to P1 immediately.
    after.uc.mem_write(STATE,state_bytes(enabled=1,phase=0,owner=1,epoch=12))
    assert read(after)==0x400
    for phase,owner in[(255,0),(2,2)]:
        after.uc.mem_write(STATE,state_bytes(enabled=1,phase=phase,owner=owner,epoch=1));assert read(after)==0
    cursor_cases=0
    for owner in (0,1):
        for button in range(1,6):
            for mask,expected in [(0x800,0x80000000|button),(0x400,0xFFFFFFFF)]:
                for vm in machines:
                    for offset in (-0x6768,-0x6764,-0x6760):vm.put(0x8062D600+offset,0)
                after.uc.mem_write(STATE,state_bytes(enabled=1,phase=2,owner=owner,epoch=1))
                seed(0,0)
                # Native flags 0x08/0x20 suppress confirm/cancel feedback
                # sounds here; the cursor and input paths remain native.
                assert after.call(ENTRY,(0x29,button,0,0))==0
                seed(mask if owner==0 else 0,mask if owner==1 else 0)
                # In the real cursor API, r4 must remain the focused button.
                assert after.call(ENTRY,(0x29,button,0,0))==expected
                assert before.call(ENTRY,(0x29,button,owner,0))==expected
                cursor_cases+=1
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PolicyTests)
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():raise AssertionError('Ownership policy failed')
    return {'status':'passed','disabled_comparisons':disabled,'p1_only_menu_cases':menus,'routed_owner_phase_read_cases':owner_cases,
        'handoff_release_barrier':'passed','same_owner_next_actor_barrier':'passed','disconnect_no_fallback_to_p1':'passed',
        'cursor_confirm_cancel_cases':cursor_cases,'cursor_focus_preserved':'passed',
        'cursor_query_flags':'0x29 (native confirm/cancel sound suppression)',
        'paired_single_context_instructions_skipped':[f'{a:08x}' for a in CURSOR_CONTEXT_PSQ],
        'policy_tests':result.testsRun,'actual_game_input_functions':['8005b5ec','802492e0','802492d8','80249310'],
        'controller_count_in_supplied_state':2,'game_input_stubs':[],
        'changed_dol_sha256':sha(changed),'status_in_game':'Not integrated; disabled at boot',
        'limits':['Cached input/connection values seeded explicitly; no live controller polling',
            'No battle actor, draft or replacement UI hooks','No two-player Dolphin test','No online session test',
            'Policy model is not yet wired to the game; not a playable coop release']}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in('source','changed','diagnostics','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=verify(a.source.read_bytes(),a.changed.read_bytes(),a.diagnostics)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
