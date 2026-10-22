import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('gitflow',Path(__file__).resolve().parents[1]/'gitflow.py')
flow=importlib.util.module_from_spec(spec);spec.loader.exec_module(flow)

def git(path,*args):return subprocess.check_output(['git','-C',str(path),*args],stderr=subprocess.DEVNULL).decode().strip()

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='homensai-gitflow-test-');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.primary=self.root/'primary.git';self.secondary=self.root/'secondary.git';self.work=self.root/'work'
        for path in (self.primary,self.secondary):subprocess.run(['git','init','--bare','-q',str(path)],check=True)
        subprocess.run(['git','init','-q','-b','main',str(self.work)],check=True)
        git(self.work,'config','user.name','Workflow test');git(self.work,'config','user.email','workflow@localhost')
        self.config={'primary':{'remote':'origin','urls':[str(self.primary)]},'secondary':{'remote':'github','urls':[str(self.secondary)]},'checks':[[sys.executable,'-c','pass']]}
        (self.work/'.gitflow.json').write_text(json.dumps(self.config));(self.work/'seed.txt').write_text('seed\n')
        git(self.work,'add','.gitflow.json','seed.txt');git(self.work,'commit','-qm','initial')
        git(self.work,'remote','add','origin',str(self.primary));git(self.work,'remote','add','github',str(self.secondary))
        git(self.work,'push','-q','origin','main');git(self.work,'push','-q','github','main');git(self.work,'checkout','-qb','feature/one')
        self.repo=flow.Repo(self.work)
    def change(self,name='feature.txt'):
        (self.work/name).write_text('feature\n');return name
    def claim(self,paths=None,agent='codex',branch=None):return self.repo.coordinate(agent,'ACTIVE','local test',paths or ['feature.txt'],branch)
    def test_finish_commits_once_and_saves_only_primary(self):
        self.claim();self.change();before=git(self.secondary,'rev-parse','refs/heads/main')
        result=self.repo.finish('add feature',['feature.txt'],'codex');head=git(self.work,'rev-parse','HEAD')
        self.assertTrue(result['created_commit']);self.assertEqual(git(self.primary,'rev-parse','refs/heads/feature/one'),head)
        self.assertEqual(git(self.secondary,'rev-parse','refs/heads/main'),before)
        self.claim();result=self.repo.finish('no content change',['feature.txt'],'codex')
        self.assertFalse(result['created_commit']);self.assertEqual(git(self.work,'rev-parse','HEAD'),head)
    def test_secondary_failure_does_not_block_primary_save(self):
        git(self.work,'remote','set-url','github',str(self.root/'offline.git'));self.config['secondary']['urls']=[str(self.root/'offline.git')]
        (self.work/'.gitflow.json').write_text(json.dumps(self.config));self.repo=flow.Repo(self.work)
        self.claim();self.change();result=self.repo.finish('work without GitHub',['feature.txt'],'codex');self.assertEqual(result['result'],'SAVED')
        self.assertEqual(self.repo.sync_plan()['result'],'SECONDARY-OFFLINE')
    def test_failed_checks_do_not_commit_or_push(self):
        self.claim();self.change();self.repo.config['checks']=[[sys.executable,'-c','raise SystemExit(1)']];before=git(self.work,'rev-parse','HEAD')
        with self.assertRaisesRegex(flow.FlowError,'CHECK-FAILED'):self.repo.finish('bad',['feature.txt'],'codex')
        self.assertEqual(git(self.work,'rev-parse','HEAD'),before)
        refs=self.repo.remote_refs(str(self.primary));self.assertNotIn('refs/heads/feature/one',refs)
    def test_checkpoint_saves_unverified_work_without_claiming_pass(self):
        self.claim();self.change();self.repo.config['checks']=[[sys.executable,'-c','raise SystemExit(1)']]
        result=self.repo.finish('unfinished',['feature.txt'],'codex',checkpoint=True)
        self.assertFalse(result['verified']);self.assertEqual(git(self.work,'log','-1','--format=%s'),'WIP: unfinished')
        self.assertEqual(self.repo.coord_status()['agents'][0]['status'],'PAUSED')
    def test_primary_outage_preserves_local_commit_and_receipt(self):
        self.claim();self.change();before=git(self.work,'rev-parse','HEAD')
        original=self.repo.remote_refs
        def offline(url):raise flow.FlowError('REMOTE-UNAVAILABLE')
        with patch.object(self.repo,'require_claim'),patch.object(self.repo,'remote_refs',side_effect=offline):
            with self.assertRaisesRegex(flow.FlowError,'REMOTE-UNAVAILABLE'):self.repo.finish('local recovery',['feature.txt'],'codex')
        self.assertNotEqual(git(self.work,'rev-parse','HEAD'),before)
        receipts=[json.loads(p.read_text()) for p in self.repo.state.glob('primary-*.json')]
        self.assertTrue(any(r['result']=='LOCAL_ONLY' and r['head']==git(self.work,'rev-parse','HEAD') for r in receipts))
    def test_ssh_transport_is_inherited_by_temporary_git_commands(self):
        git(self.work,'config','core.sshCommand','ssh -o BatchMode=yes');repo=flow.Repo(self.work)
        with patch.object(flow,'execute') as command:
            repo.run(['git','version'],env={'GIT_INDEX_FILE':'test-index'})
        self.assertEqual(command.call_args.kwargs['env']['GIT_SSH_COMMAND'],'ssh -o BatchMode=yes')
        self.assertEqual(command.call_args.kwargs['env']['GIT_INDEX_FILE'],'test-index')
    def test_external_reviewed_config_bootstraps_older_main_without_dirty_files(self):
        config=self.root/'reviewed.json';config.write_text(json.dumps(self.config))
        (self.work/'.gitflow.json').unlink()
        repo=flow.Repo(self.work,config)
        self.assertEqual(repo.remote('primary')[1],str(self.primary))
        self.assertFalse((self.work/'.gitflow.json').exists())
    def test_main_direct_commit_is_protected(self):
        git(self.work,'checkout','-q','main');self.change()
        with self.assertRaisesRegex(flow.FlowError,'MAIN-DIRECT'):self.repo.finish('unsafe',['feature.txt'],'codex')
    def test_foreign_staged_changes_are_preserved_and_refused(self):
        self.claim();self.change();self.change('other.txt');git(self.work,'add','other.txt')
        with self.assertRaisesRegex(flow.FlowError,'FOREIGN-STAGED'):self.repo.finish('feature',['feature.txt'],'codex')
        self.assertEqual(git(self.work,'diff','--cached','--name-only'),'other.txt')
    def test_secret_detection_never_prints_the_secret(self):
        self.claim();token='123456789:'+('a'*40);(self.work/'feature.txt').write_text(token)
        with self.assertRaisesRegex(flow.FlowError,'SECRET-PATTERN'):self.repo.finish('feature',['feature.txt'],'codex')
    def test_coord_claim_visible_to_another_clone_without_merging(self):
        self.claim();clone=self.root/'second';subprocess.run(['git','clone','-q',str(self.primary),str(clone)],check=True,stderr=subprocess.DEVNULL)
        # Remote HEAD defaults may not be main; select it explicitly.
        git(clone,'checkout','-q','main');git(clone,'remote','add','github',str(self.secondary));other=flow.Repo(clone)
        state=other.coord_status()['agents'];self.assertEqual(state[0]['agent'],'codex');self.assertTrue(state[0]['lease_live'])
        with self.assertRaisesRegex(flow.FlowError,'COORD-PATH-BUSY'):other.coordinate('claude','ACTIVE','overlap',['feature.txt'],'feature/two')
    def test_same_branch_cannot_be_claimed_by_two_agents(self):
        self.claim()
        with self.assertRaisesRegex(flow.FlowError,'COORD-BRANCH-BUSY'):self.repo.coordinate('claude','ACTIVE','different file',['other.txt'])
    def test_expired_claim_does_not_lock_forever(self):
        with patch.object(flow.time,'time',return_value=1000):self.claim()
        with patch.object(flow.time,'time',return_value=5000):self.repo.coordinate('claude','ACTIVE','after expiry',['feature.txt'],'feature/two')
    def test_sync_plan_never_pushes(self):
        self.change();git(self.work,'add','feature.txt');git(self.work,'commit','-qm','feature');self.repo.save_primary()
        before=self.repo.remote_refs(str(self.secondary));plan=self.repo.sync_plan()
        self.assertEqual(plan['result'],'READY');self.assertFalse(plan['push_performed']);self.assertEqual(self.repo.remote_refs(str(self.secondary)),before)
    def test_secondary_publish_requires_private_approval(self):
        with self.assertRaisesRegex(flow.FlowError,'SECONDARY-APPROVAL-REQUIRED'):self.repo.sync_plan(publish=True)
    def test_approved_sync_preserves_full_commit_ids_and_tags(self):
        self.change();git(self.work,'add','feature.txt');git(self.work,'commit','-qm','feature');self.repo.save_primary()
        git(self.work,'tag','v0.1.0-test');git(self.work,'push','-q','origin','refs/tags/v0.1.0-test')
        approval=self.root/'approval.json';approval.write_text(json.dumps({'allow_publish':True,'primary_url':str(self.primary),'secondary_url':str(self.secondary),'expires':time.time()+60}))
        result=self.repo.sync_plan(True,approval);self.assertEqual(result['result'],'SYNCED')
        self.assertEqual(git(self.secondary,'rev-parse','refs/heads/feature/one'),git(self.work,'rev-parse','HEAD'))
        self.assertEqual(git(self.secondary,'rev-parse','refs/tags/v0.1.0-test'),git(self.work,'rev-parse','refs/tags/v0.1.0-test'))
        self.assertNotIn('refs/heads/coord/agents',self.repo.remote_refs(str(self.secondary)))
    def test_divergence_or_tag_collision_stops_entire_sync(self):
        self.change();git(self.work,'add','feature.txt');git(self.work,'commit','-qm','feature');self.repo.save_primary()
        git(self.work,'tag','v0.1.0-test');git(self.work,'push','-q','origin','refs/tags/v0.1.0-test')
        git(self.secondary,'tag','v0.1.0-test','main');before=self.repo.remote_refs(str(self.secondary))
        result=self.repo.sync_plan();self.assertEqual(result['result'],'BLOCKED');self.assertEqual(result['problems'][0]['code'],'TAG-COLLISION')
        self.assertEqual(self.repo.remote_refs(str(self.secondary)),before)
    def test_safe_fast_forward_merge_checks_exact_saved_commit(self):
        self.claim();self.change();self.repo.finish('feature',['feature.txt'],'codex');target=git(self.work,'rev-parse','HEAD')
        git(self.work,'checkout','-q','main');self.claim(branch='main');result=self.repo.merge('feature/one','codex')
        self.assertEqual(result['head'],target);self.assertEqual(git(self.primary,'rev-parse','main'),target)
    def test_changed_remote_identity_is_refused(self):
        git(self.work,'remote','set-url','origin',str(self.secondary))
        with self.assertRaisesRegex(flow.FlowError,'REMOTE-IDENTITY-MISMATCH'):self.repo.save_primary()
    def test_credential_url_and_path_traversal_rejected(self):
        with self.assertRaisesRegex(flow.FlowError,'CREDENTIALS'):flow.safe_url('https://user:secret@example.invalid/project.git')
        for path in ('../outside','.git/config','C:/secret','/absolute'):
            with self.assertRaises(flow.FlowError):flow.safe_path(path)

if __name__=='__main__':unittest.main()
