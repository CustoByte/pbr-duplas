"""Inspect baked Blender motion endpoints and quaternion interpolation.

Blender: -- private-motion.blend report.json
This does not verify move effects, native SDR export, or battle compatibility.
"""
import bpy,json,math,sys
from pathlib import Path
source,output=map(Path,sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.open_mainfile(filepath=str(source))
actions={a.name.removeprefix('Body_'):a for a in bpy.data.actions if a.name.startswith('Body_')}
def channels(action,frame):
 return {(c.data_path,c.array_index):float(c.evaluate(frame)) for c in action.fcurves}
neutral=channels(actions['wait'],0)
rows=[];errors=[]
for name,action in actions.items():
 end=int(action.frame_range[1]);first=channels(action,0);last=channels(action,end)
 if not all(math.isfinite(float(k.co[1])) for c in action.fcurves for k in c.keyframe_points):errors.append(name+': non-finite key')
 target=first if name in ('wait','run','kuchu_wait') else neutral if name not in ('down','kuchu_down') else None
 gap=0.0
 if target:
  # Quaternions may differ only by sign, so compare complete rotations below.
  gap=max(abs(last[k]-v) for k,v in target.items() if 'rotation_quaternion' not in k[0])
  if gap>1e-4:errors.append(name+': endpoint translation/scale mismatch')
 groups={}
 for curve in action.fcurves:
  if curve.data_path.endswith('rotation_quaternion'):groups.setdefault(curve.data_path,{})[curve.array_index]=curve
 minimum_dot=1.0;max_rotation_gap=0.0
 for path,curves in groups.items():
  previous=None
  for frame in range(end+1):
   q=[float(curves[i].evaluate(frame)) for i in range(4)];norm=math.sqrt(sum(v*v for v in q))
   if norm<.99 or norm>1.01:errors.append(name+': invalid quaternion '+path);break
   q=[v/norm for v in q]
   if previous is not None:minimum_dot=min(minimum_dot,sum(a*b for a,b in zip(previous,q)))
   previous=q
  if target:
   a=[last[(path,i)] for i in range(4)];b=[target[(path,i)] for i in range(4)]
   dot=abs(sum(x*y for x,y in zip(a,b)))/math.sqrt(sum(x*x for x in a)*sum(y*y for y in b))
   max_rotation_gap=max(max_rotation_gap,2*math.acos(min(1.0,dot)))
 if minimum_dot< -1e-5:errors.append(name+': quaternion sign flip')
 if max_rotation_gap>1e-3:errors.append(name+': endpoint rotation mismatch')
 rows.append(dict(action=name,frames=end+1,minimum_adjacent_quaternion_dot=minimum_dot,endpoint_translation_scale_gap=gap,endpoint_rotation_radians=max_rotation_gap,endpoint_checked=target is not None))
report=dict(kind='baked-motion-numerical-review',source_name=source.name,passed=not errors,actions=rows,errors=errors,dolphin_verified=False)
output.write_text(json.dumps(report,indent=2)+'\n')
print('MOTION_NUMERICAL_REVIEW',report['passed'],errors,flush=True)
if errors:raise SystemExit(1)
