"""Author donor-free Charizard Y battle motion drafts; Blender 3.3.

-- source.blend output-directory
Own FK poses, analytic two-bone leg contact on landing, sampled at 30 Hz.
Native effects, event hooks and SDR export are not implemented by this script.
"""
import bpy,json,math,sys,hashlib
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
src,out=map(Path,sys.argv[sys.argv.index('--')+1:]);out.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(src))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
for o in list(bpy.data.objects):
 if o.type not in ('MESH','ARMATURE','EMPTY') or o.name in ('Light','Camera'):bpy.data.objects.remove(o,do_unlink=True)
 else:o.animation_data_clear()
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
rig.animation_data_create()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
axes={a:Vector(v) for a,v in [('X',(1,0,0)),('Y',(0,1,0)),('Z',(0,0,1))]}
for b in rig.pose.bones:b.rotation_mode='QUATERNION'
def ease(a,b,t):
 x=max(0,min(1,(t-a)/(b-a)));return x*x*(3-2*x)
def pulse(a,b,c,t):return ease(a,b,t)*(1-ease(b,c,t))
def qrot(name,rots):
 q=Quaternion()
 for axis,angle in rots:q=Quaternion(rest[name].to_quaternion().inverted()@axes[axis],math.radians(angle))@q
 return q
spec=[('wait',6,True),('run',2.4,True),('takeoff',2.4,False),('land',2.4,False),('hikkaku',2.4,False),('kime',2.4,False),('tackle',2.4,False),('guard',2.4,False),('ground_impact',2.4,False),('recover',3.6,False),('damage',2.4,False),('down',3.6,False),('ball_exit',2.4,False),('ball_return',2.4,False)]
report=dict(key='mega-charizard-y',method='species_specific_authored_pose_curves_and_leg_contact',donor_motion_used=False,body_actions={},dolphin_ready=False,move_effects_verified=False,pokeball_engine_effects_verified=False,tail_fire_shader_scope='preview_only',user_approved=False)
scene=bpy.context.scene;scene.render.fps=30;scene.frame_start=0
for name,seconds,loop in spec:
 count=round(seconds*30);action=bpy.data.actions.new('Body_'+name);action.use_fake_user=True;rig.animation_data.action=action;previous={}
 for f in range(count+1):
  u=f/count;phase=2*math.pi*u;flap=phase*(5 if name=='wait' else 2 if seconds==2.4 else 3)
  flight=1.0
  if name=='takeoff':flight=ease(.12,.8,u)
  if name=='land':flight=1-ease(.08,.82,u)
  if name=='down':flight=1-ease(0,.45,u)
  if name=='ball_exit':flight=ease(.25,.85,u)
  if name=='ball_return':flight=1-ease(.08,.55,u)
  if name=='ground_impact':flight=1-pulse(.08,.48,.88,u)
  if name=='recover':flight=1-pulse(.06,.45,.9,u)
  shrink=1.0
  if name=='ball_exit':shrink=max(.001,ease(.03,.38,u))
  if name=='ball_return':shrink=max(.001,1-ease(.55,.95,u))
  hit=pulse(.28,.44,.75,u) if name=='damage' else 0
  strike=pulse(.30,.49,.82,u) if name in ('hikkaku','tackle','kime') else 0
  windup=pulse(.04,.23,.42,u) if name in ('hikkaku','tackle','kime') else 0
  guard=pulse(.08,.35,.88,u) if name=='guard' else 0
  faint=ease(.35,.90,u) if name=='down' else 0
  rots={};scales={};locations={}
  def add(b,a,v):rots.setdefault(b,[]).append((a,v))
  add('Origin','X',10*flight-12*hit+(12 if name=='run' else 0)*flight+7*strike*(name=='tackle'))
  locations['Origin']=Vector((0,.30*hit-.9*strike*(name=='tackle'),1.5*flight+.07*math.sin(flap)*flight-.48*faint))
  scales['Origin']=(shrink,)*3
  add('Spine1','X',5+.5*math.sin(phase)-5*windup+6*strike*(name=='kime')+17*faint)
  scales['Spine2']=(1+.004*math.sin(phase),1+.006*math.sin(phase),1+.004*math.sin(phase))
  for b,value in [('Neck1',6),('Neck2',4),('Neck3',3)]:
   add(b,'X',value-2*hit-3*windup+3*strike*(name=='kime')+20*faint)
  add('head neck upper','X',-5-6*hit+8*faint)
  add('head neck upper','Z',.7*math.sin(phase)+5*hit)
  add('head jaw','X',22*strike*(name=='kime'))
  add('Spine2','Z',-7*windup*(name=='hikkaku')+10*strike*(name=='hikkaku')+4*hit)
  for side,sign in [('L',1),('R',-1)]:
   add(side+'Feeler1','Z',sign*(28-24*flight+35*faint+18*guard))
   add(side+'Feeler1','Y',sign*(8-2*flight+18*math.sin(flap)*flight))
   add(side+'Feeler1','X',-32*faint)
   add(side+'Feeler2','Z',sign*(10-6*flight+12*faint))
   add(side+'Feeler3','Y',sign*(8-4*flight+5*math.sin(flap-.4)*flight))
   add(side+'Feeler5','X',2*math.sin(flap-.7)*flight)
   add(side+'Arm','Y',sign*(8+5*flight))
   add(side+'ForeArm','Z',-sign*(12+12*flight+28*guard))
   add(side+'Arm','Z',-sign*15*guard)
   add(side+'Thigh','X',-20*flight)
   add(side+'Leg','X',65*flight)
   add(side+'Foot','X',-45*flight)
  add('LArm','Z',25*windup*(name=='hikkaku')-65*strike*(name=='hikkaku'))
  add('LArm','Y',15*windup*(name=='hikkaku')-50*strike*(name=='hikkaku'))
  add('LForeArm','Z',-20*strike*(name=='hikkaku'))
  add('LForeArm','X',25*strike*(name=='hikkaku'))
  add('RArm','Z',18*strike*(name=='hikkaku'))
  for i,a in enumerate([12,14,16,14,10,0,-5,-5],1):add('Tail'+str(i),'Z',a*(1-.6*flight)+(1+.15*i)*math.sin(phase-i*.38))
  for i in range(1,6):add('Feeler'+str(i),'X',2*math.sin(flap-i*.3))
  desired={}
  for b in rig.data.bones:
   parent=desired[b.parent.name] if b.parent else Matrix.Identity(4)
   basis=qrot(b.name,rots.get(b.name,[])).to_matrix().to_4x4()
   if b.name in scales:
    basis=basis@Matrix.Diagonal((*scales[b.name],1))
   if b.name in locations:basis.translation=rest[b.name].to_quaternion().inverted()@locations[b.name]
   desired[b.name]=parent@local[b.name]@basis
  # Pin the anatomical ankle rather than assuming the imported bone's tail is it.
  # Only grounded/landing poses use contact; flight retains authored leg folding.
  pin=(1-ease(0,.35,flight)) if name in ('down','land','takeoff','ground_impact','recover') else 0
  if pin>0:
   for side in ('L','R'):
    a,b,c=side+'Thigh',side+'Leg',side+'Foot';hip=desired[a].translation
    target=desired[c].translation.lerp(rest[c].translation,pin)
    la=(rest[b].translation-rest[a].translation).length;lb=(rest[c].translation-rest[b].translation).length
    direction=target-hip;dist=max(.001,min(direction.length,la+lb-.00001));direction.normalize()
    bend=Vector((0,-1,0));bend=(bend-direction*bend.dot(direction)).normalized()
    along=(la*la-lb*lb+dist*dist)/(2*dist);knee=hip+direction*along+bend*math.sqrt(max(0,la*la-along*along))
    for bn,start,end,orig in [(a,hip,knee,rest[b].translation-rest[a].translation),(b,knee,target,rest[c].translation-rest[b].translation)]:
     rot=orig.rotation_difference(end-start)@rest[bn].to_quaternion();mat=rot.to_matrix().to_4x4();mat.translation=start;desired[bn]=mat
    rot=desired[c].to_quaternion().slerp(rest[c].to_quaternion(),pin);mat=rot.to_matrix().to_4x4();mat.translation=target;desired[c]=mat
    for bn in rig.data.bones:
     if bn.name==c or not bn.parent:continue
     if c in [p.name for p in bn.parent_recursive]:desired[bn.name]=desired[bn.parent.name]@local[bn.name]
  if name=='hikkaku' and max(strike,windup)>1e-6:
   a,b,c='LArm','LForeArm','LHand';shoulder=desired[a].translation.copy();weight=max(strike,windup)
   target=desired[c].translation+Vector((.1*windup,.28*windup,.1*windup))
   target=target.lerp(shoulder+Vector((.15,-1.05,-.1)),strike)
   la=(rest[b].translation-rest[a].translation).length;lb=(rest[c].translation-rest[b].translation).length
   direction=target-shoulder;dist=max(.001,min(direction.length,la+lb-.00001));direction.normalize()
   target=shoulder+direction*dist
   bend=Vector((1,0,-.3));bend=(bend-direction*bend.dot(direction)).normalized()
   along=(la*la-lb*lb+dist*dist)/(2*dist);elbow=shoulder+direction*along+bend*math.sqrt(max(0,la*la-along*along))
   for bn,start,end,orig in [(a,shoulder,elbow,rest[b].translation-rest[a].translation),(b,elbow,target,rest[c].translation-rest[b].translation)]:
    rot=orig.rotation_difference(end-start)@rest[bn].to_quaternion()
    mat=desired[bn].to_quaternion().slerp(rot,weight).to_matrix().to_4x4()
    mat.translation=desired[bn].translation.lerp(start,weight);desired[bn]=mat
   hand_tip=rest['EndLHand'].translation-rest[c].translation
   aimed=hand_tip.rotation_difference(Vector((0,-1,-.25)))@rest[c].to_quaternion()
   mat=desired[c].to_quaternion().slerp(aimed,strike).to_matrix().to_4x4();mat.translation=desired[c].translation.lerp(target,weight);desired[c]=mat
   for bn in rig.data.bones:
    if bn.name==c or not bn.parent:continue
    if c in [p.name for p in bn.parent_recursive]:desired[bn.name]=desired[bn.parent.name]@local[bn.name]
  for b in rig.data.bones:
   parent=desired[b.parent.name] if b.parent else Matrix.Identity(4)
   basis=local[b.name].inverted()@parent.inverted()@desired[b.name]
   pb=rig.pose.bones[b.name];pb.matrix_basis=basis
   if b.name in previous and previous[b.name].dot(pb.rotation_quaternion)<0:pb.rotation_quaternion.negate()
   previous[b.name]=pb.rotation_quaternion.copy()
   for path in ('location','rotation_quaternion','scale'):pb.keyframe_insert(path,frame=f,group=b.name)
 for curve in action.fcurves:
  for k in curve.keyframe_points:k.interpolation='LINEAR'
 report['body_actions'][name]={'frames':count+1,'duration_seconds':seconds,'loop':loop}
 print('AUTHORED',name,count+1,flush=True)
rig.animation_data.action=bpy.data.actions['Body_wait'];scene.frame_set(0);scene.frame_end=180
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(out/'mega-charizard-y-battle.blend'),compress=True)
for obj in scene.objects:obj.select_set(obj.type in ('MESH','ARMATURE','EMPTY'))
glb=out/'mega-charizard-y-battle.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=True,export_nla_strips=True,export_anim_single_armature=True,export_frame_range=False,export_force_sampling=True,export_skins=True,export_yup=True)
report['glb_sha256']=hashlib.sha256(glb.read_bytes()).hexdigest();report['glb_bytes']=glb.stat().st_size
(out/'mega-charizard-y-battle.json').write_text(json.dumps(report,indent=2)+'\n')
