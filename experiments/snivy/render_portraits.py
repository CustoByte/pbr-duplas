"""Render private face/body portraits from the player's converted Snivy rig.

Run with Blender 3.3. No source meshes/textures are bundled in this script.
"""

import colorsys
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graphics_common import arguments, load_brres_addon, load_pbr_addon

args = arguments()
load_brres_addon(args)
load_pbr_addon(args)
bpy.ops.wm.open_mainfile(filepath=str(args.workdir / "snivy-export.blend"))
scene = bpy.context.scene
rig, obj = bpy.data.objects["SnivyExport"], bpy.data.objects["SnivyExportMesh"]
rig.matrix_world = Matrix.Rotation(math.pi / 2, 4, "X")
rig.animation_data.action = getattr(rig.data, "prop_wait")
scene.frame_set(0)
for material in obj.data.materials:
    material.node_tree.animation_data.action = getattr(material, "prop_wait")
for item in list(scene.objects):
    if item.type in ("CAMERA", "LIGHT"):
        bpy.data.objects.remove(item, do_unlink=True)
dep = bpy.context.evaluated_depsgraph_get()
evaluated = obj.evaluated_get(dep)
points = [evaluated.matrix_world @ vertex.co for vertex in evaluated.data.vertices]
head_materials = {i for i, m in enumerate(obj.data.materials)
                  if m.name in ("Snivy_Eye", "Snivy_Mouth")}
head_vertices = {i for polygon in obj.data.polygons
                 if polygon.material_index in head_materials for i in polygon.vertices}
head_points = [points[i] for i in head_vertices]
if len(head_points) < 10:
    raise ValueError("Head vertices could not be identified safely")


def bounds(coords):
    lo = Vector(tuple(min(v[i] for v in coords) for i in range(3)))
    hi = Vector(tuple(max(v[i] for v in coords) for i in range(3)))
    return (lo + hi) / 2, max(hi - lo)


body_center, body_span = bounds(points)
head_center, head_span = bounds(head_points)
head_center.z += head_span * 0.12
bpy.ops.object.camera_add()
camera = bpy.context.object
camera.data.type = "ORTHO"
scene.camera = camera
for direction, energy, size in (((1, -2, 3), 90, 4), ((-2, -0.5, 1), 50, 3)):
    bpy.ops.object.light_add(type="AREA", location=body_center + Vector(direction) * body_span)
    light = bpy.context.object
    light.data.energy = energy * body_span * body_span
    light.data.shape = "DISK"
    light.data.size = size * body_span
    light.rotation_euler = (body_center - light.location).to_track_quat("-Z", "Y").to_euler()
scene.world.color = (0.2, 0.2, 0.2)
scene.world.use_nodes = True
background = scene.world.node_tree.nodes.get("Background")
background.inputs["Color"].default_value = (0.4, 0.4, 0.4, 1)
background.inputs["Strength"].default_value = 0.6
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 24
scene.render.film_transparent = True
scene.render.resolution_x = scene.render.resolution_y = 384
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "Medium High Contrast"
directory = args.workdir / "portraits"
directory.mkdir(exist_ok=True)
for variant in ("normal", "shiny"):
    if variant == "shiny":
        for material in obj.data.materials:
            for node in material.node_tree.nodes:
                if node.type != "TEX_IMAGE" or not node.image:
                    continue
                image = node.image.copy()
                pixels = list(image.pixels)
                for at in range(0, len(pixels), 4):
                    h, s, v = colorsys.rgb_to_hsv(*pixels[at:at + 3])
                    if 0.16 <= h <= 0.50 and s > 0.15:
                        pixels[at:at + 3] = colorsys.hsv_to_rgb(h + 0.07, s, v)
                image.pixels = pixels
                image.update()
                node.image = image
    for kind, center, span, margin in (("face", head_center, head_span, 1.7),
                                       ("body", body_center, body_span, 1.3)):
        camera.location = center + Vector((0.85, -1.6, 0.6)) * span
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        camera.data.ortho_scale = span * margin
        scene.render.filepath = str(directory / f"{kind}-{variant}.png")
        bpy.ops.render.render(write_still=True)
(directory / "render-report.json").write_text(json.dumps(dict(
    source="private converted Snivy rig", render_size=[384, 384],
    variants=["normal", "shiny"], views=["face", "body"],
    shiny_policy="green hue +0.07; other hues/alpha preserved; visual review pending",
    rendered_in_dolphin=False,
), indent=2) + "\n")
