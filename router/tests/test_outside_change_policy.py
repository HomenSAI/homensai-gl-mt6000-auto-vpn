"""Owner decision 07.11.2026 ('by risk + notification', review F-32 / A9 finding 2): a change made outside the app while a
session is RUNNING is adopted by itself only for wireless/dhcp/gl-dns-v2 (and the network interface/address class);
anything else is HELD (PAIR-OUTSIDE-CHANGE-HELD) with the class recorded, until the owner's Start. Shared cases:
tests/outside_change_cases.json (Lua: lua/test_outside_change.lua)."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import native_switch as native
import pair_auto as pair
from test_pair_auto import Tests as Base

CASES=json.loads((Path(__file__).resolve().parent/'outside_change_cases.json').read_text(encoding='utf-8'))
SETTINGS={'pair_auto_mode':pair.MODE,'failure_model':'consecutive'}


def observed_for(case):
    observed=dict(CASES['protected']);observed.update(case.get('protected_extra',{}))
    if case['observed'] is None:
        def unreadable(*_):raise ValueError('PAIR-CONFIG-UNVERIFIED')
        return unreadable
    observed.update(case['observed'])
    return lambda *_:observed


class SharedCases(unittest.TestCase):
    def test_every_shared_case_classifies_as_recorded(self):
        for case in CASES['cases']:
            with self.subTest(case=case['name']):
                state={'protected':dict(CASES['protected'],**case.get('protected_extra',{})),'interfaces':{'wgclient1':'wgclient','ovpnclient1':'ovpnclient'}}
                with patch.object(pair,'configs',observed_for(case)),patch.object(pair,'firewall_bytes',return_value=b'x'):
                    row=pair.readopt_class(state,case['trigger'],now=5.0)
                self.assertEqual(row['decision'],case['decision']);self.assertEqual(row['packages'],case['packages'])
                self.assertEqual(row['trigger'],case['trigger']);self.assertEqual(row['time'],5.0)
                self.assertNotIn('w2',json.dumps(row))  # names only, never a digest or a value

    def test_adopt_packages_are_exactly_the_owner_list(self):
        self.assertEqual(pair.ADOPT_PACKAGES,('wireless','dhcp','gl-dns-v2'))


class RunningSession(Base):
    def running(self,protected):
        pair.request(self.revision);first=pair.intent()['id']
        self.state.update(id=first,phase='RUNNING',owned=[],started=1.0,protected=protected,interfaces={'wgclient1':'wgclient','ovpnclient1':'ovpnclient'});pair.save(self.state)
        backend=Mock();backend.order.return_value=(self.state['order'],self.state['policy_hash'])
        return backend,first

    def tick(self,backend,observed,identity='b'*64):
        with patch.object(native,'journal_read',return_value={}),patch.object(pair,'network',return_value=[]),patch.object(pair,'normalized_network',return_value=identity),\
             patch.object(pair,'configs',observed),patch.object(pair,'firewall_bytes',return_value=b'x'),patch.object(native,'publish')as publish,patch.object(pair,'_log')as log:
            result=pair.tick(backend,SETTINGS,self.revision)
        return result,publish,log

    def test_a_wifi_dhcp_dns_change_is_adopted_and_told(self):
        protected=dict(CASES['protected'])
        backend,first=self.running(protected)
        result,publish,log=self.tick(backend,lambda *_:dict(protected,wireless='l2',dhcp='d2'))
        self.assertTrue(result)
        saved=pair.read_state();self.assertEqual(saved['phase'],'STOPPED')
        res=saved['operator_resolution'];self.assertEqual(res['adopted_by'],'automatic');self.assertEqual(res['outside_change']['decision'],'ADOPT')
        self.assertEqual(res['outside_change']['packages'],['dhcp','wireless']);self.assertNotIn('outside_change',saved)
        row=pair.intent();self.assertEqual(row['mode'],'on');self.assertNotEqual(row['id'],first)
        event=publish.call_args.args[0];self.assertEqual(event['reason'],'PAIR-READOPTED');self.assertEqual(event['outside_change']['packages'],['dhcp','wireless'])
        self.assertTrue(any('PAIR-OUTSIDE-CHANGE-ADOPTED' in str(c.args[0]) for c in log.call_args_list))
        self.assertEqual(len(agent.read_json(self.runtime/'pair-readopt.json',{})['events']),1)

    def test_a_wireguard_or_ovpnclient_change_is_held_and_told_not_adopted(self):
        for name in ('wireguard','ovpnclient'):
            with self.subTest(package=name):
                for path in pair.paths():path.unlink(missing_ok=True)
                (self.runtime/'pair-readopt.json').unlink(missing_ok=True)
                protected=dict(CASES['protected'])
                backend,first=self.running(protected)
                result,publish,log=self.tick(backend,lambda *_:dict(protected,**{name:'zz'}))
                saved=pair.read_state();self.assertEqual(saved['phase'],'HELD');self.assertEqual(saved['recovery_error'],'PAIR-EXTERNAL-CONFIG-CHANGE')
                self.assertEqual(saved['outside_change']['decision'],'HOLD');self.assertEqual(saved['outside_change']['packages'],[name])
                self.assertNotIn('operator_resolution',saved);self.assertEqual(pair.intent()['id'],first,'the request is not rotated: no adoption')
                self.assertEqual(list((self.persist/'session-recovery').glob('*')) if (self.persist/'session-recovery').exists() else [],[])
                event=publish.call_args.args[0];self.assertEqual(event['state'],'BLOCKED');self.assertEqual(event['reason'],'PAIR-OUTSIDE-CHANGE-HELD')
                self.assertEqual(event['outside_change']['packages'],[name]);self.assertEqual(event['blockers'],['PAIR-EXTERNAL-CONFIG-CHANGE'])
                self.assertTrue(any('PAIR-OUTSIDE-CHANGE-HELD' in str(c.args[0]) for c in log.call_args_list))
                self.assertFalse((self.runtime/'pair-readopt.json').exists(),'a hold spends no adoption budget')
                # the next pass changes nothing and keeps telling the class
                result,publish,log=self.tick(backend,lambda *_:dict(protected,**{name:'zz'}))
                self.assertEqual(pair.read_state()['phase'],'HELD');self.assertEqual(publish.call_args.args[0]['reason'],'PAIR-OUTSIDE-CHANGE-HELD')

    def test_order_mismatch_unknown_package_and_unreadable_class_are_held(self):
        protected=dict(CASES['protected'])
        backend,first=self.running(dict(protected,system='s1'))
        result,publish,_=self.tick(backend,lambda *_:dict(protected,system='s2'))
        self.assertEqual(pair.read_state()['outside_change']['packages'],['system']);self.assertEqual(publish.call_args.args[0]['reason'],'PAIR-OUTSIDE-CHANGE-HELD')
        for path in pair.paths():path.unlink(missing_ok=True)
        backend,first=self.running(protected)
        def unreadable(*_):raise ValueError('PAIR-CONFIG-UNVERIFIED')
        result,publish,_=self.tick(backend,unreadable)
        saved=pair.read_state();self.assertEqual(saved['phase'],'HELD');self.assertEqual(pair.intent()['id'],first)
        self.assertEqual(saved['recovery_error'],'PAIR-CONFIG-UNVERIFIED')  # the read failed before the class: held, no adoption either way
        # a class that cannot be read at the moment of the decision (the digest read fails between the check and the class)
        for path in pair.paths():path.unlink(missing_ok=True)
        backend,first=self.running(protected)
        with patch.object(native,'journal_read',return_value={}),patch.object(pair,'configs',unreadable),patch.object(pair,'_log'):
            self.assertFalse(pair.readopt_running(pair.read_state(),pair.intent(),self.revision,'PAIR-EXTERNAL-CONFIG-CHANGE'))
        saved=pair.read_state();self.assertEqual(saved['phase'],'HELD');self.assertEqual(saved['outside_change']['why'],'UNREADABLE')
        self.assertEqual(saved['outside_change']['packages'],[]);self.assertEqual(pair.intent()['id'],first)
        for code in ('SOURCE-ORDER-MISMATCH','PAIR-EXTERNAL-POLICY-CHANGE'):
            for path in pair.paths():path.unlink(missing_ok=True)
            backend,first=self.running(protected)
            with patch.object(native,'journal_read',return_value={}),patch.object(pair,'_log'):
                self.assertFalse(pair.readopt_running(pair.read_state(),pair.intent(),self.revision,code))
            saved=pair.read_state();self.assertEqual(saved['phase'],'HELD');self.assertEqual(saved['recovery_error'],code)
            self.assertEqual(saved['outside_change']['packages'],['route_policy']);self.assertEqual(saved['outside_change']['decision'],'HOLD')
            self.assertEqual(pair.intent()['id'],first);self.assertFalse((self.runtime/'pair-readopt.json').exists())

    def test_start_releases_a_hold_and_records_the_adoption(self):
        protected=dict(CASES['protected'])
        backend,first=self.running(protected)
        self.tick(backend,lambda *_:dict(protected,wireguard='w2'))
        self.assertEqual(pair.read_state()['phase'],'HELD')
        from auto_control import control_lock
        with control_lock():pair.stop_locked(self.revision)
        with patch.object(native,'journal_read',return_value={'phase':'ROLLED-BACK'}),patch.object(pair,'_log'):
            reply=pair.request(self.revision)
        self.assertTrue(reply['accepted'])
        saved=pair.read_state();self.assertEqual(saved['phase'],'STOPPED');res=saved['operator_resolution']
        self.assertEqual(res['adopted_by'],'owner-start');self.assertEqual(res['outside_change']['why'],'OWNER-START')
        self.assertEqual(res['outside_change']['packages'],['wireguard']);self.assertNotIn('outside_change',saved)
        self.assertEqual(len(list((self.persist/'session-recovery').glob('pair-*-readopt-*.json'))),1)

    def test_adoption_budget_is_unchanged(self):
        self.assertEqual(pair.READOPT_LIMIT,3)
        events,allowed=pair.readopt_allowed(10000.0);self.assertEqual((events,allowed),([],True))
        agent.atomic_json(self.runtime/'pair-readopt.json',{'events':[9990,9991,9992]})
        self.assertEqual(pair.readopt_allowed(10000.0),([9990,9991,9992],False))
        self.assertEqual(pair.readopt_allowed(10900.0),([],True))


del Base  # not collected twice
if __name__=='__main__':unittest.main()
