"""Integrity regressions use throwaway Git repos, never the user's index."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools.source_manifest import MANIFEST,index_files,render,run


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.git('init','-q');self.git('config','core.autocrlf','false')
        self.git('config','core.safecrlf','false')

    def git(self,*args):
        return subprocess.run(['git','-C',str(self.root),*args],capture_output=True,check=True).stdout

    def add(self,path,contents):
        target=self.root/path;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(contents);self.git('add','--',path)

    def write_and_stage(self):
        run('write',self.root);self.git('add','--',MANIFEST)

    def test_binary_unicode_spaces_order_and_self_exclusion(self):
        self.add('z space.bin',b'\x00\xff\r\n\x00')
        self.add('alt/ç.txt','gerçek baytlar'.encode())
        self.write_and_stage();self.assertEqual(run('check',self.root),0)
        expected=hashlib.sha256('gerçek baytlar'.encode()).hexdigest()+'  alt/ç.txt\n'
        self.assertTrue((self.root/MANIFEST).read_text(encoding='utf-8').startswith(expected))
        self.assertNotIn(MANIFEST,(self.root/MANIFEST).read_text())

    def test_git_normalized_bytes_are_used_instead_of_crlf_checkout(self):
        self.add('.gitattributes',b'*.txt text eol=lf\n')
        self.add('file.txt',b'one\r\ntwo\r\n')
        self.write_and_stage();self.assertEqual(run('check',self.root),0)
        expected=hashlib.sha256(b'one\ntwo\n').hexdigest()
        self.assertIn(expected,(self.root/MANIFEST).read_text())
        self.assertNotIn(hashlib.sha256(b'one\r\ntwo\r\n').hexdigest(),(self.root/MANIFEST).read_text())

    def test_staged_modification_addition_and_deletion_are_detected(self):
        self.add('a.txt',b'first');self.write_and_stage()
        self.add('a.txt',b'changed')
        with self.assertRaisesRegex(ValueError,'differs'):run('check',self.root)
        self.write_and_stage();self.add('new.txt',b'new')
        with self.assertRaisesRegex(ValueError,'differs'):run('check',self.root)
        self.write_and_stage();self.git('rm','--cached','-f','--','new.txt')
        with self.assertRaisesRegex(ValueError,'differs'):run('check',self.root)

    def test_unstaged_source_and_manifest_tampering_fail(self):
        self.add('file.txt',b'first');self.write_and_stage()
        (self.root/'file.txt').write_bytes(b'local drift')
        with self.assertRaisesRegex(ValueError,'Unstaged'):run('check',self.root)
        self.git('checkout','--','file.txt')
        (self.root/MANIFEST).write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError,'Unstaged'):run('check',self.root)
        self.git('add',MANIFEST)
        with self.assertRaisesRegex(ValueError,'differs'):run('check',self.root)

    def test_missing_manifest_and_unrelated_untracked_files(self):
        self.add('file.txt',b'first')
        with self.assertRaisesRegex(ValueError,'not staged'):run('check',self.root)
        self.write_and_stage();(self.root/'private-user-file.txt').write_bytes(b'not part of PR')
        self.assertEqual(run('check',self.root),0)
        self.assertNotIn(b'private-user-file',render(self.root,index_files(self.root)))


if __name__=='__main__':unittest.main()
