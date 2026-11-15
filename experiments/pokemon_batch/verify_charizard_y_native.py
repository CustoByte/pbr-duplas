"""Read-only fixture replay: native SDR allocation/relocation and model bindings.

No ISO is changed; this is not rendering or an actual battle.
"""
import argparse,json,sys,struct,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'mod-source'),str(ROOT/'experiments/snivy'),'/workspace/pbr-coop']
from prepare_campaign_doubles import read_archive
from pkx_reference import scene_inventory
from verify_vm_wait import Replay
from unicorn import UC_HOOK_CODE,ppc_const as ppc

def verify(capture,candidate,donor_inventory,common):
 raw=candidate.read_bytes();scene=scene_inventory(raw);donor=json.loads(donor_inventory.read_text())['resources'][0]
 assert len(raw)<3*1024*1024
 resources=dict(read_archive(common.read_bytes()));stats=resources[0x00810200];model_id=struct.unpack_from('>H',stats,48+6*52+28)[0];models=resources[0x00800200];row=models[48+model_id*72:48+(model_id+1)*72];assert struct.unpack_from('>I',row,8)[0]==0x07d20400
 names={n['index']:n['name'] for n in donor['nodes']};target={n['name']:n['index'] for n in scene['nodes']};actions={a['name']:a['index'] for a in scene['actions']}
 node_bindings=[0 if n==0 else target[names[n]] for n in row[25:50]]
 action_bindings=[actions[donor['actions'][a]['name']] for a in row[50:72]]
 assert max(node_bindings)<256 and set(action_bindings)==set(range(15))
 h=Replay(capture)
 for address in (0x8026F024,0x8026F054,0x8026F084):h.uc.hook_add(UC_HOOK_CODE,lambda u,a,s,d:u.reg_write(ppc.UC_PPC_REG_PC,a+4),begin=address,end=address)
 archive,rid=0x2000,0x63ea0400
 assert h.get(0x80bbe1a8)==archive,'Unexpected captured FSYS descriptor'
 at=h.call(0x80008cc8,(archive,rid,len(raw)),limit=3000000);assert at
 h.uc.mem_write(at,raw)
 assert h.call(0x80008d80,(archive,rid,len(raw)),limit=30000000)==at
 assert h.call(0x801e00fc,(archive,rid))==at
 assert h.call(0x80039254,(archive,rid),limit=1000000)>0
 obj=h.get(h.get(at+8));assert at<=obj<at+len(raw)
 action_count=struct.unpack('>H',bytes(h.uc.mem_read(obj+8,2)))[0];assert action_count==15
 action_table=h.get(obj+12);assert at<=action_table<at+len(raw)
 for i,a in enumerate(scene['actions']):
  pointer=h.get(action_table+i*48);assert at<=pointer<at+len(raw)
  name=bytes(h.uc.mem_read(pointer,len(a['name'])+1));assert name==a['name'].encode()+b'\0'
 return dict(passed=True,kind='native resource allocation/SDR relocation and original Charizard model-table binding analysis',bytes=len(raw),sdr_sha256=hashlib.sha256(raw).hexdigest(),native_allocation=f'{at:08x}',relocated_action_count=action_count,native_resource_ready=True,node_bindings_checked=len(node_bindings),animation_bindings_checked=len(action_bindings),all_fifteen_actions_referenced=True,maximum_bound_node_index=max(node_bindings),fixture_only_resource_identity=f'{archive:04x}/{rid:08x}',fixture_changes=['reuse captured resource descriptor for isolated candidate','skip OS cache-maintenance calls in coherent Unicorn memory'],no_new_species_installed=True,disc_io_verified=False,gpu_render_verified=False,gameplay_verified=False)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for key in ('capture','candidate','donor-inventory','common','output'):p.add_argument('--'+key,type=Path,required=True)
 a=p.parse_args();r=verify(a.capture,a.candidate,a.donor_inventory,a.common);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
