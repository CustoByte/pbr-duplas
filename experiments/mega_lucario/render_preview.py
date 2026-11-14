"""Private Blender preview; -- work-directory. Not a Dolphin capture."""
import bpy,sys,math
from mathutils import Vector
from pathlib import Path
root=Path(sys.argv[sys.argv.index('--')+1])
bpy.ops.wm.open_mainfile(filepath=str(root/'mega-retarget.blend'))
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='Standard'
scene.world=bpy.data.worlds.new('World');scene.world.color=(0.15,0.15,0.15)
obj=bpy.data.objects['MegaLucarioMesh']
verts=[obj.matrix_world@v.co for v in obj.data.vertices];lo=Vector([min(v[i] for v in verts) for i in range(3)]);hi=Vector([max(v[i] for v in verts) for i in range(3)]);center=(hi+lo)/2;span=max(hi-lo)
bpy.ops.object.camera_add();cam=bpy.context.object;scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=span*1.25
cam.location=center+Vector((0.8,-2,0.5))*span;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
for direction,power in [((1,-2,3),80),((-2,-1,1),40)]:
 bpy.ops.object.light_add(type='AREA',location=center+Vector(direction)*span);o=bpy.context.object;o.data.energy=power*span*span;o.data.size=span*2;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
for action,frame in [('wait',0),('punch',48),('damage',30)]:
 rig=bpy.data.objects['MegaLucarioSource'];rig.animation_data.action=bpy.data.actions['Mega_'+action];scene.frame_set(frame)
 scene.render.filepath=str(root/('mega-'+action+'-preview.png'));bpy.ops.render.render(write_still=True)
