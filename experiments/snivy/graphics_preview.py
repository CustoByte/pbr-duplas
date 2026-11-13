"""Render decoded experimental SDR idle frames with simplified studio lighting.

A diagnostic preview, not a screenshot of Pokémon Battle Revolution.
"""

import math
import contextlib
import os
import json
import bpy
from mathutils import Matrix, Vector, Euler
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graphics_common import arguments, load_pbr_addon

args = arguments()
ROOT = args.workdir
pbr = load_pbr_addon(args, register=False)
io = pbr.importer
with open(os.devnull, "w") as quiet, contextlib.redirect_stdout(quiet):
    model = io.parseModel(str(ROOT / "snivy-experimental.sdr"))
skele = model["skeletons"][0]
decoded = model["meshes"][0]
action = io.anim_dict[0]
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
faces = []
mats = []
for part in decoded.parts:
    faces.extend(face.vertexIndices for face in part.faces)
    mats.extend([part.materialIndex] * len(part.faces))
mesh = bpy.data.meshes.new("SDRDecodedMesh")
mesh.from_pydata(decoded.vertices, [], faces)
mesh.update()
obj = bpy.data.objects.new("Snivy SDR preview", mesh)
bpy.context.scene.collection.objects.link(obj)
uv = mesh.uv_layers.new(name="UVMap")
loop = 0
for part in decoded.parts:
    for face in part.faces:
        for texid in face.texCoordIndices:
            uv.data[loop].uv = decoded.texCoords[texid]
            loop += 1
for matdata in model["materials"]:
    image = model["images"][model["textures"][matdata.textureIndex].imageIndex]
    if image.width <= 0 or image.height <= 0 or not image.pixels:
        raise RuntimeError("Empty SDR texture")
    img = bpy.data.images.new(matdata.name, image.width, image.height)
    img.pixels = [x / 255 for x in image.pixels]
    img.update()
    mat = bpy.data.materials.new(matdata.name)
    mat.use_nodes = True
    n = mat.node_tree.nodes
    bs = n.get("Principled BSDF")
    bs.inputs["Roughness"].default_value = 0.8
    tx = n.new("ShaderNodeTexImage")
    tx.image = img
    mat.node_tree.links.new(tx.outputs["Color"], bs.inputs["Base Color"])
    mesh.materials.append(mat)
for p, mat in zip(mesh.polygons, mats):
    p.material_index = mat
    p.use_smooth = True
C = Matrix.Rotation(math.pi / 2, 4, "X")


def frame_vertices(frame):
    time = frame / 30
    world = {}
    for bone in skele.bones:
        if bone.type == 3:
            continue
        values = {
            "location": list(bone.initialTrans),
            "rotation_euler": list(bone.initialRot),
            "scale": list(bone.initialScale),
        }
        for curve in action["bones"].get(bone.name, []):
            chosen = None
            for key in curve["keyframes"]:
                if key["time"] <= time + 1e-6:
                    chosen = key
            if chosen is not None:
                values[curve["component"]][curve["axis"] - 1] = chosen["value"]
        m = (
            Matrix.Translation(Vector(values["location"]))
            @ Euler(values["rotation_euler"], "XYZ").to_matrix().to_4x4()
            @ Matrix.Diagonal((*values["scale"], 1))
        )
        if bone.parentIndex is not None:
            m = world[skele.bones[bone.parentIndex].name] @ m
        world[bone.name] = m
    result = []
    for index, vertex in enumerate(decoded.vertices):
        position = Vector((0, 0, 0))
        point = Vector(vertex)
        for bone_index, weight in decoded.weights[index].items():
            bone = skele.bones[bone_index]
            position += weight * (world[bone.name] @ bone.inverseBindMatrix @ point)
        result.append(C @ position)
    return result


coords = frame_vertices(0)
mn = Vector(tuple(min(v[i] for v in coords) for i in range(3)))
mx = Vector(tuple(max(v[i] for v in coords) for i in range(3)))
center = (mn + mx) / 2
span = max(mx - mn)
scene = bpy.context.scene
bpy.ops.object.camera_add(
    location=center + Vector((span * 0.85, -span * 1.6, span * 0.6))
)
cam = bpy.context.object
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
cam.data.type = "ORTHO"
cam.data.ortho_scale = span * 1.35
scene.camera = cam
for loc, energy, size in [((1, -2, 3), 90, 4), ((-2, -0.5, 1), 50, 3)]:
    bpy.ops.object.light_add(type="AREA", location=center + Vector(loc) * span)
    o = bpy.context.object
    o.data.energy = energy * span * span
    o.data.shape = "DISK"
    o.data.size = size * span
    o.rotation_euler = (center - o.location).to_track_quat("-Z", "Y").to_euler()
scene.world.color = (0.2, 0.2, 0.2)
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 12
scene.render.resolution_x = 480
scene.render.resolution_y = 480
scene.render.resolution_percentage = 100
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "Medium High Contrast"
scene.render.image_settings.file_format = "PNG"
(ROOT / "idle-frames").mkdir(exist_ok=True)
first = None
max_motion = 0
for index, frame in enumerate(range(0, 84, 3)):
    coords = frame_vertices(frame)
    if first is None:
        first = coords
    else:
        max_motion = max(max_motion, max((a - b).length for a, b in zip(first, coords)))
    for v, co in zip(mesh.vertices, coords):
        v.co = co
    mesh.update()
    scene.render.filepath = str(ROOT / "idle-frames" / f"{index:03d}.png")
    bpy.ops.render.render(write_still=True)
print("DECODED_SDR_PREVIEW_OK", "max_vertex_motion", max_motion)
(ROOT / "preview-report.json").write_text(
    json.dumps(
        {
            "source": "decoded experimental SDR",
            "frames": 28,
            "frame_step": 3,
            "assumed_source_fps": 30,
            "max_vertex_motion": max_motion,
            "native_game_render": False,
            "lighting": "simplified diffuse studio",
        },
        indent=2,
    )
)
