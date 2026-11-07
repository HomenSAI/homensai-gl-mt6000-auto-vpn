"""Publication accepts only an exact package record on top of the tested commit."""
import copy
import contextlib
import io
import hashlib
import importlib.util
import json
import locale
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
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

    def test_check_only_release_does_not_call_network_save_or_create_ledger(self):
        source=self.record()
        with tempfile.TemporaryDirectory() as directory:
            receipt=Path(directory)/'ci.json';receipt.write_text(json.dumps(self.matrix()))
            argv=['publish-reviewed.py','--source',source,'--receipt',str(receipt),'--check-only',
                  '--release','v0.9.1-alpha51','--artifact',str(self.root/'releases'/self.artifact),
                  '--notes',str(self.root/'releases/v0.9.1-alpha51.md')]
            actual_run=m.run
            def local_only(*args,**kwargs):
                self.assertEqual(args[0],'git')
                self.assertIn(args[1],('status','rev-parse','rev-list','merge-base','diff'))
                return actual_run(*args,**kwargs)
            with patch.object(sys,'argv',argv),patch.object(m,'run',side_effect=local_only),patch.object(m,'scan_publication') as scan,patch.object(m,'save') as save,contextlib.redirect_stdout(io.StringIO()) as output:
                m.main()
            self.assertTrue(json.loads(output.getvalue())['check_only'])
            save.assert_not_called();scan.assert_called_once()
            self.assertFalse((self.root/'.git/handoff').exists())

    def test_extra_file_refused(self):self.reject(lambda:self.write('extra.txt','extra'))

    def existing_notes_parent(self):
        self.write('releases/v0.9.1-alpha51.md','Reviewed release description.\n')
        self.parent=self.commit('reviewed release notes')

    def test_existing_current_notes_may_only_be_appended(self):
        self.existing_notes_parent()
        source=self.record(lambda:self.write('releases/v0.9.1-alpha51.md','Reviewed release description.\n\nPackage hash and CI record.\n'))
        self.assertEqual(m.checked_source_receipt(self.matrix(),source),(self.digest,self.parent))

    def test_existing_current_notes_cannot_be_rewritten(self):
        self.existing_notes_parent()
        self.reject(lambda:self.write('releases/v0.9.1-alpha51.md','Changed release description.\n'))

    def test_existing_notes_cannot_rewrite_prefix_and_append_a_long_tail(self):
        self.existing_notes_parent()
        self.reject(lambda:self.write('releases/v0.9.1-alpha51.md',
                    'Changed release description.\n\nA long package and CI appendix must not hide rewritten reviewed text.\n'))

    def test_existing_notes_do_not_allow_private_status_memory_or_backup(self):
        self.existing_notes_parent()
        for name in ('private/x.txt','memory/x.md','docs/CURRENT-STATUS.md','backup/x.txt'):
            with self.subTest(name=name):
                self.git('reset','--hard',self.parent)
                def mutate():
                    self.write('releases/v0.9.1-alpha51.md','Reviewed release description.\n\nCI record.\n')
                    self.write(name,'out of scope')
                self.reject(mutate)
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

    # Signed record (docs/architecture/SIGNING-2026-11-03.ru.md): <ipk>.sig + extended CHAIN.jsonl + optional .ots.
    def signing_parent(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/signing'))
        import chain,usign_format
        self.chain,self.usign=chain,usign_format
        self.key=usign_format.SecretKey(bytes(range(32)),bytes.fromhex('1111111111111111'))
        self.other=usign_format.SecretKey(bytes(range(1,33)),bytes.fromhex('2222222222222222'))
        self.write(m.SIGNING_KEYS+'/1111111111111111',self.key.public_file('test main'))
        first=chain.next_entry([],'homensai-auto-vpn_0.9.1-alpha50-1_all.ipk','0.9.1-alpha50','0.9.1-alpha50-1','a'*64,5,'b'*40,
                               '2026-11-03T00:00:00Z',self.key.key_id.hex(),origin='imported')
        self.entries=[first];self.write('releases/CHAIN.jsonl',chain.make_line(first,self.key)+b'\n')
        self.parent=self.commit('keys and history')

    def signed(self,key=None,entry_key=None,ots=True,chain_text=None):
        key=key or self.key;entry_key=entry_key or self.key
        def mutate():
            entry=self.chain.next_entry(self.entries,self.artifact,'0.9.1-alpha51','0.9.1-alpha51-1',self.digest,len(self.package),
                                        self.parent,'2026-11-03T01:00:00Z',entry_key.key_id.hex())
            data=(self.root/'releases/CHAIN.jsonl').read_bytes()+self.chain.make_line(entry,entry_key)+b'\n'
            self.write('releases/CHAIN.jsonl',chain_text(data) if chain_text else data)
            self.write('releases/'+self.artifact+'.sig',key.sign_file(self.package))
            if ots:self.write('releases/ots/0.9.1-alpha51-1.ots',b'proof')
        return mutate

    def test_signed_record_accepted(self):
        self.signing_parent()
        source=self.record(self.signed())
        self.assertEqual(m.checked_source_receipt(self.matrix(),source),(self.digest,self.parent))
        self.assertEqual(sorted(m.signed_assets(Path(self.artifact),'0.9.1-alpha51-1')),
                         sorted([self.artifact+'.sig','CHAIN.jsonl','0.9.1-alpha51-1.ots']))

    def test_signed_record_without_proof_accepted(self):
        self.signing_parent()
        self.assertEqual(m.checked_source_receipt(self.matrix(),self.record(self.signed(ots=False))),(self.digest,self.parent))

    def attributes_parent(self,attributes='* text=auto\n'):
        self.signing_parent()
        self.write('.gitattributes',attributes)
        self.parent=self.commit('existing attributes')

    def test_signed_record_may_append_only_the_signature_binary_rule(self):
        self.attributes_parent()
        def mutate():
            self.signed()();self.write('.gitattributes','* text=auto\n*.sig -text\n')
        source=self.record(mutate)
        self.assertEqual(m.checked_source_receipt(self.matrix(),source),(self.digest,self.parent))

    def test_signature_rule_without_signed_record_is_refused(self):
        self.attributes_parent()
        self.reject(lambda:self.write('.gitattributes','* text=auto\n*.sig -text\n'))

    def test_signature_rule_cannot_rewrite_attributes_add_rules_or_repeat(self):
        self.attributes_parent()
        for attributes in ('* -text\n*.sig -text\n','* text=auto\n*.sig -text\n*.py filter=custom\n',
                           '* text=auto\n*.sig -text\n*.sig -text\n'):
            with self.subTest(attributes=attributes):
                self.git('reset','--hard',self.parent)
                def mutate():
                    self.signed()();self.write('.gitattributes',attributes)
                self.reject(mutate)

    def test_signature_rule_already_present_cannot_be_appended_again(self):
        self.attributes_parent('* text=auto\n*.sig -text\n')
        def mutate():
            self.signed()();self.write('.gitattributes','* text=auto\n*.sig -text\n*.sig -text\n')
        self.reject(mutate)

    def test_exact_attribute_rule_does_not_bypass_signature_verification(self):
        self.attributes_parent()
        def mutate():
            self.signed(key=self.other)();self.write('.gitattributes','* text=auto\n*.sig -text\n')
        self.reject(mutate)

    def test_exact_source_signed_assets_are_verified(self):
        self.signing_parent();source=self.record(self.signed())
        assets=m.checked_signed_assets(source,Path(self.artifact),'0.9.1-alpha51-1')
        self.assertEqual(len(assets),3)

    def test_uncommitted_ignored_proof_is_not_uploaded(self):
        self.signing_parent();source=self.record(self.signed(ots=False))
        self.write('releases/ots/0.9.1-alpha51-1.ots',b'private untracked data')
        with self.assertRaisesRegex(ValueError,'PUBLICATION-SIGNED-ASSET-UNCOMMITTED'):
            m.checked_signed_assets(source,Path(self.artifact),'0.9.1-alpha51-1')

    def test_changed_signature_bytes_are_not_uploaded(self):
        self.signing_parent();source=self.record(self.signed())
        self.write('releases/'+self.artifact+'.sig',b'changed')
        with self.assertRaisesRegex(ValueError,'PUBLICATION-SIGNED-ASSET-MISMATCH'):
            m.checked_signed_assets(source,Path(self.artifact),'0.9.1-alpha51-1')

    def test_exact_ci_source_does_not_bypass_signature_verification(self):
        self.signing_parent();source=self.record(self.signed(key=self.other))
        with self.assertRaises(ValueError):
            m.checked_signed_assets(source,Path(self.artifact),'0.9.1-alpha51-1')

    def external_fixture(self,mutate=None):
        self.signing_parent();source=self.record()
        self.signed()()
        import ots
        entry=json.loads((self.root/'releases/CHAIN.jsonl').read_bytes().splitlines()[-1])['entry']
        proof=ots.DetachedTimestamp(hashlib.sha256(self.chain.canonical(entry)).digest())
        proof.root.add_attestation(ots.Attestation.pending('https://calendar.example.invalid'))
        self.write('releases/ots/0.9.1-alpha51-1.ots',proof.serialize())
        if mutate:mutate()
        signing=self.commit('later detached signature')
        return source,signing

    def external_assets(self,source,signing,directory):
        return m.external_signed_assets(source,self.parent,signing,self.root/'releases'/self.artifact,
                                        '0.9.1-alpha51-1',self.digest,Path(directory))

    def test_approved_external_signing_exports_only_bound_public_metadata(self):
        source,signing=self.external_fixture()
        with patch.dict(m.EXTERNAL_SIGNING_SOURCES,{signing:(source,self.parent)},clear=True),tempfile.TemporaryDirectory() as directory:
            assets=self.external_assets(source,signing,directory)
            self.assertEqual(set(assets),{self.artifact+'.sig','CHAIN.jsonl','0.9.1-alpha51-1.ots','1111111111111111.pub'})
            self.assertEqual(assets['1111111111111111.pub'].read_bytes(),self.git_blob(signing,m.SIGNING_KEYS+'/1111111111111111'))

    def git_blob(self,source,path):return m.git_blob(source,path)

    def test_unapproved_external_signing_snapshot_or_source_is_refused(self):
        source,signing=self.external_fixture()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'PUBLICATION-SIGNING-SOURCE-SCOPE'):
                self.external_assets(source,signing,directory)
            with patch.dict(m.EXTERNAL_SIGNING_SOURCES,{signing:(source,'f'*40)},clear=True):
                with self.assertRaisesRegex(ValueError,'PUBLICATION-SIGNING-SOURCE-SCOPE'):
                    self.external_assets(source,signing,directory)

    def test_external_signing_cannot_substitute_the_package(self):
        source,signing=self.external_fixture()
        self.write('releases/'+self.artifact,b'other package')
        with patch.dict(m.EXTERNAL_SIGNING_SOURCES,{signing:(source,self.parent)},clear=True),tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'PUBLICATION-SIGNING-PACKAGE-MISMATCH'):
                self.external_assets(source,signing,directory)

    def test_external_signing_refuses_unsigned_snapshot(self):
        self.signing_parent();source=self.record()
        with patch.dict(m.EXTERNAL_SIGNING_SOURCES,{source:(source,self.parent)},clear=True),tempfile.TemporaryDirectory() as directory:
            with self.assertRaises((ValueError,subprocess.CalledProcessError)):
                self.external_assets(source,source,directory)

    def test_external_chain_must_name_the_tested_source_or_its_verified_record(self):
        def mutate():
            path=self.root/'releases/CHAIN.jsonl'
            lines=path.read_bytes().splitlines();entry=json.loads(lines[-1])['entry'];entry['source_commit']='f'*40
            lines[-1]=self.chain.make_line(entry,self.key);path.write_bytes(b'\n'.join(lines)+b'\n')
        source,signing=self.external_fixture(mutate)
        with patch.dict(m.EXTERNAL_SIGNING_SOURCES,{signing:(source,self.parent)},clear=True),tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'PUBLICATION-SIGNING-PROVENANCE'):
                self.external_assets(source,signing,directory)

    def test_external_signing_with_substituted_public_key_is_refused(self):
        source,signing=self.external_fixture(lambda:self.write(m.SIGNING_KEYS+'/1111111111111111',self.other.public_file('wrong key')))
        with patch.dict(m.EXTERNAL_SIGNING_SOURCES,{signing:(source,self.parent)},clear=True),tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):self.external_assets(source,signing,directory)

    def test_external_signing_refuses_a_proof_of_a_different_head(self):
        import ots
        proof=ots.DetachedTimestamp(b'x'*32);proof.root.add_attestation(ots.Attestation.pending('https://calendar.example.invalid'))
        source,signing=self.external_fixture(lambda:self.write('releases/ots/0.9.1-alpha51-1.ots',proof.serialize()))
        with patch.dict(m.EXTERNAL_SIGNING_SOURCES,{signing:(source,self.parent)},clear=True),tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,'PUBLICATION-SIGNING-OTS-MISMATCH'):
                self.external_assets(source,signing,directory)

    def test_signature_by_untrusted_key_refused(self):
        self.signing_parent();self.reject(self.signed(key=self.other))

    def test_chain_entry_by_untrusted_key_refused(self):
        self.signing_parent();self.reject(self.signed(entry_key=self.other))

    def test_rewritten_history_refused(self):
        self.signing_parent()
        def rewrite(data):
            lines=data.split(b'\n')
            old=dict(self.entries[0],size=6);lines[0]=self.chain.make_line(old,self.key)
            entry=self.chain.next_entry([old],self.artifact,'0.9.1-alpha51','0.9.1-alpha51-1',self.digest,len(self.package),
                                        self.parent,'2026-11-03T01:00:00Z',self.key.key_id.hex())
            lines[1]=self.chain.make_line(entry,self.key)
            return b'\n'.join(lines)
        self.reject(self.signed(chain_text=rewrite))

    def test_chain_without_signature_refused(self):
        self.signing_parent()
        def mutate():
            self.signed()();(self.root/'releases'/(self.artifact+'.sig')).unlink()
        self.reject(mutate)

    def test_new_trusted_key_in_record_refused(self):
        self.signing_parent()
        def mutate():
            self.signed()();self.write(m.SIGNING_KEYS+'/2222222222222222',self.other.public_file('added'))
        self.reject(mutate)

    # Test lab keys (docs/architecture/SIGNING-LAB-2026-11-04.ru.md) can never reach a publication.
    def lab_key(self):
        import lab_mode
        return lab_mode,lab_mode.new_key(True,self.usign.SecretKey.generate)

    def test_package_signature_by_a_lab_key_refused_with_its_own_code(self):
        self.signing_parent();lab_mode,lab=self.lab_key()
        source=self.record(self.signed(key=lab))
        with self.assertRaisesRegex(ValueError,'PUBLICATION-LAB-KEY'):
            m.checked_source_receipt(self.matrix(),source)

    def test_chain_entry_by_a_lab_key_refused_with_its_own_code(self):
        self.signing_parent();lab_mode,lab=self.lab_key()
        source=self.record(self.signed(key=lab,entry_key=lab))
        with self.assertRaisesRegex(ValueError,'PUBLICATION-LAB-KEY'):
            m.checked_source_receipt(self.matrix(),source)

    def test_publication_refuses_to_start_in_a_lab_environment(self):
        import lab_mode
        with patch.dict(os.environ,{lab_mode.ENV_DIR:'somewhere'}),patch.object(sys,'argv',['publish-reviewed.py']):
            with self.assertRaisesRegex(ValueError,'PUBLICATION-LAB-ENV'):
                m.main()

class PublicationTimeouts(unittest.TestCase):
    def test_old_source_uses_reviewed_scanner_and_selected_repository(self):
        selected=Path('isolated-old-source')
        with patch.object(m,'ROOT',selected),patch.object(m.subprocess,'run') as run:
            run.return_value.returncode=0
            m.scan_secrets('--tree','a'*40)
        self.assertEqual(run.call_args.args[0],(sys.executable,str(Path(m.__file__).with_name('secret_scan.py')),
                                              '--repo',str(selected),'--tree','a'*40))

    def test_release_files_scanned_under_public_names_and_entire_source_still_scanned(self):
        root=Path(tempfile.gettempdir())/'private'/'release-stage'
        with patch.object(m,'scan_secrets') as scan:
            m.scan_publication('a'*40,[root/'note.md',root/'release.ipk'])
        self.assertEqual(scan.call_args_list[0].args,('--tree','a'*40))
        self.assertEqual(scan.call_args_list[1].args,('--root',str(root.resolve()),'--paths','note.md','release.ipk'))

    def test_gitea_timeout_is_thirty_minutes(self):
        with patch.object(m,'run') as run:
            m.save('feature/test')
        self.assertEqual(run.call_args.kwargs,{'timeout':1800})
    def test_other_commands_keep_three_minute_timeout(self):
        with patch.object(m.subprocess,'run') as run:
            run.return_value.stdout='ok\n';self.assertEqual(m.run('example'),'ok')
        self.assertEqual(run.call_args.kwargs['timeout'],180)


@contextlib.contextmanager
def cp1251_default():
    """Use the real locale hooks of each supported subprocess implementation."""
    with contextlib.ExitStack() as patches:
        patches.enter_context(patch.object(locale,'getpreferredencoding',return_value='cp1251'))
        if hasattr(locale,'getencoding'):
            patches.enter_context(patch.object(locale,'getencoding',return_value='cp1251'))
        if hasattr(subprocess,'_text_encoding'):
            patches.enter_context(patch.object(subprocess,'_text_encoding',return_value='cp1251'))
        else:
            # Python 3.9 passes None straight to the C TextIOWrapper, whose
            # locale lookup bypasses the Python locale functions. Keep its real
            # decoder, supplying our simulated locale only for omitted encoding;
            # explicit production UTF-8 must pass through unchanged.
            native_wrapper=io.TextIOWrapper
            def locale_wrapper(*args,**kwargs):
                args=list(args)
                if len(args)>1:
                    if args[1] is None:args[1]=locale.getpreferredencoding(False)
                elif kwargs.get('encoding') is None:
                    kwargs['encoding']=locale.getpreferredencoding(False)
                return native_wrapper(*args,**kwargs)
            patches.enter_context(patch.object(subprocess.io,'TextIOWrapper',side_effect=locale_wrapper))
        yield


class PublicationCodecs(unittest.TestCase):
    TEXT='Подпись — Ірина 😀 日本語'

    def test_real_default_subprocess_decoder_cannot_read_utf8_emoji(self):
        payload=json.dumps({'body':self.TEXT},ensure_ascii=False).encode('utf-8')
        child='import sys;sys.stdout.buffer.write('+repr(payload)+')'
        errors=[]
        # Windows decodes in a reader thread; POSIX raises from communicate().
        with cp1251_default(),patch.object(threading,'excepthook',side_effect=lambda args:errors.append(args.exc_value)):
            try:
                reply=subprocess.run([sys.executable,'-c',child],capture_output=True,text=True,timeout=30)
            except UnicodeDecodeError as error:
                errors.append(error)
            else:
                self.assertIsNone(reply.stdout)
        self.assertTrue(any(isinstance(error,UnicodeDecodeError) for error in errors),errors)

    def test_run_decodes_utf8_under_a_cp1251_default_locale(self):
        payload=json.dumps({'body':self.TEXT},ensure_ascii=False).encode('utf-8')
        # This is the same undefined cp1251 byte that broke the real gh reader.
        with self.assertRaises(UnicodeDecodeError):payload.decode('cp1251')
        child='import sys;sys.stdout.buffer.write('+repr(payload)+')'
        with cp1251_default():
            reply=m.capture_text(sys.executable,'-c',child)
            self.assertEqual(json.loads(reply.stdout),{'body':self.TEXT})
            self.assertEqual(reply.stderr,'')
            self.assertEqual(json.loads(m.run(sys.executable,'-c',child)),{'body':self.TEXT})

    def test_release_lookup_decodes_real_utf8_json_without_a_network_request(self):
        payload=json.dumps({'body':self.TEXT,'draft':False},ensure_ascii=False).encode('utf-8')
        real_run=subprocess.run
        def fake_gh(args,**kwargs):
            self.assertEqual(args[:2],('gh','api'))
            return real_run([sys.executable,'-c','import sys;sys.stdout.buffer.write('+repr(payload)+')'],**kwargs)
        with cp1251_default(),patch.object(m.subprocess,'run',side_effect=fake_gh):
            self.assertEqual(m.lookup_json('releases/tags/v2.1.0-alpha8'),{'body':self.TEXT,'draft':False})

    def test_scanner_child_and_reader_share_utf8_for_error_diagnostics(self):
        real_run=subprocess.run
        child='import sys;print('+repr(self.TEXT)+');print('+repr(self.TEXT)+',file=sys.stderr);sys.exit(1)'
        def fake_scanner(args,**kwargs):
            return real_run([sys.executable,'-c',child],**kwargs)
        with patch.dict(os.environ,{'PYTHONIOENCODING':'cp1251'}),cp1251_default(),patch.object(m.subprocess,'run',side_effect=fake_scanner),contextlib.redirect_stderr(io.StringIO()) as error:
            with self.assertRaisesRegex(ValueError,'PUBLICATION-SECRET-SCAN'):
                m.scan_secrets('--tree','a'*40)
        self.assertEqual(error.getvalue(),self.TEXT+'\n'+self.TEXT+'\n')

    def test_utf8_404_still_means_missing_and_other_errors_still_refuse(self):
        real_run=subprocess.run
        for status in ('404','500'):
            child='import sys;sys.stderr.buffer.write('+repr(('HTTP '+status+' '+self.TEXT).encode('utf-8'))+');sys.exit(1)'
            def fake_gh(args,**kwargs):return real_run([sys.executable,'-c',child],**kwargs)
            with cp1251_default(),patch.object(m.subprocess,'run',side_effect=fake_gh):
                if status=='404':self.assertIsNone(m.lookup_json('example'))
                else:
                    with self.assertRaisesRegex(RuntimeError,'PUBLICATION-REMOTE-LOOKUP-UNCONFIRMED'):m.lookup_json('example')

    def test_unavailable_reader_output_refuses_before_json_parsing(self):
        with patch.object(m.subprocess,'run') as run:
            run.return_value.stdout=None;run.return_value.stderr='';run.return_value.returncode=0
            with self.assertRaisesRegex(ValueError,'PUBLICATION-TOOL-OUTPUT-UNAVAILABLE'):
                m.lookup_json('example')

    def test_capture_text_refuses_either_missing_output_stream(self):
        for stdout,stderr in ((None,''),('',None)):
            with self.subTest(stdout=stdout,stderr=stderr),patch.object(m.subprocess,'run') as run:
                run.return_value.stdout=stdout;run.return_value.stderr=stderr
                with self.assertRaisesRegex(ValueError,'PUBLICATION-TOOL-OUTPUT-UNAVAILABLE'):
                    m.capture_text('offline-dummy')

    def test_git_blobs_remain_binary_and_are_never_text_decoded(self):
        binary=b'\xff\x98\x00\r\n'
        with patch.object(m.subprocess,'run') as run:
            run.return_value.stdout=binary
            self.assertEqual(m.git_blob('a'*40,'release.ipk'),binary)
        self.assertNotIn('encoding',run.call_args.kwargs)
        self.assertNotIn('text',run.call_args.kwargs)


if __name__=='__main__':unittest.main()
