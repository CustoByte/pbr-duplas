"""Private Mega SDR candidate using the proven PBR exporter and compact tracks.

Blender: -- retarget.blend contract.json pbr-addon output.sdr
Not a complete runtime registration or a distributable release.
"""
import bpy,json,sys,math,inspect
from pathlib import Path
from types import SimpleNamespace
from mathutils import Matrix
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'snivy'))
from graphics_common import load_pbr_addon
from sdr_track_storage import writer
blend,contract,addon,output=map(Path,sys.argv[sys.argv.index('--')+1:])
pbr=load_pbr_addon(SimpleNamespace(pbr_addon=addon,native_contract=None))
bpy.ops.wm.open_mainfile(filepath=str(blend))
rig=bpy.data.objects['MegaLucarioSource'];mesh=bpy.data.objects['MegaLucarioMesh']
entries=json.loads(contract.read_text())['resources'][0]['actions']
pbr.exporter.SNIVY_ACTION_IDS=[e['name'] for e in entries]
compact_writer=writer(30)
def write_tracks(file,address,keyframes,scale):
 # Remove numerical jitter in the retargeted rotations before shared-array
 # compression. The complete resulting SDR must pass the same error limits.
 return compact_writer(file,address,[(f,round(v,5)) for f,v in keyframes],scale)
pbr.exporter.writeKeyframes=write_tracks
# Blender's float32 Quaternion.to_euler() takes a coarse gimbal branch near 90
# degrees. Preserve the local orientation through a double-precision XYZ solve.
sys.path.insert(0,str(Path(__file__).resolve().parent))
from rotation_math import stable_euler
pbr.exporter.stable_euler=stable_euler
for function,old,new in [('writeSDR','comps[1] = comps[1].to_euler()','comps[1] = stable_euler(comps[1])'),('writeBone','r = r.to_euler()','r = stable_euler(r)')]:
 text=inspect.getsource(getattr(pbr.exporter,function))
 if text.count(old)!=1:raise ValueError('PBR exporter version differs')
 exec(compile(text.replace(old,new),'<mega-stable-euler>','exec'),pbr.exporter.__dict__)

for name in pbr.exporter.SNIVY_ACTION_IDS:
 for cls in (bpy.types.Armature,bpy.types.Material):
  if not hasattr(cls,'prop_'+name):setattr(cls,'prop_'+name,bpy.props.PointerProperty(type=bpy.types.Action))
# Native attachment names are resolved to this rig, not copied numeric indices.
anchors={'origin':'Origin','ef_damage':'Spine2','ef_mouth':'Jaw','ef_leye':'Head',
 'ef_reye':'Head','ef_head':'Head','ef_lhand':'LHand','ef_rhand':'RHand',
 'ef_lffoot':'LToe2','ef_rffoot':'RToe2','ef_o':'Tail4','ef_hadou':'Spine2',
 'direct_set':'pm0448_51','ct_bust':'Spine2','ct_bust_move':'Head',
 'ct_all':'Origin','ct_all_move':'Waist'}
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for name,parent in anchors.items():
 b=rig.data.edit_bones.new(name);b.head=(0,0,0);b.tail=(0,0.1,0)
 b.matrix=rig.data.edit_bones[parent].matrix.copy();b.parent=rig.data.edit_bones[parent];b.use_deform=False
bpy.ops.object.mode_set(mode='OBJECT')
# Exporter expects Y-up SDR coordinates. Rotate mesh and all rig pose/rest data together.
C=Matrix.Rotation(-math.pi/2,4,'X')
# Object-space transform is baked by a parent change of basis in exporter input.
# Applying to armature data preserves local animation basis under this rigid rotation.
rig.data.transform(C)
mesh.data.transform(C)
for mat in mesh.data.materials:
 nodes=mat.node_tree.nodes;links=mat.node_tree.links
 tx=next(n for n in nodes if n.type=='TEX_IMAGE')
 uv=nodes.new('ShaderNodeUVMap');uv.uv_map=mesh.data.uv_layers[0].name
 mapping=nodes.new('ShaderNodeMapping');mapping.name='MegaUV'
 links.new(uv.outputs['UV'],mapping.inputs['Vector']);links.new(mapping.outputs['Vector'],tx.inputs['Vector'])
for e in entries:
 name=e['name'];end=max(1,round(e['length']*30))
 if name.startswith('tx_'):
  setattr(rig.data,'prop_'+name,None)
 else:setattr(rig.data,'prop_'+name,bpy.data.actions['Mega_'+name])
 for mat in mesh.data.materials:
  action=bpy.data.actions.new('MegaUV_'+name+'_'+mat.name);action.id_root='NODETREE';action.use_fake_user=True
  mat.node_tree.animation_data_create();mat.node_tree.animation_data.action=action
  setattr(mat,'prop_'+name,action)
  mapping=mat.node_tree.nodes['MegaUV']
  eye=any(n.type=='TEX_IMAGE' and 'Eye1' in n.image.name for n in mat.node_tree.nodes)
  for frame in range(end+1):
   shift=0.0
   if eye and name.startswith('tx_'):
    if name=='tx_sleep':shift=-0.75
    elif name=='tx_wakeup':shift=-0.75*(1-frame/end)
    elif name=='tx_wink':shift=-0.75 if 1<=frame<end else 0
   mapping.inputs['Location'].default_value=(0,shift,0)
   mapping.inputs['Location'].keyframe_insert('default_value',frame=frame)
  for fc in action.fcurves:
   for k in fc.keyframe_points:k.interpolation='CONSTANT'
reference={e['name']:e for e in entries}
def write_action(file,address,name):
 e=reference[name];length=max(pbr.exporter.actions[name]['length']/30,1/30)
 markers=(0,length,length) if name=='damage' else (e['start']/e['length']*length,e['end']/e['length']*length,length)
 for off,v in zip((4,8,12),markers):file.write('float',v,address,offset=off)
 for i,v in enumerate(e['flags']):file.write('uchar',v,address,offset=40+i)
 return address+48
pbr.exporter.writeAction=write_action
rig.animation_data.action=bpy.data.actions['Mega_wait'];bpy.context.scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(output.with_suffix('.blend')))
bpy.ops.pbr.pbrexport(filepath=str(output))
print('MEGA_SDR_CANDIDATE',output.stat().st_size,flush=True)
