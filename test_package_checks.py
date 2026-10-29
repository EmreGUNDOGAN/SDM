import types
import unittest
from tools.check_package import compare_code,normalized


class FrozenSourceTests(unittest.TestCase):
    def test_nested_code_matches_across_checkout_paths(self):
        source=b'def outer():\n def inner():\n  return 5\n return inner()\n'
        compare_code('module',compile(source,'different/build/path.py','exec'),source)
    def test_changed_nested_behavior_is_rejected(self):
        source=b'def outer():\n def inner():\n  return 5\n return inner()\n'
        with self.assertRaisesRegex(ValueError,'mismatch'):compare_code('module',compile(source.replace(b'return 5',b'return 6'),'module','exec'),source)
    def test_missing_or_noncode_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'compiled'):normalized(b'not code')


if __name__=='__main__':unittest.main()
