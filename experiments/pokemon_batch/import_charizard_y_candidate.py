"""Re-import the native SDR and stage its body clips for private visual review.

Blender: -- candidate.sdr pbr-addon output.glb
Material-only slots remain in the SDR and are reviewed from decoded UV tracks.
"""
import bpy,sys,json,contextlib,os,struct,inspect
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'experiments/snivy'),str(ROOT/'experiments/mega_lucario')]
from graphics_common import load_pbr_addon
source,addon,out=map(Path,sys.argv[sys.argv.index('--')+1:])
pbr=load_pbr_addon(SimpleNamespace(pbr_addon=addon,native_contract=None))
from rotation_math import stable_euler
pbr.importer.stable_euler=stable_euler
text=inspect.getsource(pbr.importer.makeAction)
for old,new in [('rot = rot.to_euler()','rot = stable_euler(rot)'),('sampleFrames = math.ceil(sampleFramerate * endTime)','sampleFrames = round(sampleFramerate * endTime) + 1')]:
 if text.count(old)!=1:raise ValueError('Importer version differs')
 text=text.replace(old,new)
exec(compile(text,'<charizard-y-stable-import>','exec'),pbr.importer.__dict__)

bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30
with open(os.devnull,'w') as quiet,contextlib.redirect_stdout(quiet):pbr.importer.importSDR(bpy.context,str(source),False,False)
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
for a in list(bpy.data.actions):
 if a.name.startswith('tx_'):bpy.data.actions.remove(a)
 else:
  rig.animation_data.action=a
  a.id_root='OBJECT'
  a.name='Body_'+a.name;a.use_fake_user=True
print('SDR_REIMPORTED_ACTIONS',[a.name for a in bpy.data.actions],flush=True)
rig.animation_data.action=bpy.data.actions['Body_wait'];bpy.context.scene.frame_set(0)
# The SDK implements GX repeat with procedural math followed by a clamped image.
# glTF cannot encode that math. Express the same wrap directly in its sampler.
for mat in bpy.data.materials:
 if not mat.use_nodes:continue
 images=[n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE']
 if not images:continue
 image=images[0];nodes=mat.node_tree.nodes;nodes.clear();links=mat.node_tree.links
 output=nodes.new('ShaderNodeOutputMaterial');bsdf=nodes.new('ShaderNodeBsdfPrincipled');tex=nodes.new('ShaderNodeTexImage');tex.image=image;tex.extension='REPEAT'
 links.new(tex.outputs['Color'],bsdf.inputs['Base Color']);links.new(tex.outputs['Alpha'],bsdf.inputs['Alpha']);links.new(bsdf.outputs[0],output.inputs['Surface'])

for o in bpy.context.scene.objects:o.select_set(o.type in ('MESH','ARMATURE','EMPTY'))
bpy.ops.export_scene.gltf(filepath=str(out),export_format='GLB',use_selection=True,export_animations=True,export_nla_strips=True,export_anim_single_armature=True,export_force_sampling=True,export_frame_range=False,export_yup=True)
raw=out.read_bytes();length=struct.unpack_from('<I',raw,12)[0];data=json.loads(raw[20:20+length])
if len(data.get('animations',[]))!=12:raise ValueError('Review GLB lost a native body clip')
print('NATIVE_SDR_REVIEW_GLB_READY',out.stat().st_size,flush=True)
