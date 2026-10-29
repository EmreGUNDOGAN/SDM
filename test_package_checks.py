import types
import unittest
from pathlib import Path
from unittest.mock import patch
import tempfile
from tools.check_package import compare_code,normalized
import prepare_ci_tools


class FrozenSourceTests(unittest.TestCase):
    def test_nested_code_matches_across_checkout_paths(self):
        source=b'def outer():\n def inner():\n  return 5\n return inner()\n'
        compare_code('module',compile(source,'different/build/path.py','exec'),source)
    def test_changed_nested_behavior_is_rejected(self):
        source=b'def outer():\n def inner():\n  return 5\n return inner()\n'
        with self.assertRaisesRegex(ValueError,'mismatch'):compare_code('module',compile(source.replace(b'return 5',b'return 6'),'module','exec'),source)
    def test_missing_or_noncode_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'compiled'):normalized(b'not code')

    def test_compiler_preparation_uses_pinned_portable_mode(self):
        with tempfile.TemporaryDirectory() as folder:
            cache=Path(folder);compiler=cache/'inno/ISCC.exe'
            compiler.parent.mkdir();compiler.write_bytes(b'fixture')
            installer=cache/'vendor.exe'
            with patch.object(prepare_ci_tools,'CACHE',cache),patch.object(prepare_ci_tools,'fetch',return_value=installer) as fetch,patch.object(prepare_ci_tools.subprocess,'run') as run:
                self.assertEqual(prepare_ci_tools.prepare_inno(),compiler)
            self.assertEqual(fetch.call_args.args[2],prepare_ci_tools.INNO_SHA256)
            command=run.call_args.args[0]
            for flag in ('/PORTABLE=1','/CURRENTUSER','/NOICONS','/TASKS=','/DIR='+str(compiler.parent)):
                self.assertIn(flag,command)
            self.assertTrue(run.call_args.kwargs['check'])
            compiler.unlink()
            with patch.object(prepare_ci_tools,'CACHE',cache),patch.object(prepare_ci_tools,'fetch',return_value=installer),patch.object(prepare_ci_tools.subprocess,'run'):
                with self.assertRaisesRegex(RuntimeError,'compiler is missing'):prepare_ci_tools.prepare_inno()


if __name__=='__main__':unittest.main()
