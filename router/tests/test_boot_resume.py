"""boot_resume.py: the owner's Start comes back after a power cut (owner decision 31.10.2026, soak trial)."""
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,auto_control,boot_resume as br,pair_auto


class BootResume(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.runtime=Path(temp.name)/'run';self.persist=Path(temp.name)/'etc';self.runtime.mkdir();self.persist.mkdir()
        for module in (agent,auto_control):
            p=patch.object(module,'RUNTIME',self.runtime);p.start();self.addCleanup(p.stop)
            if hasattr(module,'PERSIST'):p=patch.object(module,'PERSIST',self.persist);p.start();self.addCleanup(p.stop)
        self.mode={'mode':'off'}
        p=patch.object(pair_auto,'intent',side_effect=lambda:self.mode);p.start();self.addCleanup(p.stop)
        self.replies=[{'accepted':True,'queued':True}];self.calls=[]
        def start(**kw):
            self.calls.append(kw);reply=self.replies[min(len(self.calls),len(self.replies))-1]
            if reply.get('accepted'):self.mode={'mode':'on'}
            return reply
        p=patch.object(auto_control,'start',side_effect=start);p.start();self.addCleanup(p.stop)
        p=patch.object(auto_control,'current_revision',return_value='a'*32);p.start();self.addCleanup(p.stop)

    def state(self):return json.loads((self.runtime/br.STATE).read_text())

    def run_once(self,**kw):return br.run(self.runtime,self.persist,sleep=lambda s:None,uptime=kw.get('uptime',60))

    def test_owner_start_before_the_cut_is_resumed_once(self):
        br.remember(self.persist,now=500)
        self.assertEqual(self.run_once(),'RESUMED')
        self.assertEqual(self.calls,[{'control_revision':'a'*32,'request_source':'programmatic'}])
        self.assertEqual(self.state()['state'],'RESUMED')
        self.assertIsNone(self.run_once())  # once per boot
        self.assertEqual(len(self.calls),1)

    def test_a_later_stop_wins_an_older_one_does_not(self):
        br.remember(self.persist,now=500)
        agent.atomic_json(self.persist/'native-stop.json',{'requested':600.0,'trial':None})
        self.assertEqual(self.run_once(),'SKIPPED');self.assertEqual(self.state()['code'],'AUTO-RESUME-STOPPED');self.assertEqual(self.calls,[])
        (self.runtime/br.STATE).unlink()
        agent.atomic_json(self.persist/'native-stop.json',{'requested':400.0,'trial':None})
        self.assertEqual(self.run_once(),'RESUMED')

    def test_no_marker_or_old_boot_does_nothing(self):
        self.assertEqual(self.run_once(),'SKIPPED');self.assertEqual(self.state()['code'],'AUTO-RESUME-NOT-REQUESTED')
        (self.runtime/br.STATE).unlink();br.remember(self.persist,now=500)
        self.assertIsNone(self.run_once(uptime=5000));self.assertEqual(self.calls,[])

    def test_refusals_retry_and_a_final_code_stops(self):
        br.remember(self.persist,now=500)
        self.replies=[{'accepted':False,'blockers':['TRANSACTION-IN-PROGRESS']},{'accepted':True}]
        self.assertEqual(self.run_once(),'RESUMED');self.assertEqual(len(self.calls),2)
        (self.runtime/br.STATE).unlink();self.calls.clear();self.mode={'mode':'off'}
        self.replies=[{'accepted':False,'blockers':['JOURNAL-INTEGRITY-FAILED']}]
        self.assertEqual(self.run_once(),'FAILED');self.assertEqual(self.state()['code'],'JOURNAL-INTEGRITY-FAILED')

    def test_marker_matches_the_lua_format(self):
        br.remember(self.persist,now=500)
        row=json.loads((self.persist/br.MARKER).read_text())
        self.assertEqual(row,{'enabled':True,'time':500.0,'request_source':'manual'})

    # Owner decision extension 31.10.2026: an unintended supervisor restart (kill -9, crash) without a reboot
    def supervisor_start(self,ident):
        self.mode={'mode':'off'}  # the restarted supervisor's recovery fenced the intent
        agent.atomic_json(self.runtime/br.SUPERVISOR,{'id':ident*32,'time':1.0})

    def test_supervisor_killed_in_idle_is_resumed_once_per_supervisor_start(self):
        br.remember(self.persist,now=500);self.supervisor_start('1')
        state,handled=br._boot(self.runtime,self.persist,lambda s:None,60,lambda:0.0)
        self.assertEqual((state,handled),('RESUMED','1'*32))
        br.watch(self.runtime,self.persist,sleep=lambda s:None,handled=handled,rounds=2)
        self.assertEqual(len(self.calls),1,'the same supervisor start is never resumed twice')
        self.supervisor_start('2')
        br.watch(self.runtime,self.persist,sleep=lambda s:None,handled=handled,rounds=2)
        self.assertEqual(len(self.calls),2)
        self.assertEqual((self.state()['state'],self.state()['trigger'],self.state()['supervisor']),('RESUMED','supervisor-restart','2'*32))

    def test_supervisor_killed_after_a_stop_stays_off(self):
        br.remember(self.persist,now=500);self.supervisor_start('1')
        agent.atomic_json(self.persist/'native-stop.json',{'requested':600.0,'trial':None})
        self.supervisor_start('2')
        br.watch(self.runtime,self.persist,sleep=lambda s:None,handled='1'*32,rounds=1)
        self.assertEqual(self.calls,[]);self.assertEqual(self.state()['code'],'AUTO-RESUME-STOPPED')

    def test_a_crash_loop_is_bounded(self):
        # every sleep here is a new supervisor start; the 01.11.2026 watch of an accepted Start would take them too
        p=patch.object(br,'START_WATCH',0);p.start();self.addCleanup(p.stop)
        br.remember(self.persist,now=500)
        tokens=iter('12345');clock=[0.0]
        def sleep(s):
            clock[0]+=s
            ident=next(tokens,None)
            if ident:self.supervisor_start(ident)
        br.watch(self.runtime,self.persist,sleep=sleep,clock=lambda:clock[0],rounds=5)
        self.assertEqual(len(self.calls),3);self.assertEqual(self.state()['code'],'AUTO-RESUME-RESTART-LIMIT')

    # 01.11.2026 (BOOT-RECOVERY-2026-11-01.ru.md): Stop wins before every attempt; a failed pair start is retried
    def test_every_is_five_seconds_and_a_stop_during_the_window_wins(self):
        self.assertEqual(br.EVERY,5)
        br.remember(self.persist,now=500)
        self.replies=[{'accepted':False,'blockers':['PAIR-RECOVERY-REQUIRED']},{'accepted':True}]
        def sleep(seconds):
            agent.atomic_json(self.persist/'native-stop.json',{'requested':600.0,'trial':None})  # the owner's Stop
        self.assertEqual(br.run(self.runtime,self.persist,sleep=sleep,uptime=60),'SKIPPED')
        self.assertEqual(len(self.calls),1);self.assertEqual(self.state()['code'],'AUTO-RESUME-STOPPED')

    def failing(self):
        """start() queues a request with an id; fail() is pair.fail_request for it."""
        def start(**kw):
            self.calls.append(kw);self.mode={'mode':'on','id':'%032x'%len(self.calls),'revision':'a'*32};return {'accepted':True}
        p=patch.object(auto_control,'start',side_effect=start);p.start();self.addCleanup(p.stop)
        def fail():
            self.mode={'mode':'off','failed_request_id':self.mode['id'],'failure_code':'VENDOR-WORKER-QUIET-UNVERIFIED','revision':'a'*32}
        return fail

    def test_an_accepted_start_whose_pair_start_fails_is_pressed_again_bounded(self):
        br.remember(self.persist,now=500);fail=self.failing()
        clock=[0.0];slept=[0]
        def sleep(seconds):
            clock[0]+=seconds;slept[0]+=1
            if slept[0]%3==0 and self.mode.get('mode')=='on':fail()  # each queued start fails ~15 s later
        state=br._resume(self.runtime,self.persist,sleep,lambda:clock[0],br.WINDOW,'boot')[0]
        self.assertEqual(state,'FAILED');self.assertEqual(self.state()['code'],'VENDOR-WORKER-QUIET-UNVERIFIED')
        self.assertEqual(len(self.calls),1+br.START_RETRIES)

    def test_a_running_start_is_watched_then_left_alone(self):
        br.remember(self.persist,now=500);fail=self.failing()
        clock=[0.0]
        def sleep(seconds):clock[0]+=seconds
        self.assertEqual(br._resume(self.runtime,self.persist,sleep,lambda:clock[0],br.WINDOW,'boot')[0],'RESUMED')
        self.assertEqual(len(self.calls),1);self.assertGreaterEqual(clock[0],br.START_WATCH)
        # a failed request that is not ours, or a Stop (off without a failed request): finished, not pressed again
        for row in ({'mode':'off','failed_request_id':'f'*32,'failure_code':'X','revision':'a'*32},{'mode':'off','revision':'a'*32}):
            self.calls.clear();(self.runtime/br.STATE).unlink();self.mode={'mode':'off'}
            def sleep(seconds,row=row):self.mode=row
            self.assertEqual(br._resume(self.runtime,self.persist,sleep,lambda:0.0,br.WINDOW,'boot')[0],'RESUMED')
            self.assertEqual(len(self.calls),1)

    def test_a_retry_after_a_failed_pair_start_respects_the_window(self):
        br.remember(self.persist,now=500);fail=self.failing()
        clock=[0.0]
        def sleep(seconds):
            clock[0]+=seconds
            if self.mode.get('mode')=='on':clock[0]+=br.WINDOW;fail()
        self.assertEqual(br._resume(self.runtime,self.persist,sleep,lambda:clock[0],br.WINDOW,'boot')[0],'FAILED')
        self.assertEqual(len(self.calls),1,'no press after the window')

    def test_a_monitor_restart_keeps_the_token_its_boot_decision_handled(self):
        br.remember(self.persist,now=500);self.supervisor_start('1')
        agent.atomic_json(self.runtime/br.STATE,{'state':'RESUMED','supervisor':'1'*32})
        self.assertEqual(br._boot(self.runtime,self.persist,lambda s:None,60,lambda:0.0),(None,'1'*32))


if __name__=='__main__':
    unittest.main()
