"""Render normal Mega Lucario portraits for the established circular icon pipeline.

Blender: -- working-directory. No shiny variant is invented by this renderer.
"""
import bpy,sys
from pathlib import Path
from mathutils import Vector
root=Path(sys.argv[sys.argv.index('--')+1]);output=root/'portraits';output.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(root/'mega-retarget.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['MegaLucarioSource'];obj=bpy.data.objects['MegaLucarioMesh']
rig.animation_data.action=bpy.data.actions['Mega_wait'];scene.frame_set(0)
mesh=obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
points=[obj.matrix_world@v.co for v in mesh.vertices]
eye={i for p in obj.data.polygons if '193' in obj.data.materials[p.material_index].name for i in p.vertices}
if len(eye)<10:raise ValueError('Head region not found')
def bounds(points):
 lo=Vector([min(v[i] for v in points) for i in range(3)]);hi=Vector([max(v[i] for v in points) for i in range(3)])
 return (lo+hi)/2,max(hi-lo)
center,span=bounds(points);head,headspan=bounds([points[i] for i in eye])
scene.world=bpy.data.worlds.new('PortraitWorld');scene.world.color=(0.2,0.2,0.2)
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';scene.camera=camera
for direction,power in [((1,-2,3),80),((-2,-1,1),40)]:
 bpy.ops.object.light_add(type='AREA',location=center+Vector(direction)*span);o=bpy.context.object;o.data.energy=power*span*span;o.data.size=span*2;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16
scene.render.resolution_x=scene.render.resolution_y=384;scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.view_settings.view_transform='Standard'
for kind,target,size,margin in [('body',center,span,1.2),('face',head,headspan,1.35)]:
 camera.location=target+Vector((0.7,-2,0.35))*size;camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=size*margin
 scene.render.filepath=str(output/(kind+'-normal.png'));bpy.ops.render.render(write_still=True)
