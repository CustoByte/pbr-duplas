"""Exercise cumulative local asset insertion with real PowerShell and fixtures."""
import json,unittest,zipfile
from pathlib import Path
import test_delta_workflow as workflow

class MegaInstallerTests(unittest.TestCase):
 def fixture(self):
  f=workflow.DeltaTests('test_delta_also_adds_deck_and_keeps_original_and_save');f.setUp();self.addCleanup(f.doCleanups)
  f.manifest.update(local_snivy_assets=True,local_mega_assets=True);f.save_manifest()
  source=f.root/'Tsutarja.brres';source.write_bytes(b'fixture source')
  mega=f.root/'mega-lucario.zip';mega.write_bytes(b'fixture source zip')
  (f.root/'state.json').write_text(json.dumps(dict(snivy_source=str(source),mega_source=str(mega))))
  assets=f.root/'snivy-assets';assets.mkdir()
  for n in ('pkx_501.fsys','menu_face.fsys','menu_pokemon.fsys'):(assets/n).write_bytes(('Snivy '+n).encode())
  path=str(assets).replace("'","''")
  (f.package/'Preparar-Snivy.ps1').write_text("function Prepare-Snivy($Partition,$Source,$CacheRoot) { return '"+path+"' }")
  return f
 def test_cumulative_graphics_and_source_memory(self):
  f=self.fixture();assets=f.root/'mega-assets';assets.mkdir()
  for n in ('pkx_502.fsys','menu_face.fsys','menu_pokemon.fsys'):(assets/n).write_bytes(('Snivy + Mega '+n).encode())
  path=str(assets).replace("'","''")
  (f.package/'Preparar-Mega-Lucario.ps1').write_text("function Prepare-MegaLucario($Partition,$Source,$CacheRoot,$SnivyCacheRoot) { if ((Get-Content -LiteralPath (Join-Path $Partition 'files/menu_face.fsys') -Raw) -ne 'Snivy menu_face.fsys') { throw 'Wrong insertion order' }; return '"+path+"' }")
  save=f.root/'normal-save.sav';save.write_bytes(b'keep player save')
  result=f.run_app(state=True);self.assertEqual(result.returncode,0,result.stdout)
  with zipfile.ZipFile(f.output) as z:
   self.assertEqual(z.read('files/pkx_501.fsys'),b'Snivy pkx_501.fsys')
   for n in ('pkx_502.fsys','menu_face.fsys','menu_pokemon.fsys'):self.assertEqual(z.read('files/'+n),(assets/n).read_bytes())
  state=json.loads((f.root/'state.json').read_text(encoding='utf-8-sig'));self.assertEqual(state['mega_source'],str(f.root/'mega-lucario.zip'))
  self.assertEqual(save.read_bytes(),b'keep player save');self.assertEqual(f.image.read_bytes(),f.original_image)
 def test_mega_conversion_failure_preserves_original_and_save(self):
  f=self.fixture();(f.package/'Preparar-Mega-Lucario.ps1').write_text("function Prepare-MegaLucario($Partition,$Source,$CacheRoot,$SnivyCacheRoot) { throw 'conversion fixture failure' }")
  save=f.root/'normal-save.sav';save.write_bytes(b'keep player save')
  result=f.run_app(state=True);self.assertNotEqual(result.returncode,0,result.stdout)
  self.assertFalse(f.output.exists());self.assertEqual(save.read_bytes(),b'keep player save');self.assertEqual(f.image.read_bytes(),f.original_image)

if __name__=='__main__':unittest.main()
