"""Regression for root attributes lost by git archive COMMIT:router."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('sdk_source',Path(__file__).resolve().parents[1]/'scripts/export-sdk-source.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


@unittest.skipUnless(shutil.which('git'),'SDK source regression requires Git')
class SDKSourceArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
        self.repo=self.base/'repo';self.repo.mkdir()
        self.git('init','--initial-branch=main');self.git('config','user.name','SDK QA');self.git('config','user.email','qa@example.invalid')
        self.git('config','core.autocrlf','true')
        (self.repo/'.gitattributes').write_bytes(b'* text=auto\nrouter/files/style/** -text\n')
        self.asset=self.repo/'router/files/style/tokens.css';self.asset.parent.mkdir(parents=True)
        self.asset.write_bytes(b'first line\nsecond line\n')
        self.git('add','.');self.git('commit','-m','root attributes fixture');self.commit=self.git('rev-parse','HEAD')

    def git(self,*args):
        return subprocess.check_output(['git','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false',*args],cwd=self.repo,stderr=subprocess.PIPE,text=True,timeout=30).strip()

    def test_root_context_preserves_pinned_bytes_even_with_autocrlf(self):
        target=self.base/'root-context.tar';record=m.create_snapshot(self.repo,self.commit,target)
        with tarfile.open(target) as archive:actual=archive.extractfile('files/style/tokens.css').read()
        committed=subprocess.check_output(['git','show',self.commit+':router/files/style/tokens.css'],cwd=self.repo)
        self.assertEqual(actual,committed);self.assertEqual(record['source_strip_components'],0)
        self.assertEqual(record['source_kind'],'committed-tree')
        # Demonstrate that the tempting subtree shortcut actually changes these bytes.
        wrong=self.base/'subtree.tar';self.git('archive','--format=tar','--output='+str(wrong),self.commit+':router')
        with tarfile.open(wrong) as archive:wrong_bytes=archive.extractfile('files/style/tokens.css').read()
        self.assertNotEqual(wrong_bytes,actual)

    def test_existing_archive_and_short_commit_refuse_without_overwrite(self):
        target=self.base/'preserved.tar';target.write_bytes(b'preserve')
        with self.assertRaisesRegex(ValueError,'SNAPSHOT-EXISTS'):m.create_snapshot(self.repo,self.commit,target)
        self.assertEqual(target.read_bytes(),b'preserve')
        with self.assertRaisesRegex(ValueError,'FULL-COMMIT'):m.create_snapshot(self.repo,self.commit[:7],self.base/'new.tar')
