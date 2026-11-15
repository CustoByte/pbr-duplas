"""Cumulative Charizard Y delivery; consumes locally converted, verified graphics."""
import argparse,json,sys,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path[:0]=[str(HERE),str(ROOT/'mod-source'),str(ROOT/'expansion'),str(ROOT/'experiments/snivy')]
from registrations import prepare,model_package,ARCHIVE,FACE,BODY
from runtime_layer import compile_payload,patch
from prepare_campaign_doubles import read_archive,sha
from encounter_expansion import rebuild_archive
from catalog import append_archive
from resource_packages import append_resource
from icon_textures import encode_gtx,face_tile
from PIL import Image,ImageOps

def assemble(baseline,graphics,reference,toolchain,output):
 if output.exists():raise ValueError('Use a new output directory')
 sdr=(graphics/'charizard-y-candidate.sdr').read_bytes()
 proof=json.loads((graphics/'roundtrip.json').read_text())
 if not proof.get('passed') or proof.get('sha256')!=sha(sdr):raise ValueError('Unverified or changed graphics')
 original=reference.read_bytes()
 if sha(original)!='ada980b34af54f99c4db863db050605c9f8376de0591735c4c60b04b2de5639b':raise ValueError('Unexpected original Charizard')
 common=(baseline/'common.fsys').read_bytes();dol=(baseline/'main.dol').read_bytes();mes=(baseline/'mes_common.fsys').read_bytes()
 old=dict(read_archive(common));messages=dict(read_archive(mes))
 replacements,new_mes=prepare(old,messages[0x27C10000],sdr,original)
 output.mkdir(parents=True)
 payload=compile_payload(dol,output/'payload',toolchain);changed_dol,runtime=patch(dol,payload)
 faces=Image.new('RGBA',(96,96));bodies=Image.new('RGBA',(54,108))
 tile=face_tile(Image.open(graphics/'portraits/face-normal.png'))
 body=Image.open(graphics/'portraits/body-normal.png').convert('RGBA');body.thumbnail((54,54),Image.Resampling.LANCZOS)
 for row in range(2):
  faces.paste(tile,(0,row*48));faces.paste(ImageOps.mirror(tile),(48,row*48));bodies.paste(body,((54-body.width)//2,row*54+(54-body.height)//2))
 files={'main.dol':changed_dol,'common.fsys':rebuild_archive(common,replacements),'mes_common.fsys':rebuild_archive(mes,{0x27C10000:new_mes}),
  'GSfsys.toc':append_archive((baseline/'GSfsys.toc').read_bytes(),ARCHIVE,'pkx_503'),'pkx_503.fsys':model_package(original,sdr),
  'menu_face.fsys':append_resource((baseline/'menu_face.fsys').read_bytes(),FACE,encode_gtx(faces),'charizard-y-face.gtx'),
  'menu_pokemon.fsys':append_resource((baseline/'menu_pokemon.fsys').read_bytes(),BODY,encode_gtx(bodies),'charizard-y-body.gtx')}
 after=dict(read_archive(files['common.fsys']))
 assert all(old[k]==after[k] for k in old.keys()-replacements.keys())
 for k in replacements:
  if k==0x008B0000:assert after[k][8:len(old[k])]==old[k][8:]
  else:
   count,stride=struct.unpack_from('>II',old[k]);assert after[k][48:48+count*stride]==old[k][48:48+count*stride]
 for name in ('menu_face.fsys','menu_pokemon.fsys'):
  prior=dict(read_archive((baseline/name).read_bytes()));now=dict(read_archive(files[name]));assert all(now[k]==v for k,v in prior.items())
 for name,data in files.items():(output/name).write_bytes(data)
 faces.save(output/'face-atlas-preview.png');bodies.save(output/'body-atlas-preview.png')
 report=dict(outputs={n:dict(bytes=len(b),sha256=sha(b)) for n,b in files.items()},runtime=runtime,pass_target=dict(index=37,slot=2,original_species=8,level=50),old_table_rows_and_portraits_preserved=True,npc_randomization_enabled=False,gameplay_verified=False)
 (output/'integration-report.json').write_text(json.dumps(report,indent=2)+'\n');return report
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('baseline','graphics','reference','toolchain','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();print(json.dumps(assemble(a.baseline,a.graphics,a.reference,a.toolchain,a.output),indent=2))
