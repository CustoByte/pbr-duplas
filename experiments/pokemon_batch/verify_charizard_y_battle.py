"""Blender numerical checks for the authored Y motion contracts (not gameplay).

-- private-battle.blend report.json
"""
import bpy,json,math,sys
from pathlib import Path
source,output=map(Path,sys.argv[sys.argv.index('--')+1:]);bpy.ops.wm.open_mainfile(filepath=str(source))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
actions={a.name[5:]:a for a in bpy.data.actions if a.name.startswith('Body_')}
def values(a,f):return {(c.data_path,c.array_index):float(c.evaluate(f)) for c in a.fcurves}
neutral=values(actions['wait'],0);ground=values(actions['takeoff'],0);rows=[];errors=[]
for name,a in actions.items():
 end=round(a.frame_range[1]);first=values(a,0);last=values(a,end);target=None
 if name in ('wait','run'):target=first
 elif name=='land':target=ground
 elif name not in ('down','ball_return'):target=neutral
 groups={}
 for c in a.fcurves:
  if not all(math.isfinite(k.co[1]) for k in c.keyframe_points):errors.append(name+': non-finite')
  if c.data_path.endswith('rotation_quaternion'):groups.setdefault(c.data_path,{})[c.array_index]=c
 mindot=1.;angle=0.;gap=0.
 if target:gap=max(abs(last[k]-v) for k,v in target.items() if 'rotation_quaternion' not in k[0])
 for path,curves in groups.items():
  previous=None
  for f in range(end+1):
   q=[curves[i].evaluate(f) for i in range(4)];norm=math.sqrt(sum(v*v for v in q))
   if not .99<norm<1.01:errors.append(name+': non-unit quaternion');break
   q=[v/norm for v in q]
   if previous is not None:mindot=min(mindot,sum(x*y for x,y in zip(q,previous)))
   previous=q
  if target:
   q=[last[(path,i)] for i in range(4)];r=[target[(path,i)] for i in range(4)]
   dot=abs(sum(x*y for x,y in zip(q,r)))/math.sqrt(sum(x*x for x in q)*sum(y*y for y in r))
   angle=max(angle,2*math.acos(min(1,dot)))
 if mindot<0:errors.append(name+': sign flip')
 if mindot<.90:errors.append(name+': excessive per-frame rotation')
 if target and (gap>1e-4 or angle>1e-3):errors.append(name+': endpoint mismatch')
 rows.append(dict(action=name,minimum_adjacent_quaternion_dot=mindot,endpoint_rotation_gap=angle,endpoint_location_scale_gap=gap))
feet=[]
for name,frame in [('takeoff',0),('land',72),('down',108)]:
 rig.animation_data.action=actions[name];bpy.context.scene.frame_set(frame)
 gap=max((rig.pose.bones[n].matrix.translation-rig.data.bones[n].matrix_local.translation).length for n in ('LFoot','RFoot'))
 if gap>1e-4:errors.append(name+': grounded ankle drift')
 feet.append(dict(action=name,frame=frame,maximum_ankle_gap=gap))
report=dict(passed=not errors,errors=errors,actions=rows,ground_contacts=feet,dolphin_verified=False)
output.write_text(json.dumps(report,indent=2)+'\n');print('AUTHORED_BATTLE_CHECK',report['passed'],errors,flush=True)
if errors:raise SystemExit(1)
