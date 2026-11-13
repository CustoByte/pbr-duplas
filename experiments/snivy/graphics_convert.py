"""Bake an experimental SDR rig with affine compensation and candidate actions.

This preserves source matrices through auxiliary bones, not a species replacement.
Shader fidelity, event timing and native-game playback remain unverified.
"""

import math
import json
import bpy
import numpy as np
from mathutils import Matrix
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graphics_common import arguments, load_brres_addon, load_pbr_addon, SLOTS

args = arguments()
ROOT = args.workdir
load_brres_addon(args)
pbr = load_pbr_addon(args)
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "snivy-source.blend"))
scene = bpy.context.scene
scene.render.fps = 30
src = bpy.data.objects["Tsutarja"]
srcmesh = bpy.data.objects["TsutarjaSkin"]
source_bones = list(src.data.bones)
names = {
    b.name: ("SnivyMotion" if b.name == "Origin" else b.name) for b in source_bones
}
C = Matrix.Rotation(-math.pi / 2, 4, "X")
# A new static root preserves animated original root and Origin channels.
data = bpy.data.armatures.new("SnivyExportRig")
rig = bpy.data.objects.new("SnivyExport", data)
scene.collection.objects.link(rig)
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
root = data.edit_bones.new("PBR_StaticRoot")
root.head = (0, 0, 0)
root.tail = (0, 1, 0)
for bone in source_bones:
    parent = data.edit_bones[names[bone.parent.name]] if bone.parent else root
    helper = data.edit_bones.new("Affine_" + bone.name)
    helper.head = (0, 0, 0)
    helper.tail = (0, 0.1, 0)
    helper.matrix = parent.matrix.copy()
    helper.parent = parent
    b = data.edit_bones.new(names[bone.name])
    b.head = (0, 0, 0)
    b.tail = (0, 0.1, 0)
    b.matrix = C @ src.matrix_world @ bone.matrix_local
    b.parent = helper
bpy.ops.object.mode_set(mode="OBJECT")
for b in rig.pose.bones:
    b.rotation_mode = "XYZ"
mesh = srcmesh.copy()
mesh.data = srcmesh.data.copy()
mesh.name = "SnivyExportMesh"
scene.collection.objects.link(mesh)
mesh.animation_data_clear()
mesh.parent = rig
mesh.matrix_parent_inverse = Matrix.Identity(4)
mesh.matrix_world = Matrix.Identity(4)
mesh.data.transform(C @ srcmesh.matrix_world)
for vg in mesh.vertex_groups:
    if vg.name in names:
        vg.name = names[vg.name]
for mod in list(mesh.modifiers):
    mesh.modifiers.remove(mod)
mod = mesh.modifiers.new("SnivySkin", "ARMATURE")
mod.object = rig
if any(len([g for g in v.groups if g.weight > 0]) > 4 for v in mesh.data.vertices):
    raise RuntimeError("More than four weights: exporter would discard data")
# Source materials are retained. The export copy has diffuse + UV nodes only.
matpairs = []
for slot in mesh.material_slots:
    sm = slot.material
    mat = bpy.data.materials.new("Snivy_" + sm.name)
    mat.use_nodes = True
    slot.material = mat
    t = sm.brres.textures[0]
    if t.mapMode != "UV_1":
        raise RuntimeError("Unexpected primary texture mapping")
    n = mat.node_tree.nodes
    n.clear()
    links = mat.node_tree.links
    out = n.new("ShaderNodeOutputMaterial")
    bs = n.new("ShaderNodeBsdfPrincipled")
    bs.inputs["Roughness"].default_value = 0.8
    tx = n.new("ShaderNodeTexImage")
    tx.image = t.imgs[0].img
    tx.extension = "REPEAT"
    uv = n.new("ShaderNodeUVMap")
    uv.uv_map = mesh.data.uv_layers[0].name
    mp = n.new("ShaderNodeMapping")
    links.new(uv.outputs["UV"], mp.inputs["Vector"])
    links.new(mp.outputs["Vector"], tx.inputs["Vector"])
    links.new(tx.outputs["Color"], bs.inputs["Base Color"])
    links.new(bs.outputs[0], out.inputs["Surface"])
    matpairs.append((sm, mat, mp))
mod = mesh.modifiers.new("TriangulateForSDR", "TRIANGULATE")
bpy.context.view_layer.objects.active = mesh
bpy.ops.object.modifier_move_up(modifier=mod.name)
bpy.ops.object.modifier_apply(modifier=mod.name)

report = {
    "candidate_mapping": SLOTS,
    "mapping_gameplay_validated": False,
    "source_bones": len(source_bones),
    "export_bones": len(data.bones),
    "vertices": len(mesh.data.vertices),
    "triangles": len(mesh.data.polygons),
    "actions": {},
    "omitted_material_features": [
        "environment map",
        "specular map",
        "native TEV lighting",
    ],
    "pbr_game_tested": False,
}
expected = {}
for slot, source_name in SLOTS.items():
    source_action = bpy.data.actions[f"{source_name} (Tsutarja)"]
    src.animation_data.action = source_action
    for sm, mat, mp in matpairs:
        a = bpy.data.actions.get(f"{source_name} ({sm.name})") or bpy.data.actions.get(
            f"BRRES Initial State ({sm.name})"
        )
        if sm.animation_data:
            sm.animation_data.action = a
    action = bpy.data.actions.new("Snivy_" + slot)
    action.use_fake_user = True
    rig.animation_data_create()
    rig.animation_data.action = action
    setattr(data, "prop_" + slot, action)
    for sm, mat, mp in matpairs:
        a = bpy.data.actions.new("SnivyUV_" + slot + "_" + sm.name)
        a.id_root = "NODETREE"
        a.use_fake_user = True
        mat.node_tree.animation_data_create()
        mat.node_tree.animation_data.action = a
        setattr(mat, "prop_" + slot, a)
    end = int(source_action.frame_range[1])
    max_shear = 0
    maximum_error = 0
    expected[slot] = {}
    for frame in range(end + 1):
        scene.frame_set(frame)
        poses = {
            b.name: C @ src.matrix_world @ src.pose.bones[b.name].matrix
            for b in source_bones
        }
        for b in source_bones:
            pb = rig.pose.bones[names[b.name]]
            local = (
                poses[b.parent.name].inverted() @ poses[b.name]
                if b.parent
                else poses[b.name]
            )
            u, sv, vt = np.linalg.svd(np.array(local)[:3, :3])
            if np.linalg.det(u) < 0:
                u[:, -1] *= -1
                sv[-1] *= -1
            if np.linalg.det(vt) < 0:
                vt[-1, :] *= -1
                sv[-1] *= -1
            aa = Matrix.Identity(4)
            bb = Matrix.Identity(4)
            linear = u @ np.diag(sv)
            for ii in range(3):
                for jj in range(3):
                    aa[ii][jj] = float(linear[ii, jj])
                    bb[ii][jj] = float(vt[ii, jj])
            aa.translation = local.translation
            helper = rig.pose.bones["Affine_" + b.name]
            helper_rest = (
                helper.parent.bone.matrix_local.inverted() @ helper.bone.matrix_local
            )
            helper.matrix_basis = helper_rest.inverted() @ aa
            rest = pb.parent.bone.matrix_local.inverted() @ pb.bone.matrix_local
            pb.matrix_basis = rest.inverted() @ bb
            for target in (helper, pb):
                for path in ("location", "rotation_euler", "scale"):
                    target.keyframe_insert(path, frame=frame, group=target.name)
        bpy.context.view_layer.update()
        for b in source_bones:
            dif = rig.pose.bones[names[b.name]].matrix - poses[b.name]
            maximum_error = max(maximum_error, max(abs(x) for row in dif for x in row))
        if frame in (0, end // 2, end):
            expected[slot][str(frame)] = {
                names[b.name]: [list(row) for row in poses[b.name]]
                for b in source_bones
            }
        for sm, mat, mp in matpairs:
            t = sm.brres.textures[0].transform
            if abs(t.rotation) > 1e-6:
                raise RuntimeError(
                    "UV rotation unsupported by SDR exporter: " + sm.name
                )
            sx, sy = t.scale
            tx, ty = t.translation
            mp.inputs["Scale"].default_value = (sx, sy, 1)
            mp.inputs["Location"].default_value = (-sx * tx, -sy * ty, 0)
            mp.inputs["Scale"].keyframe_insert("default_value", frame=frame)
            mp.inputs["Location"].keyframe_insert("default_value", frame=frame)
    if maximum_error > 0.0005:
        errors = []
        for b in source_bones:
            pb = rig.pose.bones[names[b.name]]
            dif = pb.matrix - poses[b.name]
            errors.append((max(abs(x) for row in dif for x in row), b.name))
        print("WORST", sorted(errors, reverse=True)[:10], flush=True)
        raise RuntimeError(f"Bake lost transforms: {slot} {maximum_error}")
    for fc in action.fcurves:
        for point in fc.keyframe_points:
            point.interpolation = "LINEAR"
    report["actions"][slot] = {
        "source": source_name,
        "frames": end + 1,
        "bake_max_matrix_error": maximum_error,
    }
    print("BAKED", slot, report["actions"][slot], flush=True)
# Source hidden; preserve all source data in an independent source blend.
for o in list(scene.objects):
    if o not in (rig, mesh):
        o.hide_render = True
        o.hide_set(True)
rig.animation_data.action = data.prop_idle
for sm, mat, mp in matpairs:
    mat.node_tree.animation_data.action = mat.prop_idle
scene.frame_set(0)
for image in bpy.data.images:
    if image.name.startswith("Tsutarja"):
        if image.size[0] <= 0 or len(image.pixels) == 0:
            raise RuntimeError("Missing texture pixels: " + image.name)
        if not image.packed_file:
            image.pack()
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / "snivy-export.blend"))
bpy.ops.pbr.pbrexport(filepath=str(ROOT / "snivy-experimental.sdr"))
(ROOT / "expected-poses.json").write_text(json.dumps(expected))
(ROOT / "conversion-report.json").write_text(json.dumps(report, indent=2))
print("SDR_PROBE_EXPORTED", flush=True)
