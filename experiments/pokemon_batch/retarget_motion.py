"""Private body-motion drafts from supplied PBR donors. Blender 3.3.

-- key source.blend donor-directory plan.json output-directory
This bakes motion drafts, not game-ready animation/effect routing.
"""
import bpy
import json
import math
from pathlib import Path
import sys
from mathutils import Matrix, Quaternion, Vector
key, source, donor, plan, output = sys.argv[sys.argv.index('--')+1:]
source, donor, plan, output = map(Path, (source, donor, plan, output))
config = json.loads(plan.read_text())[key]
inventory = json.loads((donor/'inventory.json').read_text())
contract = inventory['resources'][0]['actions']
bpy.ops.wm.open_mainfile(filepath=str(source))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
rig_name = inventory['blender_rigs'][0]['name']
body_names = [a['name'] for a in contract if not a['name'].startswith('tx_')]
with bpy.data.libraries.load(str(donor/'reference.blend'), link=False) as (src, dst):
    dst.objects = [rig_name]
    dst.actions = body_names.copy()
reference = dst.objects[0]
bpy.context.collection.objects.link(reference)
actions = dict(zip(body_names, dst.actions))
if any(action is None for action in actions.values()): raise ValueError('Missing body action')
mapping = config['mapping']
missing = [(a,b) for a,b in mapping.items() if a not in rig.data.bones or b not in reference.data.bones]
if missing: raise ValueError('Missing mapped bones: '+str(missing))
C = Matrix.Rotation(math.pi/2, 4, 'X')
rest = {b.name:b.matrix_local.copy() for b in rig.data.bones}
local = {b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
native_rest = {b.name:C@b.matrix_local for b in reference.data.bones}
base_rotations = {name:matrix.to_quaternion() for name,matrix in rest.items()}
if key == 'rillaboom':
    for side, sign in [('L',1),('R',-1)]:
        arm, fore, hand = side+'Arm', side+'ForeArm', side+'Hand'
        base_rotations[arm] = Quaternion(Vector((0,1,0)),sign*math.radians(58))@base_rotations[arm]
        old_direction = (rest[hand].translation-rest[fore].translation).normalized()
        desired = Vector((-sign*.4,-1,-.4)).normalized()
        delta = old_direction.rotation_difference(desired)
        base_rotations[fore] = delta@rest[fore].to_quaternion()
        base_rotations[hand] = delta@rest[hand].to_quaternion()
# Translation scaling is anatomical, not mesh/texture resolution dependent.
height = max(matrix.translation.z for matrix in rest.values())-min(matrix.translation.z for matrix in rest.values())
ref_height = max(matrix.translation.z for matrix in native_rest.values())-min(matrix.translation.z for matrix in native_rest.values())
scale = height/max(ref_height,1e-3)
reference.animation_data_create()
rig.animation_data_create()
for bone in rig.pose.bones: bone.rotation_mode='QUATERNION'
scene = bpy.context.scene
reference.animation_data.action = actions[config.get('idle_reference','wait')]
scene.frame_set(0)
baseline = {name:C@reference.pose.bones[name].matrix.copy() for name in set(mapping.values())}
neutral = {}
report = dict(key=key,source_donor=inventory['source_name'],source_donor_sha256=inventory['source_sha256'],
              mapping=mapping,translation_scale=scale,body_actions={},aliases=config['aliases'],
              preliminary_motion_only=True,move_effects_verified=False,dolphin_ready=False,
              manual_visual_review_required=True,uv_eye_animation_ported=False)
metadata = {a['name']:a for a in contract}
names = ['wait','run','damage','down']+[n for n in body_names if n not in ('wait','run','damage','down')]
for name in names:
    source_name = config.get('source_aliases',{}).get(name,name)
    if source_name not in actions: continue
    entry = metadata[source_name]
    count = max(1,round(entry['length']*30))
    reference.animation_data.action = actions[source_name]
    source_poses = []
    # Native SDR importer stored tracks at 24 fps; sample by seconds.
    for frame in range(count+1):
        time = frame/30*24
        scene.frame_set(int(time),subframe=time-int(time))
        source_poses.append({n:C@reference.pose.bones[n].matrix.copy() for n in baseline})
    action = bpy.data.actions.new('Body_'+name)
    action.use_fake_user=True
    rig.animation_data.action=action
    looping = name in ('wait','run','kuchu_wait')
    first_basis = {}
    for frame,pose in enumerate(source_poses):
        desired = {}
        for bone in rig.data.bones:
            parent = desired[bone.parent.name] if bone.parent else Matrix.Identity(4)
            loc = local[bone.name]
            position = parent@loc.translation
            rotation = (parent@loc).to_quaternion()
            if bone.name in mapping:
                n = mapping[bone.name]
                reference_basis = baseline[n] if config['mode']=='idle_relative' else native_rest[n]
                delta = pose[n].to_quaternion()@reference_basis.to_quaternion().inverted()
                strength = 1.0
                if key=='rillaboom' and bone.name in ('Waist','Hips','Spine1','Spine2','Head','Neck'): strength=.35 if name!='down' else .8
                if key=='hydreigon' and bone.name in ('LArm','LForeArm','LHand','RArm','RForeArm','RHand'):strength=.5
                delta=Quaternion().slerp(delta,strength)
                rotation=delta@base_rotations[bone.name]
                if bone.name in ('Origin','Waist'):
                    position=rest[bone.name].translation+(pose[n].translation-reference_basis.translation)*scale
            matrix=rotation.to_matrix().to_4x4()
            matrix.translation=position
            # Props stay in the source geometry, but receive explicit control.
            if key=='rillaboom' and bone.name in ('FeelerC1','FeelerC2'):
                if bone.parent and bone.parent.name not in ('FeelerC1','FeelerC2'):
                    matrix=rest[bone.name].copy();matrix.translation+=Vector((0,-height*.43,0))
            if key=='rillaboom' and bone.name in ('LFeelerA','RFeelerA'):
                hand=desired[bone.name[0]+'Hand']
                difference=hand.to_quaternion()@base_rotations[bone.name[0]+'Hand'].inverted()
                rotate=Vector((1,0,0)).rotation_difference(Vector((0,-1,-.2)).normalized())
                matrix=(difference@rotate@rest[bone.name].to_quaternion()).to_matrix().to_4x4()
                matrix.translation=hand.translation+difference@Vector((0,-.4,0))
            desired[bone.name]=matrix
            basis=loc.inverted()@parent.inverted()@matrix
            if name=='wait' and frame==0:neutral[bone.name]=basis.copy()
            if name not in ('wait','run','down','kuchu_wait','kuchu_down') and bone.name in neutral:
                incoming=max(0.0,1-frame/3)
                outgoing=max(0.0,min(1.0,(frame-(count-8))/8))
                weight=max(incoming*incoming*(3-2*incoming),outgoing*outgoing*(3-2*outgoing))
                basis=basis.lerp(neutral[bone.name],weight)
            if frame==0:first_basis[bone.name]=basis.copy()
            if looping and frame>count-3:
                t=(frame-(count-3))/3
                basis=basis.lerp(first_basis[bone.name],t*t*(3-2*t))
            pb=rig.pose.bones[bone.name]
            pb.matrix_basis=basis
            if bone.name in config.get('hide_bones',[]):pb.scale=(.0001,)*3
            for path in ('location','rotation_quaternion','scale'):
                pb.keyframe_insert(path,frame=frame,group=bone.name)
    for curve in action.fcurves:
        for point in curve.keyframe_points:point.interpolation='LINEAR'
    report['body_actions'][name]=dict(frames=count+1,duration_seconds=count/30,source_action=source_name,loop=looping)
    print('BAKED',key,name,count+1,flush=True)
reference.hide_render=True
reference.hide_set(True)
# Donor motions and rig are not exported into the target GLB.
for obj in bpy.context.scene.objects:obj.select_set(False)
rig.select_set(True)
for obj in bpy.context.scene.objects:
    if obj.type=='MESH':obj.select_set(True)
for action in list(bpy.data.actions):
    if not action.name.startswith('Body_'):bpy.data.actions.remove(action)
rig.animation_data.action=bpy.data.actions['Body_wait']
scene.render.fps=30
scene.frame_set(0)
output.mkdir(parents=True,exist_ok=True)
blend=output/(key+'-motion.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
# One export armature so all body actions remain distinct.
bpy.data.objects.remove(reference,do_unlink=True)
glb=output/(key+'-motion.glb')
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
    export_animations=True,export_nla_strips=True,export_anim_single_armature=True,
    export_frame_range=False,export_force_sampling=True,export_skins=True,export_yup=True)
report['glb_bytes']=glb.stat().st_size
(output/(key+'-motion.json')).write_text(json.dumps(report,indent=2)+'\n')
print('MOTION_DRAFT_READY',key,flush=True)
