"""Verify the immutable owned-code package named by the current test feed.

CI does not rebuild protected/local graphics. It verifies the committed core,
manifest, reader digest and absence of protected assets before publishing it.
"""
import argparse,hashlib,json,re,shutil,zipfile,subprocess,sys,tempfile
from pathlib import Path
from urllib.parse import urlsplit
ROOT=Path(__file__).resolve().parents[1]

def check_runtime_imports(package):
 with tempfile.TemporaryDirectory(prefix='pbr-core-imports-') as temporary:
  root=Path(temporary)
  with zipfile.ZipFile(package) as z:z.extractall(root)
  code="import sys;from pathlib import Path;r=Path(sys.argv[1]);sys.path[:0]=[str(r/'experiments/mega_lucario'),str(r/'mod-source'),str(r/'expansion'),str(r/'experiments/snivy')];import registrations"
  result=subprocess.run([sys.executable,'-I','-c',code,str(root)],cwd=root,capture_output=True,text=True)
  if result.returncode:raise ValueError('Packaged Mega runtime import failed:\n'+result.stderr)

def verify(output):
 feed_path=ROOT/'expansion/update-test.json';feed=json.loads(feed_path.read_text())
 version=feed['version']
 if not re.fullmatch(r'v\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?',version):raise ValueError('Invalid immutable version')
 url=urlsplit(feed['package_url']);prefix='/CustoByte/pbr-duplas/'+version+'/'
 if url.scheme!='https' or url.netloc!='raw.githubusercontent.com' or url.query or url.fragment or not url.path.startswith(prefix):raise ValueError('Expected immutable owned repository URL')
 relative=Path(url.path[len(prefix):])
 if relative.is_absolute() or '..' in relative.parts or relative.name!='aplicador-core.zip':raise ValueError('Invalid package path')
 source=ROOT/relative;data=source.read_bytes()
 if hashlib.sha256(data).hexdigest()!=feed['package_sha256']:raise ValueError('Package hash differs from feed')
 with zipfile.ZipFile(source) as z:
  if any(n.lower().endswith(('.dol','.fsys','.brres','.fbx','.sdr','.blend','.sav','.iso','.rvz','.png','.jpg','.bin')) for n in z.namelist()):raise ValueError('Protected asset in core')
  manifest=json.loads(z.read('manifesto.json'))
  if manifest['mod_version']!=version:raise ValueError('Manifest version differs')
  if manifest.get('local_mega_assets'):
   reader=json.loads(z.read('experiments/mega_lucario/tools/reader-build.json'))
   if hashlib.sha256(z.read('experiments/mega_lucario/tools/read_source_windows.exe')).hexdigest()!=reader['exe_sha256']:raise ValueError('Reader hash differs')
  if z.read('Aplicar-Mod.ps1')!=(ROOT/'expansion/Aplicar-Mod.ps1').read_bytes():raise ValueError('Applicator source differs from packaged version')
 if manifest.get('local_mega_assets'):check_runtime_imports(source)
 output.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,output/'aplicador-core.zip');shutil.copyfile(feed_path,output/'update.json')
 shutil.copyfile(source.parent/'README.md',output/'LEIA-ME.md')
 (output/'SHA256SUMS.txt').write_text(feed['package_sha256']+'  aplicador-core.zip\n')
 print('Verified prepared test package:',version)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);verify(p.parse_args().output)
