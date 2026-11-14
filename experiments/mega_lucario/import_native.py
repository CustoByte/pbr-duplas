"""Import the supplied native Lucario privately as the animation donor.

Blender: -- pkx_448.fsys pbr-addon output-directory
"""
import bpy,sys,json,hashlib
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'mod-source'),str(ROOT/'experiments/snivy')]
from prepare_campaign_doubles import read_archive
from graphics_common import load_pbr_addon
from pkx_reference import scene_inventory
source,addon,output=map(Path,sys.argv[sys.argv.index('--')+1:])
raw=source.read_bytes()
if hashlib.sha256(raw).hexdigest()!='e77ee784794c9e24fad632437b8f63709084227848d4e162f8e05eeb2dbce85a':
 raise ValueError('Expected the audited original pkx_448.fsys')
resources=read_archive(raw)
output.mkdir(parents=True,exist_ok=True)
inventory=dict(source_sha256=hashlib.sha256(raw).hexdigest(),resources=[dict(resource_id=f'{k:08x}',**scene_inventory(v)) for k,v in resources])
(output/'lucario-reference-inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
sdr=output/'lucario.sdr';sdr.write_bytes(dict(resources)[0x09770400])
bpy.ops.wm.read_factory_settings(use_empty=True)
pbr=load_pbr_addon(SimpleNamespace(pbr_addon=addon,native_contract=None))
pbr.importer.importSDR(bpy.context,str(sdr),False,False)
for action in bpy.data.actions:action.use_fake_user=True
bpy.ops.wm.save_as_mainfile(filepath=str(output/'lucario-native.blend'))
print('LUCARIO_DONOR_IMPORTED',flush=True)
