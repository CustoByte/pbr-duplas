"""Convert only the user-supplied Mega ZIP with the existing private Blender SDK.

No model downloads, game data uploads, direct save writes or runtime compilation.
"""
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OUTPUTS=('pkx_502.fsys','menu_face.fsys','menu_pokemon.fsys')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def key_for(source,originals,reader):
 recipe=('convert_local.py','source-hashes.json','import_source.py','import_native.py','retarget_native.py','export_candidate.py','rotation_math.py','verify_candidate.py','verify_materials.py','render_portraits.py','asset_builder.py','registrations.py')
 inputs={str((HERE/n).relative_to(ROOT)):sha(HERE/n) for n in recipe}
 inputs['zip']=sha(source);inputs['reader']=sha(reader)
 for n in ('pkx_448.fsys','menu_face.fsys','menu_pokemon.fsys'):inputs[n]=sha(originals/n)
 for n in ('graphics_common.py','icon_textures.py','resource_packages.py','pkx_reference.py','sdr_track_storage.py'):
  inputs['snivy/'+n]=sha(ROOT/'experiments/snivy'/n)
 return hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()
def convert(blender,source,originals,pbr_addon,reader,cache):
 if sha(originals/'pkx_448.fsys')!='e77ee784794c9e24fad632437b8f63709084227848d4e162f8e05eeb2dbce85a':raise ValueError('Original Lucario archive differs')
 key=key_for(source,originals,reader);destination=cache/key;marker=destination/'verified-cache.json'
 if marker.is_file():
  report=json.loads(marker.read_text())
  if report.get('key')==key and all(sha(destination/n)==report['outputs'][n] for n in OUTPUTS):return destination
  raise ValueError('Mega graphics cache failed integrity validation')
 cache.mkdir(parents=True,exist_ok=True)
 env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join(map(str,(HERE,ROOT/'mod-source',ROOT/'expansion',ROOT/'experiments/snivy')))+os.pathsep+env.get('PYTHONPATH','')
 hashes=json.loads((HERE/'source-hashes.json').read_text())
 # Only known entries are read; arbitrary ZIP paths/documents are not executed.
 with tempfile.TemporaryDirectory(prefix='mega-',dir=cache) as temporary:
  work=Path(temporary)
  with zipfile.ZipFile(source) as archive:
   for name,digest in hashes.items():
    info=archive.getinfo(name)
    if info.file_size>4*1024*1024:raise ValueError('Unexpected source size')
    data=archive.read(name)
    if hashlib.sha256(data).hexdigest()!=digest:raise ValueError('Mega source differs from the approved model: '+name)
    target=work/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
  def run(command,expected,stage):
   print('Mega Lucario: '+stage,flush=True)
   log=work/(stage+'.log')
   with log.open('wb') as f:process=subprocess.run(list(map(str,command)),env=env,stdout=f,stderr=subprocess.STDOUT)
   if process.returncode or not expected.is_file():
    failure=cache/'last-failure.log';shutil.copyfile(log,failure);raise RuntimeError('Mega conversion failed at '+stage+'; log: '+str(failure))
  run([reader,work/'source/LucarioMega.fbx',work/'source-intermediate.json'],work/'source-intermediate.json','read_fbx')
  def blend(script,args,expected):
   run([blender,'--background','--threads','2','--factory-startup','--python',HERE/script,'--',*args],expected,script)
  blend('import_source.py',[work/'source-intermediate.json',work/'textures',work/'mega-source.blend'],work/'mega-source.blend')
  blend('import_native.py',[originals/'pkx_448.fsys',pbr_addon,work],work/'lucario-native.blend')
  blend('retarget_native.py',[work/'mega-source.blend',work/'lucario-native.blend',work/'mega-retarget.blend',work/'lucario-reference-inventory.json'],work/'mega-retarget.blend')
  blend('export_candidate.py',[work/'mega-retarget.blend',work/'lucario-reference-inventory.json',pbr_addon,work/'mega-candidate.sdr'],work/'mega-candidate.sdr')
  blend('verify_candidate.py',[work/'mega-candidate.blend',work/'mega-candidate.sdr',pbr_addon,work/'roundtrip-report.json'],work/'roundtrip-report.json')
  sys.path[:0]=[str(HERE),str(ROOT/'mod-source'),str(ROOT/'expansion'),str(ROOT/'experiments/snivy')]
  from verify_materials import verify
  materials=verify((work/'mega-candidate.sdr').read_bytes(),json.loads((work/'lucario-reference-inventory.json').read_text())['resources'][0]['actions'])
  (work/'material-report.json').write_text(json.dumps(materials))
  blend('render_portraits.py',[work],work/'portraits/face-normal.png')
  from asset_builder import build
  print('Mega Lucario: compactando modelos e retratos...',flush=True)
  output=work/'assets';report=build(work,originals,output);report.update(key=key,source_sha256=sha(source))
  (output/'verified-cache.json').write_text(json.dumps(report,indent=2)+'\n');output.rename(destination)
 return destination
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('blender','source','originals','pbr-addon','reader','cache','result'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();result=convert(a.blender,a.source,a.originals,a.pbr_addon,a.reader,a.cache);a.result.write_text(json.dumps(dict(private_assets=str(result)),indent=2)+'\n');print(result)
