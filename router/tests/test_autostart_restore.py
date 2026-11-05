"""After the owner's Stop the GL VPN dashboard manages the pair's tunnels again (MT3000, 03.11.2026).

Start's preparation sets network.<tunnel>.auto=0 (PREP-*-AUTOSTART) so that only Auto brings the pair up. With Auto
stopped, toggling the tunnel in the GL VPN dashboard did nothing. preparation_control.restore_autostart puts back the
value each before-record saved - only after the owner's own Stop, with a settled route, for flags that still read the
app's '0' - and removes the undone records. Real records are written by preparation_control.apply; the UCI reads and
the Lua writer are fakes (the writer itself: test_preparation_lua.py).
Owner decision 03.11.2026 (integration alpha8): the same Stop also puts back the stock GL vpn-client start link
(/etc/rc.d/S95vpn-client) that the 'vpn-boot' preparation removed - under the same conditions, only while no start link
exists and the other links are as recorded; nothing is started (no init script runs).
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,auto_control,native_switch,pair_auto  # noqa: E401
import configuration_guard
import preparation_control as p


class Fixture(unittest.TestCase):
    def start(self,mock):
        result=mock.start();self.addCleanup(mock.stop);return result

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.runtime=self.root/'run';self.persist=self.root/'persist'
        for name in ('run','persist','etc/config','etc/init.d','etc/rc.d','etc/modules.d','tmp/sysinfo','proc/sys/kernel/random'):
            (self.root/name).mkdir(parents=True,exist_ok=True)
        (self.root/'tmp/sysinfo/board_name').write_text('glinet,mt3000-snand')
        (self.root/'etc/glversion').write_text('4.11.0')
        (self.root/'proc/sys/kernel/random/boot_id').write_text('11111111-1111-1111-1111-111111111111')
        for name in p.PACKAGES:(self.root/'etc/config'/name).write_text('private fixture '+name+'\n')
        # wgclient1: auto unset by GL (the owner's new client); ovpnclient1: auto '1'; wgclient2: never prepared
        self.values={'wgclient1':{'proto':'wgclient','auto':None},'ovpnclient1':{'proto':'ovpnclient','auto':'1'},
                     'wgclient2':{'proto':'wgclient','auto':'0'},'hnat':'0','hnat_type':'mtkhnat','defaults':[]}
        for module in (p,agent,auto_control):
            for key,value in (('RUNTIME',self.runtime),('PERSIST',self.persist)):
                if hasattr(module,key):self.start(patch.object(module,key,value))
        self.start(patch.object(p,'ROOT',self.root))
        self.start(patch.object(p,'inventory',return_value={'settings':{'router_model':'auto'}}))
        self.start(patch.object(configuration_guard,'blocked',return_value=None))
        self.state={};self.intent={};self.journal={}
        self.start(patch.object(pair_auto,'read_state',side_effect=lambda:copy.deepcopy(self.state)))
        self.start(patch.object(pair_auto,'intent',side_effect=lambda:copy.deepcopy(self.intent)))
        self.start(patch.object(native_switch,'journal_read',side_effect=lambda:copy.deepcopy(self.journal)))
        self.start(patch.object(p,'options',side_effect=lambda:copy.deepcopy(self.values)))
        self.start(patch('rpc_throttle.allow',return_value=True))
        self.start(patch.object(p,'write_uci',side_effect=self.prepare_write))
        self.writes=[];self.writer_fails=False;self.logged=[]
        self.start(patch.object(p.subprocess,'run',side_effect=self.fake_run))
        self.revision=auto_control.current_revision()
        # Start's preparation: two autostart records (unset -> 0, '1' -> 0) and the stock vpn-client boot record
        for action in ('wg-autostart','ovpn-autostart'):self.prepare(action)
        self.boot('vpn-client');self.prepare('vpn-boot')
        self.assertEqual(self.values['wgclient1']['auto'],'0');self.assertEqual(len(self.records()),3)
        # the owner's Stop from the page, after the session started
        self.state={'phase':'STOPPED','started':1000.0,'owned':[]};self.intent={'mode':'off','revision':'r'}
        self.latch({'requested':2000.0,'trial':None,'request_source':'manual'})

    def boot(self,service):
        (self.root/'etc/init.d'/service).write_text('never execute this fixture')
        (self.root/'etc/rc.d'/('S95'+service)).symlink_to('../init.d/'+service)

    def prepare(self,action):
        review=p.preview({'action':action});self.assertTrue(review['accepted'],review)
        result=p.apply({k:review[k] for k in ('action','revision','control_revision')})
        self.assertTrue(result.get('verified'),result)

    def prepare_write(self,action,plan):
        path=self.root/'etc/config/network';path.write_text(path.read_text()+'# prepared\n')
        for row in plan['before']['options']:self.values[row['section']]['auto']='0'

    def fake_run(self,argv,**kwargs):
        if argv[0]=='logger':self.logged.append(argv[-1]);return subprocess.CompletedProcess(argv,0,b'',b'')
        self.assertEqual(argv,['/usr/bin/lua','/usr/lib/homensai-vpn/preparation_write.lua'])
        request=json.loads(kwargs['input'])
        self.assertEqual(request['action'],'restore-autostart')
        self.assertEqual(request['expected'],(self.root/'etc/config/network').read_text())
        self.writes.append(request['changes'])
        if self.writer_fails:return subprocess.CompletedProcess(argv,1,b'',b'')
        for change in request['changes']:
            self.assertEqual(self.values[change['section']]['auto'],change['before'])
            self.values[change['section']]['auto']=change['after']
        return subprocess.CompletedProcess(argv,0,b'OK',b'')

    def latch(self,value):agent.atomic_json(self.persist/'native-stop.json',value)

    def link(self):
        path=self.root/'etc/rc.d/S95vpn-client'
        return __import__('os').readlink(str(path)) if path.is_symlink() else None

    def records(self):
        directory=self.persist/'preparation-changes'
        return sorted(agent.read_json(path,{})['data']['action'] for path in directory.iterdir())


class Restore(Fixture):
    def test_owner_stop_restores_the_saved_values_and_removes_only_those_records(self):
        self.assertIsNone(self.link(),'preparation removed the stock start link')
        result=p.restore_autostart()
        self.assertEqual(result,{'restored':['ovpnclient1','wgclient1'],'kept':[],'boot_restored':['vpn-boot'],'boot_kept':[],'code':None})
        self.assertEqual(self.writes,[[{'section':'ovpnclient1','type':'interface','option':'auto','before':'0','after':'1'},
                                       {'section':'wgclient1','type':'interface','option':'auto','before':'0','after':None}]])
        self.assertEqual((self.values['wgclient1']['auto'],self.values['ovpnclient1']['auto']),(None,'1'))
        self.assertEqual(self.values['wgclient2']['auto'],'0','a flag the app never changed is not touched')
        self.assertEqual(self.link(),'../init.d/vpn-client','the stock vpn-client starts at boot again (same name and target)')
        self.assertEqual(self.records(),[],'every undone record is removed')
        self.assertTrue(any('PREP-BOOT-RESTORED' in line and 'vpn-client' in line for line in self.logged),self.logged)
        self.assertEqual(p.restore_autostart(),{'restored':[],'kept':[],'boot_restored':[],'boot_kept':[],'code':None},'idempotent')
        self.assertEqual(len(self.writes),1)

    def test_next_start_prepares_again_and_the_history_does_not_grow(self):
        for _ in range(3):
            self.assertEqual(p.restore_autostart()['code'],None)
            self.state={};self.intent={}
            for action in ('wg-autostart','ovpn-autostart','vpn-boot'):self.prepare(action)
            self.assertIsNone(self.link())
            self.state={'phase':'STOPPED','started':1000.0,'owned':[]};self.intent={'mode':'off','revision':'r'}
        self.assertEqual(self.records(),['ovpn-autostart','vpn-boot','wg-autostart'])

    def test_held_by_an_outside_change_and_stopped_by_the_owner_is_restored(self):
        self.state={'phase':'HELD','recovery_error':'PAIR-EXTERNAL-NETWORK-CHANGE','started':1000.0,'owned':['wgclient1']}
        self.assertEqual(p.restore_autostart()['restored'],['ovpnclient1','wgclient1'])

    def refused(self,reason):
        before=copy.deepcopy(self.values)
        result=p.restore_autostart()
        self.assertEqual((result['code'],result.get('skipped')),(None,reason));self.assertEqual(result['restored'],[])
        self.assertEqual(self.writes,[]);self.assertEqual(self.values,before)
        self.assertIsNone(self.link(),'the start link is not restored either')
        self.assertEqual(self.records(),['ovpn-autostart','vpn-boot','wg-autostart'])

    def test_auto_on_or_a_running_or_unsettled_session_is_never_touched(self):
        self.intent={'mode':'on','revision':'r'};self.refused('auto-on');self.intent={'mode':'off'}
        for state in ({'phase':'RUNNING','started':1000.0},{'phase':'STARTING'},{'phase':'STOPPING'},
                      {'phase':'HELD','recovery_error':'PAIR-RECOVERY-REQUIRED','started':1000.0},
                      {'phase':'FAILED','owned':['wgclient1']}):
            with self.subTest(state=state):
                self.state=state;self.refused('session-not-stopped')
        self.state={'phase':'STOPPED','kept':['wgclient1'],'kept_flags':{'wgclient1':'0'},'kept_at':5.0}
        self.refused('session-kept')
        self.state={'phase':'STOPPED','started':1000.0}
        for phase in ('COMMITTED','HELD-ON-RESERVE','APPLYING','RESTORING'):
            with self.subTest(journal=phase):
                self.journal={'phase':phase};self.refused('route-not-settled')
        self.journal={'phase':'ROLLED-BACK'}
        self.assertEqual(p.restore_autostart()['restored'],['ovpnclient1','wgclient1'])

    def test_only_the_owners_own_stop_counts(self):
        for latch in ({'requested':2000.0,'request_source':'programmatic'},{'requested':2000.0,'request_source':'test'},
                      {'requested':2000.0,'request_source':'manual','control_revision_failed':True},
                      {'requested':999.0,'request_source':'manual'},  # older than this session
                      {'requested':'2000','request_source':'manual'},[]):
            with self.subTest(latch=latch):
                self.latch(latch);self.refused('no-owner-stop')
        (self.persist/'native-stop.json').unlink();self.refused('no-owner-stop')
        self.latch({'requested':2000.0,'request_source':'manual'})
        agent.atomic_json(self.persist/'auto-resume.json',{'enabled':True,'time':2500.0})
        self.refused('no-owner-stop')  # the owner pressed Start after that Stop (resume marker newer)
        agent.atomic_json(self.persist/'auto-resume.json',{'enabled':True,'time':1500.0})
        self.assertEqual(p.restore_autostart()['code'],None)

    def test_pending_manual_work_waits(self):
        agent.atomic_json(self.runtime/'pair-manual-control.json',{'state':'QUEUED'})
        self.refused('manual-pending')

    def test_a_flag_the_owner_changed_meanwhile_stays_as_it_is(self):
        self.values['wgclient1']['auto']='1'  # switched on in GL after the Stop
        self.values['ovpnclient1']['proto']='wgclient'  # the section was re-created as another client
        result=p.restore_autostart()
        self.assertEqual(result,{'restored':[],'kept':['ovpnclient1','wgclient1'],'boot_restored':['vpn-boot'],'boot_kept':[],'code':None})
        self.assertEqual(self.writes,[]);self.assertEqual(self.records(),['ovpn-autostart','wg-autostart'])

    def test_unconfirmed_write_keeps_every_record(self):
        self.writer_fails=True
        result=p.restore_autostart()
        self.assertEqual(result['code'],'PREPARATION-WRITE-UNCONFIRMED');self.assertEqual(result['restored'],[])
        self.assertEqual(self.records(),['ovpn-autostart','vpn-boot','wg-autostart'])
        self.assertIsNone(self.link(),'nothing further is undone after an unconfirmed write')

    def test_a_damaged_record_blocks_the_restore(self):
        directory=self.persist/'preparation-changes'
        path=sorted(directory.iterdir())[0];path.write_text('{"data":{},"sha256":"0"}')
        self.assertEqual(p.restore_autostart()['code'],'PREPARATION-RECOVERY-REQUIRED');self.assertEqual(self.writes,[])

    def test_a_start_link_the_owner_made_or_a_changed_boot_setup_stays_as_it_is(self):
        rc=self.root/'etc/rc.d'
        cases=(('owner enabled it again', lambda:(rc/'S95vpn-client').symlink_to('../init.d/vpn-client')),
               ('owner enabled it under another order', lambda:(rc/'S50vpn-client').symlink_to('../init.d/vpn-client')),
               ('a kill link appeared', lambda:(rc/'K10vpn-client').symlink_to('../init.d/vpn-client')),
               ('the init script is gone', lambda:(self.root/'etc/init.d/vpn-client').unlink()))
        for name,change in cases:
            with self.subTest(name):
                saved={path.name:__import__('os').readlink(str(path)) for path in rc.iterdir()}
                change();after={path.name:__import__('os').readlink(str(path)) for path in rc.iterdir()}
                result=p.restore_autostart()
                self.assertEqual((result['boot_restored'],result['boot_kept'],result['code']),([],['vpn-boot'],None))
                self.assertEqual({path.name:__import__('os').readlink(str(path)) for path in rc.iterdir()},after,'links untouched')
                self.assertIn('vpn-boot',self.records(),'the record stays')
                for path in list(rc.iterdir()):
                    if path.name not in saved:path.unlink()
                if not (self.root/'etc/init.d/vpn-client').exists():(self.root/'etc/init.d/vpn-client').write_text('never execute this fixture')

    def test_an_unconfirmed_link_keeps_the_record(self):
        # the link is read back before the record goes: a link that did not appear is PREPARATION-WRITE-UNCONFIRMED
        with patch.object(p.os,'symlink',side_effect=lambda target,path:None):
            result=p.restore_autostart()
        self.assertEqual((result['code'],result['boot_restored']),('PREPARATION-WRITE-UNCONFIRMED',[]))
        self.assertIsNone(self.link());self.assertIn('vpn-boot',self.records())

    def test_only_a_boot_record_left_restores_the_link_without_reading_uci(self):
        for path in (self.persist/'preparation-changes').iterdir():
            if agent.read_json(path,{})['data']['action']!='vpn-boot':path.unlink()
        with patch.object(p,'options',side_effect=AssertionError('no UCI read needed')):
            result=p.restore_autostart()
        self.assertEqual(result,{'restored':[],'kept':[],'boot_restored':['vpn-boot'],'boot_kept':[],'code':None})
        self.assertEqual(self.link(),'../init.d/vpn-client');self.assertEqual(self.records(),[])

    def test_a_record_without_a_start_link_restores_nothing(self):
        # vpn-boot already done (no S link) when Start prepared: its record lists only what it saw; nothing to put back
        directory=self.persist/'preparation-changes'
        for path in directory.iterdir():
            data=agent.read_json(path,{})['data']
            if data['action']=='vpn-boot':
                data['before']['links']=[row for row in data['before']['links'] if not row['name'].startswith('S')]+[{'name':'K10vpn-client','target':'../init.d/vpn-client','inode':1,'device':1}]
                agent.atomic_json(path,{'data':data,'sha256':agent.checksum(data)})
        result=p.restore_autostart()
        self.assertEqual((result['boot_restored'],result['boot_kept']),([],[]));self.assertIsNone(self.link())

    def test_supervisor_hook_runs_only_when_a_deciding_file_changed(self):
        calls=[]
        with patch.object(p,'restore_autostart',side_effect=lambda:calls.append(1) or {'code':None}), \
             patch('pair_auto.paths',return_value=(self.runtime/'pair-auto-control.json',self.persist/'pair-auto-state.json')):
            p._after_stop.clear()
            p.autostart_after_stop();p.autostart_after_stop()
            self.assertEqual(len(calls),1,'an idle tick starts nothing')
            self.latch({'requested':3000.0,'request_source':'manual'})
            p.autostart_after_stop();self.assertEqual(len(calls),2,'a new Stop is looked at')
            for path in (self.persist/'preparation-changes').iterdir():path.unlink()
            p._after_stop.clear();p.autostart_after_stop();self.assertEqual(len(calls),2,'no records: nothing to look at')


if __name__=='__main__':unittest.main()
