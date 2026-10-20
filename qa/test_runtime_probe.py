"""Execute the supplemental probe against fake read-only command boundaries."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

PROBE=Path(__file__).resolve().parents[1]/'router-test-kit/00-runtime-probe.sh'


@unittest.skipUnless(os.name=='posix' and shutil.which('sh'),'isolated POSIX probe harness required')
class RuntimeProbeTests(unittest.TestCase):
    def exercise(self,probe=PROBE,status='install ok installed'):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);calls=root/'calls'
            # CI tmpfs is deliberately noexec. Shell functions and an explicit
            # child-only subprocess stub exercise the boundaries without making
            # that filesystem executable or calling the host's network tools.
            (root/'sitecustomize.py').write_text('''import os,subprocess
def fake_run(args,**kwargs):
    with open(os.environ['QA_CALLS'],'a') as stream:stream.write(' '.join(args)+'\\n')
    key=tuple(args)
    outputs={('ip','-4','-j','rule','show'):b'[{"private":"PRIVATE_ROUTE_SENTINEL"}]',
             ('ip','-4','-j','route','show','table','main'):b'[{"private":"PRIVATE_ROUTE_SENTINEL"}]',
             ('nft','-j','list','tables'):b'{"nftables":[{"private":"PRIVATE_TABLE_SENTINEL"}]}',
             ('ubus','list'):b'session\\nfile\\nPRIVATE_OBJECT_SENTINEL\\n'}
    return subprocess.CompletedProcess(args,0 if key in outputs else 71,outputs.get(key,b''))
subprocess.run=fake_run
''',encoding='utf8')
            functions='''
python3() { printf 'python3 %s PYC=%s\\n' "$*" "$PYTHONDONTWRITEBYTECODE" >> "$QA_CALLS"; REAL_PYTHON "$@"; }
opkg() { printf 'opkg %s\\n' "$*" >> "$QA_CALLS"; [ "$1" = status ] || return 72; printf 'Package: %s\\nVersion: 1.2.3\\nStatus: %s\\n' "$2" "$QA_STATUS"; }
lua() { printf 'lua %s\\n' "$*" >> "$QA_CALLS"; cat >/dev/null; printf 'lua_uci_import\\tPRESENT\\nlua_uci_cursor_api\\tPRESENT\\nlua_cjson_roundtrip\\tPRESENT\\n'; }
ip() { return 73; }
nft() { return 74; }
ubus() { return 75; }
fw4() { printf 'ILLEGAL fw4\\n' >> "$QA_CALLS"; return 76; }
rpcd() { printf 'ILLEGAL rpcd\\n' >> "$QA_CALLS"; return 77; }
uhttpd() { printf 'ILLEGAL uhttpd\\n' >> "$QA_CALLS"; return 78; }
. "$1"
'''.replace('REAL_PYTHON',shlex.quote(sys.executable))
            env=dict(os.environ,PYTHONPATH=str(root),QA_CALLS=str(calls),QA_STATUS=status)
            result=subprocess.run(['sh','-c',functions,'probe-harness',str(probe)],cwd=root,env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertNotIn('SENTINEL',result.stdout)
            rows=dict(line.split('\t',1) for line in result.stdout.splitlines())
            observed=calls.read_text().splitlines()
            self.assertFalse(list(root.rglob('__pycache__')))
            return rows,observed

    def test_probe_only_reads_tools_never_emits_raw_routes_and_disables_python_bytecode(self):
        rows,observed=self.exercise()
        self.assertEqual(rows['python_dictionary_union'],'PRESENT')
        self.assertEqual(rows['ip_rules_json'],'READABLE')
        self.assertEqual(rows['ip_main_routes_json'],'READABLE')
        self.assertEqual(rows['nft_tables_json'],'READABLE')
        self.assertEqual(rows['installation'],'NOT_AUTHORIZED_BY_PROBE')
        self.assertEqual(rows['native_switch'],'REFUSED_UNCERTIFIED_TARGET')
        self.assertEqual(rows['kernel_timeout_set_test'],'NOT_PERFORMED')
        self.assertIn('python3 -B - PYC=1',observed)
        self.assertEqual([line for line in observed if line.startswith('nft ')],['nft -j list tables'])
        self.assertTrue(all(line.startswith(('python3 -B - PYC=1','opkg status ','ip -4 -j rule show',
                                           'ip -4 -j route show table main','nft -j list tables','ubus list','lua -'))
                            for line in observed),observed)

    def test_both_scripts_accept_installed_ok_or_user_and_refuse_partial_or_conflicting_states(self):
        for script in (PROBE,PROBE.with_name('00-platform-probe.sh')):
            for status,installed in (('install ok installed',True),('install user installed',True),
                    ('deinstall ok installed',False),('install ok unpacked',False),('install user not-installed',False),
                    ('install broken installed',False),('install ok installed\nStatus: install user installed',False)):
                with self.subTest(script=script.name,status=status):
                    rows,unused=self.exercise(script,status)
                    expected='1.2.3' if installed else 'MISSING'
                    if script==PROBE:self.assertEqual(rows['package_version:lua'],expected)
                    else:self.assertEqual(rows['package_lua'],'INSTALLED' if installed else 'MISSING')
