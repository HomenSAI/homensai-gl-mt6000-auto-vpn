"""Scan publication files and nested ipk archives. Never print matched secrets."""
import io
from pathlib import Path
import re
import subprocess
import tarfile

PATTERNS = [rb'\b\d{8,12}:[A-Za-z0-9_-]{30,}\b', rb'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----',
            rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b', rb'\bgithub_pat_[A-Za-z0-9_]{30,}\b',
            rb'\btelegram_(?:token|chat)\s+[\x22\x27]?[0-9][A-Za-z0-9_:-]{5,}']


def inspect(name, data, failures):
    if name.endswith(('.ipk','.tar.gz')):
        with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
            for member in archive.getmembers():
                if member.isfile():
                    inspect(name+'!'+member.name,archive.extractfile(member).read(),failures)
    elif any(re.search(pattern,data) for pattern in PATTERNS):
        failures.append(name)


def main():
    root=Path(__file__).resolve().parents[1]
    names=subprocess.check_output(['git','-C',str(root),'ls-files','-z']).decode().split('\0')
    failures=[]
    for name in filter(None,names):
        inspect(name,(root/name).read_bytes(),failures)
    print('Publication privacy scan:', 'PASS' if not failures else 'FAIL')
    print('Files inspected:',len(list(filter(None,names))))
    if failures:
        print('Files requiring review:',failures)
    raise SystemExit(bool(failures))


if __name__=='__main__':
    main()
