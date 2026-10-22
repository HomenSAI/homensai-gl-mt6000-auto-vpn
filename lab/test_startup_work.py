import copy
import unittest
from startup_work import StartupWork,classify,describe

def sample(**changes):
    value=dict(recursive=0,retry_workers=0,flock_waiters=0,available_kib=210000,unknown_work=False,
               work_items=[],service_queue_codes=[],link_ready=True,link_generation='ifindex:9:pid:42:start:100')
    value.update(changes);return value

class Tests(unittest.TestCase):
    def model(self):return StartupWork(0,25,220000)
    def test_quiet_is_continuous_and_revocable(self):
        m=self.model();self.assertEqual([m.feed(t,sample())for t in(1,2,3,4)],['WAIT']*3+['LINK-SETTLED'])
        self.assertEqual(m.feed(5,sample(work_items=[(42,'100','RTP')])),'WAIT')
    def test_recorded_normal_wg_and_ov_fanout_can_settle(self):
        for fanout in ([1,4,2,0],[1,3,7,2,0]):
            m=self.model();now=0
            for count in fanout:
                now+=1;items=[(100+i,'100',kind)for i,kind in enumerate(['FW3']*min(count,3)+['RTP']*max(0,min(count-3,2))+['PROTO']*max(0,count-5))]
                self.assertEqual(m.feed(now,sample(work_items=items)),'WAIT')
            for _ in range(4):now+=1;out=m.feed(now,sample())
            self.assertEqual(out,'LINK-SETTLED')
    def test_exact_same_busy_workers_stall(self):
        m=self.model();row=sample(work_items=[(42,'100','RTP')])
        for t in range(1,8):self.assertEqual(m.feed(t,row),'WAIT')
        self.assertEqual(m.feed(8,row),'STARTUP-WORK-STALLED')
    def test_absolute_and_cumulative_worker_budgets(self):
        self.assertEqual(self.model().feed(1,sample(work_items=[(42+i,'100','FW3')for i in range(5)])),'STARTUP-WORK-BUDGET')
        m=self.model()
        for i in range(8):self.assertEqual(m.feed(i+1,sample(work_items=[(100+i*3+j,'100','RTP')for j in range(3)])),'WAIT')
        self.assertEqual(m.feed(9,sample(work_items=[(999,'100','RTP')])),'STARTUP-WORK-BUDGET')
    def test_original_hard_fault_order_and_memory_limits_retained(self):
        for kw,code in (({'recursive':1,'retry_workers':1},'FW3-RECURSION'),({'retry_workers':1},'VENDOR-RETRY-WORKER'),({'available_kib':131071},'MEMORY-ABORT'),({'available_kib':154464},'MEMORY-ABORT')):
            m=self.model();self.assertEqual(m.feed(1,sample(**kw)),code);self.assertEqual(m.feed(2,sample()),code)
    def test_lock_deadline_does_not_reset_on_worker_progress(self):
        m=self.model()
        for t in range(1,5):self.assertEqual(m.feed(t,sample(flock_waiters=1,work_items=[(100+t,'100','RTP')])),'WAIT')
        self.assertEqual(m.feed(5,sample(flock_waiters=1)),'LOCK-WAIT-ABORT')
    def test_unknown_queue_restart_or_duplicate_never_settles(self):
        for q in ([{'service':'OTHER','action':'RELOAD'}],[{'service':'FIREWALL','action':'RESTART'}],[{'service':'NETWORK','action':'RELOAD'}]*2):
            self.assertEqual(self.model().feed(1,sample(service_queue_codes=q)),'STARTUP-QUEUE-UNVERIFIED')

    def test_dns_restart_is_only_an_explicit_post_policy_contract(self):
        row=dict(pid=42,start='100',state='S',exe='/bin/busybox',argv=['/bin/sh','/etc/rc.common','/etc/init.d/dnsmasq','restart'])
        self.assertTrue(classify({42:row},'wgclient1',99)[1]);self.assertFalse(classify({42:row},'wgclient1',99,True)[1])
        self.assertTrue(classify({42:dict(row,argv=row['argv']+['PRIVATE'])},'wgclient1',99,True)[1])
        for service in ('NETWORK','FIREWALL'):
            m=StartupWork(0,25,220000,True)
            self.assertEqual(m.feed(1,sample(service_queue_codes=[{'service':service,'action':'RESTART'}])),'STARTUP-QUEUE-UNVERIFIED')
        m=StartupWork(0,25,220000,True);self.assertEqual(m.feed(1,sample(service_queue_codes=[{'service':'DNSMASQ','action':'RESTART'}])),'WAIT')
        for t in range(2,6):verdict=m.feed(t,sample())
        self.assertEqual(verdict,'LINK-SETTLED')
    def test_generation_loss_or_change_is_sticky(self):
        for kw,code in (({'link_ready':False},'STARTUP-LINK-LOST'),({'link_generation':'different'},'STARTUP-GENERATION-CHANGED')):
            m=self.model();m.feed(1,sample());self.assertEqual(m.feed(2,sample(**kw)),code)
    def test_deadline_invalid_types_and_huge_numbers_fail_closed(self):
        for t in (25,-1,True,float('nan'),10**1000):self.assertEqual(self.model().feed(t,sample()),'STARTUP-EVIDENCE-INVALID')
        for key,value in (('unknown_work',None),('recursive',True),('link_ready','yes')):
            self.assertIn(self.model().feed(1,sample(**{key:value})),('STARTUP-EVIDENCE-INVALID','STARTUP-WORK-UNVERIFIED'))
    def test_observation_gap_resets_quiet_window(self):
        m=self.model();m.feed(1,sample());m.feed(2,sample());self.assertEqual(m.feed(6,sample()),'WAIT')
    def test_coded_worker_classification_never_exports_private_argv(self):
        rows={42:dict(pid=42,start='100',state='S',exe='/bin/busybox',proto_source_pinned=True,argv=['/bin/sh','/lib/netifd/proto/wgclient.sh','setup','wgclient1','PRIVATE-KEY-DATA'])}
        items,unknown=classify(rows,'wgclient1',99);self.assertFalse(unknown);self.assertEqual(items,[(42,'100','PROTO')]);self.assertNotIn('PRIVATE',str(items))
        self.assertTrue(classify(rows,'ovpnclient1',99)[1]);self.assertTrue(classify(rows,'wgclient1',101)[1])
    def test_firewall_restart_unknown_include_and_real_retry_refuse(self):
        for argv in (['/bin/sh','/etc/rc.common','/etc/init.d/firewall','restart'],['/bin/sh','-c','. /usr/bin/rtp2.sh'],['/usr/bin/vpn-failover-trigger.sh','switch','wgclient1'],['/usr/bin/rtp2.sh','not_reload_network']):
            self.assertTrue(classify({42:dict(pid=42,start='100',state='S',exe='/bin/busybox',argv=argv)},'wgclient1',99)[1])

    def test_exact_read_only_firewall_enabled_query_is_not_a_reload(self):
        argv=['/bin/sh','/etc/rc.common','/etc/init.d/firewall','enabled']
        row=dict(pid=42,start='100',state='S',exe='/bin/busybox',argv=argv)
        self.assertEqual(classify({42:row},'wgclient1',99),([],False))
        for changed in (argv+['PRIVATE'],argv[:-1]+['enable'],argv[:-1]+['disable']):
            self.assertTrue(classify({42:dict(row,argv=changed)},'wgclient1',99)[1])

    def test_duplicate_timestamp_is_not_an_additional_quiet_sample(self):
        m=self.model();m.feed(1,sample());self.assertEqual(m.feed(1,sample()),'STARTUP-EVIDENCE-INVALID')

    def test_refusal_diagnosis_does_not_export_private_command_data(self):
        rows={42:dict(pid=42,start='100',state='S',exe='/bin/busybox',argv=['/bin/sh','/lib/netifd/proto/wgclient.sh','setup','wgclient1','PRIVATE-KEY-DATA'])}
        r=describe(rows,'wgclient1',101)
        self.assertTrue(r[0]['started_before_trial']);self.assertNotIn('PRIVATE',str(r));self.assertTrue(r[0]['exact_proto_path'])

    def test_relative_netifd_script_requires_both_pinned_source_and_verified_cwd(self):
        row=dict(pid=42,start='100',state='S',exe='/bin/busybox',argv=['/bin/sh','./wgclient.sh','setup','wgclient1','PRIVATE'])
        for pinned,cwd in ((False,False),(True,False),(False,True)):
            self.assertTrue(classify({42:dict(row,proto_source_pinned=pinned,proto_cwd_verified=cwd)},'wgclient1',99)[1])
        items,unknown=classify({42:dict(row,proto_source_pinned=True,proto_cwd_verified=True)},'wgclient1',99)
        self.assertFalse(unknown);self.assertEqual(items,[(42,'100','PROTO')])

if __name__=='__main__':unittest.main()
