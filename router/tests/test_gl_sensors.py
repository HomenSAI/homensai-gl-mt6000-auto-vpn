"""GL sensors (docs/architecture/GL-SENSORS-2026-11-04.ru.md): WAN-down versus tunnel-down diagnosis, WireGuard hotplug
events, the passive stall sensor, k-of-n heartbeat targets, boot cause, keep.d and the masked diagnostic bundle.

Shared cases: gl_sensors_cases.json (gen_gl_sensors_cases.py); the Lua twin replays them in
tests/lua/test_gl_sensors.lua. The hand-written assertions below state the meaning of the important cases.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROUTER=HERE.parent
LIB=ROUTER/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB));sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROUTER))
import boot_cause  # noqa: E402
import diag_bundle  # noqa: E402
import failure_diagnosis  # noqa: E402
import gen_gl_sensors_cases  # noqa: E402
import gl_sensors  # noqa: E402
import interruption  # noqa: E402
import quorum  # noqa: E402
import stall  # noqa: E402
import wan_diag  # noqa: E402
import wg_events  # noqa: E402

CASES=json.loads((HERE/'gl_sensors_cases.json').read_text(encoding='ascii'))
SH=shutil.which('sh')


def by_name(section,name):
    return next(c for c in CASES[section] if c['name']==name)


class SharedCases(unittest.TestCase):
    @unittest.skipIf(os.environ.get('GL_SENSORS_MUTATION')=='1','mutation run: only the semantic tests may kill a mutant')
    def test_the_case_file_is_current(self):
        self.assertEqual((HERE/'gl_sensors_cases.json').read_text(encoding='ascii'),gen_gl_sensors_cases.text(),
                         'run python router/tests/gen_gl_sensors_cases.py')

    def test_enough_cases_of_every_kind(self):
        self.assertGreaterEqual(len(CASES['diagnose']),400)
        holds=[c for c in CASES['diagnose'] if c['expected']['hold']];hastens=[c for c in CASES['diagnose'] if c['expected']['hasten']]
        self.assertGreaterEqual(len(holds),10);self.assertGreaterEqual(len(hastens),5)


class Diagnosis(unittest.TestCase):
    def expect(self,name,verdict,code,hold,hasten):
        result=by_name('diagnose',name)['expected']
        self.assertEqual((result['verdict'],result['code'],result['hold'],result['hasten']),(verdict,code,hold,hasten),name)

    def test_named_verdicts(self):
        self.expect('healthy world','N',None,False,False)
        self.expect('WAN proven down by the underlay echo','WAN','WAN-DOWN',True,False)
        self.expect('WAN link down','WAN','WAN-DOWN',True,False)
        self.expect('kmwan offline','WAN','WAN-DOWN',True,False)
        self.expect('both bad, WAN proven up: provider','BOTH','DIAG-VPN-BOTH-DOWN',False,False)
        self.expect('primary bad, REKEY-GIVEUP, WAN up','TUNNEL','DIAG-TUNNEL-DOWN',False,True)
        self.expect('DNS on both','DNS','DIAG-DNS-FAILED',False,False)

    def test_unknown_wan_is_the_previous_behaviour(self):
        # no WAN evidence at all: never a hold and never a hasten, whatever the channels say
        for case in CASES['diagnose']:
            ev=case['evidence']
            if not any(ev.get(k) in v for k,v in (('underlay',('ok','fail')),('link',('down',)),('kmwan',('online','offline')))):
                self.assertFalse(case['expected']['hold'],case);self.assertFalse(case['expected']['hasten'],case)

    def test_hold_only_with_hard_wan_evidence_failing_primary_and_no_healthy_reserve(self):
        for case in CASES['diagnose']:
            ev=case['evidence'];result=case['expected']
            if result['hold']:
                self.assertTrue(case['enabled'])
                self.assertTrue(ev.get('underlay')=='fail' or ev.get('link')=='down' or ev.get('kmwan')=='offline',case)
                self.assertEqual(ev.get('primary'),'bad');self.assertNotEqual(ev.get('reserve'),'ok')
                self.assertGreaterEqual(result['posterior']['WAN'],950);self.assertEqual(result['code'],'WAN-DOWN')

    def test_hasten_only_with_the_wan_proven_up(self):
        for case in CASES['diagnose']:
            ev=case['evidence']
            if case['expected']['hasten']:
                self.assertTrue(ev.get('underlay')=='ok' or ev.get('kmwan')=='online',case)
                self.assertEqual((ev.get('primary'),ev.get('reserve')),('bad','ok'))
                self.assertFalse(case['expected']['hold'])

    def test_switched_off_never_holds_or_hastens_but_still_diagnoses(self):
        off=[c for c in CASES['diagnose'] if not c['enabled']]
        self.assertTrue(off)
        for case in off:self.assertFalse(case['expected']['hold']);self.assertFalse(case['expected']['hasten'])
        self.assertEqual(by_name('diagnose','WAN link down (switched off)')['expected']['verdict'],'WAN')

    def test_python_replays_every_shared_case(self):
        # the shared file is the reviewed specification of both runtimes (the Lua twin replays the same)
        for c in CASES['channel_state']:self.assertEqual(wan_diag.channel_state(c['row'],c['now'],c['age']),c['expected'],c['name'])
        for c in CASES['evidence']:self.assertEqual(wan_diag.evidence(c['rows'],c['pair'],c['now'],c['age'],**c['sensors']),c['expected'],c['name'])
        for c in CASES['underlay']:self.assertEqual(gen_gl_sensors_cases.run_underlay(c['ops']),c['expected'],c['name'])
        for c in CASES['tracker']:self.assertEqual(gen_gl_sensors_cases.run_tracker(c['ops']),c['expected'],c['name'])
        wg=CASES['wg'];parsed=wg_events.parse(wg['text'])
        for d,n,w,expected in wg['latest']:self.assertEqual(wg_events.latest(parsed,d,n,w),expected)
        reader=wg_events.Reader()
        for chunk,fresh,items in wg['reads']:
            got=reader.new(wg_events.parse(chunk))
            self.assertEqual([list(e) for e in got],fresh)
            self.assertEqual(wg_events.suspicions(got,[{'id':'wireguard:peer_1','device':'wgclient1'},{'id':'wireguard:peer_2','device':'wgclient2'},{'device':'wgclient2'}]),items)
        for names,data,remembered,expected in CASES['boot']['evidence']:
            self.assertEqual(list(boot_cause.crash_evidence(names,data,remembered)),expected)
        for key,fn in (('kmwan',wan_diag.kmwan_verdict),('portal',wan_diag.portal_verdict),('grace',wan_diag.grace_seconds)):
            for value,expected in CASES['simple'][key]:self.assertEqual(fn(value),expected,key)

    def test_posterior_is_a_distribution(self):
        for case in CASES['diagnose']:
            total=sum(case['expected']['posterior'].values())
            self.assertTrue(997<=total<=1003,case)
        for case in CASES['diagnose']:self.assertEqual(wan_diag.diagnose(case['evidence'],case['enabled']),case['expected'])

    def test_channel_states(self):
        expected={'healthy':'ok','one https only':'unknown','https failed':'bad','tunnel missing':'bad','black hole':'bad',
                  'dns only':'dns','stale':'unknown','future':'unknown','unverified':'unknown','no time':'unknown','boolean successes':'unknown'}
        for case in CASES['channel_state']:self.assertEqual(case['expected'],expected[case['name']],case['name'])

    def test_free_verdicts(self):
        self.assertEqual(dict((str(k),v) for k,v in CASES['simple']['kmwan']),{'None':None,'':None,'wan online metric 10':'online',
            'WAN OFFLINE':'offline','wan: offline\nwwan: online':'online','garbage':None})
        self.assertEqual([v for _,v in CASES['simple']['portal']],[None,'yes','no',None,None,None])
        self.assertEqual([v for _,v in CASES['simple']['grace']],[30,30,0,120,30,30,30,45])

    def test_underlay_needs_calibration_and_two_targets(self):
        self.assertEqual(by_name('underlay','never answered: a firewall is no WAN failure')['expected'][-1],None)
        seq=by_name('underlay','calibrated, then three failures over two targets')['expected']
        self.assertEqual([x for x in seq if x is not None or True][2:],[ 'ok',None,None,None,None,None,'fail',None,'ok'])
        self.assertIsNone(by_name('underlay','three failures to one target are not enough')['expected'][-1])
        self.assertEqual(by_name('underlay','ok ages out; stale is unknown')['expected'][-3:],['ok',None,None])
        self.assertIsNone(by_name('underlay','a new device starts uncalibrated')['expected'][-1])

    def test_tracker_holds_while_down_and_until_the_primary_was_rechecked(self):
        seq=by_name('tracker','down, back, primary healthy at once')['expected']
        self.assertEqual([s['code'] for s in seq],[None,'WAN-DOWN','WAN-DOWN','WAN-RECOVERING',None,None])
        self.assertEqual([s['restored'] for s in seq],[False,False,False,True,False,False])
        seq=by_name('tracker','back, primary still failing: grace ends the hold')['expected']
        self.assertEqual([s['hold'] for s in seq],[True,True,True,False,False])
        self.assertEqual([s['hold'] for s in by_name('tracker','grace 0: no recovering hold')['expected']],[True,False])
        self.assertEqual([s['hold'] for s in by_name('tracker','old healthy sample does not end the hold')['expected']],[True,True,True,False])
        self.assertEqual([s['hold'] for s in by_name('tracker','grace ends exactly at grace seconds')['expected']],[True,True,True,False])

    def test_failure_diagnosis_reads_the_hold(self):
        codes={c['name']:(c['expected']['code'],c['expected']['suppress_switch']) for c in CASES['diagnose_status']}
        self.assertEqual(codes['WAN-DOWN holds'],('WAN-DOWN',True))
        self.assertEqual(codes['WAN-RECOVERING holds'],('WAN-RECOVERING',True))
        self.assertEqual(codes['stale WAN verdict is ignored'],('HTTPS-FAILED',False))
        self.assertEqual(codes['hold false is ignored'],('HTTPS-FAILED',False))
        self.assertEqual(codes['another code is ignored'],('HTTPS-FAILED',False))
        self.assertEqual(codes['code must be a string'],('HTTPS-FAILED',False))
        self.assertEqual(codes['no WAN verdict: previous behaviour'],('HTTPS-FAILED',False))
        for case in CASES['diagnose_status']:
            self.assertEqual(failure_diagnosis.diagnose(case['status'],'a',case['now']),case['expected'])


class Stall(unittest.TestCase):
    def test_states(self):
        states={c['name']:[x['state'] for x in c['expected']] for c in CASES['stall']}
        self.assertEqual(states['tx grows, rx flat 3 s: stall'][-2:],['stall','stall'])
        self.assertNotIn('stall',states['rx moves: no stall'])
        self.assertEqual(states['rx flowing 10 kbit/s: veto'][-2:],['flowing','flowing'])
        self.assertEqual(states['rx stops: the veto ends at once'][-3:],['flowing','idle','idle'])
        self.assertNotIn('flowing',states['slow rx 4 kbit/s is no veto'])
        self.assertEqual(states['only rx drops (new device): starts again'],['idle']*5+['stall'])
        self.assertNotIn('stall',states['idle tunnel: no tx, no stall'])
        self.assertEqual(states['counter reset starts again'],['idle']*5+['stall'])
        self.assertEqual(states['gap starts again'],['idle']*4+['stall'])
        for case in CASES['stall']:
            s=stall.Stall();self.assertEqual([s.feed(*f) for f in case['feeds']],case['expected'])

    def test_constants_match_cake_autorate_threshold(self):
        self.assertEqual(stall.VETO_BYTES*8/stall.VETO_SECONDS,10000)  # 10 kbit/s
        self.assertEqual(stall.STALL_SECONDS,3)


class Quorum(unittest.TestCase):
    def test_rotation_and_quorum(self):
        last={c['name']:c['expected'][-1] for c in CASES['quorum']}
        self.assertEqual(last['one silent target rotates out after 3 misses']['targets'],['1.1.1.1','8.8.8.8','208.67.222.222'])
        self.assertEqual(last['two silent: the beat is lost, nothing rotates'],{'verdict':'lost','targets':['1.1.1.1','8.8.8.8','9.9.9.9'],'rotations':0})
        self.assertEqual(last['start offset and wrap']['targets'],['149.112.112.112','208.67.220.220','8.8.8.8'])
        for case in CASES['quorum']:self.assertEqual(gen_gl_sensors_cases.run_quorum(case['start'],case['beats']),case['expected'])

    def test_default_is_off(self):
        self.assertFalse(quorum.enabled({}));self.assertFalse(quorum.enabled({'heartbeat_quorum':False}))
        self.assertTrue(quorum.enabled({'heartbeat_quorum':True}))
        self.assertIn("main.heartbeat_quorum=s.heartbeat_quorum=='1'",(LIB/'inventory.lua').read_text(encoding='utf-8'))


class QuorumStudy(unittest.TestCase):
    """quorum_sim.py (simulator): the quorum is not better on every metric, so it ships off (option heartbeat_quorum)."""
    def test_trade_off(self):
        import quorum_sim
        out=quorum_sim.study(days=1,trials=150)
        cur,quo=out['current'],out['quorum']
        self.assertEqual((cur['echoes_per_beat'],quo['echoes_per_beat']),(1,3),'three times the echoes (CPU, traffic)')
        for key in ('healthy_0.01','healthy_0.05','filtered','flaky'):self.assertLess(quo[key],cur[key],key)
        self.assertEqual(quo['blackout'],cur['blackout'],'a full blackout is seen equally fast')
        self.assertLess(quo['partial_0.3']['detected_10s'],cur['partial_0.3']['detected_10s'],'30 % loss: the quorum is slower')
        self.assertFalse(quorum.enabled({}),'not strictly better -> default off')


class WireGuardEvents(unittest.TestCase):
    def test_parse_latest_reader(self):
        wg=CASES['wg']
        self.assertEqual([list(e) for e in wg_events.parse(wg['text'])],wg['parsed'])
        self.assertEqual([e[1] for e in wg['parsed']],['timeout','created','giveup','created'])
        self.assertEqual([x[3] for x in wg['latest']],['created','timeout','created',None,None,None])
        reads=wg['reads']
        self.assertEqual(reads[0][1],[],'the first read only marks the position (a restart replays nothing)')
        self.assertEqual([r['profile'] for r in reads[1][2]],['wireguard:peer_1'],'GIVEUP of the primary device; KEYPAIR is no suspicion')
        self.assertEqual(reads[2][1],[])
        self.assertEqual(reads[3][1],[],'a new boot (older uptime): the position moves back, nothing replayed')
        self.assertEqual([r['evidence'] for r in reads[4][2]],[{'event':'timeout'}])

    @unittest.skipUnless(SH and os.name=='posix','the router shell (busybox/dash/bash on Linux)')
    def test_hotplug_listener_writes_only_with_the_flag_and_valid_input(self):
        script=ROUTER/'files/etc/hotplug.d/wireguard/60-homensai'
        with tempfile.TemporaryDirectory() as d:
            up=Path(d)/'uptime';up.write_text('123.45 99.00\n')
            def fire(action,ifname,extra=''):
                env=dict(os.environ,HOMENSAI_WG_RUN=d,HOMENSAI_WG_UPTIME=str(up),ACTION=action,ifname=ifname)
                # hotplug-call sources the file; ubus is a one-line fake (CI /tmp is noexec: nothing is executed from it)
                line='ubus(){ echo "$*" >> "%s/ubus.log"; }; %s . "%s"'%(Path(d).as_posix(),extra,script.as_posix())
                return subprocess.run([SH,'-c',line],env=env,timeout=10)
            self.assertEqual(fire('REKEY-TIMEOUT','wgclient1').returncode,0)
            self.assertFalse((Path(d)/'wg-events.log').exists(),'no flag: nothing written')
            (Path(d)/'wg-events.on').write_text('file\n')
            fire('REKEY-TIMEOUT','wgclient1');fire('KEYPAIR-CREATED','wgclient2');fire('ADD','wgclient1');fire('REKEY-GIVEUP','wg;rm -rf x')
            fire('REKEY-GIVEUP','a'*16)
            text=(Path(d)/'wg-events.log').read_text()
            self.assertEqual(text,'123.45 REKEY-TIMEOUT wgclient1\n123.45 KEYPAIR-CREATED wgclient2\n')
            self.assertEqual(len(wg_events.parse(text)),2)
            self.assertFalse((Path(d)/'ubus.log').exists())
            (Path(d)/'wg-events.on').write_text('ubus\n')
            fire('REKEY-GIVEUP','wgclient1')
            self.assertIn('send homensai.wg {"action":"REKEY-GIVEUP","ifname":"wgclient1","uptime":"123.45"}',(Path(d)/'ubus.log').read_text())
            (Path(d)/'wg-events.log').write_text('1 REKEY-TIMEOUT wgclient1\n'*1000)
            fire('REKEY-TIMEOUT','wgclient1')
            lines=(Path(d)/'wg-events.log').read_text().splitlines()
            self.assertEqual(len(lines),61,'trimmed to the last 60 lines before the new one');self.assertEqual(lines[-1],'123.45 REKEY-TIMEOUT wgclient1')


class BootCause(unittest.TestCase):
    def test_shared(self):
        boot=CASES['boot']
        for text,fp in boot['fingerprint']:self.assertEqual(boot_cause.fingerprint(text),fp)
        self.assertEqual(boot['fingerprint'][0][1],'');self.assertEqual(boot['fingerprint'][2][1],'1:00000061')
        verdicts=[e[3][0] for e in boot['evidence']]
        self.assertEqual(verdicts,['none','unknown','crash','none','crash','none','none','none','crash','unknown'])
        planned=[p[4] for p in boot['planned']]
        self.assertEqual(planned,[True,True,False,False,False,False,True,True,True,True,False,False,False,False,True])
        for t,w,h,m,expected,reason in boot['planned']:
            self.assertEqual(boot_cause.planned(t,w,h,m),expected);self.assertEqual(reason,'planned-reboot' if expected else 'reboot')

    def test_evaluate_and_refresh_with_files(self):
        with tempfile.TemporaryDirectory() as d:
            persist=Path(d)/'persist';persist.mkdir();pstore=Path(d)/'pstore';pstore.mkdir();log=Path(d)/'crash_log'
            writes=[]
            def write(path,value):
                writes.append(path);Path(path).write_text(json.dumps(value))
            self.assertEqual(boot_cause.evaluate(persist,pstore=pstore,crash_log=log,write=write),'unknown','first boot after install')
            self.assertEqual(json.loads((persist/boot_cause.STATE).read_text()),{'crash_fp':''})
            self.assertEqual(boot_cause.evaluate(persist,pstore=pstore,crash_log=log,write=write),'none');self.assertEqual(len(writes),1,'unchanged: no write')
            log.write_text('Kernel panic\n')
            self.assertEqual(boot_cause.evaluate(persist,pstore=pstore,crash_log=log,write=write),'crash')
            self.assertEqual(boot_cause.evaluate(persist,pstore=pstore,crash_log=log,write=write),'none','remembered now')
            (pstore/'dmesg-ramoops-0').write_text('oops')
            self.assertEqual(boot_cause.evaluate(persist,pstore=pstore,crash_log=log,write=write),'crash','pstore not merged yet')
            log.write_text('Kernel panic\nmerged later\n')
            self.assertTrue(boot_cause.refresh(persist,crash_log=log,write=write),'a merge after our start is remembered')
            self.assertFalse(boot_cause.refresh(persist,crash_log=log,write=write))
            (pstore/'dmesg-ramoops-0').unlink()
            self.assertEqual(boot_cause.evaluate(persist,pstore=pstore,crash_log=log,write=write),'none','no false crash next boot')

    def test_classification(self):
        for case in CASES['interruption']['classify']:self.assertEqual(interruption.classify(case['facts']),case['expected'],case['name'])
        for text,expected in CASES['interruption']['reasons']:self.assertEqual(interruption.previous_reason(text),expected)
        self.assertIn('RESTART-PLANNED-REBOOT',interruption.TEXT);self.assertIn('RESTART-KERNEL-CRASH',interruption.TEXT)

    def test_start_asks_the_crash_verdict_only_on_the_first_start_of_a_boot(self):
        files={'/p/service-run.json':'{"state":"running","time":1}'};asked=[]
        def crash():asked.append(1);return 'crash'
        ctx={'runtime':'/r','persist':'/p','read':files.get,'mtime':lambda p:None,'write_ram':files.__setitem__,
             'write_persist':files.__setitem__,'now':lambda:100.0,'uptime':lambda:30.0,'log':lambda line:None,'record':None,'crash':crash}
        handle=interruption.start(ctx,None)
        self.assertEqual(handle['code'],'RESTART-KERNEL-CRASH');self.assertEqual(len(asked),1)
        handle=interruption.start(ctx,None)
        self.assertEqual(handle['code'],'RESTART-PROCESS');self.assertEqual(len(asked),1,'not fresh: not asked again')
        files.clear();files['/p/service-run.json']='{"state":"stopped","time":1,"reason":"planned-reboot"}'
        self.assertEqual(interruption.start(ctx,None)['code'],'RESTART-PLANNED-REBOOT')

    def test_init_script_stores_the_shutdown_reason(self):
        text=(ROUTER/'files/etc/init.d/homensai-vpn').read_text(encoding='utf-8')
        self.assertIn('shutdown() {\n    HOMENSAI_SHUTDOWN=1\n    stop\n}',text)
        self.assertIn('/usr/lib/homensai-vpn/lua/boot_cause.lua shutdown-reason',text)
        self.assertIn('case "$reason" in planned-reboot|reboot) ;; *) reason=reboot ;; esac',text)
        self.assertIn('\'{"state":"stopped","time":%s,"reason":"%s"}\'',text)


class SystemFiles(unittest.TestCase):
    def test_keep_list_is_exact_and_secret_free(self):
        lines=(ROUTER/'files/lib/upgrade/keep.d/homensai-vpn').read_text(encoding='ascii').splitlines()
        self.assertEqual(lines,['/etc/homensai-vpn/'+n for n in ('checkpoint.json','checkpoint.backup.json','native-history.json',
            'native-history.backup.json','speed-history.json','speed-history.backup.json','speed-quota.json','latency-history.json',
            'ping-response-history.json','website-response-history.json','response-compare.json','fault-history.json','switch-timing.json',
            'telegram-state.json','telegram-state.backup.json','stats-archive/',
            # review 04.11.2026 (finding 8): the pins of the servers' keys, the network journal, the advisor's log, the owner's own keys
            'server-keys.json','netjournal.json','advisor-changes.json','keys.local/',
            # the verified release history: without it a firmware upgrade silently loses the downgrade protection
            'chain.jsonl')])
        joined='\n'.join(lines)
        # the Telegram token lives in /etc/config/homensai_vpn (kept by GL's own conffile rule, not by us); state that
        # would make a reinstall start Auto or roll back a journal of the old firmware never survives a reflash
        for never in ('/etc/config/','auto-resume','native-stop','native-transaction','preparation-changes','session-recovery',
                      'pristine','service-run','pair-auto','native-certificate'):
            self.assertNotIn(never,joined)

    def test_download_whitelist_matches_the_bundle_only(self):
        import re
        lines=(ROUTER/'files/usr/share/gl-download.d/homensai-vpn').read_text(encoding='ascii').splitlines()
        self.assertEqual(lines,['/tmp/homensai-vpn-diag.tar.gz$'])
        self.assertTrue(re.search(lines[0],diag_bundle.OUTPUT))
        self.assertFalse(re.search(lines[0],'/tmp/homensai-vpn-diag.tar.gz.new'))

    def test_diag_cli_is_packaged_executable(self):
        import build_ipk
        self.assertIn('usr/sbin/homensai-vpn-diag',build_ipk.EXECUTABLE)
        self.assertIn('$(1)/usr/sbin/homensai-vpn-diag',(ROUTER/'Makefile').read_text())


class Bundle(unittest.TestCase):
    def test_mask_cases(self):
        by_line=dict((line,masked) for line,masked in CASES['mask']).get
        for line,expected in CASES['mask']:self.assertEqual(diag_bundle.mask(line),expected)
        masked='\n'.join(m for _,m in CASES['mask'])
        self.assertEqual(by_line('blob aGVsbG8gd29ybGQgdGhpcyBpcyBhIHRlc3Qga2V5MTI= tail'),'blob <key> tail')
        for secret in ('aGVsbG8gd29ybGQgdGhpcyBpcyBhIHRlc3Qga2V5MTI=','AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsawQ','supersecret','HomeNet','p@ss word',
                       '203.0.113.7','198.51.100.4','dd:ee:ff','-100123','ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef12345','187.40.16.19','203.0.113.1','203.0.113.9',
                       'hunter2hunter2','abcdef0123456789','myvpnuser','Kyiv ua65','-1001234567890','c4ff:fe12','HomeNet'):
            self.assertNotIn(secret,masked)
        for kept in ("network.wgclient1.addresses='10.0.0.2/32'","homensai_vpn.main.interval='10'",'latest handshake: 1 minute ago',
                     '12:34:56','Chain INPUT (policy ACCEPT): 0 packets','"code":null','"name":"x"'):
            self.assertIn(kept,masked)

    def test_audit_masks_public_addresses_free_text_secrets_eui64_and_names(self):
        def m(line):return diag_bundle.mask(line)
        mask=diag_bundle.MASK
        public=m('via 203.0.113.1 and 187.40.16.19 and 172.32.0.1')
        for address in ('203.0.113.1','187.40.16.19','172.32.0.1'):self.assertNotIn(address,public)
        self.assertEqual(len(set(__import__('re').findall(r'pub-[0-9a-f]{6}',public))),3)
        self.assertEqual(m('a 187.40.16.19 b 187.40.16.19'),'a %s b %s'%((m('187.40.16.19'),)*2),'one address, one label')
        self.assertEqual(m('203.0.113.1'),'pub-ea47da','the label is a fixed function of the address (the Lua twin must agree)')
        keep='192.168.8.1 10.0.0.1 172.16.5.5 172.31.255.1 100.64.0.1 127.0.0.1 169.254.1.1 224.0.0.251 0.0.0.0 255.255.255.0 1.2.3.4.5 999.1.1.1'
        self.assertEqual(m(keep),keep,'private, shared, loopback, link-local, multicast, masks and non-addresses stay')
        self.assertEqual(m('password=hunter2hunter2 token=abc123'),'password=%s token=%s'%(mask,mask))
        self.assertEqual(m('https://x/?token=abc&x=1&sig=zz'),'https://x/?token=%s&x=1&sig=%s'%(mask,mask))
        self.assertEqual(m('psk=%s'%('0f'*32)),'psk='+mask)
        self.assertEqual(m("SSID 'HomeNet'"),"SSID '%s'"%mask)
        self.assertEqual(m('chat_id=-1001234567890 sent'),'chat_id=%s sent'%mask)
        self.assertEqual(m('chat id: 1234567'),'chat id: '+mask)
        self.assertEqual(m('{"chat_id": -1001234567890, "count": 1234567}'),'{"chat_id": "%s", "count": 1234567}'%mask)
        self.assertEqual(m("\toption username 'bob'"),"\toption username '%s'"%mask)
        self.assertEqual(m("network.wg.description='Kyiv ua65'"),"network.wg.description='%s'"%mask)
        self.assertEqual(m('inet6 fe80::9683:c4ff:fe12:3456/64'),'inet6 <ipv6>/64')
        self.assertNotIn('c4ff',m('inet6 2001:db8:0:0:9683:c4ff:fe12:3456/64'))
        self.assertEqual(m('::1 ff02::1 12:34:56'),'::1 ff02::1 12:34:56')
        self.assertEqual(m("network.wg_key1.mtu='1420' keepalive=25"),"network.wg_key1.mtu='1420' keepalive=25",'only the last name decides')
        for line in ('password=hunter2hunter2 via 203.0.113.1','inet6 fe80::1:2:3:4 chat_id=-100123456'):
            self.assertEqual(m(m(line)),m(line),'masking twice changes nothing')

    def test_collect_uses_a_fresh_label_salt_per_bundle_and_restores_it(self):
        with tempfile.TemporaryDirectory() as d:
            labels=[]
            for index in range(2):
                out=os.path.join(d,'diag%d.tar.gz'%index)
                diag_bundle.collect(out,os.path.join(d,'work%d'%index),(('r.txt',('x',)),),run=lambda argv:'to 187.40.16.19\n')
                with tarfile.open(out) as archive:labels.append(archive.extractfile('homensai-vpn-diag/r.txt').read().decode())
            self.assertNotIn('187.40.16.19',''.join(labels))
            self.assertNotEqual(labels[0],labels[1],'the salt differs between bundles')
            self.assertEqual(diag_bundle.SALT,'')

    def test_collect_never_puts_the_stored_recipient_or_token_in_the_bundle(self):
        # F-14 (owner decision 07.11.2026): a bare stored chat id or @name (no key name, no "chat id" prefix) and the bot
        # token are masked wherever they appear; the list is restored after the bundle; odd values are not used.
        token='123456789:'+'A'*35
        lines='sendMessage to -1001234567890 ok\nposted @example_channel at 12:00\nurl /bot%s/sendMessage\nplain 1234567 stays\n'%token
        with tempfile.TemporaryDirectory() as d:
            out=os.path.join(d,'diag.tar.gz')
            diag_bundle.collect(out,os.path.join(d,'w'),(('log.txt',('x',)),),run=lambda argv:lines,
                                known=('-1001234567890','@example_channel',token,'12','not valid'))
            with tarfile.open(out) as archive:text=archive.extractfile('homensai-vpn-diag/log.txt').read().decode()
        for secret in ('1001234567890','example_channel',token,'A'*30):self.assertNotIn(secret,text)
        self.assertIn('plain 1234567 stays',text,'only the stored values, not every number')
        self.assertEqual(diag_bundle.KNOWN,())
        self.assertEqual(diag_bundle.known_values(['-1001234567890\n',' @example_channel ','12','@ab','x'*40,None]),
                         ('@example_channel','-1001234567890'))   # longest first
        # a test collector without known values reads nothing from uci and still works
        with tempfile.TemporaryDirectory() as d,patch.object(diag_bundle,'read_known',side_effect=AssertionError('uci read')):
            diag_bundle.collect(os.path.join(d,'o.tar.gz'),os.path.join(d,'w'),(('r.txt',('x',)),),run=lambda argv:'ok\n')

    def test_collect_masks_and_packs_with_mode_0600(self):
        with tempfile.TemporaryDirectory() as d:
            out=os.path.join(d,'diag.tar.gz');work=os.path.join(d,'diag')
            commands=(('uci.txt',('uci','show','network')),('wg.txt',('wg','show','all')))
            fake={('uci','show','network'):"network.wg.private_key='k'\nnetwork.wg.mtu='1420'\n",
                  ('wg','show','all'):'  preshared key: abc\n  transfer: 1 MiB received\n'}
            self.assertEqual(diag_bundle.collect(out,work,commands,run=lambda argv:fake[tuple(argv)]),out)
            self.assertFalse(os.path.exists(work),'the work folder is removed')
            if os.name=='posix':self.assertEqual(stat.S_IMODE(os.stat(out).st_mode),0o600)
            with tarfile.open(out) as archive:
                names=sorted(archive.getnames())
                self.assertEqual(names,['homensai-vpn-diag','homensai-vpn-diag/uci.txt','homensai-vpn-diag/wg.txt'])
                text=archive.extractfile('homensai-vpn-diag/uci.txt').read().decode()+archive.extractfile('homensai-vpn-diag/wg.txt').read().decode()
            self.assertIn("private_key='***'",text);self.assertIn("mtu='1420'",text);self.assertIn('preshared key: ***',text)
            self.assertNotIn("'k'",text)

    @unittest.skipUnless(os.name=='posix' and hasattr(os,'symlink'),'symlinks need POSIX')
    def test_collect_never_writes_through_planted_symlinks(self):
        # R3-01: a local process plants symlinks at the old predictable names; root must not truncate their targets
        with tempfile.TemporaryDirectory() as d:
            victim=os.path.join(d,'victim');open(victim,'w').write('keep me\n')
            out=os.path.join(d,'homensai-vpn-diag.tar.gz')
            os.symlink(victim,out+'.new')
            os.symlink(os.path.join(d,'elsewhere'),os.path.join(d,'homensai-vpn-diag'))
            self.assertEqual(diag_bundle.collect(out,commands=(('r.txt',('x',)),),run=lambda argv:'ok\n'),out)
            self.assertEqual(open(victim).read(),'keep me\n','the symlink target is never written')
            self.assertFalse(os.path.islink(out));self.assertEqual(stat.S_IMODE(os.stat(out).st_mode),0o600)
            self.assertFalse(os.path.exists(os.path.join(d,'elsewhere')))
            left=sorted(os.listdir(d))
            self.assertEqual(left,['homensai-vpn-diag','homensai-vpn-diag.tar.gz','homensai-vpn-diag.tar.gz.new','victim'],'no private folder left')
            # a symlink at the final path is refused (not followed), and nothing is left behind
            os.remove(out);os.symlink(victim,out)
            with self.assertRaises(OSError):diag_bundle.collect(out,commands=(('r.txt',('x',)),),run=lambda argv:'ok\n')
            self.assertEqual(open(victim).read(),'keep me\n')
            self.assertEqual(sorted(os.listdir(d)),left)
            # an explicit work folder that already exists (here a planted symlink) is an error, never reused
            os.remove(out)
            with self.assertRaises(OSError):diag_bundle.collect(out,os.path.join(d,'homensai-vpn-diag'),(('r.txt',('x',)),),run=lambda argv:'ok\n')
            self.assertFalse(os.path.exists(out))

    def test_collect_failure_leaves_nothing_behind(self):
        def boom(argv):raise RuntimeError('collector failed')
        with tempfile.TemporaryDirectory() as d:
            out=os.path.join(d,'diag.tar.gz')
            with self.assertRaises(RuntimeError):diag_bundle.collect(out,commands=(('r.txt',('x',)),),run=boom)
            self.assertEqual(os.listdir(d),[])

    def test_commands_are_read_only(self):
        for name,argv in diag_bundle.COMMANDS:
            self.assertIn(argv[0],('cat','free','ip','nft','iptables-save','wg','tc','uci','ubus','logread','dmesg'),name)
            if argv[0]=='uci':self.assertEqual(argv[1],'show')
            if argv[0]=='ubus':self.assertEqual(argv[1:],('call','repeater','status'))
            if argv[0]=='ip':self.assertIn(argv[2],('rule','route','addr'));self.assertEqual(argv[3],'show')
            if argv[0]=='nft':self.assertEqual(argv[1:],('list','ruleset'))
            if argv[0]=='tc':self.assertEqual(argv[1:3],('-s','qdisc'))
        lua=(LIB/'lua/diag_bundle.lua').read_text(encoding='utf-8')
        for name,argv in diag_bundle.COMMANDS:
            self.assertIn("{'%s',{%s}}"%(name,','.join("'%s'"%a for a in argv)),lua,'the Lua twin runs the same commands')


class MonitorSide(unittest.TestCase):
    """gl_sensors.Sensors (agent.py) with fakes: no socket, no file outside a temporary folder."""
    def sensors(self,d,answers):
        sent=[]
        def echo(device,target):
            sent.append((device,target));return answers(len(sent))
        files={}
        s=gl_sensors.Sensors(d,d,echo=echo,read=lambda p:files.get(p),key=lambda p:files.get(p),
                             repeater=lambda:'{"portal":false}',uptime=lambda:1000.0)
        return s,sent,files

    def rows(self,now,primary='VPN-003',reserve='VPN-003'):
        def row(i,code):
            r={'id':i,'device':'wgclient'+i[-1],'time':now-1,'code':code}
            if code is None:r.update(dns_ok=True,https_success=3)
            return r
        return [row('wireguard:peer_1',primary),row('wireguard:peer_2',reserve)]

    def test_wan_down_hold_then_recovering_then_clear(self):
        with tempfile.TemporaryDirectory() as d:
            state={'up':True}
            s,sent,_=self.sensors(d,lambda n:state['up'])
            pair={'source':'wireguard:peer_1','target':'wireguard:peer_2'}
            settings={'wan_sensor':True,'wg_events':True,'wan_recover_grace':30}
            s.configure(settings,[{'device':'apcli0'}],self.rows(100),pair)
            self.assertFalse(os.path.exists(os.path.join(d,'wg-events.on')),'a pass writes nothing')
            s.tick(0)  # calibrated
            self.assertTrue(os.path.exists(os.path.join(d,'wg-events.on')),'the 1 s loop keeps the listener flag')
            state['up']=False
            for t in (2,4,6):s.alert=True;s.tick(t)
            self.assertEqual([x[1] for x in sent],['1.1.1.1','8.8.8.8','9.9.9.9','208.67.222.222'])
            s.uptime=lambda:6.0
            result=s.pass_(self.rows(100),pair,100,90,settings,{'state':'LINK-UP','time':99})
            self.assertEqual((result['code'],result['hold'],result['evidence']['underlay']),('WAN-DOWN',True,'fail'))
            self.assertTrue(s.alert)
            d1=failure_diagnosis.diagnose({'time':100,'profiles':[dict(self.rows(100)[0],interface='wgclient1')],'wan_diagnosis':result},'wireguard:peer_1',100)
            self.assertEqual((d1['code'],d1['suppress_switch']),('WAN-DOWN',True))
            state['up']=True;s.tick(8)
            s.uptime=lambda:8.0
            result=s.pass_(self.rows(110),pair,110,90,settings,{'state':'LINK-UP','time':109})
            self.assertEqual((result['code'],result['hold'],result['recovering']),('WAN-RECOVERING',True,True));self.assertTrue(s.restored)
            result=s.pass_(self.rows(120,primary=None),pair,120,90,settings,{'state':'LINK-UP','time':119})
            self.assertFalse(result['hold']);self.assertNotEqual(result['code'],'WAN-RECOVERING')

    def test_a_failed_echo_raises_the_cadence(self):
        with tempfile.TemporaryDirectory() as d:
            answers=[True,False,False]
            s,sent,_=self.sensors(d,lambda n:answers[min(n,3)-1])
            pair={'source':'wireguard:peer_1','target':'wireguard:peer_2'}
            s.configure({},[{'device':'eth0'}],self.rows(100,None,None),pair)
            s.tick(0);s.tick(5);self.assertEqual(len(sent),1,'healthy: one echo per 10 s')
            s.tick(10);self.assertEqual(len(sent),2)
            s.pass_(self.rows(100,None,None),pair,100,90,{},{'state':'LINK-UP','time':99})
            self.assertTrue(s.alert,'one failed echo: alert even with both channels healthy')
            s.tick(12);self.assertEqual(len(sent),3,'alert: every 2 s')

    def test_switched_off_no_echo_no_flag_no_hold(self):
        with tempfile.TemporaryDirectory() as d:
            s,sent,_=self.sensors(d,lambda n:False)
            open(os.path.join(d,'wg-events.on'),'w').close()
            settings={'wan_sensor':False,'wg_events':False}
            pair={'source':'wireguard:peer_1','target':'wireguard:peer_2'}
            s.configure(settings,[{'device':'apcli0'}],self.rows(100),pair)
            for t in range(0,30,2):s.tick(t)
            self.assertEqual(sent,[]);self.assertFalse(os.path.exists(os.path.join(d,'wg-events.on')))
            result=s.pass_(self.rows(100),pair,100,90,settings,{'state':'DOWN','time':99})
            self.assertFalse(result['hold']);self.assertFalse(result['enabled'])

    def test_rekey_event_of_a_pair_device_is_a_suspicion(self):
        with tempfile.TemporaryDirectory() as d:
            s,_,files=self.sensors(d,lambda n:True)
            pair={'source':'wireguard:peer_1','target':'wireguard:peer_2'}
            s.configure({},[],self.rows(100),pair)
            path=os.path.join(d,'wg-events.log')
            files[path]='5 KEYPAIR-CREATED wgclient1\n'
            self.assertEqual(s.tick(10),[])
            files[path]+='11 REKEY-TIMEOUT wgclient1\n12 REKEY-GIVEUP wgclient9\n'
            self.assertEqual(s.tick(11),[{'profile':'wireguard:peer_1','reason':'wg-rekey','evidence':{'event':'timeout'}}])
            self.assertEqual(s.tick(12),[],'an unchanged file is not read again')

    def test_agent_wiring(self):
        text=(LIB/'agent.py').read_text(encoding='utf-8')
        self.assertIn("status['wan_diagnosis']=gl.pass_(",text)
        self.assertIn("items=gl.tick(time.monotonic())",text)
        self.assertIn("'reason':'wan-ok-tunnel-down'",text)
        self.assertIn("watcher.stall_seconds=GL_STALL_SECONDS if stall_enabled(settings) else OLD_STALL_SECONDS",text)
        import probe_policy
        for reason in ('wg-rekey','wan-ok-tunnel-down','rx-stall'):self.assertIn(reason,probe_policy.SUSPICION_REASONS)
        lua=(LIB/'lua/probe_policy.lua').read_text(encoding='utf-8')
        self.assertIn("['wg-rekey']=true,['wan-ok-tunnel-down']=true",lua)
        self.assertIn('wan_diagnosis=true',(LIB/'lua/auto_control.lua').read_text(encoding='utf-8'))

    def test_suspicion_watcher_uses_the_configured_stall_window(self):
        import suspicion
        samples=[{'ifindex':5,'rx_bytes':100,'tx_bytes':1000+400*i,'rx_packets':1,'tx_packets':10+5*i,'tx_dropped':0} for i in range(10)]
        def run(seconds):
            w=suspicion.SuspicionWatcher(counters=lambda device:samples[min(run.i,9)],handshake=lambda device:0)
            w.stall_seconds=seconds
            w.configure([{'id':'openvpn:1_2','role':'source','device':'ovpnclient1','protocol':'openvpn'}])
            for t in range(10):
                run.i=t
                found=w.poll(float(t),1000.0+t)
                if found:return t
            return None
        run.i=0
        self.assertEqual(run(stall.STALL_SECONDS),3);self.assertEqual(run(suspicion.STALL_SECONDS),6)

    def test_settings_parse_in_inventory(self):
        lua=(LIB/'inventory.lua').read_text(encoding='utf-8')
        for line in ("main.wan_sensor=s.wan_sensor~='0'","main.wg_events=s.wg_events~='0'","main.stall_sensor=s.stall_sensor~='0'",
                     "main.stall_veto=s.stall_veto~='0'","main.heartbeat_quorum=s.heartbeat_quorum=='1'"):
            self.assertIn(line,lua)


if __name__=='__main__':
    unittest.main()
