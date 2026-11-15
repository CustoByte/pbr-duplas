"""Independent decoded SDR motion/skin/UV checks. Blender: -- blend sdr addon contract report"""
import bpy,json,sys,contextlib,os,hashlib,struct
from pathlib import Path
from types import SimpleNamespace
from mathutils import Matrix,Vector,Euler
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'experiments/snivy'),str(ROOT/'mod-source')]
from graphics_common import load_pbr_addon
from pkx_reference import scene_inventory
blend,sdr,addon,contract,output=map(Path,sys.argv[sys.argv.index('--')+1:])
pbr=load_pbr_addon(SimpleNamespace(pbr_addon=addon,native_contract=None),register=False)
bpy.ops.wm.open_mainfile(filepath=str(blend));rig=bpy.data.objects['MegaCharizardY'];raw=sdr.read_bytes();scene=scene_inventory(raw);ref=json.loads(contract.read_text())['resources'][0]['actions']
assert [a['name'] for a in scene['actions']]==[a['name'] for a in ref]
for a,b in zip(scene['actions'],ref):
 assert a['flags']==b['flags'] and abs(a['length']-b['length'])<1/30+.00001
 for k in ('start','end'):assert abs(a[k]/a['length']-b[k]/b['length'])<1e-5
assert len(scene['nodes'])<256 and len(raw)<3*1024*1024
with open(os.devnull,'w') as quiet,contextlib.redirect_stdout(quiet):model=pbr.importer.parseModel(str(sdr))
skele=model['skeletons'][0];skin_nodes=[b for b in skele.bones if b.type==3]
report=dict(kind='offline native SDR roundtrip; not GPU gameplay',actions={},textures=[],bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),native_action_contract_preserved=True,node_indices_fit_model_table=True,gameplay_verified=False)
for aid,a in pbr.importer.anim_dict.items():
 name=a['name']
 if name.startswith('tx_'):continue
 rig.animation_data.action=bpy.data.actions['Body_'+name];end=round(rig.animation_data.action.frame_range[1]);frames=range(end+1);matrix_error=skin_error=0.;sampled_skin=[]
 for f in frames:
  bpy.context.scene.frame_set(f);world={}
  for bone in skele.bones:
   if bone.type==3:continue
   values=dict(location=list(bone.initialTrans),rotation_euler=list(bone.initialRot),scale=list(bone.initialScale))
   for c in a['bones'].get(bone.name,[]):
    prior=[k for k in c['keyframes'] if k['time']<=f/30+1e-6]
    if prior:values[c['component']][c['axis']-1]=prior[-1]['value']
   mat=Matrix.Translation(Vector(values['location']))@Euler(values['rotation_euler'],'XYZ').to_matrix().to_4x4()@Matrix.Diagonal((*values['scale'],1))
   if bone.parentIndex is not None:mat=world[skele.bones[bone.parentIndex].name]@mat
   world[bone.name]=mat
   if bone.name in rig.pose.bones:matrix_error=max(matrix_error,max(abs(v) for row in (mat-rig.pose.bones[bone.name].matrix) for v in row))
  if f%10==0 or f==end:
   sampled_skin.append(f)
   for skin in skin_nodes:
    mesh=bpy.data.objects[skin.name];decoded=model['meshes'][skin.meshIndex];evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    assert len(decoded.vertices)==len(mesh.data.vertices)
    for i,v in enumerate(decoded.vertices):
     position=Vector()
     for bi,weight in decoded.weights[i].items():
      bone=skele.bones[bi];position+=weight*(world[bone.name]@bone.inverseBindMatrix@Vector(v))
     skin_error=max(skin_error,(position-evaluated.data.vertices[i].co).length)
  if f==end:print('SDR_CHECK',name,matrix_error,skin_error,flush=True)
 report['actions'][name]=dict(frames=end+1,max_matrix_error=matrix_error,max_skin_error=skin_error,skin_sampled_frames=sampled_skin)
for mat in model['materials']:
 original=bpy.data.materials[mat.name];image=next(n.image for n in original.node_tree.nodes if n.type=='TEX_IMAGE');decoded=model['images'][model['textures'][mat.textureIndex].imageIndex]
 assert (decoded.width,decoded.height)==tuple(image.size)
 error=max(abs(a/255-b) for a,b in zip(decoded.pixels,image.pixels));report['textures'].append(dict(name=mat.name,max_channel_error=error))
def u16(at):return struct.unpack_from('>H',raw,at)[0]
def u32(at):return struct.unpack_from('>I',raw,at)[0]
def f32(at):return struct.unpack_from('>f',raw,at)[0]
def string(at):return raw[at:raw.index(b'\0',at)].decode('ascii')
tracks={}
for i in range(u16(30)):
 mat=u32(u32(20)+i*4);name=string(u32(mat));link=u32(mat+132);seen=set()
 while link:
  assert link not in seen;seen.add(link);action=scene['actions'][u16(link)]['name'];assert u16(link+2)==4
  for j in range(4):
   c=u32(link+4)+j*16;component,axis=raw[c+1],raw[c+2];track=u32(c+8);values=u32(track);keys=u32(track+16);points=[]
   for k in range(u16(track+20)):
    at=keys+k*12;index=u16(at+2);assert index<u16(track+8);points.append((f32(at+8),f32(values+4*index)))
   tracks[action,name,component,axis]=points
  link=u32(link+12)
uv_error=0.;uv_count=0;eye_tracks={}
for action in scene['actions']:
 name=action['name'];end=round(action['length']*30)
 for mat in model['materials']:
  original=bpy.data.materials[mat.name];eye=any(n.type=='TEX_IMAGE' and 'Eye1' in n.image.name for n in original.node_tree.nodes)
  for f in range(end+1):
   shift=0.
   if eye and name=='tx_sleep':shift=-.5
   if eye and name=='tx_wink':shift=(0,-.25,-.5,-.5,-.25,0)[min(5,round(f/end*5))]
   if eye and name=='tx_wakeup':shift=(-.5,-.25,0,0)[min(3,round(f/end*3))]
   for comp,axis,target in [(20,1,0),(20,2,1-shift),(22,1,1),(22,2,1)]:
    points=tracks[name,mat.name,comp,axis];prior=[v for t,v in points if t<=f/30+1e-6];assert prior;uv_error=max(uv_error,abs(prior[-1]-target));uv_count+=1
  if eye and name.startswith('tx_'):eye_tracks[name]=dict(length=action['length'],points=[dict(time=t,offset_v=v-1) for t,v in tracks[name,mat.name,20,2]])
report['uv_samples']=uv_count;report['max_uv_error']=uv_error;report['eye_review_tracks']=eye_tracks
report['passed']=all(v['max_matrix_error']<.0005 and v['max_skin_error']<.005 for v in report['actions'].values()) and all(t['max_channel_error']<.13 for t in report['textures']) and uv_error<1e-5
output.write_text(json.dumps(report,indent=2)+'\n')
if not report['passed']:raise RuntimeError('Native SDR roundtrip failed')
print('CHARIZARD_Y_SDR_ROUNDTRIP_OK',flush=True)
