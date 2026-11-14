"""Private cumulative Mega integration. Does not publish or touch a save/ROM."""
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

def assemble(baseline,messages,graphics,snivy_assets,reference,toolchain,output):
 if output.exists():raise ValueError('Use a new output directory')
 sdr=(graphics/'mega-candidate.sdr').read_bytes()
 for proof in ('roundtrip-report.json','material-report.json'):
  report=json.loads((graphics/proof).read_text())
  if not report.get('passed') or report.get('sha256',report.get('sdr_sha256'))!=sha(sdr):raise ValueError('Unverified graphics candidate')
 original=reference.read_bytes()
 if sha(original)!='e77ee784794c9e24fad632437b8f63709084227848d4e162f8e05eeb2dbce85a':raise ValueError('Unexpected original Lucario')
 common=(baseline/'common.fsys').read_bytes();dol=(baseline/'main.dol').read_bytes();mes=messages.read_bytes()
 old=dict(read_archive(common));msg=dict(read_archive(mes))
 replacements,new_mes=prepare(old,msg[0x27C10000],sdr,original)
 output.mkdir(parents=True)
 payload=compile_payload(dol,output/'payload',toolchain);changed_dol,runtime=patch(dol,payload)
 faces=Image.new('RGBA',(96,96));bodies=Image.new('RGBA',(54,108))
 tile=face_tile(Image.open(graphics/'portraits/face-normal.png'))
 body=Image.open(graphics/'portraits/body-normal.png').convert('RGBA');body.thumbnail((54,54),Image.Resampling.LANCZOS)
 # Normal art is also the explicit fallback for a shiny flag in this test.
 for row in range(2):
  faces.paste(tile,(0,row*48));faces.paste(ImageOps.mirror(tile),(48,row*48))
  bodies.paste(body,((54-body.width)//2,row*54+(54-body.height)//2))
 face_before=(snivy_assets/'menu_face.fsys').read_bytes();body_before=(snivy_assets/'menu_pokemon.fsys').read_bytes()
 files={'main.dol':changed_dol,'common.fsys':rebuild_archive(common,replacements),
        'mes_common.fsys':rebuild_archive(mes,{0x27C10000:new_mes}),
        'GSfsys.toc':append_archive((baseline/'GSfsys.toc').read_bytes(),ARCHIVE,'pkx_502'),
        'pkx_502.fsys':model_package(original,sdr),
        'menu_face.fsys':append_resource(face_before,FACE,encode_gtx(faces),'mega-lucario-face.gtx'),
        'menu_pokemon.fsys':append_resource(body_before,BODY,encode_gtx(bodies),'mega-lucario-body.gtx')}
 after=dict(read_archive(files['common.fsys']))
 assert all(old[k]==after[k] for k in old.keys()-replacements.keys())
 for k in replacements:
  if k==0x008B0000:assert after[k][8:len(old[k])]==old[k][8:]
  else:
   count,stride=struct.unpack_from('>II',old[k]);assert after[k][48:48+count*stride]==old[k][48:48+count*stride]
 for name,data in files.items():(output/name).write_bytes(data)
 faces.save(output/'face-atlas-preview.png');bodies.save(output/'body-atlas-preview.png')
 report=dict(kind='private cumulative integration, not a tested Dolphin build',outputs={n:dict(bytes=len(b),sha256=sha(b)) for n,b in files.items()},
     baseline_sha256={'main.dol':sha(dol),'common.fsys':sha(common),'mes_common.fsys':sha(mes),'menu_face.fsys':sha(face_before),'menu_pokemon.fsys':sha(body_before)},
     all_original_and_snivy_table_rows_preserved=True,translation_rows_preserved=True,runtime=runtime,
     pass_target={'index':37,'slot':0,'original_species':2,'level':50},normal_art_for_shiny_flag=True,
     gameplay_verified=False,published=False,save_files_modified=False)
 (output/'integration-report.json').write_text(json.dumps(report,indent=2)+'\n');return report

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('baseline','messages','graphics','snivy-assets','reference','toolchain','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();print(json.dumps(assemble(a.baseline,a.messages,a.graphics,a.snivy_assets,a.reference,a.toolchain,a.output),indent=2))
