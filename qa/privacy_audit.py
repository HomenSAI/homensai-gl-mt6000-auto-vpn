"""Scan publication files and nested ipk archives. Never print matched secrets.

Containers are recognised by their content (gzip, bzip2, xz, tar, zip signatures), not by the file name, so a
compressed tar renamed to .dat or a gzip inside a gzip is still opened. UTF-16 and UTF-8-with-BOM text is decoded
before the patterns run. Anything that cannot be read completely is reported, never treated as clean."""
import bz2
import gzip
import io
import lzma
from pathlib import Path
import re
import subprocess
import tarfile
import zipfile
import zlib
from pathlib import PurePosixPath

PATTERNS = [rb'\b\d{8,12}:[A-Za-z0-9_-]{30,}\b',
            # every PEM private key flavour: RSA, EC, DSA, OPENSSH, ENCRYPTED, PGP ... PRIVATE KEY (BLOCK)
            rb'-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY(?: BLOCK)?-----',
            rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b', rb'\bgithub_pat_[A-Za-z0-9_]{30,}\b',
            rb'\btelegram_(?:token|chat)\s+[\x22\x27]?[0-9][A-Za-z0-9_:-]{5,}',
            # the Telegram recipient in UCI, shell and JSON forms: numeric IDs of 7+ digits (also negative group IDs) and
            # @usernames; shorter numbers are the synthetic fixtures of the tests, not real chats
            rb'\btelegram_chat\b[\x22\x27]?\s*[:=\s]\s*[\x22\x27]?(?:-?[0-9]{7,}|@[A-Za-z][A-Za-z0-9_]{4,})']
MAX_EXPANDED = 64*1024*1024
ZIP_MAGIC = (b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08')


class Limit(Exception):
    pass


def decompress(data, limit):
    """Content of a gzip/bzip2/xz stream (bounded by limit), or None when data is not compressed."""
    if data[:2] == b'\x1f\x8b':
        stream = gzip.GzipFile(fileobj=io.BytesIO(data))
    elif data[:3] == b'BZh':
        stream = bz2.BZ2File(io.BytesIO(data))
    elif data[:6] == b'\xfd7zXZ\x00':
        stream = lzma.LZMAFile(io.BytesIO(data))
    else:
        return None
    with stream:
        inner = stream.read(limit+1)
    if len(inner) > limit:
        raise Limit()
    return inner


def is_tar(data):
    return data[257:262] == b'ustar'


def texts(data):
    """The raw bytes plus decoded variants (UTF-8 BOM, UTF-16 with BOM or with every other byte NUL)."""
    yield data
    if data[:3] == b'\xef\xbb\xbf':
        yield data[3:]
    codec = None
    if data[:2] == b'\xff\xfe':
        codec, data = 'utf-16-le', data[2:]
    elif data[:2] == b'\xfe\xff':
        codec, data = 'utf-16-be', data[2:]
    elif len(data) >= 8:
        sample = data[:8000]
        even, odd = sample[0::2], sample[1::2]
        if odd.count(0) >= 0.4*len(odd) and even.count(0) <= 0.05*len(even):
            codec = 'utf-16-le'
        elif even.count(0) >= 0.4*len(even) and odd.count(0) <= 0.05*len(odd):
            codec = 'utf-16-be'
    if codec:
        yield data[:len(data)-len(data) % 2].decode(codec, 'replace').encode('utf-8', 'replace')


def inspect(name,data,failures,depth=0,budget=None):
    budget=[MAX_EXPANDED,10000] if budget is None else budget
    budget[0]-=len(data);budget[1]-=1
    if depth>4 or budget[0]<0 or budget[1]<0:
        failures.append(name+':archive-limit');return
    def member_ok(member):
        path=PurePosixPath(member)
        return not path.is_absolute() and '..' not in path.parts and ':' not in member
    try:
        inner=decompress(data,max(budget[0],0))
    except Limit:
        failures.append(name+':archive-limit');return
    except (OSError,EOFError,lzma.LZMAError,zlib.error,ValueError):
        failures.append(name+':invalid-archive');return
    if inner is not None:
        if is_tar(inner):
            budget[0]-=len(inner)                            # charge the expanded bytes
            if budget[0]<0:
                failures.append(name+':archive-limit');return
            data=inner                                       # a compressed tar: one archive layer
        else:
            inspect(name,inner,failures,depth+1,budget)      # nested compression, compressed text, ...
            return
    lower=name.lower()
    if is_tar(data) or (inner is None and lower.endswith(('.ipk','.tar.gz','.tgz','.tar'))):
        try:
            with tarfile.open(fileobj=io.BytesIO(data),mode='r:') as archive:
                for member in archive:
                    if member.isdir():continue
                    if not member.isfile() or not member_ok(member.name) or member.size>budget[0]:
                        failures.append(name+':unsafe-archive');return
                    inspect(name+'!'+member.name,archive.extractfile(member).read(),failures,depth+1,budget)
        except (tarfile.TarError,EOFError,OSError):failures.append(name+':invalid-archive')
    elif data[:4] in ZIP_MAGIC or lower.endswith('.zip'):
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                for member in archive.infolist():
                    if member.is_dir():continue
                    if member.flag_bits&1 or not member_ok(member.filename) or member.file_size>budget[0]:
                        failures.append(name+':unsafe-archive');return
                    inspect(name+'!'+member.filename,archive.read(member),failures,depth+1,budget)
        except (zipfile.BadZipFile,RuntimeError,EOFError,OSError,zlib.error,NotImplementedError):failures.append(name+':invalid-archive')
    elif any(re.search(pattern,text) for text in texts(data) for pattern in PATTERNS):failures.append(name)


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
