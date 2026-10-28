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


LAB_UNIT_TESTS=('test_mt3000_lan_fixture.py','test_mt3000_namespace_probe.py',
                'test_startup_work.py','test_transaction_engine.py')
LAB_SCRIPT_TESTS=('test_process_crash.py',)
LAB_NODE_TESTS=('test_router_faults.js','test_transaction_regressions.js')


def unittest_counts(result):
    """Count executed cases from unittest's successful, captured summary."""
    summary=result.stderr
    match=re.search(r'Ran (\d+) tests?',summary)
    if not match:raise RuntimeError('CI-TEST-COUNT-MISSING')
    skipped=re.search(r'skipped=(\d+)',summary)
    return int(match.group(1)),int(skipped.group(1)) if skipped else 0


def lab_exclusions(root):
    """Only reviewed offline entries run; never import hardware acceptance scripts."""
    allowed=set(LAB_UNIT_TESTS+LAB_SCRIPT_TESTS+LAB_NODE_TESTS)
    candidates=sorted(path for path in (root/'lab').iterdir() if path.suffix in ('.py','.js'))
    unreviewed=[path.name for path in candidates if path.name.startswith('test_') and path.name not in allowed]
    if unreviewed:raise RuntimeError('CI-LAB-TEST-UNREVIEWED: '+', '.join(unreviewed))
    return [str(path.relative_to(root)) for path in candidates if path.name not in allowed]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--source',required=True);parser.add_argument('--runtime-only',action='store_true')
    args=parser.parse_args()
    if not re.fullmatch('[a-f0-9]{40}',args.source):parser.error('SOURCE-SHA')
    root=Path(__file__).resolve().parents[1]
    def check(argv):
        result=subprocess.run(argv,cwd=root,capture_output=True,text=True,timeout=300)
        if result.returncode:
            print(result.stdout);print(result.stderr,file=sys.stderr)
            raise RuntimeError('CI-CHECK-FAILED: exit=%s command=%s' % (result.returncode, ' '.join(argv)))
        return result
    check([sys.executable,'qa/privacy_audit.py','--manifest',str(args.manifest)])
    application=check([sys.executable,'-m','unittest','discover','-s','router/tests','-q'])
    qa=check([sys.executable,'-m','unittest','discover','-s','qa','-q'])
    tools=check([sys.executable,'-m','unittest','discover','-s','tools/tests','-q'])
    tools_count,tools_skipped=unittest_counts(tools)
    lab_skipped_scripts=lab_exclusions(root)
    for name in lab_skipped_scripts:
        print('CI-LAB-SKIP '+name+': not an offline test entry point; VM/router/network acceptance excluded')
    lab_count=lab_skipped=0
    for name in LAB_UNIT_TESTS:
        result=check([sys.executable,'-m','unittest','discover','-s','lab','-p',name,'-q'])
        count,skipped=unittest_counts(result);lab_count+=count;lab_skipped+=skipped
    crash=json.loads(check([sys.executable,'lab/test_process_crash.py']).stdout)
    if crash.get('failed')!=0 or crash.get('cases')!=20 or crash.get('passed')!=20:
        raise RuntimeError('CI-LAB-CRASH-COUNT')
    lab_count+=crash['passed']
    # This separate run proves actual Lua/CJSON execution, rather than counting skipped tests.
    lua=check([sys.executable,'-m','unittest','discover','-s','router/tests','-p','test_lua_contracts.py','-q'])
    lua_count,lua_skipped=unittest_counts(lua);lua_count-=lua_skipped
    if not args.runtime_only and (not shutil.which('lua5.1') or lua_count<=0):
        raise RuntimeError('CI-LUA-NOT-EXECUTED')
    lab_node_suites=0
    ui_count=0
    if not args.runtime_only:
        for name in LAB_NODE_TESTS:
            check(['node',str(root/'lab'/name)]);lab_node_suites+=1
        # The shipped page is generated from router/*.inc.js; a fresh build must equal the committed files. Line endings
        # are ignored: a Windows build writes CRLF and the package normalizes every text file to LF anyway.
        outputs=[root/'router/files/usr/lib/lua/luci/controller/homensai_vpn.lua',root/'router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json']
        ui=root/'router/files/www/luci-static/resources/view/homensai-vpn'
        def snapshot():
            lazy=root/'router/files/www/luci-static/resources/homensai-vpn'
            files={str(path.relative_to(root)):path.read_bytes().replace(b'\r\n',b'\n') for folder in (ui,lazy) if folder.exists() for path in folder.iterdir() if path.is_file()}
            files.update({str(path.relative_to(root)):path.read_bytes().replace(b'\r\n',b'\n') for path in outputs if path.is_file()})
            return files
        before=snapshot();check([sys.executable,'router/build_sidebar_ui.py']);after=snapshot()
        stale=sorted(name for name in set(before)|set(after) if before.get(name)!=after.get(name))
        if stale:raise RuntimeError('CI-UI-BUILD-STALE: '+', '.join(stale))
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
                     lua_available=bool(shutil.which('lua5.1')),lua_tests=lua_count,runtime_only=args.runtime_only,
                     tools_tests=tools_count,tools_skipped_tests=tools_skipped,
                     lab_tests=lab_count,lab_skipped_tests=lab_skipped,lab_node_suites=lab_node_suites,
                     lab_skipped_scripts=lab_skipped_scripts,
                     application_tests=int(re.search(r'Ran (\d+) tests',application.stderr).group(1)),
                     skipped_tests=int(re.search(r'skipped=(\d+)',application.stderr).group(1)) if 'skipped=' in application.stderr else 0,
                     qa_tests=int(re.search(r'Ran (\d+) tests',qa.stderr).group(1)),ui_suites=ui_count,
                     qa_skipped_tests=int(re.search(r'skipped=(\d+)',qa.stderr).group(1)) if 'skipped=' in qa.stderr else 0,
                     artifact=first.name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                     scope='isolated source archive; no physical/virtual router acceptance')
    print('CI-RECEIPT '+json.dumps(receipt,sort_keys=True))


if __name__=='__main__':main()
