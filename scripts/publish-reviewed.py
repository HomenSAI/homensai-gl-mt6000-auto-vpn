"""Explicit reviewed snapshot publication. No force, mirror, bulk tags or history merge."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import os

REPOSITORY='HomenSAI/homensai-gl-mt6000-auto-vpn'
URL='https://github.com/'+REPOSITORY+'.git'
ROOT=Path(__file__).resolve().parents[1]


def run(*args,input=None):
    reply=subprocess.run(args,cwd=ROOT,input=input,capture_output=True,text=True,check=True)
    return reply.stdout.strip()


def checked_receipt(value,source):
    if not isinstance(value,list) or len(value)!=2:raise ValueError('PUBLICATION-CI-MATRIX')
    for row in value:
        if row.get('result')!='PASS' or row.get('source')!=source:raise ValueError('PUBLICATION-CI-SOURCE')
        if not re.fullmatch('[a-f0-9]{64}',row.get('sha256','')):raise ValueError('PUBLICATION-CI-HASH')
    if value[0]['sha256']!=value[1]['sha256']:raise ValueError('PUBLICATION-CI-PACKAGE-MISMATCH')
    if {row.get('runtime_only') for row in value}!={True,False}:raise ValueError('PUBLICATION-CI-RUNTIMES')
    return value[0]['sha256']


def save(branch):
    run('C:/Program Files/PowerShell/7/pwsh.exe','-NoProfile','-File',str(ROOT/'scripts/save-gitea.ps1'),'-Branch',branch)


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--receipt',type=Path,required=True)
    p.add_argument('--publish',action='store_true');p.add_argument('--release');p.add_argument('--artifact',type=Path);p.add_argument('--notes',type=Path)
    a=p.parse_args()
    if not re.fullmatch('[a-f0-9]{40}',a.source):p.error('SOURCE-SHA')
    if run('git','status','--porcelain'):raise ValueError('PUBLICATION-DIRTY')
    if run('git','rev-parse','HEAD')!=a.source:raise ValueError('PUBLICATION-NONCURRENT-SOURCE')
    package_hash=checked_receipt(json.loads(a.receipt.read_text(encoding='utf-8-sig')),a.source)
    if a.release:
        if not a.publish or not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+-alpha[0-9]+',a.release):raise ValueError('RELEASE-SCOPE')
        if not a.artifact or not a.notes or not a.notes.is_file() or hashlib.sha256(a.artifact.read_bytes()).hexdigest()!=package_hash:raise ValueError('RELEASE-ARTIFACT-HASH')
        probe=subprocess.run(['gh','api','repos/'+REPOSITORY+'/git/ref/tags/'+a.release],cwd=ROOT,capture_output=True,text=True)
        if probe.returncode==0:raise ValueError('RELEASE-TAG-EXISTS')
        if '404' not in probe.stderr:raise ValueError('RELEASE-TAG-LOOKUP-UNCONFIRMED')
    canonical=run('git','branch','--show-current');save(canonical)
    parent=run('gh','api','repos/'+REPOSITORY+'/git/ref/heads/main','--jq','.object.sha')
    run('git','-c','gc.auto=0','fetch','--no-tags',URL,'refs/heads/main:refs/remotes/origin/main')
    if run('git','rev-parse','refs/remotes/origin/main')!=parent:raise ValueError('PUBLICATION-PARENT-MOVED')
    tree=run('git','rev-parse',a.source+'^{tree}')
    # No canonical parents: only the existing public parent and reviewed tree.
    public=run('git','commit-tree',tree,'-p',parent,input='Reviewed local snapshot '+a.source+'\n\nDual-runtime CI package SHA256 '+package_hash+'\n')
    branch='feature/github-publication-'+public[:12]
    run('git','update-ref','refs/heads/'+branch,public,'0'*40);save(branch)
    if run('git','rev-parse',public+'^{tree}')!=tree:raise ValueError('PUBLICATION-TREE')
    ledger={'source':a.source,'public':public,'parent':parent,'tree':tree,'package_sha256':package_hash,'gitea_saved':True,'github_published':False}
    private=ROOT/'.git/handoff';private.mkdir(parents=True,exist_ok=True)
    receipt=private/('publication-'+public+'.json');receipt.write_text(json.dumps(ledger,indent=2),encoding='utf-8')
    if a.publish:
        if run('gh','api','repos/'+REPOSITORY+'/git/ref/heads/main','--jq','.object.sha')!=parent:raise ValueError('PUBLICATION-PARENT-MOVED')
        run('git','-c','credential.helper=','-c','credential.helper=!gh auth git-credential','-c','push.followTags=false','push',URL,'refs/heads/'+branch+':refs/heads/main')
        if run('gh','api','repos/'+REPOSITORY+'/git/ref/heads/main','--jq','.object.sha')!=public:raise ValueError('PUBLICATION-MAIN-UNCONFIRMED')
        ledger['github_published']=True;receipt.write_text(json.dumps(ledger,indent=2),encoding='utf-8')
    if a.release:
        if not a.publish or not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+-alpha[0-9]+',a.release):raise ValueError('RELEASE-SCOPE')
        if not a.artifact or not a.notes or hashlib.sha256(a.artifact.read_bytes()).hexdigest()!=package_hash:raise ValueError('RELEASE-ARTIFACT-HASH')
        # Existing tags are refused, never replaced. GitHub 422 preserves the old tag.
        run('gh','api','repos/'+REPOSITORY+'/git/refs','-f','ref=refs/tags/'+a.release,'-f','sha='+public)
        run('gh','release','create',a.release,str(a.artifact),'--repo',REPOSITORY,'--verify-tag','--prerelease','--notes-file',str(a.notes))
        downloaded=private/('download-'+public);downloaded.mkdir(exist_ok=False)
        run('gh','release','download',a.release,'--repo',REPOSITORY,'--pattern',a.artifact.name,'--dir',str(downloaded))
        if hashlib.sha256((downloaded/a.artifact.name).read_bytes()).hexdigest()!=package_hash:raise ValueError('RELEASE-DOWNLOAD-HASH')
        ledger['release_download_verified']=True
        ledger['release']=a.release;receipt.write_text(json.dumps(ledger,indent=2),encoding='utf-8')
    print(json.dumps(ledger,sort_keys=True))

if __name__=='__main__':main()
