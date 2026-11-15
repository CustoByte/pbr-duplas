"""Exercise the real resource allocator and SDR relocation with both added models.

The fixture changes one captured FSYS handle's ID/metadata to the new archive;
no disc I/O is claimed. OS cache-maintenance syscalls are skipped because Unicorn
memory is coherent. Game allocation, resource parsing and readiness stay native.
"""
import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'mod-source'),str(ROOT/'experiments/snivy'),'/workspace/pbr-coop']
from prepare_campaign_doubles import word,sha,read_archive
from verify_vm_wait import Replay
from unicorn import UC_HOOK_CODE,ppc_const as ppc

def verify(capture,snivy_path,mega_path,archive_path,charizard_path,charizard_archive):
 h=Replay(capture);handle=0x80BBE1A8
 assert h.get(handle)==0x2000 and h.get(handle+0x14)==12
 for address in (0x8026F024,0x8026F054,0x8026F084):
  h.uc.hook_add(UC_HOOK_CODE,lambda u,a,s,d:u.reg_write(ppc.UC_PPC_REG_PC,a+4),begin=address,end=address)
 snivy=snivy_path.read_bytes();mega=mega_path.read_bytes()
 def load(archive,rid,data):
  assert len(data)<3*1024*1024
  at=h.call(0x80008CC8,(archive,rid,len(data)),limit=3000000)
  assert at!=0,('Native allocation failed',hex(archive),len(data))
  h.uc.mem_write(at,data)
  assert h.call(0x80008D80,(archive,rid,len(data)),limit=30000000)==at
  assert h.call(0x801E00FC,(archive,rid))==at
  refs=h.call(0x80039254,(archive,rid),limit=1000000);assert refs>0
  return at
 a=load(0x2000,0x63EA0400,snivy)
 # Keep Snivy's actual allocation resident; change only the fixture's FSYS
 # descriptor to the new archive to exercise the second native allocation.
 data=archive_path.read_bytes();assert dict(read_archive(data))[0x73EB0400]==mega
 h.put(handle,0x2001);h.uc.mem_write(h.get(handle+0x20),data[:word(data,28)])
 b=load(0x2001,0x73EB0400,mega)
 assert b+len(mega)<=a or a+len(snivy)<=b,'Overlapping model allocations'
 data=charizard_archive.read_bytes();charizard=charizard_path.read_bytes();assert dict(read_archive(data))[0x73EC0400]==charizard
 h.put(handle,0x2002);h.uc.mem_write(h.get(handle+0x20),data[:word(data,28)]);c=load(0x2002,0x73EC0400,charizard)
 for p,size in ((a,len(snivy)),(b,len(mega))):assert c+len(charizard)<=p or p+size<=c
 return dict(charizard=dict(bytes=len(charizard),sha256=sha(charizard),allocation=f'{c:08x}'),three_allocations_resident=True,passed=True,kind='native resource allocation/SDR relocation in captured RAM, not Dolphin gameplay',
  snivy=dict(bytes=len(snivy),sha256=sha(snivy),allocation=f'{a:08x}'),
  mega=dict(bytes=len(mega),sha256=sha(mega),allocation=f'{b:08x}'),
  both_allocations_resident=True,mega_resource_ready=True,allocations_non_overlapping=True,
  fixture_changes=['one FSYS descriptor ID and metadata','skip coherent-memory OS cache-maintenance syscalls'],
  disc_io_verified=False,gpu_render_verified=False,gameplay_verified=False)
if __name__=='__main__':
 capture,snivy,mega,archive,charizard,charizard_archive,output=map(Path,sys.argv[1:]);r=verify(capture,snivy,mega,archive,charizard,charizard_archive);output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
