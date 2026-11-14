import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'launcher'))
import core


class NativeLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'

    def package(self, entries):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            for name, content in entries:
                archive.writestr(name, content)
        return stream.getvalue()

    def feed(self, data, version='v0.1.0-test.1'):
        return dict(schema=1, product='pbr-native', runtime_available=True, version=version,
                    windows_x64=dict(url=f'https://raw.githubusercontent.com/CustoByte/pbr-duplas/{version}/native/packages/runtime.zip',
                                     sha256=hashlib.sha256(data).hexdigest()))

    def install(self, data, feed=None):
        with patch.object(core.urllib.request, 'urlopen', return_value=io.BytesIO(data)):
            return core.install_runtime(self.home, feed or self.feed(data))

    def test_modified_image_registration_preserves_source(self):
        source = self.root / 'Battle Revolution modificado.iso'
        image = bytearray(1024)
        image[:6] = b'RPBE01'
        image[24:28] = bytes.fromhex('5d1c9ea3')
        image[400:420] = b'modified game assets!'
        source.write_bytes(image)
        stamp = source.stat().st_mtime_ns
        result = core.register_image(source, self.home)
        self.assertEqual(source.read_bytes(), image)
        self.assertEqual(source.stat().st_mtime_ns, stamp)
        self.assertEqual(result['sha256'], hashlib.sha256(image).hexdigest())
        self.assertFalse(result['assets_extracted'])

    def test_other_game_iso_refused(self):
        source = self.root / 'other.iso'
        image = bytearray(256)
        image[:6] = b'S2LE01'
        image[24:28] = bytes.fromhex('5d1c9ea3')
        source.write_bytes(image)
        with self.assertRaisesRegex(ValueError, 'não é do'):
            core.register_image(source, self.home)
        self.assertFalse((self.home / 'source.json').exists())

    def test_rvz_does_not_invent_game_id(self):
        source = self.root / 'modified.rvz'
        source.write_bytes(b'RVZ\x01' + bytes(252))
        self.assertIsNone(core.register_image(source, self.home)['game_id'])

    def test_external_update_repository_refused(self):
        feed = self.feed(b'payload')
        feed['windows_x64']['url'] = 'https://example.com/runtime.zip'
        with self.assertRaisesRegex(ValueError, 'repositório'):
            core.validate_feed(feed)

    def test_archive_path_attacks_refused(self):
        for name in ('../escape', '/absolute', 'C:/evil', 'dir\\evil', 'CON.txt', 'test. /a'):
            with self.subTest(name=name):
                package = self.root / 'test.zip'
                package.write_bytes(self.package([(name, b'attack'), ('PBRNative.exe', b'exe')]))
                with self.assertRaises(ValueError):
                    core.unpack_runtime(package, self.root / 'expanded')
        self.assertFalse((self.root / 'escape').exists())

    def test_symlink_and_windows_case_collision_refused(self):
        for symlink in (False, True):
            package = self.root / 'test.zip'
            with zipfile.ZipFile(package, 'w') as archive:
                archive.writestr('PBRNative.exe', b'exe')
                if symlink:
                    entry = zipfile.ZipInfo('link')
                    entry.create_system = 3
                    entry.external_attr = 0o120777 << 16
                    archive.writestr(entry, '../escape')
                else:
                    archive.writestr('pbrnative.EXE', b'collision')
            with self.assertRaises(ValueError):
                core.unpack_runtime(package, self.root / 'expanded')

    def test_hash_failure_preserves_active_release_and_save(self):
        first = self.package([('PBRNative.exe', b'first')])
        self.install(first)
        before = (self.home / 'current.json').read_bytes()
        save = self.home / 'saves' / 'campaign.dat'
        save.parent.mkdir()
        save.write_bytes(b'USER SAVE')
        wrong = self.feed(b'expected bytes', 'v0.1.0-test.2')
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            self.install(b'wrong bytes', wrong)
        self.assertEqual((self.home / 'current.json').read_bytes(), before)
        self.assertEqual(save.read_bytes(), b'USER SAVE')

    def test_install_then_rollback_retains_both_releases(self):
        self.install(self.package([('PBRNative.exe', b'first')]))
        data = self.package([('PBRNative.exe', b'second')])
        self.install(data, self.feed(data, 'v0.1.0-test.2'))
        self.assertEqual(core.runtime_path(self.home).read_bytes(), b'second')
        core.rollback(self.home)
        self.assertEqual(core.runtime_path(self.home).read_bytes(), b'first')
        self.assertEqual(len(list((self.home / 'releases').iterdir())), 2)

    def test_no_fake_playable_runtime(self):
        self.assertIsNone(core.runtime_path(self.home))
        feed = json.loads((Path(__file__).resolve().parents[1] / 'update.json').read_text())
        self.assertFalse(core.validate_feed(feed)['runtime_available'])
        with self.assertRaises(ValueError):
            core.install_runtime(self.home, feed)


if __name__ == '__main__':
    unittest.main()
