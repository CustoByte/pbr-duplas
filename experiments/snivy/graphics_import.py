"""Import the supplied Snivy source with all original animation tracks intact."""

import json
import bpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from graphics_common import arguments, load_brres_addon

args = arguments()
load_brres_addon(args)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
result = bpy.ops.import_scene.brres(
    filepath=str(args.source), scale=1, frameStart=0, sscMode="ACCURATE"
)
print("IMPORT_RESULT", result)
r = {
    "objects": [
        {
            "name": o.name,
            "type": o.type,
            "vertices": len(o.data.vertices) if o.type == "MESH" else None,
            "bones": len(o.data.bones) if o.type == "ARMATURE" else None,
        }
        for o in bpy.context.scene.objects
    ],
    "materials": [
        {
            "name": m.name,
            "textures": [
                {
                    "name": t.name,
                    "image": t.imgs[0].img.name if len(t.imgs) else None,
                    "map": t.mapMode,
                }
                for t in m.brres.textures
            ],
        }
        for m in bpy.data.materials
    ],
    "actions": [
        {"name": a.name, "frames": list(a.frame_range), "fcurves": len(a.fcurves)}
        for a in bpy.data.actions
    ],
    "images": [{"name": i.name, "size": list(i.size)} for i in bpy.data.images],
    "rigs": [
        {
            "name": o.name,
            "bones": [
                {
                    "name": b.name,
                    "parent": b.parent.name if b.parent else None,
                    "deform": b.use_deform,
                }
                for b in o.data.bones
            ],
        }
        for o in bpy.context.scene.objects
        if o.type == "ARMATURE"
    ],
}
(args.workdir / "import-probe.json").write_text(json.dumps(r, indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(args.workdir / "snivy-source.blend"))
print("IMPORT_PROBE_OK")
