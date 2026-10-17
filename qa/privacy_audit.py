"""Scan publication files and nested ipk archives. Never print matched secrets."""
import io
from pathlib import Path
import re
import subprocess
import tarfile
import zipfile
from pathlib import PurePosixPath

PATTERNS = [rb'\b\d{8,12}:[A-Za-z0-9_-]{30,}\b', rb'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----',
            rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b', rb'\bgithub_pat_[A-Za-z0-9_]{30,}\b',
            rb'\btelegram_(?:token|chat)\s+[\x22\x27]?[0-9][A-Za-z0-9_:-]{5,}']


def inspect(name, data, failures, depth=0, budget=None):
    budget=[64*1024*1024,10000] if budget is None else budget
    budget[0]-=len(data);budget[1]-=1
    if depth>4 or budget[0]<0 or budget[1]<0:
        failures.append(name+':archive-limit');return
    def member_ok(member):
        path=PurePosixPath(member)
        return not path.is_absolute() and '..' not in path.parts and ':' not in member
    if name.lower().endswith(('.ipk','.tar.gz','.tgz','.tar')):
        try:
            with tarfile.open(fileobj=io.BytesIO(data),mode='r:*') as archive:
                for member in archive:
                    if member.isdir():continue
                    if not member.isfile() or not member_ok(member.name) or member.size>budget[0]:
                        failures.append(name+':unsafe-archive');return
                    inspect(name+'!'+member.name,archive.extractfile(member).read(),failures,depth+1,budget)
        except tarfile.TarError:failures.append(name+':invalid-archive')
    elif name.lower().endswith('.zip'):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for member in archive.infolist():
                    if member.is_dir():continue
                    if member.flag_bits&1 or not member_ok(member.filename) or member.file_size>budget[0]:
                        failures.append(name+':unsafe-archive');return
                    inspect(name+'!'+member.filename,archive.read(member),failures,depth+1,budget)
        except (zipfile.BadZipFile,RuntimeError):failures.append(name+':invalid-archive')
    elif any(re.search(pattern,data) for pattern in PATTERNS):failures.append(name)


def audit_paths(root,names):
    root=root.resolve()
    if not isinstance(names,list) or len(names)>10000:
        raise ValueError('PRIVACY-MANIFEST-BOUNDS')
    failures=[]
    seen=set()
    for name in names:
        if not isinstance(name,str) or not name or len(name)>512:
            raise ValueError('PRIVACY-MANIFEST-NAME')
        path=PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or ':' in name or '\\' in name or path.parts[0].lower()=='.git' or path.as_posix()!=name or any(ord(c)<32 for c in name) or name in seen:
            raise ValueError('PRIVACY-MANIFEST-PATH')
        seen.add(name)
        target=root/name
        if target.is_symlink() or not target.resolve().is_relative_to(root) or not target.is_file() or target.stat().st_size>64*1024*1024:
            raise ValueError('PRIVACY-MANIFEST-FILE')
        inspect(name,(root/name).read_bytes(),failures)
    return failures


def main():
    import argparse,json
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path)
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    if args.manifest:
        if args.manifest.stat().st_size>2*1024*1024:raise ValueError('PRIVACY-MANIFEST-SIZE')
        names=json.loads(args.manifest.read_text(encoding='utf-8-sig'))
    else:
        names=list(filter(None,subprocess.check_output(['git','-C',str(root),'ls-files','-z']).decode().split('\0')))
    failures=audit_paths(root,names)
    print('Publication privacy scan:', 'PASS' if not failures else 'FAIL')
    print('Files inspected:',len(names))
    if failures:
        print('Files requiring review:',failures)
    raise SystemExit(bool(failures))


if __name__=='__main__':
    main()
