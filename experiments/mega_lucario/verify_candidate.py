"""Independent SDR matrix, skin and texture roundtrip checks, outside Dolphin.

Blender: -- candidate.blend candidate.sdr pbr-addon report.json
"""
import bpy,sys,json,contextlib,os,hashlib
from pathlib import Path
from types import SimpleNamespace
from mathutils import Matrix,Vector,Euler
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'snivy'))
from graphics_common import load_pbr_addon
blend,sdr,addon,output=map(Path,sys.argv[sys.argv.index('--')+1:])
pbr=load_pbr_addon(SimpleNamespace(pbr_addon=addon,native_contract=None),register=False)
bpy.ops.wm.open_mainfile(filepath=str(blend))
with open(os.devnull,'w') as quiet,contextlib.redirect_stdout(quiet):
 model=pbr.importer.parseModel(str(sdr))
skele=model['skeletons'][0];rig=bpy.data.objects['MegaLucarioSource'];mesh=bpy.data.objects['MegaLucarioMesh']
scene=bpy.context.scene
report=dict(kind='offline SDR roundtrip, not Dolphin gameplay',sha256=hashlib.sha256(sdr.read_bytes()).hexdigest(),size=sdr.stat().st_size,actions={},textures=[],gameplay_verified=False)
for aid,action in pbr.importer.anim_dict.items():
 name=action['name']
 if name.startswith('tx_'):continue
 rig.animation_data.action=bpy.data.actions['Mega_'+name]
 end=round(rig.animation_data.action.frame_range[1])
 frames=list(range(end+1)) if name in ('wait','damage') else sorted({0,end//2,end})
 matrix_error=skin_error=0.0
 worst=None
 for frame in frames:
  scene.frame_set(frame);evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
  world={}
  for bone in skele.bones:
   if bone.type==3:continue
   values=dict(location=list(bone.initialTrans),rotation_euler=list(bone.initialRot),scale=list(bone.initialScale))
   for curve in action['bones'].get(bone.name,[]):
    selected=None
    for key in curve['keyframes']:
     if key['time']<=frame/30+1e-6:selected=key
    if selected is not None:values[curve['component']][curve['axis']-1]=selected['value']
   mat=Matrix.Translation(Vector(values['location']))@Euler(values['rotation_euler'],'XYZ').to_matrix().to_4x4()@Matrix.Diagonal((*values['scale'],1))
   if bone.parentIndex is not None:mat=world[skele.bones[bone.parentIndex].name]@mat
   world[bone.name]=mat
   if bone.name in rig.pose.bones:
    target=rig.pose.bones[bone.name].matrix
    err=max(abs(v) for row in (mat-target) for v in row)
    if err>matrix_error:matrix_error=err;worst=(frame,bone.name)
  decoded=model['meshes'][0]
  if len(decoded.vertices)!=len(mesh.data.vertices):raise ValueError('Vertex count changed')
  for i,v in enumerate(decoded.vertices):
   point=Vector(v);position=Vector((0,0,0))
   for bi,weight in decoded.weights[i].items():
    b=skele.bones[bi];position+=weight*(world[b.name]@b.inverseBindMatrix@point)
   skin_error=max(skin_error,(position-evaluated.data.vertices[i].co).length)
 report['actions'][name]=dict(sampled_frames=frames,max_matrix_error=matrix_error,max_vertex_error=skin_error,worst_matrix=worst)
 print('VERIFIED',name,matrix_error,skin_error,flush=True)
for mat in model['materials']:
 original=bpy.data.materials[mat.name]
 image=next(n.image for n in original.node_tree.nodes if n.type=='TEX_IMAGE')
 decoded=model['images'][model['textures'][mat.textureIndex].imageIndex]
 pixels=list(image.pixels)
 if (decoded.width,decoded.height)!=tuple(image.size) or len(pixels)!=len(decoded.pixels):raise ValueError('Texture size changed')
 error=max(abs(a/255-b) for a,b in zip(decoded.pixels,pixels))
 report['textures'].append(dict(name=mat.name,size=list(image.size),max_channel_error=error))
report['passed']=all(a['max_matrix_error']<0.0005 and a['max_vertex_error']<0.005 for a in report['actions'].values()) and all(t['max_channel_error']<0.13 for t in report['textures'])
output.write_text(json.dumps(report,indent=2)+'\n')
if not report['passed']:raise RuntimeError('Roundtrip differs; do not install')
print('MEGA_ROUNDTRIP_OK',flush=True)
