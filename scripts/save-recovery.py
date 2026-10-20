"""Save a clean committed branch to a verified private recovery ZIP outside source."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import uuid
import zipfile
import sys

ROOT=Path(__file__).resolve().parents[1]
HANDOFF={'STATE.json':'docs/handoff/ACTIVE-STATE-2026-10-20.json',
         'TODO.md':'docs/handoff/RECOVERY-TODO-2026-10-20.md'}


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT,stderr=subprocess.PIPE,text=True,timeout=300).strip()


def committed_file(head,path):
    return subprocess.check_output(['git','show',head+':'+path],cwd=ROOT,stderr=subprocess.PIPE,timeout=300)


def verify_archive(target,head,branch,tree):
    """Verify the stored bytes, then restore the stored bundle in an empty directory."""
    with zipfile.ZipFile(target) as archive:
        expected={'source.tar','checkpoint.bundle','STATE.json','TODO.md','RESTORE.txt','MANIFEST.json'}
        if set(archive.namelist())!=expected or len(archive.namelist())!=len(expected):
            raise ValueError('BACKUP-ZIP-ENTRIES')
        if archive.testzip() is not None:raise ValueError('BACKUP-ZIP-CRC')
        manifest=json.loads(archive.read('MANIFEST.json'))
        if set(manifest)!=expected-{'MANIFEST.json'}:raise ValueError('BACKUP-MANIFEST-ENTRIES')
        for name,digest in manifest.items():
            if hashlib.sha256(archive.read(name)).hexdigest()!=digest:raise ValueError('BACKUP-HASH-MISMATCH')
        with tempfile.TemporaryDirectory(prefix='vpn-restore-') as directory:
            temp=Path(directory);bundle=temp/'checkpoint.bundle';restore=temp/'restore'
            bundle.write_bytes(archive.read('checkpoint.bundle'))
            subprocess.run(['git','clone','--quiet','--no-checkout','--branch',branch,str(bundle),str(restore)],check=True,capture_output=True,timeout=300)
            for expression,wanted in [('HEAD',head),('HEAD^{tree}',tree)]:
                actual=subprocess.check_output(['git','-C',str(restore),'rev-parse',expression],text=True,timeout=300).strip()
                if actual!=wanted:raise ValueError('BACKUP-RESTORE-MISMATCH')
            subprocess.run(['git','-C',str(restore),'fsck','--full'],check=True,capture_output=True,timeout=300)


def main(destination):
    if git('status','--porcelain'):raise ValueError('BACKUP-REQUIRES-CLEAN-COMMIT')
    head=git('rev-parse','HEAD');branch=git('branch','--show-current');tree=git('rev-parse',head+'^{tree}')
    if not branch:raise ValueError('BACKUP-REQUIRES-BRANCH')
    destination=Path(destination).resolve()
    if destination==ROOT or ROOT in destination.parents:raise ValueError('BACKUP-OUTSIDE-SOURCE-REQUIRED')
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder=destination/'archives'/(stamp+'-recovery-'+head[:7]+'-'+uuid.uuid4().hex[:6])
    # Resolve existing junctions/symlinks before writing anything, including archives/.
    resolved_folder=folder.resolve()
    git_directory=Path(git('rev-parse','--absolute-git-dir')).resolve()
    for protected in (ROOT.resolve(),git_directory):
        if resolved_folder==protected or protected in resolved_folder.parents:
            raise ValueError('BACKUP-OUTSIDE-SOURCE-REQUIRED')
    folder.mkdir(parents=True,exist_ok=False)
    target=folder/'checkpoint.zip'
    with tempfile.TemporaryDirectory(prefix='vpn-recovery-') as directory:
        temp=Path(directory);source=temp/'source.tar';bundle=temp/'checkpoint.bundle'
        git('archive','--format=tar','--output='+str(source),head)
        git('bundle','create',str(bundle),'refs/heads/'+branch)
        refs=git('bundle','list-heads',str(bundle),'refs/heads/'+branch)
        if refs!=head+' refs/heads/'+branch:raise ValueError('BACKUP-BRANCH-MOVED')
        git('bundle','verify',str(bundle))
        payload={'source.tar':source.read_bytes(),'checkpoint.bundle':bundle.read_bytes()}
        payload.update({name:committed_file(head,path) for name,path in HANDOFF.items()})
        payload['RESTORE.txt']=(f'Committed development checkpoint {head}, branch {branch}.\n'
            'Extract into a NEW directory; git clone checkpoint.bundle recovered-project\n'
            'Compare SHA256 of entries with MANIFEST.json; source.tar is the Git archive export.\n'
            'Read STATE.json and TODO.md. Offline PASS never means hardware acceptance.\n'
            'Private recovery archive with development history: never upload as a public release asset.\n').encode()
        manifest={name:hashlib.sha256(data).hexdigest() for name,data in payload.items()}
        payload['MANIFEST.json']=(json.dumps(manifest,indent=2)+'\n').encode()
        with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
            for name,data in payload.items():archive.writestr(name,data)
    verify_archive(target,head,branch,tree)
    receipt={'status':'VERIFIED_COMMIT_BACKUP','head':head,'tree':tree,'branch':branch,'archive':str(target),
             'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size,
             'bundle_restore_head_verified':True,'bundle_restore_tree_verified':True,'bundle_fsck_verified':True,
             'scope':'captured committed branch history only; excludes uncommitted and ignored files, other branches and Git configuration',
             'created_utc':stamp,'hardware_acceptance':False}
    target.with_suffix('.sha256').write_text(receipt['sha256']+'  checkpoint.zip\n',encoding='ascii')
    encoded=json.dumps(receipt,indent=2)+'\n'
    (folder/'receipt.json').write_text(encoded,encoding='utf-8')
    if git('rev-parse','HEAD')!=head or git('branch','--show-current')!=branch:
        raise ValueError('BACKUP-SOURCE-MOVED-BEFORE-CURRENT')
    pending=destination/('CURRENT.local.'+uuid.uuid4().hex+'.tmp')
    pending.write_text(encoded,encoding='utf-8');pending.replace(destination/'CURRENT.local.json')
    print(encoded,end='')
    return receipt


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: python scripts/save-recovery.py D:/homensai/homensai-gl-mt6000-auto-vpn')
    main(sys.argv[1])
