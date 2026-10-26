"""Reviewed preparation writes against temporary router state; no real service."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,auto_control,native_switch,pair_auto,preparation_status
import configuration_guard
import preparation_control as p


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.runtime=self.root/'run';self.persist=self.root/'persist'
        for name in ('run','persist','etc/config','etc/init.d','etc/rc.d','etc/modules.d','tmp/sysinfo','proc/sys/kernel/random','sys/kernel/debug/hnat'):
            (self.root/name).mkdir(parents=True,exist_ok=True)
        (self.root/'tmp/sysinfo/board_name').write_text('glinet,mt3000-snand')
        (self.root/'etc/glversion').write_text('4.11.0')
        (self.root/'proc/sys/kernel/random/boot_id').write_text('11111111-1111-1111-1111-111111111111')
        for name in p.PACKAGES:(self.root/'etc/config'/name).write_text('private fixture '+name+'\n')
        self.values={'wgclient1':{'proto':'wgclient','auto':'1'},'ovpnclient1':{'proto':'ovpnclient','auto':'1'},'hnat':'1','hnat_type':'mtkhnat','defaults':[{'section':'cfg0001','flow_offloading':'1','flow_offloading_hw':None}]}
        self.acceleration={'loaded':[],'hnat_runtime':'disabled'}
        for module in (p,agent,auto_control):
            for key,value in (('RUNTIME',self.runtime),('PERSIST',self.persist)):
                if hasattr(module,key):self.start(patch.object(module,key,value))
        self.start(patch.object(p,'ROOT',self.root))
        self.start(patch.object(p,'inventory',return_value={'settings':{'router_model':'auto','native_enabled':False}}))
        self.blocked=self.start(patch.object(configuration_guard,'blocked',return_value=None))
        self.pair_state=self.start(patch.object(pair_auto,'read_state',return_value={}))
        self.pair_intent=self.start(patch.object(pair_auto,'intent',return_value={}))
        self.start(patch.object(p,'options',side_effect=lambda:copy.deepcopy(self.values)))
        self.start(patch.object(native_switch.Linux,'acceleration',side_effect=lambda:copy.deepcopy(self.acceleration)))
        self.start(patch('rpc_throttle.allow',return_value=True))
        self.write=self.start(patch.object(p,'write_uci',side_effect=self.write_uci))
        self.revision=auto_control.current_revision()

    def start(self,mock):
        result=mock.start();self.addCleanup(mock.stop);return result

    def write_uci(self,action,plan):
        package=plan['before']['package'];path=self.root/'etc/config'/package
        path.write_text(path.read_text()+'# only reviewed options changed\n')
        for row in plan['before']['options']:
            if action in ('wg-autostart','ovpn-autostart','source-autostart','target-autostart'):self.values[row['section']]['auto']='0'
            elif action=='hnat':self.values['hnat']='0'
            else:self.values['defaults'][0][row['option']]='0'

    def review(self,action):
        result=p.preview({'action':action});self.assertTrue(result['accepted'],result)
        return {k:result[k] for k in ('action','revision','control_revision')}

    def boot(self,service):
        (self.root/'etc/init.d'/service).write_text('never execute this fixture')
        for prefix in ('S95','K10'):(self.root/'etc/rc.d'/(prefix+service)).symlink_to('../init.d/'+service)

    def test_preview_never_changes_config_and_supports_each_actual_model(self):
        for board,model in [('glinet,mt3000-snand','mt3000'),('glinet,gl-mt6000','mt6000')]:
            (self.root/'tmp/sysinfo/board_name').write_text(board)
            before=p.file_hashes();result=p.preview({'action':'wg-autostart'})
            self.assertTrue(result['accepted']);self.assertEqual(result['board'],model)
            self.assertEqual(p.file_hashes(),before);self.write.assert_not_called()
            self.assertFalse((self.persist/'preparation-changes').exists())

    def test_absent_unrelated_profile_catalogue_does_not_block_a_boot_only_change(self):
        for name in ('wireguard','ovpnclient'):(self.root/'etc/config'/name).unlink()
        self.boot('vpn-client');request=self.review('vpn-boot')
        self.assertTrue(p.apply(request)['verified'])
        self.assertFalse((self.root/'etc/config/wireguard').exists())

    def test_role_startup_action_follows_the_current_second_interface(self):
        self.values['ovpnclient2']={'proto':'ovpnclient','auto':None}
        self.start(patch.object(p,'inventory',return_value={'settings':{'router_model':'auto','plan_source_tunnel':'wireguard:wgclient1','plan_target_tunnel':'openvpn:ovpnclient2'}}))
        preview=p.preview({'action':'target-autostart'});self.assertTrue(preview['accepted']);self.assertEqual(preview['interface'],'ovpnclient2')
        result=p.apply({k:preview[k]for k in('action','revision','control_revision')})
        self.assertTrue(result['verified'],result);self.assertEqual(self.values['ovpnclient2']['auto'],'0')
        self.assertEqual(self.values['ovpnclient1']['auto'],'1')

    def test_each_uci_action_changes_only_its_package_and_has_durable_original_before_write(self):
        for action in ('wg-autostart','ovpn-autostart','hnat','flow-offload'):
            with self.subTest(action=action):
                before=p.file_hashes();request=self.review(action);original=copy.deepcopy(self.values)
                def write(name,plan):
                    paths=list((self.persist/'preparation-changes').glob('*.json'))
                    pending=[agent.read_json(path)['data'] for path in paths if agent.read_json(path)['data']['state']=='PREPARED']
                    self.assertEqual(len(pending),1);self.assertEqual(pending[0]['action'],action)
                    self.assertEqual(pending[0]['before'],plan['before']);self.write_uci(name,plan)
                with patch.object(p,'write_uci',side_effect=write):result=p.apply(request)
                self.assertTrue(result['verified'],result);self.assertFalse(result['auto_started'])
                changed=[key for key,value in p.file_hashes().items() if value!=before[key]]
                self.assertEqual(changed,[p.ACTIONS[action]['package']])
                self.assertTrue(all(row['state']=='VERIFIED' for row in p.records()))
                if action=='flow-offload':
                    self.assertTrue(result['restart_required']);self.assertEqual(p.auto_blocker(),'PREPARATION-RESTART-REQUIRED')
                    (self.root/'proc/sys/kernel/random/boot_id').write_text('22222222-2222-2222-2222-222222222222')
                    self.assertIsNone(p.auto_blocker())

    def test_boot_buttons_remove_only_the_reviewed_start_link_without_service_execution(self):
        for action,service in [('vpn-boot','vpn-client'),('sfe-boot','shortcut-fe')]:
            self.boot(service);before=p.file_hashes();request=self.review(action)
            with patch.object(p.subprocess,'run',side_effect=AssertionError('Do not invoke a service')):
                result=p.apply(request)
            self.assertTrue(result['verified'],result)
            self.assertFalse((self.root/'etc/rc.d'/('S95'+service)).exists())
            self.assertTrue((self.root/'etc/rc.d'/('K10'+service)).is_symlink())
            self.assertEqual(p.file_hashes(),before)
            saved=next(row for row in p.records() if row['action']==action)['before']['links'];self.assertTrue(any(row['name']=='S95'+service for row in saved))

    def test_sfe_autoload_preserves_exact_bytes_and_never_unloads_loaded_modules(self):
        content=b'shortcut-fe\nshortcut-fe-ipv6\n'
        source=self.root/'etc/modules.d/09-shortcut-fe';source.write_bytes(content)
        pin=__import__('hashlib').sha256(content).hexdigest()
        self.acceleration['loaded']=['shortcut_fe']
        with patch.object(preparation_status,'AUTOLOAD_SHA',pin):
            request=self.review('sfe-autoload');result=p.apply(request)
        self.assertTrue(result['verified'],result);self.assertTrue(result['restart_required'])
        self.assertFalse(source.exists())
        self.assertEqual((self.root/'etc/homensai-vpn/disabled-module-autoload/09-shortcut-fe').read_bytes(),content)
        self.assertEqual(p.auto_blocker(),'PREPARATION-RESTART-REQUIRED')

    def test_unknown_board_firmware_or_wrong_interface_proto_never_writes(self):
        for path,value in [('tmp/sysinfo/board_name','unknown'),('etc/glversion','99')]:
            target=self.root/path;before=target.read_text();target.write_text(value)
            self.assertFalse(p.preview({'action':'wg-autostart'})['accepted']);target.write_text(before)
        self.values['wgclient1']['proto']='other'
        self.assertEqual(p.preview({'action':'wg-autostart'})['code'],'PREPARATION-BINDING-UNVERIFIED')
        self.write.assert_not_called()

    def test_active_auto_old_ownership_and_pending_manual_work_refuse_before_backup(self):
        self.blocked.return_value='CONFIG-STOP-AUTO-FIRST'
        self.assertEqual(p.preview({'action':'wg-autostart'})['code'],'PREPARATION-STOP-AUTO-FIRST')
        self.blocked.return_value=None
        for state in ({'phase':'RUNNING','owned':['wgclient1']},{'phase':'HELD','owned':['wgclient1']}):
            self.pair_state.return_value=state
            self.assertEqual(p.preview({'action':'wg-autostart'})['code'],'PREPARATION-RECOVERY-REQUIRED')
        self.pair_state.return_value={};self.pair_intent.return_value={'mode':'on'}
        self.assertFalse(p.preview({'action':'wg-autostart'})['accepted']);self.pair_intent.return_value={}
        (self.runtime/'manual-control.json').write_text('{"state":"QUEUED"}')
        self.assertFalse(p.preview({'action':'wg-autostart'})['accepted']);self.write.assert_not_called()

    def test_edit_stop_and_reboot_invalidate_a_review_without_a_write(self):
        for change in ('config','stop','boot'):
            request=self.review('wg-autostart')
            if change=='config':
                with (self.root/'etc/config/network').open('a') as stream:stream.write('# external edit\n')
            elif change=='stop':auto_control.current_revision(rotate=True)
            else:(self.root/'proc/sys/kernel/random/boot_id').write_text('33333333-3333-3333-3333-333333333333')
            self.assertEqual(p.apply(request)['code'],'PREPARATION-STALE-REVIEW')
        self.write.assert_not_called();self.assertFalse((self.persist/'preparation-changes').exists())

    def test_already_disabled_is_noop_and_duplicate_apply_cannot_write_twice(self):
        self.values['wgclient1']['auto']='0';request=self.review('wg-autostart')
        result=p.apply(request);self.assertTrue(result['already_done']);self.write.assert_not_called()
        self.values['wgclient1']['auto']='1';request=self.review('wg-autostart')
        self.assertTrue(p.apply(request)['verified']);self.assertFalse(p.apply(request)['applied'])
        self.assertEqual(self.write.call_count,1)

    def test_write_failure_retains_backup_and_blocks_new_writes_and_auto(self):
        request=self.review('wg-autostart')
        with patch.object(p,'mutate',side_effect=OSError('PRIVATE_FAILURE_SENTINEL')):result=p.apply(request)
        self.assertFalse(result['verified']);self.assertTrue(result['change_may_have_applied'])
        self.assertNotIn('PRIVATE_FAILURE_SENTINEL',json.dumps(result))
        self.assertEqual(p.auto_blocker(),'PREPARATION-RECOVERY-REQUIRED')
        self.assertEqual(p.preview({'action':'wg-autostart'})['code'],'PREPARATION-RECOVERY-REQUIRED')
        self.assertEqual(len(list((self.persist/'preparation-changes').glob('*.json'))),1)

    def test_backup_failure_never_attempts_mutation(self):
        request=self.review('wg-autostart')
        with patch.object(p,'atomic_json',side_effect=OSError),patch.object(p,'mutate') as mutate:result=p.apply(request)
        self.assertFalse(result['applied']);mutate.assert_not_called()

    def test_readback_failure_is_not_claimed_as_success(self):
        request=self.review('wg-autostart')
        with patch.object(p,'write_uci'):result=p.apply(request)
        self.assertFalse(result['verified']);self.assertEqual(result['code'],'PREPARATION-WRITE-UNCONFIRMED')

    def test_unsafe_boot_link_or_changed_autoload_never_removed(self):
        self.boot('vpn-client');path=self.root/'etc/rc.d/S95vpn-client';path.unlink();path.symlink_to('../init.d/unrelated')
        self.assertEqual(p.preview({'action':'vpn-boot'})['code'],'PREPARATION-BOOT-UNVERIFIED');self.assertTrue(path.is_symlink())
        source=self.root/'etc/modules.d/09-shortcut-fe';source.write_bytes(b'changed')
        self.assertFalse(p.preview({'action':'sfe-autoload'})['accepted']);self.assertEqual(source.read_bytes(),b'changed')

    def test_hnat_active_without_verified_hook_refuses(self):
        self.acceleration.update(loaded=['mtkhnat'],hnat_runtime='enabled')
        with patch.object(p,'hook_available',return_value=False):result=p.preview({'action':'hnat'})
        self.assertEqual(result['code'],'PREPARATION-HNAT-UNVERIFIED');self.write.assert_not_called()

    def test_malformed_verified_record_cannot_bypass_restart_or_recovery(self):
        request=self.review('flow-offload');self.assertTrue(p.apply(request)['verified'])
        path=next((self.persist/'preparation-changes').glob('*.json'));original=agent.read_json(path)['data']
        for field,value in [('boot_id',None),('restart_required','false'),('action',[]),('verified_at',True)]:
            row=dict(original);row[field]=value
            agent.atomic_json(path,{'data':row,'sha256':agent.checksum(row)})
            self.assertEqual(p.auto_blocker(),'PREPARATION-RECOVERY-REQUIRED')

    def test_hostile_or_extra_rpc_fields_never_reach_the_writer(self):
        for action in (None,[],{},'../network','hnat;reboot','constructor',''):
            self.assertFalse(p.preview({'action':action})['accepted'])
            self.assertFalse(p.apply({'action':action,'revision':'a'*64,'control_revision':'b'*32})['applied'])
        self.assertFalse(p.apply(dict(self.review('wg-autostart'),command='reboot'))['applied'])
        self.write.assert_not_called()


if __name__=='__main__':unittest.main()
