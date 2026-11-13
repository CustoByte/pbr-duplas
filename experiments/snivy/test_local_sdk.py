"""Reject unsafe dependency archive paths; verify private cache integrity."""
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import prepare_local_sdk as sdk
import convert_local as converter


class LocalSDKTests(unittest.TestCase):
    def test_archive_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / 'source.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('tool/../../escape', 'bad')
            with self.assertRaises(ValueError):
                sdk.extract_zip(archive, root / 'output', 'tool/')
            self.assertFalse((root / 'escape').exists())

    def test_cache_reuse_requires_matching_output_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            cache = Path(temporary)
            destination = cache / 'fixture-key'
            destination.mkdir()
            outputs = {}
            for name in converter.OUTPUTS:
                (destination / name).write_bytes(name.encode())
                outputs[name] = converter.digest(destination / name)
            (destination / 'verified-cache.json').write_text(json.dumps(dict(key='fixture-key', outputs=outputs)))
            with patch.object(converter, 'pipeline_key', return_value='fixture-key'):
                args = [Path('unused')] * 5 + [cache]
                self.assertEqual(converter.convert(*args), destination)
                (destination / converter.OUTPUTS[0]).write_bytes(b'corrupt')
                with self.assertRaises(ValueError):
                    converter.convert(*args)


if __name__ == '__main__':
    unittest.main()
