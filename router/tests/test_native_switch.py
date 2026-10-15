import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch,MagicMock

ROOT=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(ROOT))
import native_switch as native


def fixture():
    profiles=[{'id':'openvpn:1_1','interface':'ovpnclient1'}, {'id':'wireguard:peer_2','interface':'wgclient1'}]
    sections=[{'.name':'global','.type':'policy','enabled':'1'},
              {'.name':'default','.type':'default','enabled':'0','via':'novpn'},
              {'.name':'special','.type':'rule','enabled':'1','killswitch':'1','via':'ovpnclient2','to_type':'domain'},
              {'.name':'a','.type':'rule','enabled':'1','killswitch':'1','via':'ovpnclient1'},
              {'.name':'b','.type':'rule','enabled':'1','killswitch':'1','via':'wgclient1'}]
    return {'sections':sections,'settings':{'plan_source':profiles[0]['id'],'plan_target':profiles[1]['id'],
        'native_order_direction':'first','native_baseline_exit':'8.8.8.8'},'ipv6':'0','lan':'br-lan','firewall_defaults':[{}]},profiles


class Backend:
    def __init__(self):
        self.data,self.profiles=fixture();self.selection=native.choose(self.data,self.profiles)
        self.current=self.selection['order'][:];self.fingerprint=self.selection['hash'];self.calls=[]
    def policy(self):return self.data
    def order(self):return self.current[:],self.fingerprint
    def guard(self,devices=None):self.calls.append(('guard',devices))
    def reorder(self,order):self.calls.append(('reorder',order));self.current=list(order)
    def apply(self):self.calls.append(('apply',))
    def devices(self):return ['wgclient1','tun0']
    def diagnostic(self):return [],self.selection


class NativeTests(unittest.TestCase):
    def test_exact_supported_policy_and_hash(self):
        data,profiles=fixture();s=native.choose(data,profiles)
        self.assertEqual(s['source_rule'],'a');self.assertEqual(s['target_rule'],'b')
        data['sections'][3],data['sections'][4]=data['sections'][4],data['sections'][3]
        self.assertEqual(native.policy_hash(data['sections']),s['hash'])
        data['sections'][3]['killswitch']='0'
        self.assertNotEqual(native.policy_hash(data['sections']),s['hash'])

    def test_unsafe_layouts_fail_closed(self):
        mutations=[lambda d,p:d.update(ipv6='1'),lambda d,p:d['sections'][1].update(enabled='1'),
            lambda d,p:d['sections'][3].update(killswitch='0'),lambda d,p:d['sections'][3].update(from_type='device'),
            lambda d,p:d['sections'].append(copy.deepcopy(d['sections'][3])),
            lambda d,p:d['sections'].insert(4,{'.name':'extra','.type':'rule_process'}),
            lambda d,p:d['sections'].append({'.name':'late','.type':'rule','enabled':'1','killswitch':'1','to_type':'domain'}),
            lambda d,p:d['firewall_defaults'][0].update(flow_offloading='1'),
            lambda d,p:p[1].update(interface=None),lambda d,p:d['settings'].update(native_order_direction='guess'),
            lambda d,p:d['settings'].update(plan_target=p[0]['id'])]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                d,p=fixture();mutation(d,p)
                with self.assertRaises(native.Refused):native.choose(d,p)

    def test_journal_integrity_and_order(self):
        with tempfile.TemporaryDirectory() as d,patch.object(native,'JOURNAL',Path(d)/'tx.json'):
            value={'before':['a','b'],'after':['b','a']};native.journal_write(value)
            self.assertEqual(native.journal_read(),value)
            envelope=json.loads(native.JOURNAL.read_text());envelope['data']['after']=['a','a'];native.JOURNAL.write_text(json.dumps(envelope))
            with self.assertRaisesRegex(native.Refused,'INTEGRITY'):native.journal_read()
            native.journal_write({'before':['a','b'],'after':['a','a']})
            with self.assertRaisesRegex(native.Refused,'ORDER'):native.journal_read()

    def test_external_writer_never_overwritten(self):
        b=Backend();b.fingerprint='changed'
        with self.assertRaisesRegex(native.Refused,'EXTERNAL'):
            native.rollback(b,{'hash':b.selection['hash'],'before':b.current,'after':list(reversed(b.current))},'test')
        self.assertEqual(b.calls,[('guard',None)])

    def test_rollback_restores_only_order_then_restricts_to_vpn(self):
        b=Backend();before=b.current[:];after=before[:];after[-2],after[-1]=after[-1],after[-2];b.current=after
        with tempfile.TemporaryDirectory() as d,patch.object(native,'JOURNAL',Path(d)/'tx.json'):
            native.rollback(b,{'before':before,'after':after,'hash':b.fingerprint},'test')
            self.assertEqual(b.current,before)
            self.assertEqual(native.journal_read()['phase'],'ROLLED-BACK')
            self.assertEqual(b.calls[0],('guard',None));self.assertEqual(b.calls[-1],('guard',['wgclient1','tun0']))

    def test_failed_rollback_never_opens_guard(self):
        b=Backend();b.apply=MagicMock(side_effect=OSError('mock'))
        with self.assertRaises(OSError):native.rollback(b,{'hash':b.fingerprint,'before':b.current,'after':b.current},'test')
        self.assertEqual(b.calls,[('guard',None)])

    def test_trial_certificate_requires_client_confirmation_and_restores_original(self):
        b=Backend();before=b.current[:];process=MagicMock(pid=123,returncode=0)
        def spawn(*a,**k):
            b.current[-2],b.current[-1]=b.current[-1],b.current[-2]
            b.data['settings']['native_ack']='t'*32
            return process
        with tempfile.TemporaryDirectory() as d,patch.object(native,'JOURNAL',Path(d)/'journal'),patch.object(native,'STATE',Path(d)/'status'),patch.object(native,'CERT',Path(d)/'cert'),patch.object(native.uuid,'uuid4',return_value=MagicMock(hex='t'*32)),patch.object(native.subprocess,'Popen',side_effect=spawn),patch.object(native,'trace',side_effect=lambda p:'8.8.8.8' if p['id']==b.profiles[0]['id'] else '9.9.9.9'):
            native.attempt(b,b.selection,time.time()+120,True)
            self.assertEqual(b.current,before)
            self.assertEqual(json.loads(native.STATE.read_text())['state'],'ARMED')
            self.assertEqual(json.loads(native.CERT.read_text())['target'],b.profiles[1]['id'])

    def test_vendor_failure_rolls_back_without_certificate(self):
        b=Backend();before=b.current[:];process=MagicMock(pid=123,returncode=1)
        with tempfile.TemporaryDirectory() as d,patch.object(native,'JOURNAL',Path(d)/'journal'),patch.object(native,'STATE',Path(d)/'status'),patch.object(native,'CERT',Path(d)/'cert'),patch.object(native.subprocess,'Popen',return_value=process):
            with self.assertRaisesRegex(native.Refused,'VENDOR-APPLY'):
                native.attempt(b,b.selection,time.time()+120,False)
            self.assertEqual(b.current,before);self.assertFalse(native.CERT.exists())

    def test_no_client_confirmation_means_rollback(self):
        b=Backend();before=b.current[:];process=MagicMock(pid=123,returncode=0)
        def spawn(*a,**k):
            b.current[-2],b.current[-1]=b.current[-1],b.current[-2]
            return process
        with tempfile.TemporaryDirectory() as d,patch.object(native,'JOURNAL',Path(d)/'journal'),patch.object(native,'STATE',Path(d)/'status'),patch.object(native,'CERT',Path(d)/'cert'),patch.object(native.subprocess,'Popen',side_effect=spawn),patch.object(native,'trace',return_value='9.9.9.9'),patch.object(native.os,'killpg'):
            with self.assertRaisesRegex(native.Refused,'CONFIRMATION-TIMEOUT'):
                native.attempt(b,b.selection,time.time()-1,False)
            self.assertEqual(b.current,before);self.assertFalse(native.CERT.exists())

    def test_late_external_change_during_exit_probe_is_rejected(self):
        b=Backend();process=MagicMock(pid=123,returncode=0);calls=[]
        def spawn(*a,**k):
            b.current[-2],b.current[-1]=b.current[-1],b.current[-2]
            b.data['settings']['native_ack']='t'*32
            return process
        def exit_probe(profile):
            calls.append(profile)
            if len(calls)==2:b.fingerprint='external'
            return '9.9.9.9'
        with tempfile.TemporaryDirectory() as d,patch.object(native,'JOURNAL',Path(d)/'journal'),patch.object(native,'STATE',Path(d)/'status'),patch.object(native,'CERT',Path(d)/'cert'),patch.object(native.uuid,'uuid4',return_value=MagicMock(hex='t'*32)),patch.object(native.subprocess,'Popen',side_effect=spawn),patch.object(native,'trace',side_effect=exit_probe),patch.object(native.os,'killpg'):
            with self.assertRaisesRegex(native.Refused,'EXTERNAL'):
                native.attempt(b,b.selection,time.time()+120,False)
            self.assertFalse(native.CERT.exists())
            self.assertEqual(b.calls[-1],('guard',None))

    def test_guard_transaction_is_atomic_and_scoped(self):
        b=native.Linux()
        with patch.object(b,'guard_exists',return_value=True),patch.object(native.subprocess,'run',return_value=MagicMock(returncode=0)) as run:
            b.guard(['wgclient1','tun0']);args=run.call_args
            self.assertEqual(args.args[0],['nft','-f','-'])
            script=args.kwargs['input'].decode()
            self.assertIn('delete table inet homensai_vpn_guard;',script)
            self.assertIn('hook forward',script);self.assertNotIn('hook input',script)
            self.assertIn('meta nfproto ipv6 drop',script);self.assertIn('oifname !=',script)
            self.assertNotIn('flush ruleset',script)

    def test_explicit_timezone_deadline(self):
        self.assertEqual(native.deadline('2026-10-15T14:00:00+02:00'),native.deadline('2026-10-15T12:00:00Z'))
        with self.assertRaises(native.Refused):native.deadline('2026-10-15T14:00:00')

    def test_only_fresh_kernel_read_status_is_evidence(self):
        self.assertEqual(native.fresh_hook_state('[ 100.1] hnat hook is disabled',100),'disabled')
        self.assertEqual(native.fresh_hook_state('[ 100.1] hnat hook is disabled',101),'unknown')
        self.assertEqual(native.fresh_hook_state('[ 100.1] hnat hook is going to be disabled !',100),'unknown')
        self.assertEqual(native.fresh_hook_state('[ 100.1] hnat hook is enabled',100),'enabled')

    def test_acceleration_requires_explicit_bounded_request(self):
        b=Backend()
        with patch.object(native,'command') as cmd:
            with self.assertRaises(native.Refused):native.disable_acceleration(b,'')
            with self.assertRaises(native.Refused):native.disable_acceleration(b,'off; reboot')
            cmd.assert_not_called()

    def test_acceleration_prepare_uses_stock_services_and_checks_runtime(self):
        b=Backend();b.data['hnat_enable']='1';b.data['firewall_defaults'][0]['.name']='defaults'
        acceleration={'loaded':['mtkhnat','shortcut_fe'],'hnat_runtime':'enabled'}
        b.acceleration=lambda:copy.deepcopy(acceleration)
        exists=Path.exists;read=Path.read_text;write=Path.write_text
        def fake_exists(p):return str(p) in ('/etc/init.d/shortcut-fe','/etc/init.d/mtkhnat','/sys/kernel/debug/hnat/hook_toggle') or exists(p)
        def fake_read(p,*a,**k):return 'disabled' if str(p)=='/sys/kernel/debug/hnat/hook_toggle' else read(p,*a,**k)
        def fake_write(p,text,*a,**k):
            if str(p)=='/sys/kernel/debug/hnat/hook_toggle':acceleration['hnat_runtime']='disabled';return len(text)
            return write(p,text,*a,**k)
        def cmd(args,**k):
            if args==['/etc/init.d/shortcut-fe','stop']:acceleration['loaded'].remove('shortcut_fe')
            return b''
        with tempfile.TemporaryDirectory() as d,patch.object(native,'PREPARE',Path(d)/'prepare.json'),patch.object(Path,'exists',fake_exists),patch.object(Path,'read_text',fake_read),patch.object(Path,'write_text',fake_write),patch.object(Path,'is_mount',return_value=True),patch.object(native,'command',side_effect=cmd) as call:
            result=native.disable_acceleration(b,'off-'+'a'*32)
            self.assertEqual(result['phase'],'DONE');self.assertIn('shortcut_fe',result['before']['acceleration']['loaded'])
            self.assertEqual(result['after']['hnat_runtime'],'disabled');self.assertNotIn('shortcut_fe',result['after']['loaded'])
            call.assert_any_call(['/etc/init.d/shortcut-fe','stop'],timeout=20)
            call.assert_any_call(['/etc/init.d/mtkhnat','reload'],timeout=20)
            count=call.call_count;native.disable_acceleration(b,'off-'+'a'*32);self.assertEqual(call.call_count,count)

    def test_missing_debugfs_uses_only_normal_accelerator_module_unload(self):
        b=Backend();b.data['hnat_enable']='0';b.data['firewall_defaults'][0]['.name']='defaults'
        acceleration={'loaded':['mtkhnat','shortcut_fe'],'hnat_runtime':'unknown'}
        b.acceleration=lambda:copy.deepcopy(acceleration)
        exists=Path.exists
        def fake_exists(p):
            if str(p).startswith('/sys/kernel/debug/'):return False
            return str(p) in ('/etc/init.d/shortcut-fe','/etc/init.d/mtkhnat') or exists(p)
        def cmd(args,**k):
            if args[0]=='rmmod':acceleration['loaded'].remove(args[1])
            return b''
        with tempfile.TemporaryDirectory() as d,patch.object(native,'PREPARE',Path(d)/'prepare.json'),patch.object(Path,'exists',fake_exists),patch.object(native,'command',side_effect=cmd) as call:
            result=native.disable_acceleration(b,'off-'+'b'*32)
            self.assertEqual(result['phase'],'DONE');self.assertEqual(result['after']['loaded'],[])
            commands=[c.args[0] for c in call.call_args_list]
            self.assertIn(['rmmod','shortcut_fe'],commands);self.assertIn(['rmmod','mtkhnat'],commands)
            self.assertTrue(all('-f' not in c for c in commands));self.assertTrue(all(c[0]!='mount' for c in commands))


if __name__=='__main__':unittest.main()
