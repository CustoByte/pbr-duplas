"""Replay native delivery/model dispatch on a private clone, never a save file.

Uses the original menu capture and native constructors/getters. Allocation/free
use the existing bounded scratch fixture; GPU/Dolphin gameplay is not simulated.
"""
import json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'mod-source'),str(ROOT/'expansion'),str(ROOT/'experiments/snivy'),'/workspace/pbr-coop']
from prepare_campaign_doubles import read_archive,sha
from verify_pass_delivery import MenuReplay
from catalog import relocate
from translation.messages import read_messages,readable
from unicorn import ppc_const as ppc

def register(h,common,messages,catalog):
 refs={0x00810200:0x80625184,0x00800200:0x80625174,0x007D0200:0x80625178,0x16410200:0x806251C0,0x1D9D0200:0x806251D8,0x00820200:0x80625188,0x12A90200:0x806251BC}
 resources=dict(read_archive(common))
 for slot,(rid,ref) in enumerate(refs.items()):
  table=resources[rid];count,stride=struct.unpack_from('>II',table);obj=bytearray(h.uc.mem_read(h.get(ref),48))
  at,data=0x81B00000+slot*0x100,0x81810000+slot*0x10000;rows=table[48:48+count*stride]
  for off,v in ((0,count),(8,data),(16,data),(20,len(rows)),(24,data+len(rows))):struct.pack_into('>I',obj,off,v)
  h.uc.mem_write(at,bytes(obj));h.uc.mem_write(data,rows);h.put(ref,at)
 context=0x8048062C;mapping=resources[0x008B0000]
 h.uc.mem_write(0x92C00000,dict(read_archive(messages))[0x27C10000]);h.uc.mem_write(0x92E00000,mapping)
 h.put(context+0x64F34,0x92C00000);h.put(context+0xD34,struct.unpack_from('>I',mapping,4)[0]);h.put(context+0xD38,0x92E00008)
 h.uc.mem_write(0x81B80000,relocate(catalog,0x81B80000));h.put(0x80627B5C,0x81B80000)

def verify(capture,baseline,integrated):
 old=baseline.read_bytes();dol=(integrated/'main.dol').read_bytes();h=MenuReplay(capture,old,dol)
 base=h.get(0x80453184);before=bytes(h.uc.mem_read(base,159*0x6EC));clone=0x81D00000
 h.uc.mem_write(clone,before);h.put(0x80453184,clone)
 h.call(0x800E8594,(0,),limit=10000000)
 assert bytes(h.uc.mem_read(clone,len(before)))==before,'Readiness guard failed'
 common=(integrated/'common.fsys').read_bytes();messages=(integrated/'mes_common.fsys').read_bytes();catalog=(integrated/'GSfsys.toc').read_bytes()
 register(h,common,messages,catalog)
 h.call(0x800E8594,(0,),limit=10000000)
 after=bytes(h.uc.mem_read(clone,len(before)));changed=[i for i in range(159) if before[i*0x6EC:(i+1)*0x6EC]!=after[i*0x6EC:(i+1)*0x6EC]]
 print('CHANGED_PASSES',changed,flush=True)
 records=[]
 for pi,slot in [(37,0),(37,1),(0,0),(37,2)]:
  mon=clone+pi*0x6EC+0x1FC+slot*0x8C
  get=lambda f:h.call(0x803DE52C,(mon,f,0))
  r=dict(pass_index=pi,slot=slot,species=get(5),level=get(160),moves=[get(f) for f in range(0x36,0x3a)],pp=[get(f) for f in range(0x3a,0x3e)],ability=get(10),item=get(6),nature=get(0)%25,ivs=[get(f) for f in range(0x46,0x4c)],evs=[get(f) for f in range(0xD,0x13)],presence=h.call(0x80058C34,(mon,)),illegal=h.call(0x80058E8C,(mon,)))
  dest=0x81D90000;h.uc.mem_write(dest,bytes(0xA4));h.call(0x803DFD78,(mon,dest),limit=3000000)
  r['stats_hp_atk_def_speed_spatk_spdef']=[h.call(0x803E100C,(dest,f,0)) for f in range(163,169)]
  records.append(r);print('RECORD',json.dumps(r),flush=True)
 assert changed==[0,37]
 mega,snivy,little,charizard=records
 assert mega['species']==502 and mega['level']==50 and mega['moves']==[418,370,396,182] and mega['ability']==91 and mega['item']==0
 assert mega['pp']==[30,5,20,10]
 assert mega['nature']==0 and mega['stats_hp_atk_def_speed_spatk_spdef']==[146,181,108,163,176,90]
 assert mega['presence']==1 and mega['illegal']==0
 assert charizard['species']==503 and charizard['level']==50 and charizard['ability']==70 and charizard['item']==0
 assert charizard['moves']==[53,403,76,182] and charizard['nature']==10
 assert charizard['pp']==[15,20,10,10]
 assert charizard['stats_hp_atk_def_speed_spatk_spdef']==[148,107,93,115,150,110]
 assert charizard['ivs']==[20]*6 and charizard['evs']==[0]*6
 assert charizard['presence']==1 and charizard['illegal']==0
 assert snivy['species']==501 and snivy['level']==50 and little['species']==501 and little['level']==5
 from runtime_layer import target
 previous=Path('/workspace/pbr-coop/work/mega-name-fix')
 prior=MenuReplay(capture,old,(previous/'main.dol').read_bytes())
 register(prior,*[(previous/n).read_bytes() for n in ('common.fsys','mes_common.fsys','GSfsys.toc')])
 prior.call(0x800E8594,(0,),limit=10000000)
 oldbase=prior.get(0x80453184)
 for slot in (0,1,3,4,5):
  at=37*0x6EC+0x1FC+slot*0x8C
  assert bytes(prior.uc.mem_read(oldbase+at,140))==bytes(h.uc.mem_read(clone+at,140))
 h.call(0x800E8594,(0,),limit=10000000);assert bytes(h.uc.mem_read(clone,len(before)))==after,'Repeated delivery reset pass'
 assert bytes(h.uc.mem_read(base,len(before)))==before,'Original capture pass memory changed'
 # Native table and catalog getters, including preserved Snivy.
 for species,index,archive in ((448,569,5448),(501,670,8192),(502,671,8193),(503,672,8194)):
  assert h.call(0x80396B74,(0x80625184,species))==index
  assert h.call(0x80395E90,(0x80625174,index))==archive
  ptr=h.call(0x8024C32C,(archive,));assert ptr!=0 and h.get(ptr)==archive
 # Every native effect/action role must reference the corresponding candidate node/action.
 from pkx_reference import scene_inventory
 assets=dict(read_archive((integrated/'pkx_503.fsys').read_bytes()));scene=scene_inventory(assets[0x73EC0400])
 for role in range(25):assert h.call(0x80395DE8,(0x80625174,672,role))<len(scene['nodes'])
 for role in range(22):assert h.call(0x80395E3C,(0x80625174,672,role))<len(scene['actions'])
 # Name thunk returns correct global IDs and unchanged legacy dispatch.
 for species in (1,448,493,494,495,500,501,502,503,65535):
  assert h.call(0x803E3458,(2,species))==({501:21775,502:21776,503:21777}.get(species,species+10))
 # Both arena aliases protect the entire extra payload.
 for setter in (0x8026EABC,0x8026EACC):assert h.call(setter,(0x80640000,))==0x80658000
 return dict(passed=True,kind='native PPC replay on private cloned pass memory, not Dolphin gameplay',records=records,changed_passes=changed,readiness_guard=True,idempotent_delivery=True,original_capture_memory_untouched=True,snivy_and_little_pass_preserved=True,model_catalog_chain_verified=True,effect_roles_verified=25,action_roles_verified=22,dol_sha256=sha(dol),gameplay_verified=False,save_file_modified=False)

if __name__=='__main__':
 capture,baseline,integrated,output=map(Path,sys.argv[1:]);r=verify(capture,baseline,integrated);output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
