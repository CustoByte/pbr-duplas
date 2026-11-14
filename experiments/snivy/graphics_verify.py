"""Compare decoded SDR matrices and skinned vertices with the original import.

Tests every idle frame and initial/mid/final frames of other candidate actions,
outside the game. Texture comparisons account for RGB5A3 quantization.
"""

import json
import contextlib
import os
import hashlib
import math
import bpy
from mathutils import Matrix, Vector, Euler
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graphics_common import arguments, load_brres_addon, load_pbr_addon

args = arguments()
ROOT = args.workdir
load_brres_addon(args)
pbr = load_pbr_addon(args, register=False)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "snivy-source.blend"))
source = bpy.data.objects["Tsutarja"]
source_mesh = bpy.data.objects["TsutarjaSkin"]
scene = bpy.context.scene
C = Matrix.Rotation(-math.pi / 2, 4, "X")
conversion = json.loads((ROOT / "conversion-report.json").read_text())
slots = conversion["candidate_mapping"]
authored = conversion.get("fluidity_profile", {})
authored_poses = json.loads((ROOT / "expected-poses.json").read_text()) if authored else {}
io = pbr.importer
with open(os.devnull, "w") as quiet, contextlib.redirect_stdout(quiet):
    model = io.parseModel(str(ROOT / "snivy-experimental.sdr"))
skele = model["skeletons"][0]
report = {
    "kind": "SDR decoded matrix/skin/texture roundtrip, not Dolphin",
    "actions": {},
    "material_only_actions": [],
    "textures": [],
    "sdr_sha256": hashlib.sha256(
        (ROOT / "snivy-experimental.sdr").read_bytes()
    ).hexdigest(),
}
for material in model["materials"]:
    source_name = material.name.removeprefix("Snivy_")
    original = bpy.data.materials[source_name].brres.textures[0].imgs[0].img
    source_dimensions = list(original.size)
    w, h = original.size
    target = (1 << (w - 1).bit_length(), 1 << (h - 1).bit_length())
    if target != (w, h):
        original = original.copy()
        original.scale(*target)
    decoded = model["images"][model["textures"][material.textureIndex].imageIndex]
    if [decoded.width, decoded.height] != list(original.size) or not decoded.pixels:
        raise RuntimeError("Missing or resized SDR texture: " + material.name)
    pixels = list(original.pixels)
    if len(pixels) != len(decoded.pixels):
        raise RuntimeError("Pixel count mismatch")
    rgb_error = max(
        abs(a / 255 - b)
        for i, (a, b) in enumerate(zip(decoded.pixels, pixels))
        if i % 4 != 3
    )
    alpha_error = max(
        abs(a / 255 - b)
        for i, (a, b) in enumerate(zip(decoded.pixels, pixels))
        if i % 4 == 3
    )
    if rgb_error > 17 / 255 + 1e-5 or alpha_error > 32 / 255 + 1e-5:
        raise RuntimeError(
            "Texture regression: " + material.name + str((rgb_error, alpha_error))
        )
    report["textures"].append(
        {
            "name": material.name,
            "source_dimensions": source_dimensions,
            "dimensions": [decoded.width, decoded.height],
            "repeat_dimensions_are_power_of_two": all(v > 0 and v & (v - 1) == 0 for v in (decoded.width, decoded.height)),
            "max_rgb_error": rgb_error,
            "max_alpha_error": alpha_error,
        }
    )
for actionid, action in io.anim_dict.items():
    name = action["name"]
    worst = 0
    worstbone = None
    vertex_error = 0
    if name not in slots:
        continue
    if args.native_contract:
        reference_action = next(
            a
            for a in args.native_contract["resources"][0]["actions"]
            if a["name"] == name
        )
        if not reference_action["flags"][1]:
            report["material_only_actions"].append(name)
            continue
    source.animation_data.action = bpy.data.actions[slots[name] + " (Tsutarja)"]
    end = conversion["actions"][name]["frames"] - 1
    frames = (
        list(range(end + 1)) if name in ("idle", "wait") or name in authored else sorted({0, end // 2, end})
    )
    for frame in frames:
        scene.frame_set(frame)
        dep = bpy.context.evaluated_depsgraph_get()
        evaluated = source_mesh.evaluated_get(dep)
        poses = {
            ("SnivyMotion" if b.name == "Origin" else b.name): C
            @ source.matrix_world
            @ b.matrix
            for b in source.pose.bones
        }
        if name in authored:
            poses = {bone: Matrix(rows) for bone, rows in authored_poses[name][str(frame)].items()}
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
        for bone, target in poses.items():
            error = max(
                abs(world[bone][i][j] - target[i][j])
                for i in range(4)
                for j in range(4)
            )
            if error > worst:
                worst = error
                worstbone = bone
        decoded = model["meshes"][0]
        assert len(decoded.vertices) == len(evaluated.data.vertices)
        for index, vertex in enumerate(decoded.vertices):
            position = Vector((0, 0, 0))
            point = Vector(vertex)
            for bone_index, weight in decoded.weights[index].items():
                bone = skele.bones[bone_index]
                position += weight * (world[bone.name] @ bone.inverseBindMatrix @ point)
            if name in authored:
                original_vertex = source_mesh.data.vertices[index]
                original_point = C @ source_mesh.matrix_world @ original_vertex.co
                target = Vector((0, 0, 0))
                for group in original_vertex.groups:
                    bone_name = source_mesh.vertex_groups[group.group].name
                    exported_name = 'SnivyMotion' if bone_name == 'Origin' else bone_name
                    original_bind = C @ source.matrix_world @ source.data.bones[bone_name].matrix_local
                    target += group.weight * (poses[exported_name] @ original_bind.inverted() @ original_point)
            else:
                target = C @ evaluated.matrix_world @ evaluated.data.vertices[index].co
            vertex_error = max(vertex_error, (position - target).length)
    report["actions"][name] = {
        "max_vertex_distance": vertex_error,
        "max_matrix_error": worst,
        "worst_bone": worstbone,
        "sampled_frames": frames,
        "authored_transition": name in authored,
    }
report["passed"] = (
    len(report["actions"]) + len(report["material_only_actions"])
) == len(slots) and not any(
    v["max_vertex_distance"] > 0.005 or v["max_matrix_error"] > 0.0005
    for v in report["actions"].values()
)
print(json.dumps(report, indent=2))
(ROOT / "roundtrip-report.json").write_text(json.dumps(report, indent=2))
if not report["passed"]:
    raise RuntimeError("SDR transform regression")
print("ROUNDTRIP_MATRIX_OK")
