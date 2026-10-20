"""Exercise recovery on disposable repositories; never touch the real D: backup."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec=importlib.util.spec_from_file_location('save_recovery',Path(__file__).resolve().parents[1]/'scripts/save-recovery.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


@unittest.skipUnless(shutil.which('git'),'Recovery integration requires the Git executable')
class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'source';self.root.mkdir()
        self.destination=Path(self.temp.name)/'backup'
        self.addCleanup(patch.stopall);patch.object(module,'ROOT',self.root).start()
        self.run_git('init','--initial-branch=main')
        self.run_git('config','user.email','qa@example.invalid');self.run_git('config','user.name','QA')
        for name,path in module.HANDOFF.items():
            file=self.root/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(('committed '+name).encode())
        (self.root/'.gitignore').write_text('ignored-secret.txt\n',encoding='utf-8')
        (self.root/'ignored-secret.txt').write_text('DO-NOT-COPY',encoding='utf-8')
        self.run_git('add','.');self.run_git('commit','-m','test checkpoint')

    def run_git(self,*args):
        return subprocess.check_output(['git','-c','core.hooksPath=/dev/null','-c','commit.gpgsign=false',*args],cwd=self.root,stderr=subprocess.PIPE,text=True,timeout=120).strip()

    def save(self):
        with contextlib.redirect_stdout(io.StringIO()):return module.main(self.destination)

    def test_stored_bundle_restores_and_manifest_covers_all_payload(self):
        receipt=self.save();target=Path(receipt['archive'])
        self.assertEqual(receipt['head'],self.run_git('rev-parse','HEAD'))
        self.assertEqual(receipt['sha256'],hashlib.sha256(target.read_bytes()).hexdigest())
        self.assertTrue(receipt['bundle_restore_tree_verified']);self.assertTrue(receipt['bundle_fsck_verified'])
        self.assertEqual(json.loads((self.destination/'CURRENT.local.json').read_text()),receipt)
        with zipfile.ZipFile(target) as archive:
            manifest=json.loads(archive.read('MANIFEST.json'))
            self.assertEqual(set(manifest),set(archive.namelist())-{'MANIFEST.json'})
            self.assertNotIn(b'DO-NOT-COPY',archive.read('source.tar'))
            self.assertEqual(archive.read('TODO.md'),b'committed TODO.md')

    def test_live_handoff_edits_cannot_mix_with_captured_commit(self):
        original=module.git
        def concurrent_edit(*args):
            result=original(*args)
            if args[:2]==('bundle','verify'):
                (self.root/module.HANDOFF['TODO.md']).write_text('UNCOMMITTED CHANGE',encoding='utf-8')
            return result
        with patch.object(module,'git',side_effect=concurrent_edit):receipt=self.save()
        with zipfile.ZipFile(receipt['archive']) as archive:
            self.assertEqual(archive.read('TODO.md'),b'committed TODO.md')

    def test_dirty_or_detached_source_refuses_without_publishing(self):
        (self.root/'dirty.txt').write_text('dirty',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'CLEAN-COMMIT'):self.save()
        (self.root/'dirty.txt').unlink();self.run_git('checkout','--detach')
        with self.assertRaisesRegex(ValueError,'REQUIRES-BRANCH'):self.save()
        self.assertFalse(self.destination.exists())

    def test_source_destination_refuses(self):
        for destination in (self.root,self.root/'backups'):
            with self.subTest(destination=str(destination)),self.assertRaisesRegex(ValueError,'OUTSIDE-SOURCE'):
                module.main(destination)

    def test_branch_motion_refuses_without_current_receipt(self):
        original=module.git
        def concurrent_commit(*args):
            if args[:2]==('bundle','create'):
                self.run_git('commit','--allow-empty','-m','concurrent commit')
            return original(*args)
        with patch.object(module,'git',side_effect=concurrent_commit):
            with self.assertRaisesRegex(ValueError,'BRANCH-MOVED'):self.save()
        self.assertFalse((self.destination/'CURRENT.local.json').exists())

    def test_corrupted_payload_never_publishes_current_receipt(self):
        original=module.verify_archive
        def corrupt(target,*args):
            with zipfile.ZipFile(target) as archive:payload={name:archive.read(name) for name in archive.namelist()}
            payload['TODO.md']=b'changed after writing'
            with zipfile.ZipFile(target,'w') as archive:
                for name,data in payload.items():archive.writestr(name,data)
            original(target,*args)
        with patch.object(module,'verify_archive',side_effect=corrupt):
            with self.assertRaisesRegex(ValueError,'HASH-MISMATCH'):self.save()
        self.assertFalse((self.destination/'CURRENT.local.json').exists())

    def test_hashed_but_unrestorable_bundle_refuses(self):
        original=module.verify_archive
        def corrupt(target,*args):
            with zipfile.ZipFile(target) as archive:payload={name:archive.read(name) for name in archive.namelist()}
            payload['checkpoint.bundle']=b'not a bundle'
            manifest=json.loads(payload['MANIFEST.json'])
            manifest['checkpoint.bundle']=hashlib.sha256(payload['checkpoint.bundle']).hexdigest()
            payload['MANIFEST.json']=json.dumps(manifest).encode()
            with zipfile.ZipFile(target,'w') as archive:
                for name,data in payload.items():archive.writestr(name,data)
            original(target,*args)
        with patch.object(module,'verify_archive',side_effect=corrupt):
            with self.assertRaises(subprocess.CalledProcessError):self.save()
        self.assertFalse((self.destination/'CURRENT.local.json').exists())

    def test_moved_head_after_verification_does_not_replace_current(self):
        original=module.verify_archive
        self.destination.mkdir();current=self.destination/'CURRENT.local.json';current.write_bytes(b'previous receipt')
        def move_head(*args):
            original(*args);self.run_git('commit','--allow-empty','-m','concurrent late commit')
        with patch.object(module,'verify_archive',side_effect=move_head):
            with self.assertRaisesRegex(ValueError,'SOURCE-MOVED'):self.save()
        self.assertEqual(current.read_bytes(),b'previous receipt')

    def test_archives_symlink_into_source_refuses(self):
        self.destination.mkdir()
        try:(self.destination/'archives').symlink_to(self.root,target_is_directory=True)
        except OSError:self.skipTest('Directory symlinks unavailable on this test host')
        with self.assertRaisesRegex(ValueError,'OUTSIDE-SOURCE'):self.save()
