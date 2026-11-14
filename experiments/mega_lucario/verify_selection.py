"""Execute actual four-pick selection/packing with Mega and Snivy in cloned RAM.

Uses the existing reconstructed selection-UI/controller fixture and bounded
constructor scratch allocator. No live UI, GPU or battle scene is exercised.
"""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(Path(__file__).resolve().parent),str(ROOT/'mod-source'),str(ROOT/'expansion'),str(ROOT/'experiments/snivy'),'/workspace/pbr-coop']
from verify_coop_draft import DraftReplay,PACK
from verify_integration import register
from unicorn import UC_HOOK_CODE,ppc_const as ppc

def verify(capture,integrated):
 h=DraftReplay(capture,(integrated/'main.dol').read_bytes());next_allocation=0x81C00000
 def scratch(u,address,size,unused):
  nonlocal next_allocation
  value=0
  if address in (0x801728E4,0x801DF6B4):
   n=u.reg_read(ppc.UC_PPC_REG_4 if address==0x801728E4 else ppc.UC_PPC_REG_3);assert 0<n<=0x20000
   value=next_allocation;next_allocation+=(n+31)&~31;assert next_allocation<0x81C80000;u.mem_write(value,bytes(n))
  u.reg_write(ppc.UC_PPC_REG_3,value);u.reg_write(ppc.UC_PPC_REG_PC,u.reg_read(ppc.UC_PPC_REG_LR))
 for a in (0x801728E4,0x801DF6B4,0x80172A14,0x801DF6FC):h.uc.hook_add(UC_HOOK_CODE,scratch,begin=a,end=a)
 base=h.get(0x80453184);passes=bytes(h.uc.mem_read(base,159*0x6EC));clone=0x81D00000;h.uc.mem_write(clone,passes);h.put(0x80453184,clone)
 register(h,(integrated/'common.fsys').read_bytes(),(integrated/'mes_common.fsys').read_bytes(),(integrated/'GSfsys.toc').read_bytes())
 rental=h.call(0x800E8594,(37,),limit=10000000);h.pool=bytes(h.uc.mem_read(rental,0x6EC));results=[]
 for coop in (False,):
  h.setup(coop)
  for slot in (0,1,2,3):assert h.choose(slot)==1
  h.call(PACK,(),limit=10000000)
  packed=h.packed();assert len(packed)==4
  expected=[h.pool[0x1FC+i*0x8C:0x1FC+i*0x8C+0x88] for i in (0,1,2,3)]
  # Co-op alternates the two players' chosen pairs: 0,2,1,3.
  if coop:expected=[expected[i] for i in (0,2,1,3)]
  assert packed==expected
  species=[]
  for record in packed:
   h.uc.mem_write(0x81D90000,record+bytes(4));species.append(h.call(0x803DE52C,(0x81D90000,5,0)))
  assert species[0:2]==[502,501];results.append(dict(coop=coop,selected_species=species,four_picks_packed=True))
 assert bytes(h.uc.mem_read(base,len(passes)))==passes
 return dict(passed=True,kind='native four-pick selection and packing in reconstructed UI fixture',modes=results,original_pass_memory_untouched=True,gameplay_verified=False)
if __name__=='__main__':
 capture,integrated,output=map(Path,sys.argv[1:]);r=verify(capture,integrated);output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
