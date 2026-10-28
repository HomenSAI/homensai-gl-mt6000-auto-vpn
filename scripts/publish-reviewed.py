"""Explicit reviewed snapshot publication. No force, mirror, bulk tags or history merge."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import os
import sys
import tempfile

REPOSITORY='HomenSAI/homensai-gl-mt6000-auto-vpn'
URL='https://github.com/'+REPOSITORY+'.git'
ROOT=Path(__file__).resolve().parents[1]


def run(*args,input=None):
    reply=subprocess.run(args,cwd=ROOT,input=input,capture_output=True,text=True,check=True,timeout=180)
    return reply.stdout.strip()


def checked_receipt(value,source):
    if not isinstance(value,list) or len(value)!=2:raise ValueError('PUBLICATION-CI-MATRIX')
    for row in value:
        if not isinstance(row,dict):raise ValueError('PUBLICATION-CI-ROW')
        if row.get('result')!='PASS' or row.get('source')!=source:raise ValueError('PUBLICATION-CI-SOURCE')
        if not re.fullmatch('[a-f0-9]{64}',row.get('sha256','')):raise ValueError('PUBLICATION-CI-HASH')
    if value[0]['sha256']!=value[1]['sha256']:raise ValueError('PUBLICATION-CI-PACKAGE-MISMATCH')
    if {row.get('runtime_only') for row in value}!={True,False}:raise ValueError('PUBLICATION-CI-RUNTIMES')
    return value[0]['sha256']


def save(branch):
    run('C:/Program Files/PowerShell/7/pwsh.exe','-NoProfile','-File',str(ROOT/'scripts/save-gitea.ps1'),'-Branch',branch)


def checked_manifest(data,package_hash,release=None):
    app=data.get('application',{}) if isinstance(data,dict) else {}
    if not isinstance(app,dict) or app.get('sha256')!=package_hash or package_hash=='0'*64:
        raise ValueError('PUBLICATION-MANIFEST-PACKAGE-MISMATCH')
    if release and app.get('release_tag')!=release:raise ValueError('PUBLICATION-MANIFEST-TAG-MISMATCH')
    return app


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--receipt',type=Path,required=True)
    p.add_argument('--resume',type=Path);p.add_argument('--publish',action='store_true');p.add_argument('--release');p.add_argument('--artifact',type=Path);p.add_argument('--notes',type=Path)
    a=p.parse_args()
    if not re.fullmatch('[a-f0-9]{40}',a.source):p.error('SOURCE-SHA')
    if run('git','status','--porcelain'):raise ValueError('PUBLICATION-DIRTY')
    if run('git','rev-parse','HEAD')!=a.source:raise ValueError('PUBLICATION-NONCURRENT-SOURCE')
    package_hash=checked_receipt(json.loads(a.receipt.read_text(encoding='utf-8-sig')),a.source)
    checked_manifest(json.loads((ROOT/'VERSION.json').read_text(encoding='utf-8-sig')),package_hash,a.release)
    if a.release:
        # Alpha, beta and release-candidate tags; a plain version tag (final release) stays a separate owner decision.
        if not a.publish or not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+-(?:alpha|beta|rc)[0-9]+',a.release):raise ValueError('RELEASE-SCOPE')
        if not a.artifact or not a.notes or not a.notes.is_file() or hashlib.sha256(a.artifact.read_bytes()).hexdigest()!=package_hash:raise ValueError('RELEASE-ARTIFACT-HASH')
        probe=subprocess.run(['gh','api','repos/'+REPOSITORY+'/git/ref/tags/'+a.release],cwd=ROOT,capture_output=True,text=True,timeout=60)
        if probe.returncode==0 and not a.resume:raise ValueError('RELEASE-TAG-EXISTS')
        if probe.returncode!=0 and '404' not in probe.stderr:raise ValueError('RELEASE-TAG-LOOKUP-UNCONFIRMED')
    private=ROOT/'.git/handoff';private.mkdir(parents=True,exist_ok=True)
    tree=run('git','rev-parse',a.source+'^{tree}')
    if a.resume:
        receipt=a.resume.resolve()
        if receipt.parent!=private.resolve() or receipt.is_symlink() or not receipt.name.startswith('publication-'):raise ValueError('PUBLICATION-RESUME-PATH')
        ledger=json.loads(receipt.read_text(encoding='utf-8'))
        if any(ledger.get(key)!=value for key,value in [('source',a.source),('tree',tree),('package_sha256',package_hash),('planned_release',a.release)]):raise ValueError('PUBLICATION-RESUME-IDENTITY')
        public=ledger['public']
        if run('git','rev-parse',public+'^{tree}')!=tree:raise ValueError('PUBLICATION-RESUME-TREE')
    else:
        canonical=run('git','branch','--show-current');save(canonical)
        parent=run('gh','api','repos/'+REPOSITORY+'/git/ref/heads/main','--jq','.object.sha')
        run('git','-c','gc.auto=0','fetch','--no-tags',URL,'refs/heads/main:refs/remotes/origin/main')
        if run('git','rev-parse','refs/remotes/origin/main')!=parent:raise ValueError('PUBLICATION-PARENT-MOVED')
        public=run('git','commit-tree',tree,'-p',parent,input='Reviewed local snapshot '+a.source+'\n\nDual-runtime CI package SHA256 '+package_hash+'\n')
        branch='feature/github-publication-'+public[:12]
        run('git','update-ref','refs/heads/'+branch,public,'0'*40);save(branch)
        ledger={'source':a.source,'public':public,'parent':parent,'tree':tree,'package_sha256':package_hash,'gitea_saved':True,'github_published':False,'planned_release':a.release,'notes_sha256':hashlib.sha256(a.notes.read_bytes()).hexdigest() if a.release else None}
        receipt=private/('publication-'+public+'.json')
    def persist(value):
        pending=receipt.with_suffix('.pending')
        with pending.open('w',encoding='utf-8') as stream:
            json.dump(value,stream,indent=2);stream.flush();os.fsync(stream.fileno())
        os.replace(pending,receipt)
    persist(ledger)
    class Remote:
        def main(self):return run('gh','api','repos/'+REPOSITORY+'/git/ref/heads/main','--jq','.object.sha')
        def push(self):run('git','-c','credential.helper=','-c','credential.helper=!gh auth git-credential','-c','push.followTags=false','push',URL,'refs/heads/feature/github-publication-'+public[:12]+':refs/heads/main')
        def lookup(self,endpoint):
            reply=subprocess.run(['gh','api','repos/'+REPOSITORY+'/'+endpoint],cwd=ROOT,capture_output=True,text=True,timeout=60)
            if reply.returncode==0:return json.loads(reply.stdout)
            if '404' in reply.stderr:return None
            raise RuntimeError('PUBLICATION-REMOTE-LOOKUP-UNCONFIRMED')
        def tag(self):
            row=self.lookup('git/ref/tags/'+a.release)
            return None if row is None else row['object']['sha']
        def create_tag(self):run('gh','api','repos/'+REPOSITORY+'/git/refs','-f','ref=refs/tags/'+a.release,'-f','sha='+public)
        def release(self):return self.lookup('releases/tags/'+a.release)
        def create_release(self):run('gh','release','create',a.release,'--repo',REPOSITORY,'--verify-tag','--prerelease','--notes-file',str(a.notes))
        def expected_assets(self):return [(a.artifact.name,package_hash),(a.artifact.name+'.sha256',checksum_sha)]
        def asset_hash(self,name):
            release=self.release()
            if release is None or not any(item.get('name')==name for item in release.get('assets',[])):return None
            with tempfile.TemporaryDirectory(prefix='download-',dir=private) as directory:
                run('gh','release','download',a.release,'--repo',REPOSITORY,'--pattern',name,'--dir',directory)
                return hashlib.sha256((Path(directory)/name).read_bytes()).hexdigest()
        def upload(self,name):
            asset=a.artifact if name==a.artifact.name else checksum_path
            run('gh','release','upload',a.release,str(asset),'--repo',REPOSITORY)
    if a.release:
        checksum_dir=private/('checksum-'+public);checksum_dir.mkdir(exist_ok=True)
        checksum_path=checksum_dir/(a.artifact.name+'.sha256')
        checksum_path.write_text(package_hash+'  '+a.artifact.name+'\n',encoding='utf-8')
        checksum_sha=hashlib.sha256(checksum_path.read_bytes()).hexdigest()
        notes_sha=hashlib.sha256(a.notes.read_bytes()).hexdigest()
        if a.resume and ledger.get('notes_sha256')!=notes_sha:raise ValueError('RELEASE-NOTES-MISMATCH')
        ledger['notes_sha256']=notes_sha;persist(ledger)
    if a.publish:
        sys.path.insert(0,str(ROOT/'scripts'))
        from publication_resume import finish
        finish(ledger,Remote(),persist)
    print(json.dumps(ledger,sort_keys=True))

if __name__=='__main__':main()
