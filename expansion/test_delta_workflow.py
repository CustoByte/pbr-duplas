"""Run the real PowerShell applicator over simulated images plus real file deltas."""
import json,shutil,unittest,zipfile
from pathlib import Path
import test_windows_applicator as legacy
from binary_delta import create,sha
legacy.SCRIPT=Path(__file__).with_name('Aplicar-Mod.ps1')

class DeltaTests(legacy.WorkflowTests):
    def setUp(self):
        super().setUp()
        shutil.copyfile(Path(__file__).with_name('Aplicar-Delta.ps1'),self.package/'Aplicar-Delta.ps1')
        self.manifest['replacements']=[]
        for index,(name,data) in enumerate(self.replacements.items()):
            path=f'patches/{index}.pbrdelta';patch=create(self.original[name],data)
            (self.package/path).parent.mkdir(exist_ok=True);(self.package/path).write_bytes(patch)
            self.manifest['replacements'].append({'package_path':path,'installed_path':name,
                'sha256':sha(data),'patch_sha256':sha(patch),'format':'pbr-delta-v1'})
        self.save_manifest()
    def test_corrupted_package_refused(self):
        path=self.package/self.manifest['replacements'][0]['package_path']
        path.write_bytes(b'corrupt patch')
        result=self.run_app();self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertFalse(self.output.exists())
    def test_new_version_rebuilds_stable_output_and_keeps_backup(self):
        first=self.run_app(state=True);self.assertEqual(first.returncode,0,first.stdout)
        previous=self.output.read_bytes();data=b'new version of dol'
        entry=self.manifest['replacements'][0];patch=create(self.original['sys/main.dol'],data)
        (self.package/entry['package_path']).write_bytes(patch)
        entry['sha256']=sha(data);entry['patch_sha256']=sha(patch)
        self.manifest['mod_version']='fixture-v2';self.save_manifest()
        second=self.run_app(state=True,use_saved=True);self.assertEqual(second.returncode,0,second.stdout)
        self.assertEqual(Path(str(self.output)+'.anterior.rvz').read_bytes(),previous)
        with zipfile.ZipFile(self.output) as z:self.assertEqual(z.read('sys/main.dol'),data)
        state=json.loads((self.root/'state.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(state['mod_version'],'fixture-v2')
    def test_delta_also_adds_deck_and_keeps_original_and_save(self):
        name='files/deck.fsys';data=b'expanded deck fixture';patch=create(self.original[name],data)
        (self.package/'patches/deck.pbrdelta').write_bytes(patch)
        self.manifest['replacements'].append({'package_path':'patches/deck.pbrdelta','installed_path':name,
            'sha256':sha(data),'patch_sha256':sha(patch),'format':'pbr-delta-v1'})
        self.save_manifest();save=self.root/'save.sav';save.write_bytes(b'campaign save fixture')
        result=self.run_app();self.assertEqual(result.returncode,0,result.stdout)
        self.assertEqual(self.image.read_bytes(),self.original_image)
        self.assertEqual(save.read_bytes(),b'campaign save fixture')
        with zipfile.ZipFile(self.output) as archive:self.assertEqual(archive.read(name),data)
    def test_wrong_delta_source_is_refused_before_convert(self):
        path=self.package/self.manifest['replacements'][0]['package_path']
        patch=create(b'wrong original',b'wrong output');path.write_bytes(patch)
        self.manifest['replacements'][0]['patch_sha256']=sha(patch);self.save_manifest()
        result=self.run_app();self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertFalse(self.output.exists());self.assertEqual(self.image.read_bytes(),self.original_image)

if __name__=='__main__':unittest.main(verbosity=2)
