"""Blender check of calibrated Y jaw motion across all baked body clips.

-- private.blend output.json
Checks actual sampled local rotations, including interpolation between keys.
"""
import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
src,out=map(Path,sys.argv[sys.argv.index('--')+1:]);bpy.ops.wm.open_mainfile(filepath=str(src))
r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');b=r.pose.bones['head jaw']
axis=r.data.bones[b.name].matrix_local.to_quaternion().inverted()@Vector((1,0,0));rows=[];errors=[]
for a in bpy.data.actions:
 if not a.name.startswith('Body_'):continue
 r.animation_data.action=a;angles=[];offaxis=0.;peak=0
 for f in range(round(a.frame_range[1])*2+1):
  t=f/2;bpy.context.scene.frame_set(int(t),subframe=t-int(t));q=b.rotation_quaternion.normalized()
  angle=2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w);angle=(angle+math.pi)%(2*math.pi)-math.pi
  angles.append(math.degrees(angle));offaxis=max(offaxis,Vector((q.x,q.y,q.z)).cross(axis).length)
 if min(angles)<-.001 or max(angles)>65.001 or offaxis>1e-4:errors.append(a.name)
 peak=max(range(len(angles)),key=angles.__getitem__)/2
 rows.append(dict(action=a.name,min_degrees=min(angles),max_degrees=max(angles),max_off_axis=offaxis,peak_frame=peak))
report=dict(passed=not errors,errors=errors,closed_limit_degrees=0,maximum_limit_degrees=65,half_frame_sampling=True,actions=rows,gameplay_verified=False)
out.write_text(json.dumps(report,indent=2)+'\n');print('JAW_HINGE_CHECK',report['passed'],errors,flush=True)
if errors:raise SystemExit(1)
