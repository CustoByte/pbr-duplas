"""Build a private Blender scene from the audited ufbx C intermediate.

Blender 3.3 script; expects -- intermediate.json textures-dir output.blend.
Keeps skin bind poses, corner UVs and all source vertices. Does not install assets.
"""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Matrix, Vector

source, textures, output = map(Path, sys.argv[sys.argv.index('--') + 1:])
r = json.loads(source.read_text())
if len(r['meshes']) != 1:
    raise ValueError('Expected the inspected single mesh')
m = r['meshes'][0]

def matrix(cols):
    return Matrix([list(row) for row in zip(*cols)] + [[0, 0, 0, 1]])

bpy.ops.wm.read_factory_settings(use_empty=True)
# FBX world is Y-up in centimetres; PBR preview is Z-up in decimetres.
C = Matrix.Scale(0.1, 4) @ Matrix.Rotation(math.pi / 2, 4, 'X')
nodes = {n['id']: n for n in r['nodes']}
binds = {c['node']: matrix(c['bind_world']) for c in m['clusters']}
geometry = matrix(nodes[m['node']]['geometry'])
for c in m['clusters']:
    d = binds[c['node']] @ matrix(c['geometry_to_bone']) - geometry
    if max(abs(v) for row in d for v in row) > 1e-5:
        raise ValueError('Inconsistent source bind matrices')
rig_data = bpy.data.armatures.new('MegaLucarioSource')
rig = bpy.data.objects.new('MegaLucarioSource', rig_data)
bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for n in r['nodes']:
    if n['id'] in (0, m['node']):
        continue
    b = rig_data.edit_bones.new(n['name'])
    b.head = (0, 0, 0)
    b.tail = (0, 0.2, 0)
    b.matrix = C @ binds.get(n['id'], matrix(n['world']))
    parent = nodes.get(n['parent'])
    if parent and parent['name'] in rig_data.edit_bones:
        b.parent = rig_data.edit_bones[parent['name']]
bpy.ops.object.mode_set(mode='OBJECT')
faces = [m['indices'][at:at + count] for at, count in m['faces']]
mesh = bpy.data.meshes.new('MegaLucarioMesh')
mesh.from_pydata([C @ geometry @ Vector(v) for v in m['positions']], [], faces)
mesh.update()
obj = bpy.data.objects.new('MegaLucarioMesh', mesh)
bpy.context.collection.objects.link(obj)
obj.parent = rig
uv = mesh.uv_layers.new(name='UVMap')
for loop in mesh.loops:
    uv.data[loop.index].uv = m['uvs'][loop.index]
mesh.normals_split_custom_set([((C @ geometry).to_3x3().inverted().transposed() @ Vector(n)).normalized() for n in m['normals']])
mesh.use_auto_smooth = True
for p in mesh.polygons:
    p.use_smooth = True
    p.material_index = m['face_materials'][p.index]
for data in m['materials']:
    mat = bpy.data.materials.new(data['name'])
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Roughness'].default_value = 0.8
    filename = Path(data['textures'][0].replace('\\', '/')).name
    image = bpy.data.images.load(str(textures / filename), check_existing=True)
    image.pack()
    tx = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tx.image = image
    tx.interpolation = 'Linear'
    mat.node_tree.links.new(tx.outputs['Color'], shader.inputs['Base Color'])
    mesh.materials.append(mat)
for c in m['clusters']:
    group = obj.vertex_groups.new(name=nodes[c['node']]['name'])
    for vertex, weight in c['weights']:
        if weight > 0:
            group.add([vertex], weight, 'REPLACE')
weights = [sum(g.weight for g in v.groups) for v in mesh.vertices]
if min(weights) < 0.99 or max(weights) > 1.01:
    raise ValueError('Missing or non-normalized skin weights')
if max(len(v.groups) for v in mesh.vertices) > 4:
    raise ValueError('Source exceeds the audited four-weight exporter limit')
mod = obj.modifiers.new('MegaLucarioSkin', 'ARMATURE')
mod.object = rig
bpy.context.view_layer.update()
evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
rest_error = max((a.co - b.co).length for a,b in zip(mesh.vertices,evaluated.data.vertices))
if rest_error > 0.001:
    raise ValueError('Source rest pose changed during import')
report = dict(vertices=len(mesh.vertices),triangles=len(mesh.polygons),bones=len(rig_data.bones),
              materials=len(mesh.materials),max_weights=max(len(v.groups) for v in mesh.vertices),
              rest_pose_max_vertex_error=rest_error, source_vertices_preserved=True,
              pbr_game_tested=False)
output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(output))
print('MEGA_SOURCE_IMPORTED',json.dumps(report),flush=True)
