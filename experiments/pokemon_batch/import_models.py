"""Private Blender 3.3 model staging; not a Dolphin archive or animation builder.

-- kind(glTF|ufbx) source textures-root output.blend output.glb
FBX inputs use the audited ufbx intermediate; multiple body/prop meshes survive.
"""
import bpy
import hashlib
import json
import math
from pathlib import Path
import sys
from mathutils import Matrix, Vector

kind, src, textures, blend, glb = sys.argv[sys.argv.index('--')+1:]
src, textures, blend, glb = map(Path, (src, textures, blend, glb))
bpy.ops.wm.read_factory_settings(use_empty=True)
report = dict(source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
              source_kind=kind, animation_created=False, dolphin_ready=False,
              native_battle_ready=False, animations_verified=False)


def matrix(columns):
    return Matrix([list(row) for row in zip(*columns)] + [[0, 0, 0, 1]])


if kind == 'glTF':
    bpy.ops.import_scene.gltf(filepath=str(src))
    report['source_coordinate_conversion'] = 'Blender glTF importer Y-up to Z-up'
elif kind == 'ufbx':
    data = json.loads(src.read_text())
    nodes = {n['id']: n for n in data['nodes']}
    mesh_nodes = {m['node'] for m in data['meshes']}
    binds = {}
    rest_error = 0.0
    for mesh in data['meshes']:
        geometry = matrix(nodes[mesh['node']]['geometry'])
        for cluster in mesh['clusters']:
            bind = matrix(cluster['bind_world'])
            difference = bind @ matrix(cluster['geometry_to_bone']) - geometry
            if max(abs(v) for row in difference for v in row) > 1e-3:
                raise ValueError('Inconsistent skin bind: ' + nodes[cluster['node']]['name'])
            if cluster['node'] in binds:
                difference = bind - binds[cluster['node']]
                if max(abs(v) for row in difference for v in row) > 1e-3:
                    raise ValueError('Meshes disagree about shared bone bind')
            binds[cluster['node']] = bind
    # FBX dump is Y-up; keep Blender staging Z-up, export back to glTF Y-up.
    basis = Matrix.Scale(.1, 4) @ Matrix.Rotation(math.pi/2, 4, 'X')
    armature = bpy.data.armatures.new('SourceRig')
    rig = bpy.data.objects.new('SourceRig', armature)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bone_names = {}
    for node in data['nodes']:
        if node['id'] == 0 or node['id'] in mesh_nodes:
            continue
        bone = armature.edit_bones.new(node['name'] or ('Node_' + str(node['id'])))
        bone_names[node['id']] = bone.name
        bone.head = (0, 0, 0)
        bone.tail = (0, .2, 0)
        bone.matrix = basis @ binds.get(node['id'], matrix(node['world']))
    for node in data['nodes']:
        if node['id'] in bone_names and node['parent'] in bone_names:
            armature.edit_bones[bone_names[node['id']]].parent = armature.edit_bones[bone_names[node['parent']]]
    bpy.ops.object.mode_set(mode='OBJECT')
    images = list(textures.rglob('*.png'))
    texture_cache = {}
    def find_texture(name):
        path = Path(name.replace('\\', '/'))
        matches = [p for p in images if p.name.casefold() == path.name.casefold()]
        if not matches:
            raise ValueError('Missing diffuse texture: ' + path.name)
        preferred = [p for p in matches if 'shiny' not in str(p).casefold() and '_rare' not in p.stem.casefold()]
        if preferred: matches = preferred
        if path.exists() and path in matches: return path
        if len(matches) != 1:
            raise ValueError('Ambiguous diffuse texture: ' + path.name)
        return matches[0]
    for number, item in enumerate(data['meshes']):
        geometry = matrix(nodes[item['node']]['geometry'])
        name = nodes[item['node']]['name'] or ('Part_' + str(number))
        mesh = bpy.data.meshes.new(name)
        faces = [item['indices'][start:start+count] for start, count in item['faces']]
        mesh.from_pydata([basis @ geometry @ Vector(v) for v in item['positions']], [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        bpy.context.collection.objects.link(obj)
        obj.parent = rig
        uv = mesh.uv_layers.new(name='UVMap')
        for loop in mesh.loops:
            uv.data[loop.index].uv = item['uvs'][loop.index]
        normal_matrix = (basis @ geometry).to_3x3().inverted().transposed()
        mesh.normals_split_custom_set([(normal_matrix @ Vector(n)).normalized() for n in item['normals']])
        mesh.use_auto_smooth = True
        for polygon in mesh.polygons:
            polygon.use_smooth = True
            polygon.material_index = item['face_materials'][polygon.index]
        for material in item['materials']:
            mat = bpy.data.materials.new(material['name'])
            mat.use_nodes = True
            shader = mat.node_tree.nodes.get('Principled BSDF')
            shader.inputs['Roughness'].default_value = .8
            candidates = [n for n in material['textures'] if n.lower().endswith(('.png', '.tga'))]
            if not candidates:
                raise ValueError('Material without diffuse texture: ' + material['name'])
            path = find_texture(candidates[0])
            if str(path) not in texture_cache:
                texture_cache[str(path)] = bpy.data.images.load(str(path), check_existing=True)
                texture_cache[str(path)].pack()
            image = texture_cache[str(path)]
            node = mat.node_tree.nodes.new('ShaderNodeTexImage')
            node.image = image
            mat.node_tree.links.new(node.outputs['Color'], shader.inputs['Base Color'])
            mesh.materials.append(mat)
        for cluster in item['clusters']:
            group = obj.vertex_groups.new(name=bone_names[cluster['node']])
            for vertex, weight in cluster['weights']:
                if weight > 0: group.add([vertex], weight, 'REPLACE')
        for vertex in mesh.vertices:
            weights = [g.weight for g in vertex.groups if g.weight > 0]
            if len(weights) > 4 or abs(sum(weights)-1) > .01:
                raise ValueError('Invalid weight budget on ' + name)
        modifier = obj.modifiers.new('Skin', 'ARMATURE')
        modifier.object = rig
        bpy.context.view_layer.update()
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        error = max((a.co-b.co).length for a, b in zip(mesh.vertices, evaluated.data.vertices))
        rest_error = max(rest_error, error)
    if rest_error > .002:
        raise ValueError('Skin bind pose changed: ' + str(rest_error))
    report.update(source_coordinate_conversion='Y-up to Blender Z-up', max_rest_skin_error=rest_error)
else:
    raise ValueError('Unsupported staging input')

meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
rigs = [o for o in bpy.context.scene.objects if o.type == 'ARMATURE']
if not meshes or not rigs:
    raise ValueError('Missing mesh/skin')
for obj in bpy.context.scene.objects: obj.select_set(obj.type in ('MESH', 'ARMATURE', 'EMPTY'))
for rig in rigs:
    if rig.animation_data: rig.animation_data_clear()
report.update(meshes=[dict(name=o.name, vertices=len(o.data.vertices), polygons=len(o.data.polygons)) for o in meshes],
              rigs=[dict(name=o.name, bones=len(o.data.bones), bone_names=[b.name for b in o.data.bones]) for o in rigs],
              images=[dict(name=i.name, size=list(i.size)) for i in bpy.data.images], supplied_motion_clips=0)
blend.parent.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', use_selection=True,
    export_animations=False, export_skins=True, export_yup=True, export_materials='EXPORT',
    export_texcoords=True, export_normals=True)
report.update(glb_sha256=hashlib.sha256(glb.read_bytes()).hexdigest(), glb_bytes=glb.stat().st_size)
blend.with_suffix('.json').write_text(json.dumps(report, indent=2)+'\n')
print('STAGED_PRIVATE_MODEL', glb.name, report['glb_bytes'])
