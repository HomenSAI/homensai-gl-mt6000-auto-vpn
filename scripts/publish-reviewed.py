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
sys.path.insert(0,str(ROOT/'scripts/signing'))
import lab_mode  # noqa: E402


def capture_text(*args,input=None,timeout=180,check=False,env=None):
    """Git, gh and PowerShell 7 emit UTF-8; never use the Windows locale codec."""
    reply=subprocess.run(args,cwd=ROOT,input=input,capture_output=True,text=True,
                         encoding='utf-8',errors='strict',check=check,timeout=timeout,env=env)
    if reply.stdout is None or reply.stderr is None:
        raise ValueError('PUBLICATION-TOOL-OUTPUT-UNAVAILABLE')
    return reply


def run(*args,input=None,timeout=180):
    reply=capture_text(*args,input=input,check=True,timeout=timeout)
    return reply.stdout.strip()


def lookup_json(endpoint):
    reply=capture_text('gh','api','repos/'+REPOSITORY+'/'+endpoint,timeout=60)
    if reply.returncode==0:return json.loads(reply.stdout)
    if '404' in reply.stderr:return None
    raise RuntimeError('PUBLICATION-REMOTE-LOOKUP-UNCONFIRMED')


def checked_receipt(value,source):
    if not isinstance(value,list) or len(value)!=2:raise ValueError('PUBLICATION-CI-MATRIX')
    for row in value:
        if not isinstance(row,dict):raise ValueError('PUBLICATION-CI-ROW')
        if row.get('result')!='PASS' or row.get('source')!=source:raise ValueError('PUBLICATION-CI-SOURCE')
        if not re.fullmatch('[a-f0-9]{64}',row.get('sha256','')):raise ValueError('PUBLICATION-CI-HASH')
        if type(row.get('runtime_only')) is not bool:raise ValueError('PUBLICATION-CI-RUNTIMES')
    if value[0]['sha256']!=value[1]['sha256']:raise ValueError('PUBLICATION-CI-PACKAGE-MISMATCH')
    if {row.get('runtime_only') for row in value}!={True,False}:raise ValueError('PUBLICATION-CI-RUNTIMES')
    for row in value:
        if row.get('runtime_only') is False:
            count=row.get('lua_tests')
            if row.get('lua_available') is not True or type(count) is not int or count<=0:
                raise ValueError('PUBLICATION-CI-LUA')
    return value[0]['sha256']


def scan_secrets(*args, repo=None):
    """Run the offline secret scanner (values are never printed); any finding or error refuses the publication."""
    # An old reviewed source may predate the scanner; execute this publisher's
    # reviewed scanner, while Git reads still target the selected source repo.
    scanner=Path(__file__).resolve().with_name('secret_scan.py')
    reply = capture_text(sys.executable,str(scanner),'--repo',str(ROOT if repo is None else repo),*args,
                         timeout=3600,env=dict(os.environ,PYTHONIOENCODING='utf-8'))
    if reply.returncode:
        sys.stderr.write(reply.stdout + reply.stderr)
        raise ValueError('PUBLICATION-SECRET-SCAN')


def scan_publication(source, files=(), repo=None):
    """The whole tree that will be published, plus release files that are not in it (package, notes, signed assets)."""
    scan_secrets('--tree', source, repo=repo)
    # Files are exported under their basenames, not their local staging directory.
    # The complete source tree above still rejects private/memory/backup paths.
    folders={}
    for file in files:
        path=Path(file).resolve()
        folders.setdefault(path.parent,[]).append(path.name)
    for folder,names in folders.items():
        scan_secrets('--root',str(folder),'--paths',*names)


def scan_new_commit(public, parent, repo=None):
    """Objects of the new public commit that the public parent does not already hold."""
    scan_secrets('--range', public, '--not', parent, repo=repo)


def save(branch):
    run('C:/Program Files/PowerShell/7/pwsh.exe','-NoProfile','-File',str(ROOT/'scripts/save-gitea.ps1'),'-Branch',branch,timeout=1800)


def git_blob(commit,path):
    return subprocess.run(['git','show',commit+':'+path],cwd=ROOT,capture_output=True,
                          check=True,timeout=180).stdout


def checked_record_commit(parent,source,package_hash):
    """Prove that a direct child only records the package already tested in parent."""
    def refuse():raise ValueError('PUBLICATION-RECORD-SCOPE')
    try:
        if run('git','rev-list','--parents','-n','1',source).split()!=[source,parent]:refuse()
        # main() requires source == HEAD; still prove the CI source belongs to that branch.
        run('git','merge-base','--is-ancestor',parent,'HEAD')
        before=json.loads(git_blob(parent,'VERSION.json').decode('utf-8-sig'))
        after=json.loads(git_blob(source,'VERSION.json').decode('utf-8-sig'))
        app=checked_manifest(after,package_hash)
        artifact=app.get('artifact','')
        version=app.get('version','')
        if (not re.fullmatch(r'homensai-auto-vpn_[0-9]+\.[0-9]+\.[0-9]+-(?:alpha|beta|rc)[0-9]+-[0-9]+_all\.ipk',artifact)
                or app.get('package_version')!=artifact[len('homensai-auto-vpn_'):-len('_all.ipk')]
                or app.get('release_tag')!='v'+version):refuse()
        old_app=before.get('application')
        if not isinstance(old_app,dict) or 'sha256' not in old_app or old_app['sha256']==package_hash:refuse()
        old_app['sha256']=package_hash
        if before!=after:refuse()
        package_path='releases/'+artifact
        notes_path='releases/'+app['release_tag']+'.md'
        expected={'VERSION.json':'M','router-test-kit/02-install.sh':'M',package_path:'A',
                  package_path+'.sha256':'A',notes_path:'A'}
        fields=run('git','diff','--name-status','--no-renames','-z',parent,source).split('\0')
        if fields[-1:]==['']:fields.pop()
        if len(fields)%2:refuse()
        changes={fields[index+1]:fields[index] for index in range(0,len(fields),2)}
        # Notes may have been reviewed with the tested source already. Only append
        # to those exact bytes, for this release; never rewrite existing notes.
        if changes.get(notes_path)=='M':
            old_notes=git_blob(parent,notes_path)
            new_notes=git_blob(source,notes_path)
            old_notes.decode('utf-8');new_notes.decode('utf-8')
            if (not old_notes or not old_notes.endswith(b'\n') or not new_notes.startswith(old_notes)
                    or not new_notes[len(old_notes):].strip()):refuse()
            expected[notes_path]='M'
        if len(changes)*2!=len(fields) or {name:changes.get(name) for name in expected}!=expected:refuse()
        # Optional signed record (docs/architecture/SIGNING-2026-11-03.ru.md): <ipk>.sig, the extended release chain and
        # the OpenTimestamps proof of its new head. Chain or proof without the package signature is not a record.
        optional={package_path+'.sig':('A',),'releases/CHAIN.jsonl':('A','M'),'releases/ots/'+app['package_version']+'.ots':('A',),
                  '.gitattributes':('M',)}
        extra={name:status for name,status in changes.items() if name not in expected}
        if any(status not in optional.get(name,()) for name,status in extra.items()):refuse()
        if '.gitattributes' in extra:
            # A Windows clone must preserve the exact signature bytes. This one
            # final rule affects signatures only; no filters or other rules change.
            old_attributes=git_blob(parent,'.gitattributes')
            if (extra.get(package_path+'.sig')!='A' or not old_attributes.endswith(b'\n')
                    or b'*.sig' in old_attributes
                    or git_blob(source,'.gitattributes')!=old_attributes+b'*.sig -text\n'):refuse()
        if extra:checked_signatures(parent,source,package_path,app['package_version'])
        package=git_blob(source,package_path)
        if hashlib.sha256(package).hexdigest()!=package_hash:refuse()
        checksum=git_blob(source,package_path+'.sha256').decode('utf-8')
        if not re.fullmatch(re.escape(package_hash)+r' [ *]'+re.escape(artifact)+r'\r?\n?',checksum):refuse()
        scripts=[git_blob(commit,'router-test-kit/02-install.sh').decode('utf-8')
                 for commit in (parent,source)]
        wanted={'EXPECTED_SHA':package_hash,'EXPECTED_SIZE':str(len(package))}
        for key,value in wanted.items():
            pattern=r'^'+key+r'=([^\n]*)$'
            matches=[re.findall(pattern,script,re.MULTILINE) for script in scripts]
            if any(len(items)!=1 for items in matches) or matches[1][0]!=value:refuse()
            scripts=[re.sub(pattern,key+'=<recorded>',script,flags=re.MULTILINE) for script in scripts]
        if scripts[0]!=scripts[1]:refuse()
    except lab_mode.LabRefused:
        raise
    except (KeyError,TypeError,ValueError,UnicodeError,subprocess.CalledProcessError):
        raise ValueError('PUBLICATION-RECORD-SCOPE') from None


SIGNING_KEYS='router/files/etc/homensai-vpn/keys'


def checked_signatures(parent,source,package_path,package_version):
    """The record's package signature and its new chain head verify with the keys of the source tree, and the chain
    only extends the parent's history (no rewritten past)."""
    import chain,keytool,usign_format
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        keys=[name for name in run('git','ls-tree','--name-only',source,SIGNING_KEYS+'/').split('\n') if name]
        lab_mode.refuse_in_publication(keys,git_blob(source,'releases/CHAIN.jsonl'),
                                       usign_format.signature_key_id(git_blob(source,package_path+'.sig')).hex())
        for name in keys+[package_path,package_path+'.sig','releases/CHAIN.jsonl']:
            target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(git_blob(source,name))
        report=keytool.verify_release(root,package_path)
        if report['head']!=package_version:raise ValueError('PUBLICATION-SIGNED-HEAD')
        try:previous=git_blob(parent,'releases/CHAIN.jsonl') if parent else b''
        except subprocess.CalledProcessError:previous=b''
        if previous and chain.check_extends(previous,(root/'releases/CHAIN.jsonl').read_bytes())!='extends':raise ValueError('PUBLICATION-CHAIN-NOT-EXTENDED')
    return report


def signed_assets(artifact,package_version):
    """Signature, chain and proof published next to the package when the record carries them."""
    paths={artifact.name+'.sig':ROOT/'releases'/(artifact.name+'.sig'),'CHAIN.jsonl':ROOT/'releases/CHAIN.jsonl',
           package_version+'.ots':ROOT/'releases/ots'/(package_version+'.ots')}
    if not paths[artifact.name+'.sig'].is_file():return {}
    return {name:path for name,path in paths.items() if path.is_file()}


def checked_signed_assets(source,artifact,package_version,directory=None):
    """Bind every uploaded signed asset to the reviewed commit, including exact-CI releases. With a directory, the
    returned paths are private copies of the committed bytes, so the uploaded files cannot change after the check."""
    paths=signed_assets(artifact,package_version)
    if not paths:return paths
    copies={}
    for asset,path in paths.items():
        name=path.relative_to(ROOT).as_posix()
        try:committed=git_blob(source,name)
        except subprocess.CalledProcessError:raise ValueError('PUBLICATION-SIGNED-ASSET-UNCOMMITTED') from None
        if path.is_symlink() or path.read_bytes()!=committed:
            raise ValueError('PUBLICATION-SIGNED-ASSET-MISMATCH')
        if directory is not None:
            target=Path(directory)/asset;target.parent.mkdir(parents=True,exist_ok=True)
            with open(target,'xb') as stream:stream.write(committed)
            os.chmod(target,0o400);copies[asset]=target
    checked_signatures(None,source,'releases/'+artifact.name,package_version)
    return copies if directory is not None else paths


# Alpha8 predates the signing tooling and public keys. Only this reviewed,
# immutable later snapshot may supply its detached public signing metadata.
# Its product tree and history are never selected for publication.
EXTERNAL_SIGNING_SOURCES={
    '37b2033b58ea8f60165ae85aecedc46c5a04434c':(
        '5bf54807c50ec7f3a19c1e9d89ae2a477c8302fd',
        '98bec145d06d2473ce4b343250009d59d6113a50'),
}


def external_signed_assets(source,ci_source,signing_source,artifact,package_version,package_hash,directory):
    """Verified public metadata from the one approved historical signing snapshot."""
    if EXTERNAL_SIGNING_SOURCES.get(signing_source)!=(source,ci_source):
        raise ValueError('PUBLICATION-SIGNING-SOURCE-SCOPE')
    package_path='releases/'+artifact.name
    payload=git_blob(signing_source,package_path)
    if payload!=artifact.read_bytes() or hashlib.sha256(payload).hexdigest()!=package_hash:
        raise ValueError('PUBLICATION-SIGNING-PACKAGE-MISMATCH')
    checked_signatures(None,signing_source,package_path,package_version)
    import chain,ots
    head=json.loads(git_blob(signing_source,'releases/CHAIN.jsonl').splitlines()[-1])['entry']
    if head['source_commit'] not in (source,ci_source) or head['origin']!='release':
        raise ValueError('PUBLICATION-SIGNING-PROVENANCE')
    proof=ots.parse(git_blob(signing_source,'releases/ots/'+package_version+'.ots'))
    if proof.hash_tag!=ots.OP_SHA256 or proof.digest!=hashlib.sha256(chain.canonical(head)).digest():
        raise ValueError('PUBLICATION-SIGNING-OTS-MISMATCH')
    names={artifact.name+'.sig':package_path+'.sig','CHAIN.jsonl':'releases/CHAIN.jsonl',
           package_version+'.ots':'releases/ots/'+package_version+'.ots'}
    keys=run('git','ls-tree','--name-only',signing_source,SIGNING_KEYS+'/').splitlines()
    for path in keys:
        name=Path(path).name
        if re.fullmatch('[0-9a-f]{16}',name):names[name+'.pub']=path
    assets={}
    for name,path in names.items():
        target=Path(directory)/name
        target.write_bytes(git_blob(signing_source,path))
        assets[name]=target
    return assets


def checked_source_receipt(value,source):
    """Accept exact-source CI, or its narrowly verified package-record child."""
    if not isinstance(value,list) or len(value)!=2:raise ValueError('PUBLICATION-CI-MATRIX')
    ci_source=value[0].get('source') if isinstance(value[0],dict) else None
    if ci_source==source:return checked_receipt(value,source),source
    if not isinstance(ci_source,str) or not re.fullmatch('[a-f0-9]{40}',ci_source):
        raise ValueError('PUBLICATION-CI-SOURCE')
    package_hash=checked_receipt(value,ci_source)
    checked_record_commit(ci_source,source,package_hash)
    return package_hash,ci_source


def checked_manifest(data,package_hash,release=None):
    app=data.get('application',{}) if isinstance(data,dict) else {}
    if not isinstance(app,dict) or app.get('sha256')!=package_hash or package_hash=='0'*64:
        raise ValueError('PUBLICATION-MANIFEST-PACKAGE-MISMATCH')
    if release and app.get('release_tag')!=release:raise ValueError('PUBLICATION-MANIFEST-TAG-MISMATCH')
    return app


def push_arguments(public):
    """Push the exact reviewed public commit, never a branch name that could have moved after review (F-02)."""
    if not isinstance(public,str) or not re.fullmatch('[a-f0-9]{40}',public):raise ValueError('PUBLICATION-LEDGER-SHA')
    return ['git','-c','credential.helper=','-c','credential.helper=!gh auth git-credential','-c','push.followTags=false',
            'push',URL,public+':refs/heads/main']


def checked_public_commit(public,parent,tree,read=None):
    """The public commit is a full SHA whose only parent and tree are the recorded ones (new and resumed runs)."""
    read=read or run
    for value in (public,parent):
        if not isinstance(value,str) or not re.fullmatch('[a-f0-9]{40}',value):raise ValueError('PUBLICATION-LEDGER-SHA')
    if (read('git','rev-parse','--verify',public+'^{commit}')!=public
            or read('git','rev-list','--parents','-n','1',public).split()!=[public,parent]
            or read('git','rev-parse',public+'^{tree}')!=tree):raise ValueError('PUBLICATION-RESUME-TREE')
    return public


def snapshot_file(path,directory,expected_sha=None):
    """Read the file once, check those bytes, and keep a private read-only copy: later steps (scan, upload,
    release notes) use the copy, so replacing the original after validation cannot change what is published (F-03)."""
    path=Path(path)
    if path.is_symlink() or not path.is_file():raise ValueError('RELEASE-INPUT-FILE')
    data=path.read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    if expected_sha is not None and digest!=expected_sha:raise ValueError('RELEASE-ARTIFACT-HASH')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    target=directory/path.name
    with open(target,'xb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    os.chmod(target,0o400)
    if hashlib.sha256(target.read_bytes()).hexdigest()!=digest:raise ValueError('RELEASE-INPUT-SNAPSHOT')
    return target,digest


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--receipt',type=Path,required=True)
    p.add_argument('--resume',type=Path);p.add_argument('--publish',action='store_true');p.add_argument('--release');p.add_argument('--artifact',type=Path);p.add_argument('--notes',type=Path)
    p.add_argument('--check-only',action='store_true',help='offline validation only: no save, fetch, refs, ledger or publication')
    p.add_argument('--signing-source',help='exact approved historical commit supplying detached public signing assets')
    lab_mode.refuse_lab_environment()
    a=p.parse_args()
    with tempfile.TemporaryDirectory(prefix='reviewed-signing-') as directory:
        return publish(a,Path(directory))


def publish(a,signing_directory):
    if a.check_only and (a.publish or a.resume):raise ValueError('PUBLICATION-CHECK-ONLY-SCOPE')
    if not re.fullmatch('[a-f0-9]{40}',a.source):raise ValueError('SOURCE-SHA')
    if a.signing_source and not a.release:raise ValueError('PUBLICATION-SIGNING-SOURCE-SCOPE')
    if run('git','status','--porcelain'):raise ValueError('PUBLICATION-DIRTY')
    if run('git','rev-parse','HEAD')!=a.source:raise ValueError('PUBLICATION-NONCURRENT-SOURCE')
    package_hash,ci_source=checked_source_receipt(json.loads(a.receipt.read_text(encoding='utf-8-sig')),a.source)
    checked_manifest(json.loads((ROOT/'VERSION.json').read_text(encoding='utf-8-sig')),package_hash,a.release)
    if a.release:
        # Alpha, beta and release-candidate tags; a plain version tag (final release) stays a separate owner decision.
        if not (a.publish or a.check_only) or not re.fullmatch(r'v[0-9]+\.[0-9]+\.[0-9]+-(?:alpha|beta|rc)[0-9]+',a.release):raise ValueError('RELEASE-SCOPE')
        if not a.artifact or not a.notes or not a.notes.is_file():raise ValueError('RELEASE-ARTIFACT-HASH')
        # Everything after this point reads the validated private copies, never the caller's mutable paths (F-03).
        a.artifact,_=snapshot_file(a.artifact,signing_directory/'reviewed-artifact',package_hash)
        a.notes,_=snapshot_file(a.notes,signing_directory/'reviewed-notes')
        if not a.check_only:
            probe=capture_text('gh','api','repos/'+REPOSITORY+'/git/ref/tags/'+a.release,timeout=60)
            if probe.returncode==0 and not a.resume:raise ValueError('RELEASE-TAG-EXISTS')
            if probe.returncode!=0 and '404' not in probe.stderr:raise ValueError('RELEASE-TAG-LOOKUP-UNCONFIRMED')
    version=json.loads((ROOT/'VERSION.json').read_text(encoding='utf-8-sig'))['application']['package_version']
    signed=(external_signed_assets(a.source,ci_source,a.signing_source,a.artifact,version,package_hash,signing_directory)
            if a.signing_source else checked_signed_assets(a.source,a.artifact,version,signing_directory/'reviewed-signed')) if a.release else {}
    scan_publication(a.source,[f for f in (a.artifact,a.notes) if f]+list(signed.values()))
    if a.check_only:
        print(json.dumps(dict(result='PASS',check_only=True,source=a.source,ci_source=ci_source,
                              package_sha256=package_hash,signing_source=a.signing_source,signed_assets=sorted(signed)),sort_keys=True))
        return
    private=ROOT/'.git/handoff';private.mkdir(parents=True,exist_ok=True)
    tree=run('git','rev-parse',a.source+'^{tree}')
    if a.resume:
        receipt=a.resume.resolve()
        if receipt.parent!=private.resolve() or receipt.is_symlink() or not receipt.name.startswith('publication-'):raise ValueError('PUBLICATION-RESUME-PATH')
        ledger=json.loads(receipt.read_text(encoding='utf-8'))
        if any(ledger.get(key)!=value for key,value in [('source',a.source),('tree',tree),('package_sha256',package_hash),('planned_release',a.release),('signing_source',a.signing_source)]):raise ValueError('PUBLICATION-RESUME-IDENTITY')
        public=checked_public_commit(ledger.get('public'),ledger.get('parent'),tree)
    else:
        canonical=run('git','branch','--show-current');save(canonical)
        parent=run('gh','api','repos/'+REPOSITORY+'/git/ref/heads/main','--jq','.object.sha')
        run('git','-c','gc.auto=0','fetch','--no-tags',URL,'refs/heads/main:refs/remotes/origin/main')
        if run('git','rev-parse','refs/remotes/origin/main')!=parent:raise ValueError('PUBLICATION-PARENT-MOVED')
        if not re.fullmatch('[a-f0-9]{40}',parent):raise ValueError('PUBLICATION-PARENT-SHA')
        public=run('git','commit-tree',tree,'-p',parent,input='Reviewed local snapshot '+a.source+'\n\nDual-runtime CI package SHA256 '+package_hash+'\n')
        checked_public_commit(public,parent,tree)
        scan_new_commit(public,parent)
        branch='feature/github-publication-'+public[:12]
        run('git','update-ref','refs/heads/'+branch,public,'0'*40);save(branch)
        ledger={'source':a.source,'ci_source':ci_source,'record_commit_verified':ci_source!=a.source,'public':public,'parent':parent,'tree':tree,'package_sha256':package_hash,'gitea_saved':True,'github_published':False,'planned_release':a.release,'notes_sha256':hashlib.sha256(a.notes.read_bytes()).hexdigest() if a.release else None}
        ledger['signing_source']=a.signing_source
        receipt=private/('publication-'+public+'.json')
    def persist(value):
        pending=receipt.with_suffix('.pending')
        with pending.open('w',encoding='utf-8') as stream:
            json.dump(value,stream,indent=2);stream.flush();os.fsync(stream.fileno())
        os.replace(pending,receipt)
    persist(ledger)
    class Remote:
        def main(self):return run('gh','api','repos/'+REPOSITORY+'/git/ref/heads/main','--jq','.object.sha')
        def push(self):run(*push_arguments(public))
        def lookup(self,endpoint):
            return lookup_json(endpoint)
        def tag(self):
            row=self.lookup('git/ref/tags/'+a.release)
            return None if row is None else row['object']['sha']
        def create_tag(self):run('gh','api','repos/'+REPOSITORY+'/git/refs','-f','ref=refs/tags/'+a.release,'-f','sha='+public)
        def release(self):return self.lookup('releases/tags/'+a.release)
        def create_release(self):run('gh','release','create',a.release,'--repo',REPOSITORY,'--verify-tag','--prerelease','--notes-file',str(a.notes))
        def expected_assets(self):
            return [(a.artifact.name,package_hash),(a.artifact.name+'.sha256',checksum_sha)]+[
                (name,hashlib.sha256(path.read_bytes()).hexdigest()) for name,path in sorted(signed.items())]
        def asset_hash(self,name):
            release=self.release()
            if release is None or not any(item.get('name')==name for item in release.get('assets',[])):return None
            with tempfile.TemporaryDirectory(prefix='download-',dir=private) as directory:
                run('gh','release','download',a.release,'--repo',REPOSITORY,'--pattern',name,'--dir',directory)
                return hashlib.sha256((Path(directory)/name).read_bytes()).hexdigest()
        def upload(self,name):
            asset=a.artifact if name==a.artifact.name else signed[name] if name in signed else checksum_path
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
