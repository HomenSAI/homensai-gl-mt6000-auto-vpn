"""Execute fixed checks on an extracted, immutable committed source snapshot."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--source',required=True);parser.add_argument('--runtime-only',action='store_true')
    args=parser.parse_args()
    if not re.fullmatch('[a-f0-9]{40}',args.source):parser.error('SOURCE-SHA')
    root=Path(__file__).resolve().parents[1]
    def check(argv):
        result=subprocess.run(argv,cwd=root,capture_output=True,text=True,timeout=120)
        if result.returncode:
            print(result.stdout);print(result.stderr,file=sys.stderr)
            raise RuntimeError('CI-CHECK-FAILED: exit=%s command=%s' % (result.returncode, ' '.join(argv)))
        return result
    check([sys.executable,'qa/privacy_audit.py','--manifest',str(args.manifest)])
    application=check([sys.executable,'-m','unittest','discover','-s','router/tests','-q'])
    qa=check([sys.executable,'-m','unittest','discover','-s','qa','-q'])
    ui_count=0
    if not args.runtime_only:
        for path in sorted((root/'router/tests').glob('test_*ui*.js')):
            check(['node',str(path)])
            ui_count+=1
    sys.path.insert(0,str(root/'router'))
    from build_ipk import build
    sys.path.insert(0,str(root/'qa'))
    from privacy_audit import inspect
    with tempfile.TemporaryDirectory() as directory:
        first=build(directory);data=first.read_bytes();second=build(directory).read_bytes()
        if data!=second:raise RuntimeError('CI-PACKAGE-NOT-REPRODUCIBLE')
        failures=[];inspect(first.name,data,failures)
        if failures:raise RuntimeError('CI-PACKAGE-PRIVACY')
        receipt=dict(result='PASS',source=args.source,python=platform.python_version(),
                     lua_available=bool(shutil.which('lua5.1')),runtime_only=args.runtime_only,
                     application_tests=int(re.search(r'Ran (\d+) tests',application.stderr).group(1)),
                     skipped_tests=int(re.search(r'skipped=(\d+)',application.stderr).group(1)) if 'skipped=' in application.stderr else 0,
                     qa_tests=int(re.search(r'Ran (\d+) tests',qa.stderr).group(1)),ui_suites=ui_count,
                     qa_skipped_tests=int(re.search(r'skipped=(\d+)',qa.stderr).group(1)) if 'skipped=' in qa.stderr else 0,
                     artifact=first.name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                     scope='isolated source archive; no physical/virtual router acceptance')
    print('CI-RECEIPT '+json.dumps(receipt,sort_keys=True))


if __name__=='__main__':main()
