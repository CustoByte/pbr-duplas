"""Compare validated source poses with the SDR-export scene after axis conversion.

Blender: -- corrected-source.blend native-export.blend report.json
"""
import bpy,json,sys,math
from pathlib import Path
from mathutils import Matrix
source,export,output=map(Path,sys.argv[sys.argv.index('--')+1:])
def sample(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and o.animation_data and o.animation_data.action and o.animation_data.action.name.startswith('Body_'));result={}
 for a in bpy.data.actions:
  if not a.name.startswith('Body_'):continue
  r.animation_data.action=a;end=round(a.frame_range[1]);poses={}
  for f in sorted({0,end//2,end}):
   bpy.context.scene.frame_set(f);poses[f]={b.name:b.matrix.copy() for b in r.pose.bones}
  result[a.name]=poses
 return result
before=sample(source);after=sample(export);C=Matrix.Rotation(-math.pi/2,4,'X');worst=0.;where=None;count=0
for name,frames in before.items():
 for f,bones in frames.items():
  for bone,m in bones.items():
   target='CharizardYMotion' if bone=='Origin' else bone
   error=max(abs(v) for row in (C@m-after[name][f][target]) for v in row);count+=1
   if error>worst:worst=error;where=[name,f,bone]
report=dict(passed=worst<.0001,sampled_source_bone_poses=count,actions=len(before),max_matrix_error=worst,worst_sample=where,gameplay_verified=False)
output.write_text(json.dumps(report,indent=2)+'\n');print('SOURCE_EXPORT_POSE_CHECK',report,flush=True)
if not report['passed']:raise SystemExit(1)
