"""Exercise delta/overlay assembly; does not execute macOS or Dolphin."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from binary_delta import create, sha
import build_mac_overlay as overlay


class MacOverlayTests(unittest.TestCase):
    def test_private_overlay_adds_species_without_changing_originals(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original, core, assets = [root / name for name in ('original', 'core', 'assets')]
            for p in (original / 'sys', original / 'files', core, assets):
                p.mkdir(parents=True, exist_ok=True)
            before = {'sys/main.dol': b'original exe', 'files/common.fsys': b'original common'}
            manifest = dict(local_snivy_assets=True, mod_version='fixture', original_sha256={}, replacements=[])
            for i, (name, data) in enumerate(before.items()):
                (original / name).write_bytes(data)
                target = b'patched ' + data
                patch_data = create(data, target)
                filename = str(i) + '.pbrdelta'
                (core / filename).write_bytes(patch_data)
                manifest['original_sha256'][name] = sha(data)
                manifest['replacements'].append(dict(installed_path=name, package_path=filename,
                    patch_sha256=sha(patch_data), sha256=sha(target), format='pbr-delta-v1'))
            (core / 'manifesto.json').write_text(json.dumps(manifest))
            for name in ('pkx_501.fsys', 'menu_face.fsys', 'menu_pokemon.fsys'):
                (assets / name).write_bytes(b'private fixture')
            image = root / 'original.rvz'
            image.write_bytes(b'image fixture')
            output = root / 'overlay'
            with patch.object(overlay, 'convert', return_value=assets):
                descriptor = overlay.build(core, original, root / 'blender', root / 'source', root / 'sdk', root / 'cache', output, image)
            doc = json.loads(descriptor.read_text())
            self.assertEqual(doc['base-file'], str(image.resolve()))
            xml = ET.parse(output / 'riivolution.xml')
            files = {node.attrib['disc']: node.attrib for node in xml.findall('./patch/file')}
            self.assertEqual(files['/pkx_501.fsys']['create'], 'true')
            self.assertEqual(files['main.dol']['external'], '/mod/sys/main.dol')
            for name, data in before.items():
                self.assertEqual((original / name).read_bytes(), data)
                self.assertEqual((output / 'mod' / name).read_bytes(), b'patched ' + data)
            self.assertEqual(image.read_bytes(), b'image fixture')


if __name__ == '__main__':
    unittest.main()
