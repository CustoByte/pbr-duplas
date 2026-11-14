"""Check serialized blink/sleep/wakeup UV tracks and native action contract."""
import json,struct,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'snivy'))
from pkx_reference import scene_inventory

def verify(data,reference):
 scene=scene_inventory(data)
 if scene['object_name']!='MegaLucarioSource':raise ValueError('Wrong scene')
 if len(data)>3*1024*1024:raise ValueError('Exceeds the existing 3 MiB conversion budget')
 if [a['name'] for a in scene['actions']]!=[a['name'] for a in reference]:raise ValueError('Action order differs')
 for a,b in zip(scene['actions'],reference):
  if a['flags']!=b['flags']:raise ValueError('Action flags differ')
  if a['name']=='damage' and abs(a['end']-a['length'])>1e-6:raise ValueError('Recovery would be cut short')
 for tex in scene['textures']:
  if any(v<=0 or v&(v-1) for v in (tex['width'],tex['height'])):raise ValueError('Non-power-of-two texture')
 def u16(at):return struct.unpack_from('>H',data,at)[0]
 def u32(at):return struct.unpack_from('>I',data,at)[0]
 def f32(at):return struct.unpack_from('>f',data,at)[0]
 def string(at):return data[at:data.index(b'\0',at)].decode('ascii')
 curves={}
 for i in range(u16(30)):
  mat=u32(u32(20)+i*4);material=string(u32(mat));link=u32(mat+132);seen=set()
  while link:
   if link in seen:raise ValueError('Cyclic material chain')
   seen.add(link);action=scene['actions'][u16(link)]['name']
   if u16(link+2)!=4:raise ValueError('Wrong UV channel count')
   for j in range(4):
    c=u32(link+4)+j*16;component,axis=data[c+1],data[c+2]
    if data[c+6:c+8]!=b'\0\0':raise ValueError('Wrong UV format')
    track=u32(c+8);values=u32(track);keys=u32(track+16);points=[]
    for k in range(u16(track+20)):
     at=keys+k*12;index=u16(at+2)
     if u16(at)!=0 or index>=u16(track+8):raise ValueError('Invalid UV key')
     points.append((f32(at+8),f32(values+index*4)))
    curves[action,material,component,axis]=points
   link=u32(link+12)
 count=0;max_error=0
 for action in scene['actions']:
  end=round(action['length']*30)
  for frame in range(end+1):
   for mat in ('Material #191','Material #192','Material #193'):
    shift=0.0
    if mat=='Material #193':
     if action['name']=='tx_sleep':shift=-0.75
     elif action['name']=='tx_wakeup':shift=-0.75*(1-frame/end)
     elif action['name']=='tx_wink' and 1<=frame<end:shift=-0.75
    for component,axis,target in ((20,1,0),(20,2,1-shift),(22,1,1),(22,2,1)):
     points=curves[action['name'],mat,component,axis]
     prior=[v for t,v in points if t<=frame/30+1e-6]
     if not prior:raise ValueError('Missing UV state')
     max_error=max(max_error,abs(prior[-1]-target));count+=1
 if max_error>1e-5:raise ValueError('Wrong serialized UV state')
 return dict(passed=True,actions=len(scene['actions']),nodes=len(scene['nodes']),
             uv_samples=count,max_uv_error=max_error,sdr_sha256=scene['sha256'],
             bytes=len(data),native_game_tested=False,effect_positions_calibrated=False)

if __name__=='__main__':
 sdr,contract,report=map(Path,sys.argv[1:])
 result=verify(sdr.read_bytes(),json.loads(contract.read_text())['resources'][0]['actions'])
 report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
