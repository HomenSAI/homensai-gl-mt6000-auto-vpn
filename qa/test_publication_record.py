"""Publication accepts only an exact package record on top of the tested commit."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('publication_record',Path(__file__).resolve().parents[1]/'scripts/publish-reviewed.py')
m=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(m)


@unittest.skipUnless(shutil.which('git'),'Git integration covered by Python 3.11 full CI')
class PublicationRecord(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)
        self.root_patch=patch.object(m,'ROOT',self.root);self.root_patch.start();self.addCleanup(self.root_patch.stop)
        self.git('init','-q')
        self.package=b'reproducible package bytes\n'
        self.digest=hashlib.sha256(self.package).hexdigest()
        self.artifact='homensai-auto-vpn_0.9.1-alpha51-1_all.ipk'
        self.manifest={'schema':1,'application':{'version':'0.9.1-alpha51','package_version':'0.9.1-alpha51-1',
                       'release_tag':'v0.9.1-alpha51','artifact':self.artifact,'sha256':'0'*64},'handoff':{'keep':True}}
        self.script='#!/bin/sh\nEXPECTED_SHA='+('0'*64)+'\nEXPECTED_SIZE=0\nEXPECTED_VERSION=0.9.1-alpha51-1\necho protected\n'
        self.write('VERSION.json',json.dumps(self.manifest))
        self.write('router-test-kit/02-install.sh',self.script)
        self.write('router/app.py','print("tested")\n')
        self.write('releases/v0.9.1-alpha50.md','old release notes\n')
        self.parent=self.commit('code')

    def git(self,*args):
        return subprocess.run(['git','-c','user.name=Publication QA','-c','user.email=qa@example.invalid',*args],
                              cwd=self.root,capture_output=True,text=True,check=True,timeout=30).stdout.strip()

    def write(self,name,data):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(data if isinstance(data,bytes) else data.encode('utf-8'))

    def commit(self,message):
        self.git('add','-A');self.git('commit','-q','-m',message)
        return self.git('rev-parse','HEAD')

    def record(self,mutate=None):
        manifest=copy.deepcopy(self.manifest);manifest['application']['sha256']=self.digest
        self.write('VERSION.json',json.dumps(manifest,indent=2))
        self.write('router-test-kit/02-install.sh',self.script.replace('EXPECTED_SHA='+('0'*64),'EXPECTED_SHA='+self.digest).replace('EXPECTED_SIZE=0','EXPECTED_SIZE='+str(len(self.package))))
        self.write('releases/'+self.artifact,self.package)
        self.write('releases/'+self.artifact+'.sha256',self.digest+'  '+self.artifact+'\n')
        self.write('releases/v0.9.1-alpha51.md','One CI run; independently checked package record.\n')
        if mutate:mutate()
        return self.commit('record')

    def matrix(self):
        return [dict(result='PASS',source=self.parent,sha256=self.digest,runtime_only=runtime,
                     lua_available=True,lua_tests=13) for runtime in (True,False)]

    def reject(self,mutate):
        source=self.record(mutate)
        with self.assertRaisesRegex(ValueError,'PUBLICATION-RECORD-SCOPE'):
            m.checked_source_receipt(self.matrix(),source)

    def test_accepts_exact_five_file_record(self):
        source=self.record()
        self.assertEqual(m.checked_source_receipt(self.matrix(),source),(self.digest,self.parent))

    def test_exact_source_path_does_not_need_a_record(self):
        self.assertEqual(m.checked_source_receipt(self.matrix(),self.parent),(self.digest,self.parent))

    def test_extra_file_refused(self):self.reject(lambda:self.write('extra.txt','extra'))
    def test_changed_code_line_refused(self):self.reject(lambda:self.write('router/app.py','print("untested")\n'))
    def test_wrong_package_hash_refused(self):self.reject(lambda:self.write('releases/'+self.artifact,b'wrong package'))
    def test_wrong_checksum_refused(self):self.reject(lambda:self.write('releases/'+self.artifact+'.sha256','c'*64+'  '+self.artifact+'\n'))
    def test_checksum_wrong_filename_refused(self):self.reject(lambda:self.write('releases/'+self.artifact+'.sha256',self.digest+'  old.ipk\n'))
    def test_edited_old_release_notes_refused(self):self.reject(lambda:self.write('releases/v0.9.1-alpha50.md','rewritten old notes\n'))
    def test_changed_install_code_refused(self):self.reject(lambda:self.write('router-test-kit/02-install.sh',self.script.replace('echo protected','echo untested')))
    def test_install_script_line_endings_outside_record_fields_refused(self):
        self.git('config','core.autocrlf','false')
        def mutate():
            path=self.root/'router-test-kit/02-install.sh'
            path.write_bytes(path.read_bytes().replace(b'\n',b'\r\n'))
        self.reject(mutate)
    def test_install_script_one_code_line_ending_refused(self):
        self.git('config','core.autocrlf','false')
        def mutate():
            path=self.root/'router-test-kit/02-install.sh'
            path.write_bytes(path.read_bytes().replace(b'echo protected\n',b'echo protected\r\n'))
        self.reject(mutate)
    def test_wrong_install_hash_refused(self):self.reject(lambda:self.write('router-test-kit/02-install.sh',self.script))
    def test_wrong_install_size_refused(self):
        self.reject(lambda:self.write('router-test-kit/02-install.sh',self.script.replace('0'*64,self.digest).replace('EXPECTED_SIZE=0','EXPECTED_SIZE=999')))
    def test_duplicate_install_hash_refused(self):
        self.reject(lambda:self.write('router-test-kit/02-install.sh',self.script+'EXPECTED_SHA='+self.digest+'\n'))
    def test_other_manifest_key_refused(self):
        def mutate():
            data=json.loads((self.root/'VERSION.json').read_text());data['handoff']['keep']=False
            self.write('VERSION.json',json.dumps(data))
        self.reject(mutate)
    def test_wrong_manifest_hash_refused(self):
        self.reject(lambda:self.write('VERSION.json',json.dumps(self.manifest)))
    def test_merge_commit_refused(self):
        source=self.record()
        self.git('checkout','--detach',self.parent)
        self.write('second-parent.txt','unreviewed');other=self.commit('other')
        tree=self.git('rev-parse',source+'^{tree}')
        merge=self.git('commit-tree',tree,'-p',self.parent,'-p',other,'-m','record merge')
        self.git('checkout','--detach',merge)
        with self.assertRaisesRegex(ValueError,'PUBLICATION-RECORD-SCOPE'):
            m.checked_source_receipt(self.matrix(),merge)
    def test_non_child_refused(self):
        self.write('intervening.txt','intervening');self.commit('intervening')
        source=self.record()
        with self.assertRaisesRegex(ValueError,'PUBLICATION-RECORD-SCOPE'):
            m.checked_source_receipt(self.matrix(),source)
    def test_ci_parent_not_on_branch_refused(self):
        source=self.record();self.git('checkout','--detach',self.parent)
        self.write('other.txt','other');self.git('checkout','--orphan','other');self.commit('unrelated')
        with self.assertRaisesRegex(ValueError,'PUBLICATION-RECORD-SCOPE'):
            m.checked_source_receipt(self.matrix(),source)
    def test_missing_new_notes_refused(self):
        self.reject(lambda:(self.root/'releases/v0.9.1-alpha51.md').unlink())

class PublicationTimeouts(unittest.TestCase):
    def test_gitea_timeout_is_thirty_minutes(self):
        with patch.object(m,'run') as run:
            m.save('feature/test')
        self.assertEqual(run.call_args.kwargs,{'timeout':1800})
    def test_other_commands_keep_three_minute_timeout(self):
        with patch.object(m.subprocess,'run') as run:
            run.return_value.stdout='ok\n';self.assertEqual(m.run('example'),'ok')
        self.assertEqual(run.call_args.kwargs['timeout'],180)


if __name__=='__main__':unittest.main()
