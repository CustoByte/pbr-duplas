"""Render the corrected model, using its open eyes and closed neutral jaw."""
import bpy,sys
from pathlib import Path
from mathutils import Vector
root=Path(sys.argv[sys.argv.index('--')+1]);output=root/'portraits';output.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(root.parent/'charizard-y-jaw-fix/mega-charizard-y-motion.blend'))
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
rig.animation_data.action=bpy.data.actions['Body_wait'];scene.frame_set(0)
meshes=[o for o in scene.objects if o.type=='MESH']
points=[];eyes=[]
for obj in meshes:
 ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
 verts=[obj.matrix_world@v.co for v in ev.data.vertices];points+=verts
 if obj.name.startswith('7_'):eyes+=verts
assert eyes
head=sum(eyes,Vector())/len(eyes)
def bounds(vs):
 lo=Vector([min(v[i] for v in vs) for i in range(3)]);hi=Vector([max(v[i] for v in vs) for i in range(3)])
 return (lo+hi)/2,max(hi-lo)
center,span=bounds(points);_,headspan=bounds(eyes)
# Use the source Z-up pose for portrait rendering; SDR conversion is separate. Material repeat must survive the portrait renderer.
scene.world=bpy.data.worlds.new('PortraitWorld');scene.world.color=(.3,.3,.3)
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';scene.camera=camera
for direction,power in [((1,3,2),80),((-2,1,1),40)]:
 bpy.ops.object.light_add(type='AREA',location=center+Vector(direction)*span);o=bpy.context.object;o.data.energy=power*span*span;o.data.size=span*2;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16
scene.render.resolution_x=scene.render.resolution_y=384;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.view_settings.view_transform='Standard'
for kind,target,size,margin in [('body',center,span,1.1),('face',head,headspan*2.3,1.2)]:
 camera.location=target+Vector((.85,-2,.28))*size;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=size*margin
 scene.render.filepath=str(output/(kind+'-normal.png'));bpy.ops.render.render(write_still=True)
