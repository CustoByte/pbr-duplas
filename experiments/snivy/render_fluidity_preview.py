"""Private before/after preview sampled from decoded SDRs at every 30 fps frame.

Studio render, not Dolphin footage. Only the declared file markers determine
these demonstration cuts; the game's event timing/blending may differ.
"""
import argparse
import bisect
import contextlib
import copy
import json
import math
import os
from pathlib import Path
import sys
import bpy
from mathutils import Matrix, Vector, Euler

sys.path[:0] = [str(Path(__file__).resolve().parent), str(Path(__file__).resolve().parents[2] / 'mod-source')]
from graphics_common import load_pbr_addon
from pkx_reference import scene_inventory

p = argparse.ArgumentParser()
for name in ('before', 'after', 'pbr-addon', 'output'):
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--first-frame-only', action='store_true')
p.add_argument('--data-only', action='store_true')
a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
a.native_contract = None
sdk = load_pbr_addon(a, register=False)
C = Matrix.Rotation(math.pi / 2, 4, 'X')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
scene = bpy.context.scene


class Actor:
    def __init__(self, path, offset):
        data = path.read_bytes()
        self.meta = {v['name']: v for v in scene_inventory(data)['actions']}
        with open(os.devnull, 'w') as quiet, contextlib.redirect_stdout(quiet):
            self.model = sdk.importer.parseModel(str(path))
        self.actions = copy.deepcopy({v['name']: v for v in sdk.importer.anim_dict.values()})
        self.bones = self.model['skeletons'][0].bones
        self.decoded = self.model['meshes'][0]
        self.cache = {}
        faces, mats, texcoords = [], [], []
        for part in self.decoded.parts:
            for face in part.faces:
                faces.append(face.vertexIndices)
                mats.append(part.materialIndex)
                texcoords.extend(self.decoded.texCoords[i] for i in face.texCoordIndices)
        self.mesh = bpy.data.meshes.new('decoded SDR')
        self.mesh.from_pydata(self.decoded.vertices, [], faces)
        self.mesh.update()
        uv = self.mesh.uv_layers.new(name='UVMap')
        for loop, coord in zip(uv.data, texcoords):
            loop.uv = coord
        self.obj = bpy.data.objects.new(path.parent.name, self.mesh)
        scene.collection.objects.link(self.obj)
        self.obj.location = offset
        for source in self.model['materials']:
            image = self.model['images'][self.model['textures'][source.textureIndex].imageIndex]
            img = bpy.data.images.new(source.name, image.width, image.height)
            img.pixels = [x / 255 for x in image.pixels]
            img.update()
            mat = bpy.data.materials.new(source.name)
            mat.use_nodes = True
            bs = mat.node_tree.nodes.get('Principled BSDF')
            bs.inputs['Roughness'].default_value = 0.8
            texture = mat.node_tree.nodes.new('ShaderNodeTexImage')
            texture.image = img
            texture.extension = 'REPEAT'
            mat.node_tree.links.new(texture.outputs['Color'], bs.inputs['Base Color'])
            self.mesh.materials.append(mat)
        for polygon, material in zip(self.mesh.polygons, mats):
            polygon.material_index = material
            polygon.use_smooth = True

    def vertices(self, name, frame):
        frame = round(frame, 5)
        key = (name, frame)
        if key in self.cache:
            return self.cache[key]
        action = self.actions.get(name) if name else None
        time = frame / 30
        world = {}
        for bone in self.bones:
            if bone.type == 3:
                continue
            values = {'location': list(bone.initialTrans), 'rotation_euler': list(bone.initialRot), 'scale': list(bone.initialScale)}
            if action:
                for curve in action['bones'].get(bone.name, []):
                    keys = curve['keyframes']
                    index = bisect.bisect_right([k['time'] for k in keys], time + 1e-6) - 1
                    if index >= 0:
                        values[curve['component']][curve['axis'] - 1] = keys[index]['value']
            mat = Matrix.Translation(Vector(values['location'])) @ Euler(values['rotation_euler'], 'XYZ').to_matrix().to_4x4() @ Matrix.Diagonal((*values['scale'], 1))
            if bone.parentIndex is not None:
                mat = world[self.bones[bone.parentIndex].name] @ mat
            world[bone.name] = mat
        result = []
        skin = {i: world[bone.name] @ bone.inverseBindMatrix for i, bone in enumerate(self.bones) if bone.type != 3}
        for i, vertex in enumerate(self.decoded.vertices):
            point = Vector(vertex)
            out = Vector((0, 0, 0))
            for bone_id, weight in self.decoded.weights[i].items():
                out += weight * (skin[bone_id] @ point)
            result.append(C @ out)
        self.cache[key] = result
        return result

    def set(self, name, frame):
        vertices = self.vertices(name, frame)
        self.mesh.vertices.foreach_set('co', [v for co in vertices for v in co])
        self.mesh.update()

    def jump(self, start, end):
        return max((a - b).length for a, b in zip(start, end))


right = Vector((1.6, 0.85, 0)).normalized()
actors = [Actor(a.before, -right * 2.65), Actor(a.after, right * 2.65)]
for actor in actors:
    actor.set('wait', 0)
# Same camera, scale, timing and lights for both columns.
center = Vector((0, 0, 2.0))
bpy.ops.object.camera_add(location=center + Vector((0.85, -1.6, 0.48)) * 8)
camera = bpy.context.object
camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 5.6
scene.camera = camera
for direction, energy in (((1, -2, 3), 1300), ((-2, -0.5, 1), 700)):
    bpy.ops.object.light_add(type='AREA', location=center + Vector(direction) * 4)
    light = bpy.context.object
    light.data.energy = energy
    light.data.shape = 'DISK'
    light.data.size = 6
    light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
scene.world.color = (0.10, 0.13, 0.18)
scene.world.use_nodes = True
scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value = (0.16, 0.2, 0.26, 1)
scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value = 0.5
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, 0.30))
plane = bpy.context.object
floor = bpy.data.materials.new('neutral ground')
floor.diffuse_color = (0.12, 0.16, 0.22, 1)
plane.data.materials.append(floor)
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 8
scene.render.threads_mode = 'FIXED'
scene.render.threads = 2
scene.render.resolution_x = 960
scene.render.resolution_y = 480
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'Standard'
scene.view_settings.look = 'Medium High Contrast'
a.output.mkdir(parents=True, exist_ok=True)


def sample(actor, section, time):
    if section == 'selection':
        if time < 0.3:
            return 'wait', 0, 'Espera inicial'
        time -= 0.3
        duration = actor.meta['kime_a']['end']
        if time < duration:
            return 'kime_a', time * 30, 'Seleção'
        return 'wait', ((time - duration) % actor.meta['wait']['length']) * 30, 'Espera'
    if time < 0.6:
        return 'wait', time * 30, 'Espera'
    time -= 0.6
    duration = actor.meta['damage']['end']
    if time < duration:
        return 'damage', time * 30, 'Dano'
    return 'wait', ((time - duration) % actor.meta['wait']['length']) * 30, 'Recuperação / espera'


labels = []
frame_positions = []
frames = [('selection', i / 30) for i in range(120)] + [('damage', i / 30) for i in range(96)]
if a.first_frame_only:
    frames = frames[:1]
for index, (section, time) in enumerate(frames):
    states = []
    for actor in actors:
        name, frame, state = sample(actor, section, time)
        actor.set(name, frame)
        states.append(state)
    labels.append(dict(frame=index, section=section, seconds=time, states=states))
    if a.data_only:
        frame_positions.append([[list(vertex.co) for vertex in actor.mesh.vertices] for actor in actors])
    else:
        scene.render.filepath = str(a.output / f'{index:04d}.png')
        bpy.ops.render.render(write_still=True)
    print('PREVIEW_FRAME', index, len(frames), flush=True)
if a.data_only:
    import numpy as np
    payload = {'positions': np.array(frame_positions, dtype='float32')}
    for i, actor in enumerate(actors):
        payload[f'faces_{i}'] = np.array([list(p.vertices) for p in actor.mesh.polygons], dtype='int32')
        payload[f'uv_{i}'] = np.array([list(v.uv) for v in actor.mesh.uv_layers[0].data], dtype='float32')
        payload[f'materials_{i}'] = np.array([p.material_index for p in actor.mesh.polygons], dtype='int32')
        for j, material in enumerate(actor.model['materials']):
            image = actor.model['images'][actor.model['textures'][material.textureIndex].imageIndex]
            payload[f'texture_{i}_{j}'] = np.array(image.pixels, dtype='uint8').reshape(image.height, image.width, 4)
    np.savez_compressed(a.output / 'decoded-frames.npz', **payload)
metrics = []
for actor in actors:
    idle = actor.vertices('wait', 0)
    metrics.append(dict(initial_to_wait=actor.jump(actor.vertices(None, 0), idle),
                        selection_to_wait=actor.jump(actor.vertices('kime_a', actor.meta['kime_a']['end'] * 30), idle),
                        damage_to_wait=actor.jump(actor.vertices('damage', actor.meta['damage']['end'] * 30), idle),
                        damage_marker_end_seconds=actor.meta['damage']['end'],
                        selection_marker_end_seconds=actor.meta['kime_a']['end']))
(a.output / 'preview.json').write_text(json.dumps(dict(fps=30, frames=labels, before=metrics[0], after=metrics[1],
    source='actual decoded SDRs', native_game_render=False, simplified_lighting=True,
    transition_assumption='cut at declared end marker; actual game event timing may differ'), indent=2) + '\n')
