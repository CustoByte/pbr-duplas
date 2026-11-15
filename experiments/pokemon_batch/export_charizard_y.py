"""Private native SDR motion candidate. Blender 3.3.

-- corrected-motion.blend donor-inventory.json pbr-addon output.sdr
Keeps the native 15-action contract. Does not install or publish game assets.
The approved procedural tail flame still requires a native effect implementation.
"""
import bpy,json,sys,math,inspect,hashlib
from pathlib import Path
from types import SimpleNamespace
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'experiments/snivy'),str(ROOT/'experiments/mega_lucario')]
from graphics_common import load_pbr_addon
from sdr_track_storage import writer
from rotation_math import stable_euler
blend,contract,addon,output=map(Path,sys.argv[sys.argv.index('--')+1:]);output.parent.mkdir(parents=True,exist_ok=True)
pbr=load_pbr_addon(SimpleNamespace(pbr_addon=addon,native_contract=None))
bpy.ops.wm.open_mainfile(filepath=str(blend))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and o.animation_data and o.animation_data.action and o.animation_data.action.name.startswith('Body_'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
# Remove the hidden donor object from the saved/exported candidate.
for obj in list(bpy.context.scene.objects):
 if obj.type=='ARMATURE' and obj!=rig:bpy.data.objects.remove(obj,do_unlink=True)
rig.name='MegaCharizardY'
if max(abs(v) for row in (rig.matrix_world-Matrix.Identity(4)) for v in row)>1e-5:raise ValueError('Unexpected object-space rig transform')
for mesh in meshes:
 if max(abs(v) for row in (mesh.matrix_world-Matrix.Identity(4)) for v in row)>1e-5:raise ValueError('Unexpected mesh object transform')
 mesh.parent=rig;mesh.matrix_parent_inverse=Matrix.Identity(4)
 for mod in mesh.modifiers:
  if mod.type=='ARMATURE':mod.object=rig
# The native exporter reserves origin for static model scaling. Preserve animated
# motion on a differently named bone, as in the existing Snivy pipeline.
rig.data.bones['Origin'].name='CharizardYMotion'
for action in bpy.data.actions:
 for c in action.fcurves:c.data_path=c.data_path.replace('pose.bones["Origin"]','pose.bones["CharizardYMotion"]')
for mesh in meshes:
 if 'Origin' in mesh.vertex_groups:mesh.vertex_groups['Origin'].name='CharizardYMotion'
source_root=next(b.name for b in rig.data.bones if b.parent is None)
root='PBR_StaticRoot'
anchors={'origin':root,'lizardon':root,'direct_set':root,'ct_all':'CharizardYMotion','ct_all_move':'Waist','ct_bust':'Spine2','ct_bust_move':'head neck upper','ef_damage':'Spine2','ef_head':'head neck upper','ef_mouth':'head neck upper','ef_leye':'head neck upper','ef_reye':'head neck upper','ef_lhand':'LHand','ef_rhand':'RHand','ef_lffoot':'LFoot','ef_rffoot':'RFoot','ef_lrfoot':'LFoot','ef_rrfoot':'RFoot','ef_lknee':'LLeg','ef_rknee':'RLeg','ef_lelbow':'LForeArm','ef_relbow':'RForeArm','ef_o':'Tail8'}
# Calibrated target-space attachment points; never reuse numeric donor indices.
positions={'ef_mouth':rig.data.bones['EndJaw'].head_local.copy()+Vector((0,0,.10)), 'ef_lhand':rig.data.bones['EndLHand'].head_local.copy(),'ef_rhand':rig.data.bones['EndRHand'].head_local.copy(),'ef_lffoot':rig.data.bones['EndLToeC'].head_local.copy(),'ef_rffoot':rig.data.bones['EndRToeC'].head_local.copy()}
for side,sign in [('l',1),('r',-1)]:
 eye=next(m for m in meshes if m.name.startswith('7_'))
 points=[v.co for v in eye.data.vertices if v.co.x*sign>0]
 positions['ef_'+side+'eye']=sum(points,Vector())/len(points)
# Locate the real tail surface, not the EndTail8 marker beyond it.
points=[]
for mesh in meshes:
 for v in mesh.data.vertices:
  if any(mesh.vertex_groups[g.group].name=='Tail8' and g.weight>.999 for g in v.groups):points.append(v.co.copy())
positions['ef_o']=max(points,key=lambda v:v.y)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
static=rig.data.edit_bones.new(root);static.head=(0,0,0);static.tail=(0,.1,0)
# After the Z-up to Y-up conversion the export root must be identity.
static.matrix=Matrix.Rotation(math.pi/2,4,'X');static.use_deform=False
rig.data.edit_bones[source_root].parent=static
for name,parent in anchors.items():
 if name in rig.data.edit_bones:raise ValueError('Attachment collision: '+name)
 b=rig.data.edit_bones.new(name);b.head=(0,0,0);b.tail=(0,.1,0);b.matrix=rig.data.edit_bones[parent].matrix.copy()
 if name in positions:b.matrix.translation=positions[name]
 b.parent=rig.data.edit_bones[parent];b.use_deform=False
bpy.ops.object.mode_set(mode='OBJECT')
if rig.data.bones[0].name!=root:raise ValueError('Exporter root ordering differs')
entries=json.loads(contract.read_text())['resources'][0]['actions'];names=[e['name'] for e in entries]
if len(names)!=15 or set(n for n in names if not n.startswith('tx_'))!={a.name[5:] for a in bpy.data.actions if a.name.startswith('Body_')}:raise ValueError('Incomplete Charizard body action contract')
pbr.exporter.SNIVY_ACTION_IDS=names
compact=writer(30)
pbr.exporter.writeKeyframes=lambda file,address,keyframes,scale:compact(file,address,[(f,round(v,5)) for f,v in keyframes],scale)
pbr.exporter.stable_euler=stable_euler
for function,old,new in [('writeSDR','comps[1] = comps[1].to_euler()','comps[1] = stable_euler(comps[1])'),('writeBone','r = r.to_euler()','r = stable_euler(r)')]:
 text=inspect.getsource(getattr(pbr.exporter,function))
 if text.count(old)!=1:raise ValueError('PBR exporter version differs')
 exec(compile(text.replace(old,new),'<charizard-y-stable-euler>','exec'),pbr.exporter.__dict__)
for name in names:
 for cls in (bpy.types.Armature,bpy.types.Material):
  if not hasattr(cls,'prop_'+name):setattr(cls,'prop_'+name,bpy.props.PointerProperty(type=bpy.types.Action))
C=Matrix.Rotation(-math.pi/2,4,'X');rig.data.transform(C)
materials=[]
for mesh in meshes:
 mesh.data.transform(C)
 for slot in mesh.material_slots:
  old=slot.material;image=next(n.image for n in old.node_tree.nodes if n.type=='TEX_IMAGE')
  mat=bpy.data.materials.new('Y_'+old.name);mat.use_nodes=True;nodes=mat.node_tree.nodes;nodes.clear();links=mat.node_tree.links
  out=nodes.new('ShaderNodeOutputMaterial');bs=nodes.new('ShaderNodeBsdfPrincipled');tx=nodes.new('ShaderNodeTexImage');tx.image=image;tx.extension='REPEAT';mp=nodes.new('ShaderNodeMapping');mp.name='NativeUV';uv=nodes.new('ShaderNodeUVMap');uv.uv_map=mesh.data.uv_layers[0].name
  links.new(uv.outputs['UV'],mp.inputs['Vector']);links.new(mp.outputs['Vector'],tx.inputs['Vector']);links.new(tx.outputs['Color'],bs.inputs['Base Color']);links.new(bs.outputs[0],out.inputs['Surface']);slot.material=mat;materials.append(mat)
for e in entries:
 name=e['name'];end=max(1,round(e['length']*30));setattr(rig.data,'prop_'+name,None if name.startswith('tx_') else bpy.data.actions['Body_'+name])
 for mat in materials:
  action=bpy.data.actions.new('NativeUV_'+name+'_'+mat.name);action.id_root='NODETREE';action.use_fake_user=True;mat.node_tree.animation_data_create();mat.node_tree.animation_data.action=action;setattr(mat,'prop_'+name,action);mp=mat.node_tree.nodes['NativeUV'];eye=any(n.type=='TEX_IMAGE' and 'Eye1' in n.image.name for n in mat.node_tree.nodes)
  for f in range(end+1):
   shift=0.
   if eye and name=='tx_sleep':shift=-.5
   if eye and name=='tx_wink':shift=(0,-.25,-.5,-.5,-.25,0)[min(5,round(f/end*5))]
   if eye and name=='tx_wakeup':shift=(-.5,-.25,0,0)[min(3,round(f/end*3))]
   mp.inputs['Location'].default_value=(0,shift,0);mp.inputs['Location'].keyframe_insert('default_value',frame=f)
  for fc in action.fcurves:
   for k in fc.keyframe_points:k.interpolation='CONSTANT'
ref={e['name']:e for e in entries}
def write_action(file,address,name):
 e=ref[name];length=max(pbr.exporter.actions[name]['length']/30,1/30)
 for off,v in zip((4,8,12),(e['start']/e['length']*length,e['end']/e['length']*length,length)):file.write('float',v,address,offset=off)
 for i,v in enumerate(e['flags']):file.write('uchar',v,address,offset=40+i)
 return address+48
pbr.exporter.writeAction=write_action
rig.animation_data.action=bpy.data.actions['Body_wait'];bpy.context.scene.frame_set(0);bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(output.with_suffix('.blend')),compress=True)
bpy.ops.pbr.pbrexport(filepath=str(output))
report=dict(kind='private native SDR motion candidate',object_name=rig.name,actions=names,anchors=anchors,meshes=[m.name for m in meshes],jaw_fix_retained=True,eye_states=['tx_wink','tx_sleep','tx_wakeup'],tail_flame_native_port_verified=False,gameplay_verified=False,eligible_for_game_package=False,sha256=hashlib.sha256(output.read_bytes()).hexdigest(),bytes=output.stat().st_size)
output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print('CHARIZARD_Y_SDR_READY',output.stat().st_size,flush=True)
