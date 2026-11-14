"""Blender 3.3: export a PRIVATE converted Mega blend to runtime GLB.

blender -b mega-candidate.blend --python export_local_glb.py -- output.glb
No assets are committed/published by this script.
"""
import bpy
import json
from pathlib import Path
import sys

output = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
mesh = bpy.data.objects.get('MegaLucarioMesh')
if mesh is None:
    raise ValueError('Missing converted Mega mesh')
rigs = [m.object for m in mesh.modifiers if m.type == 'ARMATURE' and m.object]
if len(rigs) != 1:
    raise ValueError('Expected one skin armature')
rig = rigs[0]
actions = [a for a in bpy.data.actions if a.name.startswith('Mega_')]
if len(actions) != 9:
    raise ValueError('Expected the nine validated body actions')
for obj in bpy.context.scene.objects:
    obj.select_set(False)
mesh.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
for action in list(bpy.data.actions):
    if action not in actions:
        bpy.data.actions.remove(action)
rig.animation_data_create()
rig.animation_data.action = bpy.data.actions['Mega_wait']
for track in list(rig.animation_data.nla_tracks):
    rig.animation_data.nla_tracks.remove(track)
rig.animation_data.use_nla = False
# The Blender exporter only enumerates all actions when exactly one armature
# exists in its export tree. The native reference rig is no longer needed.
for other in list(bpy.data.objects):
    if other.type == 'ARMATURE' and other != rig:
        bpy.data.objects.remove(other, do_unlink=True)
# This private converted rig already uses Y-up (the game coordinate system).
# Do not apply Blender Z-up -> glTF Y-up conversion a second time.
# Body-only prototype: freeze materials at the open-eye/default UV pose.
# Removing node actions alone leaves the last sleep/wakeup offset cached.
for material in mesh.data.materials:
    if material.node_tree:
        material.node_tree.animation_data_clear()
        mapping = material.node_tree.nodes.get('MegaUV')
        if mapping:
            mapping.inputs['Location'].default_value = (0, 0, 0)
# GLTF stores bone transforms in seconds, independently of rendering frequency.
bpy.context.scene.render.fps = 30
bpy.context.scene.frame_set(0)
output.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.export_scene.gltf(filepath=str(output), export_format='GLB', use_selection=True,
    export_animations=True, export_frame_range=False, export_force_sampling=True,
    export_nla_strips=True, export_anim_single_armature=True, export_skins=True, export_yup=False,
    export_materials='EXPORT', export_texcoords=True, export_normals=True)
print('NATIVE_GLB_EXPORTED', json.dumps(dict(bytes=output.stat().st_size,
    actions=[a.name for a in actions], source='private converted model',
    body_animation_fps=30, protected_asset_published=False)))
