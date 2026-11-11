"""Replay the reported introduction deadlock using actual savestate memory.

Native VM reset/start/readiness/interpreter execute in PPC. Allocation during
constructor tests and the script's debug print are explicit stubs. Only two
paired-single context-save/load instructions are skipped by scalar Unicorn.
No graphics, battle simulation or save-state execution inside Dolphin.
"""
import argparse,json,struct
from pathlib import Path
from unicorn import Uc,UC_ARCH_PPC,UC_MODE_32,UC_MODE_BIG_ENDIAN,UC_HOOK_CODE
from unicorn import ppc_const as ppc
from prepare_campaign_doubles import file_offset,word

STOP=0x81FFF000
VM=0x80BA2D40
TASK=0x80BA4400
CALLBACK=0x81199B74
GATE=0x81199E1C


class Replay:
    def __init__(self, diagnostics, dol=None):
        self.uc=Uc(UC_ARCH_PPC,UC_MODE_32|UC_MODE_BIG_ENDIAN)
        for name,base in [('mem1.bin',0x80000000),('mem2.bin',0x90000000)]:
            data=(diagnostics/name).read_bytes();self.uc.mem_map(base,len(data));self.uc.mem_write(base,data)
        if dol:
            # Only overlay declared v7 changes, keeping actual runtime data/code.
            original=(diagnostics/'mem1.bin').read_bytes()
            addresses=[0x8022DF50,0x8022E1C8]+list(range(0x80077060,0x80077070,4))
            # Include the optional v8 appearance layer so shared-space
            # regressions execute the exact distributed code, not just v7.
            if word(dol,file_offset(dol,0x803DF700))==0x9421FFD0:
                from rental_shiny_asm import assemble as shiny_words
                addresses+=list(shiny_words())
            for a in addresses:self.uc.mem_write(a,dol[file_offset(dol,a):file_offset(dol,a)+4])
        self.allocate=False;self.allocations=[];self.log_calls=0
        self.uc.reg_write(ppc.UC_PPC_REG_MSR,0x2000)
        self.uc.hook_add(UC_HOOK_CODE,self.hook)

    def hook(self,u,a,size,data):
        if a in(0x8022F8C0,0x8022F9A4):
            u.reg_write(ppc.UC_PPC_REG_PC,a+4);return
        if self.allocate and a==0x801DF6B4:
            size=u.reg_read(ppc.UC_PPC_REG_3)
            if size not in(0x800,0x200):raise AssertionError('Unexpected constructor allocation')
            dest=0x81C00000+len(self.allocations)*0x2000
            self.allocations.append(size)
            u.mem_write(dest,bytes(size));u.reg_write(ppc.UC_PPC_REG_3,dest)
            u.reg_write(ppc.UC_PPC_REG_PC,u.reg_read(ppc.UC_PPC_REG_LR));return
        if a==0x80230D38 and u.reg_read(ppc.UC_PPC_REG_4)==0 and u.reg_read(ppc.UC_PPC_REG_5)==0x88:
            # Script debug-print primitive. No gameplay callback is substituted.
            out=u.reg_read(ppc.UC_PPC_REG_7);u.mem_write(out,b'\0\1\0\0'+bytes(4))
            self.log_calls+=1;u.reg_write(ppc.UC_PPC_REG_3,0)
            u.reg_write(ppc.UC_PPC_REG_PC,u.reg_read(ppc.UC_PPC_REG_LR))

    def put(self,a,value):self.uc.mem_write(a,struct.pack('>I',value))
    def get(self,a):return word(self.uc.mem_read(a,4),0)

    def call(self,address,args=(),limit=500000):
        for i in range(32):self.uc.reg_write(getattr(ppc,f'UC_PPC_REG_{i}'),0)
        for i,v in {1:0x81F00000,2:0x806308E0,13:0x8062D600}.items():self.uc.reg_write(getattr(ppc,f'UC_PPC_REG_{i}'),v)
        self.uc.reg_write(ppc.UC_PPC_REG_LR,STOP);self.uc.reg_write(ppc.UC_PPC_REG_CR,0)
        for i,v in enumerate(args,3):self.uc.reg_write(getattr(ppc,f'UC_PPC_REG_{i}'),v)
        self.uc.emu_start(address,STOP,count=limit)
        if self.uc.reg_read(ppc.UC_PPC_REG_PC)!=STOP:raise AssertionError('Native replay instruction limit')
        return self.uc.reg_read(ppc.UC_PPC_REG_3)


def verify(diagnostics,changed_dol):
    before=Replay(diagnostics);after=Replay(diagnostics,changed_dol)
    observed={'wait_type':before.uc.mem_read(TASK+0x16C,1)[0],
              'flag_index':before.uc.mem_read(TASK+0x16D,1)[0],
              'expected_flag':before.get(TASK+0x170),'callback_pc':f'{before.get(TASK+0xC):08x}'}
    if observed!={'wait_type':2,'flag_index':138,'expected_flag':357088,'callback_pc':'81199b74'}:
        raise AssertionError('Replay does not match reported stalled callback')
    if before.call(0x8022E1E4,(TASK,))!=0:raise AssertionError('Captured task unexpectedly runnable')
    callback_results=[]
    for vm in(before,after):
        # Release that slot and let the real native start/reset functions reuse it.
        vm.put(TASK,0)
        if vm.call(0x8022F2F0,(VM,CALLBACK,0x81E00000,0x81E00004))!=1:raise AssertionError('Native callback start failed')
        token=vm.get(0x81E00004)
        ready=vm.call(0x8022E1E4,(TASK,))
        vm.call(0x8022F8B0,(VM,token))
        for _ in range(3):
            if not ready or vm.get(TASK)==0:break
            vm.call(0x8022F8B0,(VM,token))
        callback_results.append({'ready':ready,'gate_value':vm.get(GATE),'task_state':vm.get(TASK),'debug_prints':vm.log_calls})
    if callback_results[0]!=dict(ready=0,gate_value=0,task_state=1,debug_prints=0):raise AssertionError(callback_results)
    if callback_results[1]!=dict(ready=1,gate_value=1,task_state=0,debug_prints=1):raise AssertionError(callback_results)
    resets=0;constructors=0
    scratch=0x81D00000
    for kind in(0,1,2,3,255):
        for index in(*range(16),16,138,255):
            for expected in(0,1,357088):
                after.uc.mem_write(scratch,b'\xCC'*0x1A0)
                for off,val in[(0x154,0x81C00000),(0x158,0x100),(0x15C,0x81C02000),(0x160,0x80),(0x174,VM)]:after.put(scratch+off,val)
                after.uc.mem_write(scratch+0x16C,bytes([kind,index,0xCC,0xCC]));after.put(scratch+0x170,expected)
                after.call(0x8022E14C,(scratch,))
                if bytes(after.uc.mem_read(scratch+0x16C,8))!=bytes(8):raise AssertionError('Stale wait fields remain after reset')
                for off,val in[(0x154,0x81C00000),(0x158,0x100),(0x15C,0x81C02000),(0x160,0x80),(0x174,VM)]:
                    if after.get(scratch+off)!=val:raise AssertionError('Reset destroyed allocation/owner fields')
                if bytes(after.uc.mem_read(scratch+0x184,0x1C))!=b'\xCC'*0x1C:raise AssertionError('Reset exceeds task allocation')
                resets+=1
    for vm in(before,after):
        vm.allocate=True;vm.allocations=[]
        vm.uc.mem_write(scratch,b'\xCC'*0x1A0)
        vm.uc.mem_write(scratch+0x16C,b'\x02\x8A\x40\0');vm.put(scratch+0x170,357088)
        vm.call(0x8022DF44,(scratch,))
        if vm is after:
            if vm.get(scratch+0x16C)!=0 or vm.get(scratch+0x170)!=0:raise AssertionError('Constructor left stale waits')
            if vm.uc.mem_read(scratch+0x184,0x1C)!=b'\xCC'*0x1C:raise AssertionError('Constructor exceeds 0x184 bytes')
        else:
            if vm.get(scratch+0x16C)!=0x028A4000:raise AssertionError('Baseline constructor mismatch')
        vm.allocate=False;constructors+=1
    # Active legitimate waits are still checked by the untouched native predicate.
    waits=0
    for kind in(1,2):
        for index in range(16):
            for flag in(0,1,255):
                results=[]
                for vm in(before,after):
                    vm.uc.mem_write(TASK+0x16C,bytes([kind,index,0,0]));vm.put(TASK+0x170,1)
                    vm.uc.mem_write(VM+0x918+index,bytes([flag]));vm.put(TASK,1)
                    results.append(vm.call(0x8022E1E4,(TASK,)))
                if results[0]!=results[1]:raise AssertionError('Active wait semantics changed')
                waits+=1
    return {'status':'passed','source_state':'Dolphin 2506-25 / RPBE01 user-provided freeze',
            'observed_deadlock':observed,'native_callback_before_after':callback_results,
            'dirty_task_reset_cases':resets,'constructor_cases':constructors,'active_wait_regression_cases':waits,
            'archive_strategy':'Original common.fsys size/offsets preserved by in-place compression',
            'stubs':['VM constructor allocation only','Script debug-print primitive'],
            'skipped_context_instructions':['8022f8c0','8022f9a4'],
            'limits':['Isolated PPC replay of captured memory, not full Dolphin continuation',
                      'No rendered battle or portrait validation','No real save persistence test']}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--diagnostics',type=Path,required=True);p.add_argument('--work',type=Path,required=True)
    args=p.parse_args();report=verify(args.diagnostics,(args.work/'main.dol').read_bytes())
    (args.work/'vm-wait-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
