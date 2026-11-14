"""Closed-package imports and persistent errors before/after worker stages."""
import contextlib,importlib.util,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from verify_prepared_package import check_runtime_imports
ROOT=Path(__file__).resolve().parents[1]

class MegaPackagingTests(unittest.TestCase):
 def test_old_package_reproduces_missing_translation(self):
  with self.assertRaisesRegex(ValueError,"No module named 'translation'"):
   check_runtime_imports(ROOT/'expansion/packages/mega-lucario-test1/aplicador-core.zip')
 def test_new_package_imports_without_checkout_on_pythonpath(self):
  check_runtime_imports(ROOT/'expansion/packages/mega-lucario-test2/aplicador-core.zip')
 def test_failure_outside_worker_stages_is_logged(self):
  path=ROOT/'experiments/mega_lucario/convert_local.py'
  spec=importlib.util.spec_from_file_location('mega_error_fixture',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);args=[str(path)]
   for name in ('blender','source','originals','pbr-addon','reader','cache','result'):args.extend(['--'+name,str(root/name)])
   with patch.object(sys,'argv',args),patch.object(module,'convert',side_effect=ModuleNotFoundError("No module named 'translation'")),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
    self.assertEqual(module.main(),1)
   log=(root/'cache/conversion-failure.log').read_text(encoding='utf-8');self.assertIn("No module named 'translation'",log)
   self.assertFalse((root/'result').exists())

if __name__=='__main__':unittest.main()
