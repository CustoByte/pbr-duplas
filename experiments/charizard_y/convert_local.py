"""Hash-pinned local Charizard Y conversion. No game/model downloads or save writes."""
import argparse,hashlib,io,json,os,shutil,subprocess,sys,tempfile,zipfile,traceback
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];BATCH=ROOT/'experiments/pokemon_batch'
OUTPUTS=('pkx_503.fsys','menu_face.fsys','menu_pokemon.fsys')
SOURCE='e0fed6598797fafcb22620894418238f8074740b0ed284e5d87b527bd033004f'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def convert(blender,source,originals,pbr_addon,cache):
 if sha(source)!=SOURCE:raise ValueError('Selecione o mega-charizard-y-pokemon.zip aprovado.')
 if sha(originals/'pkx_006.fsys')!='ada980b34af54f99c4db863db050605c9f8376de0591735c4c60b04b2de5639b':raise ValueError('Original Charizard differs')
 recipes=[*HERE.glob('*.py'),HERE/'source-hashes.json',*[BATCH/n for n in ('import_models.py','import_donor.py','retarget_motion.py','retarget-plan.json','export_charizard_y.py','verify_charizard_y_sdr.py')],ROOT/'experiments/mega_lucario/rotation_math.py',*[ROOT/'experiments/snivy'/n for n in ('graphics_common.py','sdr_track_storage.py','icon_textures.py','resource_packages.py','pkx_reference.py')]]
 inputs={str(p.relative_to(ROOT)):sha(p) for p in recipes};inputs['zip']=sha(source)
 for n in ('pkx_006.fsys','menu_face.fsys','menu_pokemon.fsys'):inputs[n]=sha(originals/n)
 # Bind cache to the actual SDK scripts used for export, too.
 for p in sorted(pbr_addon.rglob('*.py')):inputs['sdk/'+str(p.relative_to(pbr_addon))]=sha(p)
 key=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest();destination=cache/key
 if (destination/'verified-cache.json').is_file():
  r=json.loads((destination/'verified-cache.json').read_text())
  if r.get('key')==key and all(sha(destination/n)==r['outputs'][n] for n in OUTPUTS):return destination
  raise ValueError('Charizard graphics cache failed integrity validation')
 cache.mkdir(parents=True,exist_ok=True)
 env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join(map(str,(HERE,ROOT/'mod-source',ROOT/'expansion',ROOT/'experiments/snivy',ROOT/'experiments/mega_lucario')))+os.pathsep+env.get('PYTHONPATH','')
 with tempfile.TemporaryDirectory(prefix='charizard-y-',dir=cache) as temporary:
  work=Path(temporary);model=work/'model';model.mkdir()
  with zipfile.ZipFile(source) as outer:
   with zipfile.ZipFile(io.BytesIO(outer.read('source/Mega Charizard Y - Pokemon.zip'))) as archive:
    for n,digest in json.loads((HERE/'source-hashes.json').read_text()).items():
     if Path(n).name!=n or archive.getinfo(n).file_size>4*1024*1024:raise ValueError('Unsafe source entry')
     data=archive.read(n)
     if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Source changed: '+n)
     (model/n).write_bytes(data)
  def blend(script,args,expected):
   print('Mega Charizard Y: '+script.name,flush=True);log=work/(script.stem+'.log')
   with log.open('wb') as f:p=subprocess.run(list(map(str,[blender,'--background','--threads','2','--factory-startup','--python-exit-code','1','--python',script,'--',*args])),env=env,stdout=f,stderr=subprocess.STDOUT)
   if p.returncode or not expected.is_file():
    failure=cache/'last-failure.log';shutil.copyfile(log,failure);raise RuntimeError('Conversion failed: '+script.name+'; '+str(failure))
  staged=work/'source.blend';donor=work/'donor';motion=work/'charizard-y-jaw-fix';graphics=work/'graphics';graphics.mkdir()
  blend(BATCH/'import_models.py',['glTF',model/'Mega Charizard Y - Pokemon.gltf',model,staged,work/'source.glb'],staged)
  blend(BATCH/'import_donor.py',[originals/'pkx_006.fsys',pbr_addon,donor],donor/'reference.blend')
  blend(BATCH/'retarget_motion.py',['mega-charizard-y',staged,donor,BATCH/'retarget-plan.json',motion],motion/'mega-charizard-y-motion.blend')
  sdr=graphics/'charizard-y-candidate.sdr'
  blend(BATCH/'export_charizard_y.py',[motion/'mega-charizard-y-motion.blend',donor/'inventory.json',pbr_addon,sdr],sdr)
  blend(BATCH/'verify_charizard_y_sdr.py',[sdr.with_suffix('.blend'),sdr,pbr_addon,donor/'inventory.json',graphics/'roundtrip.json'],graphics/'roundtrip.json')
  blend(HERE/'render_portraits.py',[graphics],graphics/'portraits/face-normal.png')
  sys.path[:0]=[str(HERE),str(ROOT/'mod-source'),str(ROOT/'expansion'),str(ROOT/'experiments/snivy')]
  from asset_builder import build
  output=work/'assets';r=build(graphics,originals,output);r.update(key=key,source_sha256=sha(source),npc_randomization_enabled=False)
  (output/'verified-cache.json').write_text(json.dumps(r,indent=2)+'\n');output.rename(destination)
 return destination
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('blender','source','originals','pbr-addon','cache','result'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args()
 try:
  output=convert(a.blender,a.source,a.originals,a.pbr_addon,a.cache);a.result.write_text(json.dumps(dict(private_assets=str(output)))+'\n')
 except Exception:
  a.cache.mkdir(parents=True,exist_ok=True);detail=traceback.format_exc();stage=a.cache/'last-failure.log'
  if stage.exists():detail+='\n'+stage.read_text(errors='replace')
  (a.cache/'conversion-failure.log').write_text(detail);print(detail,file=sys.stderr);sys.exit(1)
