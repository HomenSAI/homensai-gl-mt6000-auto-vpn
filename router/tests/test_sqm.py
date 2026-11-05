"""Optional SQM (cake) on the VPN tunnel egress: sqm.py, its monitor wiring and the init script's release.

Shared cases with the Lua twin: tests/sqm_cases.json (tests/lua/test_sqm.lua). tc is faked: no router is touched.
"""
import json
import shlex
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT/'files/usr/lib/homensai-vpn'))
import sqm  # noqa: E402

CASES=json.loads((HERE/'sqm_cases.json').read_text(encoding='utf-8'))


class FakeTc:
    def __init__(self,devices,fail_replace=False,missing_tc=False):
        self.roots={name:list(root) for name,root in devices.items()};self.fail_replace=fail_replace;self.missing=missing_tc
        self.commands=[]

    def __call__(self,argv):
        self.commands.append(' '.join(argv))
        if self.missing:return 127,''
        assert argv[:2]==['tc','qdisc'] and argv[3]=='dev' and argv[5]=='root',argv
        verb,device=argv[2],argv[4]
        if device not in self.roots:return 1,''
        if verb=='show':
            kind,handle=self.roots[device];return 0,'qdisc %s %s root refcnt 2 \n'%(kind,handle)
        if verb=='replace':
            if self.fail_replace:return 2,''
            self.roots[device]=['cake','8001:'];return 0,''
        if verb=='del':
            self.roots[device]=['noqueue','0:'];return 0,''
        raise AssertionError(argv)


class SharedCases(unittest.TestCase):
    def test_sync(self):
        for case in CASES['sync']:
            settings=CASES['on'] if case['settings']=='on' else case['settings']
            tc=FakeTc(case['devices'],case.get('fail_replace',False),case.get('missing_tc',False))
            state,report=sqm.sync(settings,case['rows'],case['state'],tc,case['now'])
            self.assertEqual(tc.commands,case['commands'],case['name'])
            self.assertEqual(report['code'],case['code'],case['name'])
            self.assertEqual(report['devices'],case['result'],case['name'])
            self.assertEqual(state,{'schema':1,'devices':case['records']},case['name'])
            self.assertEqual(tc.roots,case['roots'],case['name'])

    def test_release(self):
        for case in CASES['release']:
            tc=FakeTc(case['devices'])
            state,failed=sqm.release(case['state'],tc)
            self.assertEqual(tc.commands,case['commands'],case['name'])
            self.assertEqual(failed,case['failed']);self.assertEqual(state,{'schema':1,'devices':[]})
            self.assertEqual(tc.roots,case['roots'])

    def test_config_and_root_qdisc(self):
        for settings,kbit,code in CASES['config']:self.assertEqual(sqm.config(settings),(kbit,code),repr(settings))
        for text,expect in CASES['root_qdisc']:self.assertEqual(sqm.root_qdisc(text),tuple(expect) if expect else None,repr(text))


class Safety(unittest.TestCase):
    def test_only_the_tunnel_root_qdisc_is_ever_named(self):
        self.assertEqual(sqm.cake_argv('wgclient1',18000),
                         ['tc','qdisc','replace','dev','wgclient1','root','cake','bandwidth','18000kbit','besteffort','triple-isolate','nat'])
        self.assertEqual(sqm.delete_argv('wgclient1'),['tc','qdisc','del','dev','wgclient1','root'])

    def test_off_costs_nothing(self):
        self.assertFalse(sqm.active({'sqm_enabled':False,'sqm_upload_kbit':18000},{}))
        self.assertFalse(sqm.active({'sqm_enabled':True,'sqm_upload_kbit':0},{}))
        self.assertTrue(sqm.active(CASES['on'],{}))
        self.assertTrue(sqm.active({},{'devices':[{'device':'wgclient1','ifindex':1,'kbit':1000,'checked':1}]}))

    def test_a_failed_restore_keeps_the_record_and_reports(self):
        def stuck(argv):
            return (0,'qdisc cake 8001: root refcnt 2 \n') if argv[2]=='show' else (2,'')
        state={'devices':[{'device':'wgclient1','ifindex':12,'kbit':18000,'checked':1}]}
        new,report=sqm.sync({'sqm_enabled':False},[{'device':'wgclient1','ifindex':12}],state,stuck,10)
        self.assertEqual(report['devices'],{'wgclient1':'restore-failed'});self.assertEqual(report['code'],'SQM-RESTORE-FAILED')
        self.assertEqual(len(new['devices']),1)
        new,failed=sqm.release(state,stuck);self.assertEqual(failed,['wgclient1']);self.assertEqual(len(new['devices']),1)

    def test_executor_reports_a_missing_tc(self):
        self.assertEqual(sqm.execute(['/nonexistent/tc-homensai-test'])[0],127)

    def test_inventory_reads_both_options_strictly(self):
        source=(ROOT/'files/usr/lib/homensai-vpn/inventory.lua').read_text(encoding='utf-8')
        self.assertIn("main.sqm_enabled=s.sqm_enabled=='1'",source)
        self.assertIn('sqm_kbit>=1000 and sqm_kbit<=1000000',source)


@unittest.skipIf(os.name!='posix','the init script runs under a POSIX shell')
class InitScriptRelease(unittest.TestCase):
    """stop_service's sqm_release: from the RAM state file, only where the root is still cake."""

    def run_release(self,state,roots):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);log=d/'tc.log'
            roots_file=d/'roots.json';roots_file.write_text(json.dumps(roots))
            # tc qdisc <verb> dev <device> root, over a JSON table of root qdiscs
            (d/'faketc.py').write_text('import json,sys\nroots=json.load(open(%r))\nverb,device=sys.argv[2],sys.argv[4]\n'
                'if device not in roots:sys.exit(1)\n'
                'if verb=="show":print("qdisc %%s %%s root refcnt 2 "%%tuple(roots[device]))\n'
                'elif verb=="del":roots[device]=["noqueue","0:"];json.dump(roots,open(%r,"w"))\n'
                'else:sys.exit(2)\n'%(str(roots_file),str(roots_file)))
            # jsonfilter -i <file> -e '@.devices[*].device'
            (d/'fakejf.py').write_text('import json,sys\nfor row in json.load(open(sys.argv[2]))["devices"]:print(row["device"])\n')
            # tc and jsonfilter as shell functions (command -v finds them): temp directories may be mounted noexec (CI)
            fakes=('tc() { echo "$*" >>%s; %s %s "$@"; }\njsonfilter() { %s %s "$@"; }\n'
                   %(shlex.quote(str(log)),shlex.quote(sys.executable),shlex.quote(str(d/'faketc.py')),
                     shlex.quote(sys.executable),shlex.quote(str(d/'fakejf.py'))))
            run=d/'run';run.mkdir();state_file=run/'sqm-state.json';state_file.write_text(json.dumps(state))
            script=(ROOT/'files/etc/init.d/homensai-vpn').read_text(encoding='utf-8')
            body=script[script.index('sqm_release() {'):]
            body=body[:body.index('\n}\n')+3].replace('/var/run/homensai-vpn/sqm-state.json',str(state_file))
            subprocess.run(['sh','-c',fakes+body+'sqm_release\n'],check=True,timeout=30)
            commands=log.read_text().splitlines() if log.exists() else []
            return commands,json.loads(roots_file.read_text()),state_file.exists()

    def test_cake_goes_back_other_roots_and_bad_names_untouched(self):
        state={'schema':1,'devices':[{'device':'wgclient1','ifindex':12,'kbit':18000,'checked':1},
                                     {'device':'ovpnclient2','ifindex':14,'kbit':18000,'checked':1},
                                     {'device':'bad;name','ifindex':15,'kbit':18000,'checked':1}]}
        commands,roots,exists=self.run_release(state,{'wgclient1':['cake','8001:'],'ovpnclient2':['htb','1:']})
        self.assertEqual(commands,['qdisc show dev wgclient1 root','qdisc del dev wgclient1 root','qdisc show dev ovpnclient2 root'])
        self.assertEqual(roots,{'wgclient1':['noqueue','0:'],'ovpnclient2':['htb','1:']});self.assertFalse(exists)

    def test_stop_service_calls_it_after_the_monitor_hook(self):
        script=(ROOT/'files/etc/init.d/homensai-vpn').read_text(encoding='utf-8')
        stop=script[script.index('stop_service() {'):]
        self.assertLess(stop.index('call homensai-vpn-lua shutdown'),stop.index('    sqm_release\n'))


class MonitorWiring(unittest.TestCase):
    def test_both_monitors_reconcile_and_release(self):
        agent=(ROOT/'files/usr/lib/homensai-vpn/agent.py').read_text(encoding='utf-8')
        self.assertIn('sqm.sync(settings,measured,sqm_state,sqm.execute,time.monotonic())',agent)
        self.assertIn('sqm.release(sqm_state,sqm.execute)',agent)
        monitor=(ROOT/'files/usr/lib/homensai-vpn/lua/monitor.lua').read_text(encoding='utf-8')
        self.assertIn('self:sqm_pass(settings,measured,status)',monitor)
        self.assertIn('pcall(function() self:sqm_release() end)',monitor)


if __name__=='__main__':
    unittest.main()
