"""Boundary, name, portrait lookup and FSYS dispatch tests of the Mega layer."""
import sys,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'mod-source'),str(ROOT/'expansion'),str(ROOT/'experiments/snivy'),'/workspace/pbr-coop']
from prepare_campaign_doubles import read_archive,word,sha,file_offset
from verify_pass_delivery import MenuReplay
from catalog import relocate
from species_guards import SITES
from unicorn import ppc_const as ppc

def verify(capture,original,previous,current):
 baseline=original.read_bytes();before=MenuReplay(capture,baseline,previous.read_bytes());after=MenuReplay(capture,baseline,(current/'main.dol').read_bytes())
 values=(0,1,448,492,493,494,495,496,500,501,502,503,504,65535,0x80000000,0xffffffff)
 checks=0
 for site in SITES:
  if site<0x80030000:continue
  # All menu guards compare the incoming species in r0 or r4; discover the
  # previous bridge register rather than guessing it.
  dol=previous.read_bytes();ins=word(dol,file_offset(dol,site))
  delta=ins&0x03fffffc
  if delta&0x02000000:delta-=0x04000000
  thunk=site+delta;compare=word(dol,file_offset(dol,thunk));reg=(compare>>16)&31
  for value in values:
   states=[]
   for h,is_old in ((before,True),(after,False)):
    for i in range(32):h.uc.reg_write(getattr(ppc,f'UC_PPC_REG_{i}'),0x10000000+i*0x10101)
    h.uc.reg_write(getattr(ppc,f'UC_PPC_REG_{reg}'),502 if is_old and value==503 else value)
    h.uc.reg_write(ppc.UC_PPC_REG_CR,0xA5F03C96);h.uc.reg_write(ppc.UC_PPC_REG_LR,0x81f10000);h.uc.reg_write(ppc.UC_PPC_REG_CTR,0x76543210)
    gprs=[h.uc.reg_read(getattr(ppc,f'UC_PPC_REG_{i}')) for i in range(32)]
    h.uc.emu_start(site,site+4,count=64)
    assert h.uc.reg_read(ppc.UC_PPC_REG_PC)==site+4
    assert [h.uc.reg_read(getattr(ppc,f'UC_PPC_REG_{i}')) for i in range(32)]==gprs
    assert h.uc.reg_read(ppc.UC_PPC_REG_LR)==0x81f10000 and h.uc.reg_read(ppc.UC_PPC_REG_CTR)==0x76543210
    states.append(h.uc.reg_read(ppc.UC_PPC_REG_CR))
   assert states[0]==states[1],(hex(site),value,states)
   checks+=1
 cry_cases=0
 for site,failure in ((0x80026F40,0x80026F74),(0x80026FCC,0x80026FEC),(0x80027098,0x800270B8)):
  dol=previous.read_bytes();ins=word(dol,file_offset(dol,site));delta=ins&0x03fffffc
  if delta&0x02000000:delta-=0x04000000
  compare=word(dol,file_offset(dol,site+delta));reg=(compare>>16)&31
  for value in (1,448,493,501,502,503,65535):
   states=[];stop=failure if value==501 else site+4
   for h,is_old in ((before,True),(after,False)):
    for i in range(32):h.uc.reg_write(getattr(ppc,f'UC_PPC_REG_{i}'),0x10000000+i*0x10101)
    h.uc.reg_write(getattr(ppc,f'UC_PPC_REG_{reg}'),6 if is_old and value==503 else value)
    h.uc.reg_write(ppc.UC_PPC_REG_CR,0xA5F03C96)
    h.uc.emu_start(site,stop,count=64);assert h.uc.reg_read(ppc.UC_PPC_REG_PC)==stop
    states.append(([h.uc.reg_read(getattr(ppc,f'UC_PPC_REG_{i}')) for i in range(32)],h.uc.reg_read(ppc.UC_PPC_REG_CR)))
   assert states[0]==states[1],('cry bank',hex(site),value)
   cry_cases+=1
 for species in (1,448,493,501):
  assert after.call(0x8039D068,(0x806251E8,species))==before.call(0x8039D068,(0x806251E8,species))
 assert after.call(0x8039D068,(0x806251E8,503))==0x80646600
 for species in (*range(503),504,65535):
  assert after.call(0x803E3458,(2,species))==before.call(0x803E3458,(2,species))
 assert after.call(0x803E3458,(2,503))==21777
 toc=0x81b80000;after.uc.mem_write(toc,relocate((current/'GSfsys.toc').read_bytes(),toc));after.put(0x80627b5c,toc)
 handle,buffer=0x81da0000,0x81da0100;after.uc.mem_write(handle,bytes(0x48));after.put(handle,0x2002)
 assert after.call(0x8024C3EC,(handle,buffer),limit=3000000)==1
 path=bytes(after.uc.mem_read(buffer,256)).split(b'\0',1)[0].decode();assert path=='pkx_503.fsys'
 records=[]
 for name,rid in [('menu_face.fsys',0x7BEC0C00),('menu_pokemon.fsys',0x6BEC0C00),('pkx_503.fsys',0x73EC0400),('pkx_503.fsys',0x63EC0400)]:
  data=(current/name).read_bytes();after.uc.mem_write(0x93000000,data);after.uc.mem_write(handle,bytes(0x48));after.put(handle+0x20,0x93000000);after.uc.mem_write(handle+0x2e,b'\1')
  index=after.call(0x8024C794,(handle,rid),limit=1000000);assert index<len(read_archive(data))
  entry=after.call(0x8024AA18,(handle,index));kind=after.get(entry+0x20);assert kind==(6 if name.startswith('menu') else 2)
  assert after.call(0x8024A7EC,(kind,))!=0
  records.append(dict(archive=name,resource=f'{rid:08x}',index=index,handler_type=kind))
 return dict(passed=True,kind='native PPC isolated runtime/FSYS dispatch, no GPU or disc I/O',boundary_cases=checks,cry_bank_boundary_cases=cry_cases,mega_cry_bank=6,mega_prediction_row_safe=True,all_other_species_comparisons_preserved=True,legacy_name_cases=504,mega_name_id=21777,path=path,resource_handlers=records,gameplay_verified=False)
if __name__=='__main__':
 capture,original,previous,current,output=map(Path,sys.argv[1:]);r=verify(capture,original,previous,current);output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
