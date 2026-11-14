"""Experimental native Lucario-to-Mega retarget; private assets only.

Blender 3.3: -- mega-source.blend lucario-native.blend output.blend contract.json
Global rest-orientation correction retains target proportions and extra hair bones.
Runtime compatibility is not inferred from successful Blender baking.
"""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Matrix,Vector
source,native,output,contract=map(Path,sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.open_mainfile(filepath=str(source))
with bpy.data.libraries.load(str(native),link=False) as (src,dst):
    dst.objects=['lucario']
    action_names=list(src.actions)
    dst.actions=action_names.copy()
reference=dst.objects[0]
bpy.context.collection.objects.link(reference)
rig=bpy.data.objects['MegaLucarioSource']
ref_actions=dict(zip(action_names,dst.actions))
C=Matrix.Rotation(math.pi/2,4,'X')
MAPPING={
 'Origin':'origin','Waist':'hips','Hips':'hips','Spine1':'chest','Neck':'neck','Head':'head','Jaw':'jaw',
 'LShoulder':'left_shoulder','LArm':'left_arm','LForeArm':'left_fore','LHand':'left_hand',
 'RShoulder':'right_shoulder','RArm':'right_arm','RForeArm':'right_fore','RHand':'right_hand',
 'LThigh':'left_upleg','LLeg':'left_leg','LFoot':'left_foot','LToe1':'left_ball','LToe2':'left_toe',
 'RThigh':'right_upleg','RLeg':'right_leg','RFoot':'right_foot','RToe1':'right_ball','RToe2':'right_toe',
 'Tail1':'tail1','Tail2':'tail2','Tail3':'tail3','Tail4':'tail4',
 'LEar1':'left_ear1','LEar2':'left_ear2','REar1':'right_ear1','REar2':'right_ear2',
}
for side,prefix in [('L','left'),('R','right')]:
 for chain,suffix in [('A','a'),('B','b')]:
  for i in range(1,4): MAPPING[f'{side}Feeler{chain}{i}']=f'{prefix}_tassel_{suffix}{i}'
for dst_name,src_name in MAPPING.items():
 if dst_name not in rig.data.bones or src_name not in reference.data.bones:raise ValueError('Missing mapped bone')
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
native_rest={b.name:C@b.matrix_local for b in reference.data.bones}
relative={b.name:(rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]) for b in rig.data.bones}
reference.animation_data_create();rig.animation_data_create()
report=dict(mapping=MAPPING,actions={},gameplay_verified=False,retarget_visual_review_required=True)
contracts=json.loads(contract.read_text())['resources'][0]['actions']
scene=bpy.context.scene
for pb in rig.pose.bones:pb.rotation_mode='QUATERNION'
idle_basis={}
for entry in contracts:
 name=entry['name']
 if name.startswith('tx_'):continue
 reference.animation_data.action=ref_actions[name]
 action=bpy.data.actions.new('Mega_'+name);action.use_fake_user=True;rig.animation_data.action=action
 frames=round(entry['length']*30)
 # Importer sampled the native tracks in a 24 fps scene; evaluate in that clock.
 poses=[]
 for f in range(frames+1):
  t=f/30*24;scene.frame_set(int(t),subframe=t-int(t))
  poses.append({n:C@reference.pose.bones[n].matrix for n in MAPPING.values()})
 for frame,pose in enumerate(poses):
  desired={}
  for b in rig.data.bones:
   parent=desired[b.parent.name] if b.parent else Matrix.Identity(4)
   local=relative[b.name]
   pos=parent@local.translation
   if b.name in MAPPING:
    n=MAPPING[b.name];delta=pose[n].to_quaternion()@native_rest[n].to_quaternion().inverted()
    rot=delta@rest[b.name].to_quaternion()
    # The Mega rig has separate hip and spine branches under Waist;
    # native center is a moving pivot, not a matching rest-pose joint.
    if b.name == 'Waist':
     pos=rest[b.name].translation+pose[n].translation-native_rest[n].translation
    elif b.name == 'Origin':
     pos=rest[b.name].translation+pose[n].translation-native_rest[n].translation
   else:rot=(parent@local).to_quaternion()
   matrix=rot.to_matrix().to_4x4();matrix.translation=pos;desired[b.name]=matrix
   pb=rig.pose.bones[b.name]
   basis=local.inverted()@parent.inverted()@matrix
   if name == 'wait' and frame == 0: idle_basis[b.name]=basis.copy()
   if name not in ('wait','run','down'):
    # Same smoothstep recovery principle used for Snivy, with this clip's timing.
    incoming=max(0.0,1-frame/2)
    outgoing=max(0.0,min(1.0,(frame-(frames-8))/8))
    w=max(incoming*incoming*(3-2*incoming),outgoing*outgoing*(3-2*outgoing))
    basis=basis.lerp(idle_basis[b.name],w)
   pb.matrix_basis=basis
   for path in ('location','rotation_quaternion','scale'):pb.keyframe_insert(path,frame=frame,group=b.name)
  if frame==0:first={n:x.copy() for n,x in desired.items()}
 last=desired
 for fc in action.fcurves:
  for p in fc.keyframe_points:p.interpolation='LINEAR'
 report['actions'][name]={'frames':frames+1,'duration_seconds':frames/30,'loop_translation_gap':max((first[n].translation-last[n].translation).length for n in rest)}
 print('RETARGET',name,frames+1,flush=True)
reference.hide_render=True;reference.hide_set(True)
scene.render.fps=30
rig.animation_data.action=bpy.data.actions['Mega_wait'];scene.frame_set(0)
scene.frame_start=0;scene.frame_end=40
bpy.ops.wm.save_as_mainfile(filepath=str(output))
output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
