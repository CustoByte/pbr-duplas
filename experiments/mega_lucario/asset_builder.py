"""Private graphics outputs from a verified locally converted Mega model."""
import json,sys
from pathlib import Path
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(Path(__file__).resolve().parent),str(ROOT/'mod-source'),str(ROOT/'expansion'),str(ROOT/'experiments/snivy')]
from registrations import model_package,FACE,BODY
from resource_packages import append_resource
from icon_textures import face_tile,encode_gtx
from prepare_campaign_doubles import sha,read_archive

def build(work,originals,output):
 sdr=(work/'mega-candidate.sdr').read_bytes()
 for filename in ('roundtrip-report.json','material-report.json'):
  proof=json.loads((work/filename).read_text())
  if not proof.get('passed') or proof.get('sha256',proof.get('sdr_sha256'))!=sha(sdr):raise ValueError('Requires matching passed graphics checks')
 reference=(originals/'pkx_448.fsys').read_bytes()
 if sha(reference)!='e77ee784794c9e24fad632437b8f63709084227848d4e162f8e05eeb2dbce85a':raise ValueError('Requires the original audited Lucario')
 faces=Image.new('RGBA',(96,96));bodies=Image.new('RGBA',(54,108));tile=face_tile(Image.open(work/'portraits/face-normal.png'))
 body=Image.open(work/'portraits/body-normal.png').convert('RGBA');body.thumbnail((54,54),Image.Resampling.LANCZOS)
 for row in range(2):
  faces.paste(tile,(0,row*48));faces.paste(ImageOps.mirror(tile),(48,row*48));bodies.paste(body,((54-body.width)//2,row*54+(54-body.height)//2))
 before_face=(originals/'menu_face.fsys').read_bytes();before_body=(originals/'menu_pokemon.fsys').read_bytes()
 # Require the preserved Snivy portraits before appending Mega; wrong order
 # would discard the first added Pokemon's images.
 if 0x7BEA0C00 not in dict(read_archive(before_face)) or 0x6BEA0C00 not in dict(read_archive(before_body)):raise ValueError('Snivy graphics must be installed first')
 files={'pkx_502.fsys':model_package(reference,sdr),
        'menu_face.fsys':append_resource(before_face,FACE,encode_gtx(faces),'mega-lucario-face.gtx'),
        'menu_pokemon.fsys':append_resource(before_body,BODY,encode_gtx(bodies),'mega-lucario-body.gtx')}
 for name,source in [('menu_face.fsys',before_face),('menu_pokemon.fsys',before_body)]:
  assert read_archive(files[name])[:-1]==read_archive(source)
 output.mkdir(parents=True,exist_ok=False)
 for name,data in files.items():(output/name).write_bytes(data)
 return dict(outputs={n:sha(b) for n,b in files.items()},normal_art_for_shiny_flag=True,gameplay_verified=False)
