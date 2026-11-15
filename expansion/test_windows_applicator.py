"""Execute the real PowerShell workflow with a simulated image tool on Linux.

Does not exercise DolphinTool, Windows dialogs or a real Wii/RVZ image.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import zipfile

PWSH = Path(shutil.which('pwsh') or '/tmp/pbr-pwsh/pwsh')
SCRIPT = Path(__file__).with_name('windows-aplicador') / 'Aplicar-Mod.ps1'
FAKE = '''#!/usr/bin/env python3
import os,sys,zipfile
from pathlib import Path
args=sys.argv[1:]
mode=args[0]
source=Path(args[args.index('-i')+1]);dest=Path(args[args.index('-o')+1])
if mode=='extract':
    with zipfile.ZipFile(source) as z: z.extractall(dest/'DATA')
    if source.name=='resultado.rvz' and os.environ.get('PBR_TEST_CORRUPT'):
        (dest/'DATA/files/common.fsys').write_bytes(b'bad result')
elif mode=='convert':
    if os.environ.get('PBR_TEST_FAIL_CONVERT'): sys.exit(9)
    root=source.parent.parent
    with zipfile.ZipFile(dest,'w') as z:
        for f in root.rglob('*'):
            if f.is_file(): z.write(f,f.relative_to(root).as_posix())
else: sys.exit(2)
'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


@unittest.skipUnless(PWSH.exists(), 'Portable PowerShell runtime unavailable')
class ApplicatorFixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="pbr cópia d' & teste ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / 'aplicador'
        self.package.mkdir()
        shutil.copyfile(SCRIPT, self.package / SCRIPT.name)
        self.tool = self.root / 'fake tool.py'
        self.tool.write_text(FAKE)
        self.tool.chmod(0o755)
        self.image = self.root / 'original.rvz'
        self.output = self.root / 'saida.rvz'
        boot = bytearray(0x440)
        boot[:8] = b'RPBE01\0\0'
        boot[24:28] = bytes.fromhex('5d1c9ea3')
        self.original = {'sys/boot.bin': bytes(boot), 'sys/main.dol': b'original dol',
                         'sys/fst.bin': b'original fst', 'files/common.fsys': b'original common',
                         'files/deck.fsys': b'deck', 'files/other.bin': b'other'}
        self.replacements = {'sys/main.dol': b'new dol', 'files/common.fsys': b'new longer common'}
        self.manifest = {'mod_version': 'fixture',
                         'original_sha256': {n: sha(self.original[n]) for n in ('sys/main.dol', 'sys/fst.bin', 'files/common.fsys', 'files/deck.fsys')},
                         'game_files': [{'path': n[6:], 'size': len(b)} for n,b in self.original.items() if n.startswith('files/')],
                         'replacements': []}
        for index, (name,data) in enumerate(self.replacements.items()):
            path = f'mod/{index}.bin'
            (self.package / path).parent.mkdir(exist_ok=True)
            (self.package / path).write_bytes(data)
            self.manifest['replacements'].append({'package_path': path, 'installed_path': name, 'sha256': sha(data)})
        self.save_manifest()
        self.save_image()
        self.original_image = self.image.read_bytes()

    def save_manifest(self):
        (self.package / 'manifesto.json').write_text(json.dumps(self.manifest))

    def save_image(self):
        with zipfile.ZipFile(self.image,'w') as z:
            for n,b in self.original.items(): z.writestr(n,b)

    def run_app(self, env_extra=None, source=None, output=None, default_output=False, launch=False, state=False, use_saved=False):
        env = dict(os.environ, XDG_CACHE_HOME='/tmp/pbr-ps-cache', XDG_CONFIG_HOME='/tmp/pbr-ps-config', XDG_DATA_HOME='/tmp/pbr-ps-data')
        env.update(env_extra or {})
        command = [str(PWSH), '-NoProfile', '-File', str(self.package / SCRIPT.name),
                   '-ImagePath', str(source or self.image), '-ToolPath', str(self.tool), '-NoGui']
        if not launch: command.append('-DoNotLaunch')
        else:
            launcher = self.root / 'Dolphin.exe'
            launcher.write_text('#!/usr/bin/env python3\nfrom pathlib import Path\nimport sys\nPath(__file__).with_name("launched.json").write_text(__import__("json").dumps(sys.argv[1:]))\n')
            launcher.chmod(0o755)
            command += ['-DolphinPath', str(launcher)]
        if not default_output: command += ['-OutputPath', str(output or self.output)]
        if state: command += ['-StatePath', str(self.root/'state.json')]
        if use_saved:
            for option in ('-ImagePath','-ToolPath','-OutputPath'):
                if option in command:
                    at=command.index(option);del command[at:at+2]
        result = subprocess.run(command, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=40)
        self.assertEqual(self.image.read_bytes(), self.original_image, result.stdout)
        return result


class WorkflowTests(ApplicatorFixture):
    def test_full_pipeline_and_content_roundtrip_with_nonascii_and_shell_chars(self):
        r = self.run_app()
        self.assertEqual(r.returncode,0,r.stdout)
        with zipfile.ZipFile(self.output) as z:
            for n,b in self.original.items(): self.assertEqual(z.read(n),self.replacements.get(n,b))
        report=json.loads(Path(str(self.output)+'.relatorio.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(report['checked_game_files'],3)
        self.assertFalse(report['dolphin_gameplay_tested'])
        self.assertEqual(list(self.root.glob('.pbr-duplas-*')),[])

    def test_selects_single_image_in_folder_and_automatic_output(self):
        r=self.run_app(source=self.root,default_output=True)
        self.assertEqual(r.returncode,0,r.stdout)
        self.assertTrue((self.root/'original-Duplas.rvz').exists())

    def test_automatic_launch(self):
        r=self.run_app(launch=True)
        self.assertEqual(r.returncode,0,r.stdout)
        import time
        for _ in range(20):
            if (self.root/'launched.json').exists(): break
            time.sleep(.05)
        self.assertEqual(json.loads((self.root/'launched.json').read_text()),['-e',str(self.output)])

    def test_saved_rom_reused_without_extraction_when_unchanged(self):
        first=self.run_app(state=True)
        self.assertEqual(first.returncode,0,first.stdout)
        second=self.run_app(state=True,use_saved=True,env_extra={'PBR_TEST_FAIL_CONVERT':'1'})
        self.assertEqual(second.returncode,0,second.stdout)
        self.assertIn('ja esta atualizada',second.stdout)
        self.assertEqual(list(self.root.glob('.pbr-duplas-*')),[])

    def test_new_version_rebuilds_stable_output_and_keeps_backup(self):
        first=self.run_app(state=True)
        self.assertEqual(first.returncode,0,first.stdout)
        old=self.output.read_bytes()
        data=b'new version of dol'
        (self.package/'mod/0.bin').write_bytes(data)
        self.manifest['mod_version']='fixture-v2'
        self.manifest['replacements'][0]['sha256']=sha(data)
        self.save_manifest()
        second=self.run_app(state=True,use_saved=True)
        self.assertEqual(second.returncode,0,second.stdout)
        self.assertEqual(Path(str(self.output)+'.anterior.rvz').read_bytes(),old)
        with zipfile.ZipFile(self.output) as z:self.assertEqual(z.read('sys/main.dol'),data)
        state=json.loads((self.root/'state.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(state['mod_version'],'fixture-v2')

    def test_failed_update_keeps_previous_game_and_state(self):
        first=self.run_app(state=True)
        self.assertEqual(first.returncode,0,first.stdout)
        old=self.output.read_bytes(); state=(self.root/'state.json').read_bytes()
        self.manifest['mod_version']='fixture-v2';self.save_manifest()
        second=self.run_app(state=True,use_saved=True,env_extra={'PBR_TEST_FAIL_CONVERT':'1'})
        self.assertNotEqual(second.returncode,0,second.stdout)
        self.assertEqual(self.output.read_bytes(),old)
        self.assertEqual((self.root/'state.json').read_bytes(),state)

    def test_existing_output_is_preserved(self):
        self.output.write_bytes(b'keep')
        r=self.run_app()
        self.assertNotEqual(r.returncode,0,r.stdout)
        self.assertEqual(self.output.read_bytes(),b'keep')

    def test_default_output_collision_gets_new_name(self):
        old=self.root/'original-Duplas.rvz';old.write_bytes(b'keep')
        r=self.run_app(default_output=True)
        self.assertEqual(r.returncode,0,r.stdout)
        self.assertEqual(old.read_bytes(),b'keep')
        self.assertEqual(len(list(self.root.glob('original-Duplas-*.rvz'))),1)

    def test_same_source_and_output_refused(self):
        r=self.run_app(output=self.image)
        self.assertNotEqual(r.returncode,0,r.stdout)

    def test_manifest_cannot_write_outside_partition(self):
        self.manifest['replacements'][0]['installed_path']='files/../../outside.bin'
        self.save_manifest()
        result=self.run_app()
        self.assertNotEqual(result.returncode,0,result.stdout)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.rglob('outside.bin')))

    def test_corrupted_package_refused(self):
        (self.package/'mod/0.bin').write_bytes(b'corrupt')
        r=self.run_app()
        self.assertNotEqual(r.returncode,0,r.stdout)
        self.assertFalse(self.output.exists())

    def test_wrong_revision_refused(self):
        b=bytearray(self.original['sys/boot.bin']);b[7]=1;self.original['sys/boot.bin']=bytes(b)
        self.save_image();self.original_image=self.image.read_bytes()
        r=self.run_app()
        self.assertNotEqual(r.returncode,0,r.stdout)
        self.assertFalse(self.output.exists())

    def test_modified_original_hash_refused(self):
        self.original['files/common.fsys']=b'modified common'
        self.save_image();self.original_image=self.image.read_bytes()
        r=self.run_app()
        self.assertNotEqual(r.returncode,0,r.stdout)
        self.assertFalse(self.output.exists())

    def test_missing_game_file_refused(self):
        del self.original['files/other.bin']
        self.save_image();self.original_image=self.image.read_bytes()
        r=self.run_app()
        self.assertNotEqual(r.returncode,0,r.stdout)
        self.assertFalse(self.output.exists())

    def test_tool_failure_preserves_diagnostic_and_no_output(self):
        r=self.run_app({'PBR_TEST_FAIL_CONVERT':'1'})
        self.assertNotEqual(r.returncode,0,r.stdout)
        self.assertFalse(self.output.exists())
        self.assertEqual(len(list(self.root.glob('.pbr-duplas-*/falha.txt'))),1)

    def test_bad_roundtrip_refused(self):
        r=self.run_app({'PBR_TEST_CORRUPT':'1'})
        self.assertNotEqual(r.returncode,0,r.stdout)
        self.assertFalse(self.output.exists())


if __name__=='__main__': unittest.main(verbosity=2)
