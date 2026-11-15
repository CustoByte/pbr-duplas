"""Author a private Mega Charizard Y standing idle without donor motion.

Blender 3.3: -- source.blend output-directory
Only pose and idle are authored; no battle/attack compatibility is claimed.
"""
import bpy,json,math,sys,hashlib
from pathlib import Path
from mathutils import Quaternion,Vector
source,output=map(Path,sys.argv[sys.argv.index('--')+1:]);output.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(source))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
for obj in list(bpy.data.objects):
 if obj.type not in ('MESH','ARMATURE','EMPTY'):bpy.data.objects.remove(obj,do_unlink=True)
 else:obj.animation_data_clear()
for action in list(bpy.data.actions):bpy.data.actions.remove(action)
rig.animation_data_create()
rest={b.name:b.matrix_local.to_quaternion() for b in rig.data.bones}
# The source's legs already form a grounded stance. Keep their complete branch
# unchanged; breathing is confined to the chest, neck, wings and appendages.
base={'Spine1':[("X",5)],'Neck1':[("X",6)],'Neck2':[("X",4)],'Neck3':[("X",3)],'head neck upper':[("X",-5)]}
for side,sign in [('L',1),('R',-1)]:
 base[side+'Feeler1']=[('Z',sign*28),('Y',sign*8)]
 base[side+'Feeler2']=[('Z',sign*10)]
 base[side+'Feeler3']=[('Y',sign*8)]
 base[side+'Arm']=[('Y',sign*8)]
 base[side+'ForeArm']=[('Z',-sign*12)]
for i,angle in enumerate([12,14,16,14,10,0,-5,-5],1):base['Tail'+str(i)]=[('Z',angle)]
axes={'X':Vector((1,0,0)),'Y':Vector((0,1,0)),'Z':Vector((0,0,1))}
def rotation(name,rotations):
 result=Quaternion()
 for axis,degrees in rotations:
  result=Quaternion(rest[name].inverted()@axes[axis],math.radians(degrees))@result
 return result
for bone in rig.pose.bones:bone.rotation_mode='QUATERNION'
action=bpy.data.actions.new('Body_wait');action.use_fake_user=True;rig.animation_data.action=action
scene=bpy.context.scene;scene.render.fps=30;scene.frame_start=0;scene.frame_end=180
previous={}
for frame in range(181):
 phase=2*math.pi*frame/180;breath=math.sin(phase*2)
 for bone in rig.pose.bones:
  name=bone.name;rots=list(base.get(name,[]))
  bone.location=(0,0,0);bone.scale=(1,1,1)
  if name=='Spine1':rots.append(('X',.45*breath))
  if name=='Spine2':bone.scale=(1+.004*breath,1+.006*breath,1+.004*breath)
  if name=='Neck1':rots.append(('X',-.35*breath))
  if name=='head neck upper':rots.append(('Z',.7*math.sin(phase)))
  for side,sign in [('L',1),('R',-1)]:
   if name==side+'Feeler1':rots.append(('Y',sign*.65*math.sin(phase*2-.4)))
   if name==side+'Feeler3':rots.append(('Y',sign*1.2*math.sin(phase*2-.9)))
   if name==side+'Feeler5':rots.append(('X',1.4*math.sin(phase*2-1.3)))
   if name==side+'Arm':rots.append(('X',.4*breath))
  if name.startswith('Tail') and name[4:].isdigit():
   i=int(name[4:]);rots.append(('Z',(0.35+.12*i)*math.sin(phase-i*.38)))
  if name.startswith('Feeler') and name[6:].isdigit():
   i=int(name[6:]);rots.append(('X',2*math.sin(phase*3-i*.4)));rots.append(('Y',1.2*math.sin(phase*2-i*.3)))
  bone.rotation_quaternion=rotation(name,rots)
  if name in previous and previous[name].dot(bone.rotation_quaternion)<0:bone.rotation_quaternion.negate()
  previous[name]=bone.rotation_quaternion.copy()
  for path in ('location','rotation_quaternion','scale'):bone.keyframe_insert(path,frame=frame,group=name)
for curve in action.fcurves:
 for point in curve.keyframe_points:point.interpolation='LINEAR'
scene.frame_set(0)
# Check actual posed foot transforms across the cycle, not just keyed channels.
feet={name:rig.pose.bones[name].matrix.copy() for name in ('LFoot','RFoot')}
max_foot_gap=0.0
for frame in range(181):
 scene.frame_set(frame)
 for name,matrix in feet.items():max_foot_gap=max(max_foot_gap,(rig.pose.bones[name].matrix.translation-matrix.translation).length)
if max_foot_gap>1e-5:raise ValueError('Standing feet drifted')
scene.frame_set(0);bpy.context.preferences.filepaths.save_version=0
blend=output/'mega-charizard-y-idle.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
for obj in scene.objects:obj.select_set(obj.type in ('MESH','ARMATURE','EMPTY'))
glb=output/'mega-charizard-y-idle.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=True,export_nla_strips=True,export_anim_single_armature=True,export_frame_range=True,export_force_sampling=True,export_skins=True,export_yup=True)
report=dict(key='mega-charizard-y',method='authored_local_pose_and_periodic_motion_no_donor',donor_motion_used=False,body_actions={'wait':{'frames':181,'duration_seconds':6,'loop':True}},base_pose_world_axis_degrees=base,maximum_foot_translation_drift=max_foot_gap,source_blend_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),glb_sha256=hashlib.sha256(glb.read_bytes()).hexdigest(),glb_bytes=glb.stat().st_size,user_approved=False,dolphin_ready=False,attacks_authored=False)
(output/'mega-charizard-y-idle.json').write_text(json.dumps(report,indent=2)+'\n')
print('OWN_IDLE_AUTHORED',max_foot_gap,flush=True)
