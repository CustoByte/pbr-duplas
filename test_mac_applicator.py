"""Native macOS launcher integration tests. No GUI, real ROM or Dolphin run."""
import hashlib,json,os,plistlib,platform,shutil,subprocess,tempfile,unittest,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/'mac-aplicador'

def digest(data):return hashlib.sha256(data).hexdigest()

@unittest.skipUnless(platform.system()=='Darwin','Native macOS commands required')
class MacTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="pbr cópia d' & mac ");self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.client=self.root/'client';self.client.mkdir()
        shutil.copyfile(SOURCE/'INICIAR-MAC.command',self.client/'INICIAR-MAC.command')
        self.app=self.root/'Dolphin.app';executable=self.app/'Contents/MacOS/Dolphin';executable.parent.mkdir(parents=True)
        executable.write_text('#!/bin/sh\nexit 0\n');executable.chmod(0o755)
        self.game=self.root/'Pokemon original.rvz';data=bytearray(0xD8);data[:4]=b'RVZ\1';data[88:96]=b'RPBE01\0\0';data[112:116]=bytes.fromhex('5d1c9ea3');self.game.write_bytes(data)
        self.original=self.game.read_bytes();self.state=self.root/'data';self.feed=self.root/'feed.json'
        self.core=self.root/'core.zip';self.contents={n:(SOURCE/n).read_bytes() for n in('aplicar-mac.sh','descriptor.jxa')}
        self.contents['riivolution.xml']=b'<wiidisc version="1"/>'
        self.contents['mod/main.dol']=b'fixture dol';self.contents['mod/common.fsys']=b'fixture common'
        self.manifest={'mod_version':'fixture-v1','replacements':[
            {'package_path':'mod/main.dol','sha256':digest(self.contents['mod/main.dol'])},
            {'package_path':'mod/common.fsys','sha256':digest(self.contents['mod/common.fsys'])}]}
        self.release();shutil.copyfile(self.core,self.client/'base.zip')
        (self.client/'base.sha256').write_text(digest(self.core.read_bytes()))

    def release(self):
        self.contents['manifesto.json']=json.dumps(self.manifest).encode()
        with zipfile.ZipFile(self.core,'w') as z:
            for name,data in self.contents.items():z.writestr(name,data)
        self.feed.write_text(json.dumps({'schema':1,'version':self.manifest['mod_version'],'package_sha256':digest(self.core.read_bytes()),'package_url':'file://'+str(self.core)}))

    def launch(self,remembered=False):
        env=dict(os.environ,PBR_DATA_ROOT=str(self.state),PBR_FEED_URL='file://'+str(self.feed),PBR_TEST_MODE='1')
        cmd=['/bin/bash',str(self.client/'INICIAR-MAC.command'),'--no-gui','--no-launch']
        if not remembered:cmd+=['--image',str(self.game),'--dolphin',str(self.app)]
        r=subprocess.run(cmd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
        self.assertEqual(self.game.read_bytes(),self.original)
        return r

    def test_initial_install_and_descriptor_matches_official_schema(self):
        r=self.launch();self.assertEqual(r.returncode,0,r.stdout)
        descriptor=json.loads((self.state/'Jogar-PBR-Duplas.json').read_text())
        self.assertEqual(descriptor['type'],'dolphin-game-mod-descriptor');self.assertEqual(descriptor['version'],1)
        self.assertEqual(descriptor['base-file'],str(self.game))
        patch=descriptor['riivolution']['patches'][0]
        self.assertTrue(Path(patch['xml']).is_file());self.assertEqual(patch['options'][0]['choice'],1)
        self.assertEqual(patch['options'][0]['option-id'],'pbr-duplas')
        state=plistlib.loads((self.state/'config.plist').read_bytes());self.assertEqual(state['source_image'],str(self.game))

    def test_remembered_paths_and_offline_cache(self):
        r=self.launch();self.assertEqual(r.returncode,0,r.stdout)
        self.feed.unlink();self.core.unlink()
        r=self.launch(remembered=True);self.assertEqual(r.returncode,0,r.stdout)

    def test_next_version_updates_descriptor_preserves_save_and_original(self):
        save=self.root/'Dolphin-User/Wii/title/save.dat';save.parent.mkdir(parents=True);save.write_bytes(b'progress')
        r=self.launch();self.assertEqual(r.returncode,0,r.stdout)
        old=json.loads((self.state/'Jogar-PBR-Duplas.json').read_text())['riivolution']['patches'][0]['xml']
        self.manifest['mod_version']='fixture-v2';self.contents['mod/main.dol']=b'next version'
        self.manifest['replacements'][0]['sha256']=digest(self.contents['mod/main.dol']);self.release()
        r=self.launch(remembered=True);self.assertEqual(r.returncode,0,r.stdout)
        new=json.loads((self.state/'Jogar-PBR-Duplas.json').read_text())['riivolution']['patches'][0]['xml']
        self.assertNotEqual(new,old);self.assertTrue(Path(old).exists());self.assertEqual(save.read_bytes(),b'progress')

    def test_wrong_revision_rejected_without_state(self):
        data=bytearray(self.original);data[95]=1;self.game.write_bytes(data);self.original=bytes(data)
        r=self.launch();self.assertNotEqual(r.returncode,0,r.stdout);self.assertFalse((self.state/'config.plist').exists())

    def test_iso_header_supported(self):
        data=bytearray(1088);data[:8]=b'RPBE01\0\0';data[24:28]=bytes.fromhex('5d1c9ea3')
        self.game=self.root/'original.iso';self.game.write_bytes(data);self.original=bytes(data)
        r=self.launch();self.assertEqual(r.returncode,0,r.stdout)

    def test_corrupt_download_falls_back_to_previous_version(self):
        r=self.launch();self.assertEqual(r.returncode,0,r.stdout)
        self.feed.write_text(json.dumps({'schema':1,'version':'bad','package_sha256':'0'*64,'package_url':'file://'+str(self.core)}))
        r=self.launch(remembered=True);self.assertEqual(r.returncode,0,r.stdout)
        self.assertEqual(plistlib.loads((self.state/'config.plist').read_bytes())['mod_version'],'fixture-v1')

    def test_archive_parent_path_refused(self):
        with zipfile.ZipFile(self.core,'w') as z:z.writestr('../outside.sh','bad')
        self.feed.write_text(json.dumps({'schema':1,'version':'bad','package_sha256':digest(self.core.read_bytes()),'package_url':'file://'+str(self.core)}))
        r=self.launch();self.assertNotEqual(r.returncode,0,r.stdout);self.assertFalse(list(self.state.rglob('outside.sh')))

    def test_payload_hash_mismatch_refused(self):
        self.contents['mod/main.dol']=b'corrupt';self.release()
        r=self.launch();self.assertNotEqual(r.returncode,0,r.stdout);self.assertFalse((self.state/'config.plist').exists())

if __name__=='__main__':
    import sys
    report_path=Path(os.environ.get('PBR_MAC_TEST_REPORT','mac-test-report.json'))
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(MacTests))
    report={'status':'passed' if result.wasSuccessful() and not result.skipped else 'failed_or_skipped',
            'tests':result.testsRun,'skipped':len(result.skipped),'platform':platform.platform(),
            'limits':['No interactive chooser or actual Dolphin launch','ISO/RVZ headers are fixtures, not real disc images','No gameplay or real save test']}
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    sys.exit(0 if report['status']=='passed' else 1)
