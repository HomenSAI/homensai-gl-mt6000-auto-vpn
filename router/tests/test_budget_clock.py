"""BH3-03 (bug hunt third pass, 07.11.2026): a backward wall-clock step no longer blocks every failover.

budget() clamps a ledger stamp in the future to "now", and the cooldown spacing was measured on that clamped wall stamp:
after the clock stepped back by X (sysfixtime on the RTC-less MT3000/MT6000 starts from the newest mtime under /etc, a
bad NTP answer) every failover from a dead primary was refused with PAIR-RATE-LIMIT for X + cooldown. Now each charge
also notes its /proc/uptime second and boot_id in RAM and the spacing uses the monotonic age inside one boot; a stamp more
than CLOCK_SKEW s in the future without a note counts as old as the current uptime (at most one cooldown). The wall age
still wins when larger. Lua twin: tests/lua/test_budget_clock.lua (the same budget_clock_cases.json).
"""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
import agent  # noqa: E402
import auto_control  # noqa: E402
import native_switch as native  # noqa: E402
import pair_auto as pair  # noqa: E402
from recovery_settings import normalized  # noqa: E402

DATA=json.loads((HERE/'budget_clock_cases.json').read_text(encoding='utf-8'))
BOOT=DATA['boot'];SPACING=DATA['spacing']


def spacing_met(effective,now):
    events,_=pair.budget(effective,now,900,3)
    return not events or now-events[-1]>=SPACING


def timeline(case,t):
    """(effective events, now) t seconds after the charge of the case."""
    now=case['stamp']-case['behind']+t
    if case['mode']=='same_boot':
        record,uptime={'boot':BOOT,'at':[[case['stamp'],case['start']]]},case['start']+t
    else:
        record,uptime={},case['start']+t
    return pair.charge_clock([case['stamp']],record,now,uptime,BOOT),now


class SharedCases(unittest.TestCase):
    def test_constants_and_default_spacing(self):
        self.assertEqual((pair.CLOCK_SKEW,pair.CLOCK_NAME),(120,'pair-budget-clock.json'))
        policy=normalized({})
        self.assertEqual(max(policy['cooldown'],policy['min_dwell']),SPACING)

    def test_charge_clock_cases(self):
        for case in DATA['charge_clock']:
            with self.subTest(case['name']):
                self.assertEqual(pair.charge_clock(case['events'],case['record'],case['now'],case['uptime'],BOOT),case['expect'])

    def test_timelines(self):
        for case in DATA['timelines']:
            for t,allowed in case['checks']:
                with self.subTest(case['name'],t=t):
                    effective,now=timeline(case,t)
                    self.assertEqual(spacing_met(effective,now),allowed)

    def test_the_old_clamp_blocked_for_hours(self):
        # the finding's repro: without the clock note the 3 h step blocks the failover at every t below 3 h + cooldown
        case=DATA['timelines'][0]
        now=case['stamp']-case['behind']+600
        self.assertFalse(spacing_met([case['stamp']],now),'raw stamps (the old behaviour) are still refused')
        self.assertTrue(spacing_met(timeline(case,600)[0],now))

    def test_no_clock_keeps_the_old_behaviour(self):
        self.assertEqual(pair.charge_clock([9000.0],{},1000.0,None,None),[9000.0])
        self.assertIsNone(pair.charge_clock(None,{},1000.0,5.0,BOOT))


class Ledger(unittest.TestCase):
    """The real charge_attempt / ledger_charge / tick inputs with a patched wall clock and /proc clock."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.runtime=root/'run';self.persist=root/'persist'
        self.runtime.mkdir();self.persist.mkdir()
        for module in (agent,auto_control,native):
            for name,value in (('RUNTIME',self.runtime),('PERSIST',self.persist)):
                if hasattr(module,name):
                    p=patch.object(module,name,value);p.start();self.addCleanup(p.stop)
        self.revision=auto_control.current_revision()
        pair.request(self.revision)
        self.clock=[5000.0,BOOT]
        p=patch.object(pair,'boot_clock',side_effect=lambda:tuple(self.clock));p.start();self.addCleanup(p.stop)

    def at(self,wall,uptime):
        self.clock[0]=uptime
        return patch.object(pair.time,'time',return_value=wall)

    def ledger(self):
        return agent.read_json(self.persist/'pair-auto-budget.json',{'events':[]})

    def test_a_failover_after_a_3h_backward_step_waits_one_cooldown(self):
        S=1800000000.0
        with self.at(S,5000.0):self.assertEqual(pair.charge_attempt({},self.revision,limited=False),S)
        self.assertEqual(self.ledger(),{'events':[S]},'the ledger file keeps its format')
        self.assertEqual(agent.read_json(self.runtime/pair.CLOCK_NAME,{}),{'boot':BOOT,'at':[[S,5000.0]]})
        back=S-3*3600
        for t in (0,30,59):
            with self.subTest(t=t),self.at(back+t,5000.0+t):
                with self.assertRaisesRegex(native.Refused,'PAIR-RATE-LIMIT'):pair.charge_attempt({},self.revision,limited=False)
        with self.at(back+60,5060.0):self.assertEqual(pair.charge_attempt({},self.revision,limited=False),back+60)
        events=self.ledger()['events']
        self.assertTrue(all(x<=back+60 for x in events),'the future stamp is written back on the current wall clock: '+str(events))
        self.assertEqual(agent.read_json(self.runtime/pair.CLOCK_NAME,{})['at'][-1],[back+60,5060.0])

    def test_after_a_reboot_a_future_stamp_waits_at_most_one_cooldown_of_uptime(self):
        S=1800000000.0
        agent.atomic_json(self.persist/'pair-auto-budget.json',{'events':[S]})   # charged in an earlier boot, clock ahead
        self.clock[1]='ffffffff-0000-4000-8000-00000000000a'
        with self.at(S-3600,59.0):
            with self.assertRaisesRegex(native.Refused,'PAIR-RATE-LIMIT'):pair.charge_attempt({},self.revision,limited=False)
        with self.at(S-3600+1,60.0):self.assertEqual(pair.charge_attempt({},self.revision,limited=False),S-3599)

    def test_a_note_of_another_boot_is_not_used(self):
        S=1800000000.0
        with self.at(S,5000.0):pair.charge_attempt({},self.revision,limited=False)
        self.clock[1]='ffffffff-0000-4000-8000-00000000000a'
        with self.at(S-10,5100.0):   # 10 s behind, no usable note: wall time (inside CLOCK_SKEW) as before
            with self.assertRaisesRegex(native.Refused,'PAIR-RATE-LIMIT'):pair.charge_attempt({},self.revision,limited=False)

    def test_forward_steps_and_normal_time_are_unchanged(self):
        S=9000.0
        with self.at(S,5000.0):pair.charge_attempt({},self.revision,limited=False)
        with self.at(S+59,5059.0):
            with self.assertRaisesRegex(native.Refused,'PAIR-RATE-LIMIT'):pair.charge_attempt({},self.revision,limited=False)
        with self.at(S+600,5001.0):   # wall jumped forward: the wall age wins, as before
            self.assertEqual(pair.charge_attempt({},self.revision,limited=False),S+600)

    def test_an_abort_stamp_far_in_the_future_is_dropped(self):
        self.assertEqual(pair.abort_stamps([1000.0+121,1000.0+120,990.0],1000.0),[990.0,1000.0])
        self.assertEqual(pair.retry_wait([5000.0],[],1000.0,normalized({})),0,'an abort before a backward step does not hold the retry')

    def test_unreadable_clock_note_or_proc_keep_the_old_path(self):
        (self.runtime/pair.CLOCK_NAME).write_text('{bad')
        S=9000.0
        with self.at(S,5000.0):self.assertEqual(pair.charge_attempt({},self.revision,limited=False),S)
        self.clock[0]=None;self.clock[1]=None
        with patch.object(pair.time,'time',return_value=S+60):self.assertEqual(pair.charge_attempt({},self.revision,limited=False),S+60)

    def test_effective_events_reads_the_note_of_this_boot(self):
        agent.atomic_json(self.runtime/pair.CLOCK_NAME,{'boot':BOOT,'at':[[11800.0,500.0]]})
        self.clock[0]=545.0
        self.assertEqual(pair.effective_events({'events':[11800.0]},1045.0),[1000.0])


class Proc(unittest.TestCase):
    def test_boot_clock_on_this_host(self):
        up,boot=pair.boot_clock()
        if Path('/proc/uptime').exists() and Path(pair.BOOT_ID).exists():
            self.assertGreaterEqual(up,0);self.assertRegex(boot,r'^[0-9a-f-]{8,64}$')
        else:
            self.assertEqual((up,boot),(None,None))


if __name__ == '__main__':
    unittest.main()
