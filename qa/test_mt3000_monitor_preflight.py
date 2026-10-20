"""Dedicated stock-target preflight against controlled read-only facts."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/'router-test-kit/00-mt3000-monitor-preflight.sh'


@unittest.skipUnless(os.name=='posix' and shutil.which('sh'),'isolated POSIX harness required')
class Mt3000MonitorPreflightTests(unittest.TestCase):
    def probe(self,**changes):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);calls=root/'calls'
            (root/'sitecustomize.py').write_text('''import os,ssl,subprocess,sys
class Context:
    def cert_store_stats(self):return {'x509_ca':1}
ssl.create_default_context=Context
def read_only(args,**kwargs):
    with open(os.environ['QA_CALLS'],'a') as stream:stream.write(' '.join(args)+'\\n')
    valid=args in (['ip','-4','-j','rule','show'],['ip','-4','-j','route','show','table','main'])
    return subprocess.CompletedProcess(args,0 if valid else 71,b'[]')
subprocess.run=read_only
if os.environ.get('QA_PY_OLD')=='1':sys.version_info=(3,8,20)
''',encoding='utf8')
            functions='''
ubus() { printf '{"board_name":"%s","model":"GL.iNet GL-MT3000","release":{"target":"%s"}}\\n' "$QA_BOARD" "$QA_TARGET"; }
jsonfilter() { cat >/dev/null; case "$2" in @.board_name) printf '%s\\n' "$QA_BOARD";; @.model) printf '%s\\n' "$QA_MODEL";; @.release.target) printf '%s\\n' "$QA_TARGET";; *) return 72;; esac; }
opkg() { printf 'opkg %s\\n' "$*" >> "$QA_CALLS"; case "$1" in print-architecture) printf 'arch all 1\\narch aarch64_cortex-a53 10\\n';; status) [ "$2" = homensai-auto-vpn ] && return 1; [ "$2" = "$QA_MISSING" ] && return 1; printf 'Package: %s\\nStatus: install user installed\\nVersion: 1.0\\n' "$2";; *) return 73;; esac; }
uci() { printf 'uci %s\\n' "$*" >> "$QA_CALLS"; case "$*" in '-q get homensai_vpn.main.monitor_only') printf '%s\\n' "$QA_MODE";; '-q get homensai_vpn.main.enabled') printf '1\\n';; '-q get homensai_vpn.main.native_enabled') printf '%s\\n' "$QA_NATIVE";; '-q changes homensai_vpn') printf '%s' "$QA_DELTA";; '-q get homensai_vpn.main.native_until'|'-q get homensai_vpn.main.native_trial'|'-q get homensai_vpn.main.native_prepare_acceleration') return 1;; *) return 74;; esac; }
cat() { if [ "$1" = /etc/glversion ]; then printf '%s\\n' "$QA_FIRMWARE"; else command cat "$@"; fi; }
uname() { case "$1" in -m) printf 'aarch64\\n';; -r) printf '5.4.211\\n';; *) return 75;; esac; }
df() { printf 'Filesystem 1K-blocks Used Available Use%% Mounted\\nroot 100000 1000 50000 1%% /overlay\\n'; }
nft() { printf 'nft %s\\n' "$*" >> "$QA_CALLS"; [ "$*" = 'list tables' ] || return 76; printf '%s\\n' "$QA_TABLES"; [ "$QA_NFT_FAIL" != 1 ]; }
ip() { return 77; }
lua() { cat >/dev/null; [ "$QA_LUA_FAIL" != 1 ]; }
python3() { printf 'python3 %s PYC=%s\\n' "$*" "$PYTHONDONTWRITEBYTECODE" >> "$QA_CALLS"; REAL_PYTHON "$@"; }
probe=$1
set -- --backup-receipt-sha256 "$QA_BACKUP"
. "$probe"
'''.replace('REAL_PYTHON',shlex.quote(sys.executable))
            env=dict(os.environ,PYTHONPATH=str(root),QA_CALLS=str(calls),QA_BOARD='glinet,mt3000-snand',
                     QA_TARGET='mediatek/mt7981',QA_MODEL='GL.iNet GL-MT3000',QA_FIRMWARE='4.11.0',QA_MODE='1',
                     QA_NATIVE='0',QA_DELTA='',QA_MISSING='',QA_TABLES='',QA_NFT_FAIL='0',QA_LUA_FAIL='0',QA_PY_OLD='0',QA_BACKUP='a'*64)
            env.update(changes)
            result=subprocess.run(['sh','-c',functions,'preflight-harness',str(SCRIPT)],env=env,cwd=root,
                                  capture_output=True,text=True,timeout=30)
            observed=calls.read_text().splitlines()
            self.assertFalse(any(line.startswith(('uci set','uci commit','opkg install','opkg update','nft -f')) for line in observed))
            self.assertEqual([line for line in observed if line.startswith('nft ')],['nft list tables'])
            self.assertNotIn('Traceback',result.stdout+result.stderr)
            return result

    def test_complete_synthetic_stock_facts_only_propose_monitor_review(self):
        result=self.probe()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('PASS\tMONITOR-CANDIDATE-REVIEW',result.stdout)
        self.assertIn('INSTALLATION\tNOT-AUTHORIZED-BY-PREFLIGHT',result.stdout)
        self.assertIn('NATIVE-SWITCH\tREFUSED-UNCERTIFIED-TARGET',result.stdout)
        self.assertIn('EXTERNAL-REVIEW-CLAIM\t'+'a'*64,result.stdout)

    def test_wrong_board_family_or_unreviewed_firmware_is_not_bypassed(self):
        for change in ({'QA_BOARD':'glinet,gl-mt6000'},{'QA_BOARD':'glinet,gl-mt3000'},
                       {'QA_TARGET':'mediatek/filogic'},{'QA_FIRMWARE':'4.8.2'}):
            with self.subTest(change=change):self.assertNotEqual(self.probe(**change).returncode,0)

    def test_missing_backup_mode_or_dependency_refuses(self):
        for change in ({'QA_BACKUP':''},{'QA_BACKUP':'not-a-hash'},{'QA_MODE':'0'},{'QA_MODE':'yes'},
                       {'QA_MISSING':'python3'},{'QA_PY_OLD':'1'},{'QA_LUA_FAIL':'1'}):
            with self.subTest(change=change):self.assertNotEqual(self.probe(**change).returncode,0)

    def test_uncertain_nft_or_owned_table_or_native_scope_refuses(self):
        for change in ({'QA_TABLES':'table inet homensai_vpn_guard'},{'QA_TABLES':'table inet homensai_vpn_fault'},
                       {'QA_NFT_FAIL':'1'},{'QA_NATIVE':'1'},{'QA_DELTA':"homensai_vpn.main.enabled='1'"}):
            with self.subTest(change=change):self.assertNotEqual(self.probe(**change).returncode,0)
