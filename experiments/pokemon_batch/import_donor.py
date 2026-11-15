"""Blender 3.3: -- original.fsys pbr-addon private-output-dir"""
import bpy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'mod-source'), str(ROOT/'experiments/snivy')]
from prepare_campaign_doubles import read_archive
from graphics_common import load_pbr_addon
from pkx_reference import scene_inventory
source, addon, output = map(Path, sys.argv[sys.argv.index('--')+1:])
resources = read_archive(source.read_bytes())
output.mkdir(parents=True, exist_ok=True)
scenes = [(rid, data, scene_inventory(data)) for rid, data in resources]
# The supplied native packages contain normal then shiny resources. Retain both
# in the inventory and use the first supplied resource for motion reference.
rid, data, inventory = scenes[0]
report = dict(source_name=source.name, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              resources=[dict(resource_id=f'{r:08x}', **i) for r, _, i in scenes],
              imported_resource_id=f'{rid:08x}', donor_not_modified=True)
(output/'inventory.json').write_text(json.dumps(report, indent=2)+'\n')
sdr = output/'reference.sdr'
sdr.write_bytes(data)
bpy.ops.wm.read_factory_settings(use_empty=True)
sdk = load_pbr_addon(SimpleNamespace(pbr_addon=addon, native_contract=None))
sdk.importer.importSDR(bpy.context, str(sdr), False, False)
for action in bpy.data.actions: action.use_fake_user = True
bpy.ops.wm.save_as_mainfile(filepath=str(output/'reference.blend'), compress=True)
report['blender_rigs'] = [dict(name=o.name, bones=[b.name for b in o.data.bones]) for o in bpy.data.objects if o.type == 'ARMATURE']
report['blender_actions'] = [dict(name=a.name, frames=list(a.frame_range)) for a in bpy.data.actions]
(output/'inventory.json').write_text(json.dumps(report, indent=2)+'\n')
print('DONOR_IMPORTED', source.name, inventory['object_name'], flush=True)
