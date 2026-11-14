"""Verify local asset insertion in real PowerShell with a conversion fixture.

The fixture tests packaging and preservation, not Blender or a real RVZ image.
"""
import json
import unittest
import zipfile
from pathlib import Path
import test_delta_workflow as workflow


class SnivyInstallerTests(unittest.TestCase):
    def test_local_assets_added_and_remembered_without_touching_save(self):
        fixture = workflow.DeltaTests('test_delta_also_adds_deck_and_keeps_original_and_save')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.manifest['local_snivy_assets'] = True
        fixture.save_manifest()
        source = fixture.root / 'Tsutarja.brres'
        source.write_bytes(b'local conversion source fixture')
        assets = fixture.root / 'private assets'
        assets.mkdir()
        names = ('pkx_501.fsys', 'menu_face.fsys', 'menu_pokemon.fsys')
        for name in names:
            (assets / name).write_bytes(('fixture ' + name).encode())
        # Existing remembered state supplies the source without opening a dialog.
        (fixture.root / 'state.json').write_text(json.dumps(dict(snivy_source=str(source))))
        escaped = str(assets).replace("'", "''")
        (fixture.package / 'Preparar-Snivy.ps1').write_text(
            "function Prepare-Snivy($Partition, $Source, $CacheRoot) { return '" + escaped + "' }\n")
        save = fixture.root / 'normal-save.sav'
        save.write_bytes(b'keep campaign save')
        result = fixture.run_app(state=True)
        self.assertEqual(result.returncode, 0, result.stdout)
        with zipfile.ZipFile(fixture.output) as archive:
            for name in names:
                self.assertEqual(archive.read('files/' + name), (assets / name).read_bytes())
            for name, data in fixture.original.items():
                self.assertEqual(archive.read(name), fixture.replacements.get(name, data))
        state = json.loads((fixture.root / 'state.json').read_text(encoding='utf-8-sig'))
        self.assertEqual(state['snivy_source'], str(source))
        self.assertEqual(save.read_bytes(), b'keep campaign save')


if __name__ == '__main__':
    unittest.main()
