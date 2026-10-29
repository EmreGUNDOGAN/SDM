import types
import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch
import tempfile
from tools.check_package import compare_code,normalized
from tools import check_package
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


class PackagedCredentialTests(unittest.TestCase):
    marker=b'-----BEGIN '+b'PRIVATE KEY-----'

    def test_only_exact_vendor_hash_accepts_a_null_terminated_format_literal(self):
        content=b'MZ\0'+self.marker+b'\0format constant'
        expected=hashlib.sha256(content).hexdigest()
        with patch.dict(check_package.PEM_LITERAL_BINARIES,{'ffmpeg.exe':expected}):
            check_package.scan_packaged_credentials(Path('ffmpeg.exe'),content)
            with self.assertRaisesRegex(ValueError,'private key'):
                check_package.scan_packaged_credentials(Path('other.dll'),content)
            with self.assertRaisesRegex(ValueError,'vendor binary mismatch'):
                check_package.scan_packaged_credentials(Path('ffmpeg.exe'),content+b'changed')
        with self.assertRaisesRegex(ValueError,'vendor binary mismatch'):
            check_package.scan_packaged_credentials(Path('ffmpeg.exe'),content)

    def test_key_payload_is_rejected_even_in_an_otherwise_trusted_blob(self):
        for newline in (b'\n',b'\r\n'):
            content=b'MZ\0'+self.marker+newline+b'c3ludGhldGlj'+newline+b'-----END '+b'PRIVATE KEY-----'
            with self.subTest(newline=newline),patch.dict(check_package.PEM_LITERAL_BINARIES,{'ffmpeg.exe':hashlib.sha256(content).hexdigest()}):
                with self.assertRaisesRegex(ValueError,'private key'):
                    check_package.scan_packaged_credentials(Path('ffmpeg.exe'),content)

    def test_other_secret_signatures_are_not_exempted_by_a_vendor_hash(self):
        content=b'MZ\0'+self.marker+b'\0'+b'ghp_'+b'a'*40+b'\0'
        with patch.dict(check_package.PEM_LITERAL_BINARIES,{'ffmpeg.exe':hashlib.sha256(content).hexdigest()}):
            with self.assertRaisesRegex(ValueError,'GitHub token'):
                check_package.scan_packaged_credentials(Path('ffmpeg.exe'),content)

    def test_null_terminated_marker_in_unknown_binary_still_fails(self):
        with self.assertRaisesRegex(ValueError,'private key'):
            check_package.scan_packaged_credentials(Path('application.exe'),b'MZ\0'+self.marker+b'\0')

    def test_public_vendor_identifier_requires_exact_path_and_content(self):
        content=b'client = "'+b'AKIA'+b'A'*16+b'"\n';path=Path('yt_dlp/extractor/shahid.py')
        with patch.dict(check_package.PUBLIC_VENDOR_FILES,{path.as_posix():hashlib.sha256(content).hexdigest()}):
            check_package.scan_packaged_credentials(path,content)
            with self.assertRaisesRegex(ValueError,'AWS access key'):
                check_package.scan_packaged_credentials(Path('shahid.py'),content)
            with self.assertRaisesRegex(ValueError,'vendor source mismatch'):
                check_package.scan_packaged_credentials(path,content+b'changed')

    def test_public_vendor_identifier_does_not_exempt_an_added_token(self):
        content=b'AKIA'+b'A'*16+b'\0'+b'ghp_'+b'b'*40;path=Path('yt_dlp/extractor/shahid.py')
        with patch.dict(check_package.PUBLIC_VENDOR_FILES,{path.as_posix():hashlib.sha256(content).hexdigest()}):
            with self.assertRaisesRegex(ValueError,'GitHub token'):
                check_package.scan_packaged_credentials(path,content)

    def test_public_vendor_file_does_not_exempt_a_private_key_marker(self):
        content=self.marker+b'\0';path=Path('yt_dlp/extractor/shahid.py')
        with patch.dict(check_package.PUBLIC_VENDOR_FILES,{path.as_posix():hashlib.sha256(content).hexdigest()}):
            with self.assertRaisesRegex(ValueError,'private key'):
                check_package.scan_packaged_credentials(path,content)


if __name__=='__main__':unittest.main()
