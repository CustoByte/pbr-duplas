"""Exercise the existing updater against a delta core and remembered source ROM."""
import json,os,shutil,subprocess,unittest,zipfile
from pathlib import Path
from test_delta_workflow import DeltaTests
from binary_delta import create,sha

class UpdaterDeltaTest(unittest.TestCase):
    def test_download_cache_update_failure_and_save_preservation(self):
        f=DeltaTests('test_delta_also_adds_deck_and_keeps_original_and_save');f.setUp();self.addCleanup(f.doCleanups)
        bootstrap=f.package/'Atualizar-Iniciar.ps1';shutil.copyfile(Path(__file__).resolve().parents[1]/'src/Atualizar-Iniciar.ps1',bootstrap)
        feed=f.root/'feed.json';core=f.root/'core.zip';data=f.root/'userdata'
        save=f.root/'Dolphin-User/Wii/save.sav';save.parent.mkdir(parents=True);save.write_bytes(b'normal campaign save')
        def release():
            with zipfile.ZipFile(core,'w') as z:
                for path in [f.package/'Aplicar-Mod.ps1',f.package/'Aplicar-Delta.ps1',f.package/'manifesto.json',*(f.package/'patches').glob('*')]:
                    z.write(path,path.relative_to(f.package))
            feed.write_text(json.dumps({'schema':1,'version':f.manifest['mod_version'],'package_url':str(core),'package_sha256':sha(core.read_bytes())}))
        def run(remembered=False,fail=False):
            args=[str(Path(shutil.which('pwsh') or '/tmp/pbr-pwsh/pwsh')),'-NoProfile','-File',str(bootstrap),'-FeedUrl',str(feed),'-DataRoot',str(data),'-NoGui','-DoNotLaunch']
            if not remembered:args+=['-ImagePath',str(f.image),'-ToolPath',str(f.tool),'-OutputPath',str(f.output)]
            env=dict(os.environ,XDG_CACHE_HOME=str(f.root/'cache'),XDG_CONFIG_HOME=str(f.root/'config'),XDG_DATA_HOME=str(f.root/'data'))
            if fail:env['PBR_TEST_FAIL_CONVERT']='1'
            return subprocess.run(args,env=env,capture_output=True,text=True,timeout=45)
        release();shutil.copyfile(core,f.package/'base.zip');(f.package/'base.sha256').write_text(sha(core.read_bytes()))
        result=run();self.assertEqual(result.returncode,0,result.stdout+result.stderr);first=f.output.read_bytes()
        entry=f.manifest['replacements'][0];target=b'updated delta version';patch=create(f.original['sys/main.dol'],target)
        (f.package/entry['package_path']).write_bytes(patch);entry.update(sha256=sha(target),patch_sha256=sha(patch))
        f.manifest['mod_version']='fixture-v2';f.save_manifest();release()
        result=run(remembered=True);self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        with zipfile.ZipFile(f.output) as z:self.assertEqual(z.read('sys/main.dol'),target)
        self.assertEqual(Path(str(f.output)+'.anterior.rvz').read_bytes(),first)
        current=f.output.read_bytes();state=(data/'estado.json').read_bytes()
        f.manifest['mod_version']='fixture-v3';f.save_manifest();release()
        result=run(remembered=True,fail=True);self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertEqual(f.output.read_bytes(),current);self.assertEqual((data/'estado.json').read_bytes(),state)
        self.assertEqual(f.image.read_bytes(),f.original_image);self.assertEqual(save.read_bytes(),b'normal campaign save')
if __name__=='__main__':unittest.main(verbosity=2)
