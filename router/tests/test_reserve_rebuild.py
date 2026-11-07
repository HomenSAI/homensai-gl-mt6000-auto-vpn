"""A vendor rebuild of the reserve must not hold Auto on it for ever (finding 7).

MT3000, 2.1.0-alpha8, 04.11.2026 14:06-15:33 (Lua runtime; private/soak-24h cycle 12, evidence-reserve-identity-20261104.json):
during an upstream outage the vendor rebuilt the OpenVPN reserve while traffic was on it. Its vendor_generation changed
(journal eb5934ad..., status 1b9ca694...), committed_recovery_decision returned HOLD RESERVE-IDENTITY-UNKNOWN on every pass
and Auto stayed DEGRADED-ON-RESERVE for over an hour with both tunnels healthy, until the owner's Stop + Start.
Lua twin: tests/lua/test_reserve_rebuild.lua (reserve_rebuild_cases.json, the same decisions and the same replay).
"""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
sys.path.insert(0,str(HERE))
import agent  # noqa: E402
import native_switch as native  # noqa: E402
import pair_auto as pair  # noqa: E402
from failure_diagnosis import resolve_pair, scoped_samples  # noqa: E402
from observation_freshness import settle_for, valid_for  # noqa: E402
from recovery_settings import normalized, stable_seconds, stable_success  # noqa: E402
import test_pair_activation_epoch as epoch  # noqa: E402

DATA=json.loads((HERE/'reserve_rebuild_cases.json').read_text(encoding='utf-8'))
PRIMARY='wireguard:peer_2006';RESERVE='openvpn:40354_2029'
OLD='eb5934adf3c54f90a1b27fe9215f2402';NEW='1b9ca6945c504157b4a0dff608ab2d0b'
P_OLD='1747efccea1b4be5a1c0fdc527bc3f52';P_NEW='5eea6867210845d086b220343cf919fb'
GENERATIONS={'OLD':OLD,'NEW':NEW}


def identity(profile,generation,interface,protocol):
    return {'id':profile,'protocol':protocol,'interface':interface,'vendor_tunnel_id':protocol+':'+interface,'vendor_generation':generation}


PROOFS={'source':identity(PRIMARY,P_OLD,'wgclient1','wireguard'),'target':identity(RESERVE,OLD,'ovpnclient1','openvpn')}


def decide_case(case):
    D=DATA['defaults'];now=case.get('now',D['now'])
    row=dict(PROOFS['target'],vendor_generation=GENERATIONS[case['generation']],vendor_changed_at=D['changed_at'],time=now)
    row.update(case.get('live',{}))
    count,generation,code=case['samples']
    # the samples follow the live profile: only the proof can tell another tunnel from a rebuild
    samples=[dict(row,time=now-10.0*i,code=code,dns_ok=code is None,https_success=2 if code is None else 0,vendor_generation=GENERATIONS[generation]) for i in range(count)]
    journal={'source':PRIMARY,'target':RESERVE,'confirmed':case.get('confirmed',D['confirmed']),'vendor_profiles':PROOFS}
    asked=[];backend=Mock();backend.health.return_value=True
    def ready(identifier,settings):
        asked.append(stable_seconds(settings));return identifier==PRIMARY and case['primary_ready']
    backend.recovery_ready.side_effect=ready
    pair_row={'coordination':{'state':case.get('coordination','READY')},'target':row,'source':{'id':PRIMARY}}
    with patch('failure_diagnosis.resolve_pair',return_value=pair_row),patch('fault_control.testing_profile',return_value=False),\
         patch('channel_model.return_ready',return_value=case.get('model_ready',True)),patch('channel_model.channel_failed',return_value=False):
        return native.committed_recovery_decision(backend,journal,dict(case.get('settings',D['settings'])),samples,now,{},hold=case.get('hold')),asked


class SharedCases(unittest.TestCase):
    def test_decisions(self):
        for case in DATA['cases']:
            with self.subTest(case['name']):
                result,asked=decide_case(case)
                self.assertEqual((result['action'],result['reason'],bool(result.get('rebind'))),(case['action'],case['reason'],case['rebind']))
                self.assertEqual(asked[-1] if asked else None,case['asked'])


class ManualHold(unittest.TestCase):
    """pair_manual.held_reserve: the same comparison held a manual session for ever (BLOCKED / DEGRADED-ON-RESERVE)."""
    def hold(self,case):
        import pair_manual,pair_policy
        D=DATA['defaults'];now=D['now'];role=case['hold'];profile=RESERVE if role=='target' else PRIMARY
        generation=GENERATIONS[case['generation']]
        expected=PROOFS[role]['vendor_generation'] if role=='source' else OLD
        live=generation if role=='target' or case['generation']=='NEW' else expected
        base=dict(PROOFS[role])
        row=dict(base,vendor_generation=live,vendor_changed_at=D['changed_at'],time=now);row.update(case.get('live',{}))
        count,gen,code=case['samples']
        sample_generation=live if gen=='NEW' or role=='target' and gen=='OLD' else expected
        samples=[dict(row,time=now-10.0*i,vendor_generation=GENERATIONS[gen] if role=='target' else sample_generation,code=code,dns_ok=code is None,
                      https_success=2 if code is None else 0) for i in range(count)]
        journal={'source':PRIMARY,'target':RESERVE,'confirmed':D['confirmed'],'phase':'COMMITTED','vendor_profiles':{} if case.get('no_proof') else PROOFS,'after':['b','a'],'hash':'c'*64}
        state={'manual_hold':role,'revision':'f'*32}
        backend=Mock();backend.attest_policy.return_value={'verified':True};backend.order.return_value=(['b','a'],'c'*64)
        settings=dict(D['settings']);status={'samples':samples,'profiles':[row]}
        resolved={'coordination':{'state':case.get('coordination','READY')},'source':None,'target':None};resolved[role]=row
        context=None if case['branch']=='legacy' else {'x':1}
        published=[]
        with patch.object(native,'bind_policy_context'),patch.object(pair_policy,'metadata',return_value=context),patch.object(pair_policy,'current_role',return_value=role),\
             patch.object(pair_policy,'state_order_matches',return_value=True),patch('failure_diagnosis.resolve_pair',return_value=resolved),\
             patch.object(native,'publish',side_effect=published.append),patch.object(pair,'save'),patch.object(pair,'resume_running'),\
             patch.object(pair,'ledger_hold',return_value=60),patch.object(pair_manual.time,'time',return_value=now),\
             patch.object(pair,'reserve_rebound',return_value=True) as rebound,\
             patch.object(native,'committed_recovery_decision',return_value={'action':case['decision'],'reason':'PRIMARY-STABLY-RECOVERED'}) as decision:
            returned=pair_manual.held_reserve(backend,state,journal,settings,status)
        return returned,published,rebound,decision,state

    def test_shared_cases(self):
        for case in DATA['manual']:
            with self.subTest(case['name']):
                returned,published,rebound,decision,state=self.hold(case)
                self.assertEqual(returned,case['returns'])
                self.assertEqual((published[-1].get('state'),published[-1].get('reason')) if published else (None,None),(case['state'],case['reason']))
                self.assertEqual(rebound.called,case['rebound'])
                self.assertEqual('manual_hold' not in state,case['released'])
                self.assertEqual(decision.called,case['asked'])
                if case['rebound']:self.assertEqual(rebound.call_args.kwargs,{'settled':True})


class Replay(unittest.TestCase):
    """The incident, decision by decision, with the real resolve_pair, streak, return gate and stable_success."""
    R=DATA['replay'];T0=1793797580.0
    SETTINGS={'interval':'30','plan_source':PRIMARY,'plan_target':RESERVE,'plan_source_tunnel':'wireguard:wgclient1','plan_target_tunnel':'openvpn:ovpnclient1'}

    def generation(self,role,at):
        changed=self.R['primary_rebuilt' if role=='source' else 'reserve_rebuilt']
        if role=='source':return P_NEW if at>=changed else P_OLD
        return NEW if at>=changed else OLD

    def status(self,at):
        R=self.R;now=self.T0+at;rows=[];groups=[];samples=[]
        for role,profile in (('source',PRIMARY),('target',RESERVE)):
            changed=R['primary_rebuilt' if role=='source' else 'reserve_rebuilt']
            after=at>=changed
            state='PENDING' if after and at<changed+R['pending'] else 'SETTLED'
            stamp=self.T0+changed if after else self.T0-1000.0
            proof=PROOFS[role];generation=self.generation(role,at)
            rows.append(dict(proof,vendor_generation=generation,vendor_state=state,vendor_changed_at=stamp,time=now,code=None,dns_ok=True,https_success=2))
            groups.append({'id':proof['vendor_tunnel_id'],'protocol':proof['protocol'],'current_profile':profile,'profiles':[profile],'active_profiles':[profile],
                           'generation':generation,'state':state,'stable_samples':2,'changed_at':stamp,'time':now})
            for back in range(0,31):
                when=at-10*back
                bad=(role=='source' and R['cut'][0]<=when<R['cut'][1]) or (role=='target' and changed<=when<changed+R['pending'])
                samples.append(dict(proof,time=self.T0+when,vendor_generation=self.generation(role,when),code='VPN-003' if bad else None,
                                    dns_ok=not bad,https_success=0 if bad else 2))
        return {'time':now,'profiles':rows,'samples':samples,'vendor_observation':{'version':1,'time':now,'groups':groups}}

    def run_replay(self):
        R=self.R;journal={'source':PRIMARY,'target':RESERVE,'confirmed':self.T0+R['committed'],'vendor_profiles':dict(PROOFS)}
        backend=Mock();current={};log=[]
        def ready(identifier,settings):
            policy=normalized(settings);status=current['status'];now=status['time']
            age=valid_for(settings);resolved=resolve_pair(status,settings,now,age,settle_for(settings))
            row=next((resolved[role] for role in ('source','target') if resolved[role] and resolved[role]['id']==identifier),None)
            return (resolved['coordination']['state']=='READY' and row is not None
                    and stable_success(scoped_samples(status['samples'],row),identifier,policy['primary_successes'],stable_seconds(settings,policy),now,age))
        backend.recovery_ready.side_effect=ready;backend.health.return_value=True
        at=R['first']
        while at<=R['last']:
            status=current['status']=self.status(at)
            decision=native.committed_recovery_decision(backend,journal,dict(self.SETTINGS),status['samples'],status['time'],status,hold=R['hold'])
            log.append((at,decision['action'],decision['reason'],bool(decision.get('rebind'))))
            if decision.get('rebind'):  # pair_auto.reserve_rebound
                row=next(x for x in status['profiles'] if x['id']==RESERVE)
                journal['vendor_profiles']=dict(journal['vendor_profiles'],target=dict(PROOFS['target'],vendor_generation=row['vendor_generation']))
            if decision['action']=='RESTORE-PRIMARY':break
            at+=R['step']
        return log

    def test_the_incident_ends_by_itself(self):
        steps=[]
        for row in self.run_replay():
            if not steps or steps[-1][1:]!=list(row[1:]):steps.append(list(row))
        # rebound once, after the vendor went quiet and two new samples passed (a short hold while the vendor rebuilds the
        # primary too), then the normal return. alpha8: HOLD RESERVE-IDENTITY-UNKNOWN from 230 to the end.
        self.assertEqual(steps,self.R['expect'])


class Rebind(unittest.TestCase):
    """pair_auto.reserve_rebound on the real journal; the tick's hook. Fixture: test_pair_activation_epoch."""
    def setUp(self):
        epoch.ActivationEpoch.setUp(self)
        log=patch.object(pair,'_log');log.start();self.addCleanup(log.stop)
        journal=dict(self.original,phase='COMMITTED');journal.pop('activation_reapply');native.journal_write(journal)
        self.proofs=journal['vendor_profiles'];self.journal=journal
        self.live={role:dict(self.proofs[role],vendor_generation=('c' if role=='target' else 'd')*32) for role in ('source','target')}

    def selection(self,**fields):return dict(self.live,vendor_identity='e'*64,**fields)

    def rebound(self,blockers=(),selection=None):
        with patch.object(self.case.backend,'diagnostic',return_value=(list(blockers),selection or self.selection())):
            return pair.reserve_rebound(self.case.backend,self.case.revision)

    def test_the_journal_follows_both_generations(self):
        self.assertTrue(self.rebound())
        journal=native.journal_read()
        self.assertEqual((journal['vendor_profiles'],journal['vendor_identity'],journal['phase']),(self.live,'e'*64,'COMMITTED'))
        self.assertFalse(self.rebound(),'once')

    def test_nothing_is_written_without_proof(self):
        other=dict(self.live['target'],interface='ovpnclient2',vendor_tunnel_id='openvpn:ovpnclient2')
        before=native.JOURNAL.read_bytes()
        self.assertFalse(self.rebound(blockers=['VENDOR-SETTLING']),'the vendor is not quiet')
        self.assertFalse(self.rebound(selection=dict(self.selection(),target=other)),'another tunnel')
        self.assertFalse(self.rebound(selection=dict(self.selection(),vendor_identity=None)))
        self.assertFalse(self.rebound(selection=dict(self.selection(),source=dict(self.live['source'],id='wireguard:peer_1'))),'another primary')
        native.journal_write(dict(self.journal,phase='ROLLED-BACK',restored_order=self.journal['before']));before=native.JOURNAL.read_bytes()
        self.assertFalse(self.rebound(),'a finished journal')
        self.assertEqual(native.JOURNAL.read_bytes(),before)

    def test_a_stop_wins_over_the_rebind(self):
        before=native.JOURNAL.read_bytes()
        with patch.object(native,'require_control_revision',side_effect=native.Refused('CLIENT-STOP')):
            self.assertFalse(self.rebound())
        self.assertEqual(native.JOURNAL.read_bytes(),before)

    def test_the_tick_rebinds_on_a_proven_rebuild_only(self):
        for decision,calls in (({'action':'OBSERVE','reason':'CLIENT-CONFIRMED','rebind':True},1),
                               ({'action':'OBSERVE','reason':'CLIENT-CONFIRMED'},0),
                               ({'action':'HOLD','reason':'RESERVE-IDENTITY-UNKNOWN','reserve_healthy':None},0)):
            with self.subTest(decision=decision),patch.object(native,'committed_recovery_decision',return_value=decision),patch.object(pair,'reserve_rebound') as hook:
                pair.tick(self.case.backend,self.case.settings,self.case.revision)
                self.assertEqual(hook.call_count,calls)


class SettledRebind(Rebind):
    def test_a_primary_hold_rebinds_a_rolled_back_journal(self):
        native.journal_write(dict(self.journal,phase='ROLLED-BACK',restored_order=self.journal['before']))
        with patch.object(self.case.backend,'diagnostic',return_value=([],self.selection())):
            self.assertTrue(pair.reserve_rebound(self.case.backend,self.case.revision,settled=True))
        self.assertEqual((native.journal_read()['vendor_profiles'],native.journal_read()['phase']),(self.live,'ROLLED-BACK'))


class GuardedReturn(unittest.TestCase):
    """The return from an unknown reserve is the normal one: finish_committed does not stop on the stale proof (the owner's
    Stop did the same in the incident, RESTORING - STOPPED in 33 s)."""
    def test_a_stale_proof_does_not_stop_the_return(self):
        case=epoch.fixture.PairManualDirections();case.setUp();self.addCleanup(case.doCleanups)
        case.request('reserve')
        self.assertTrue(epoch.fixture.manual.request('resume',case.revision)['accepted'])
        epoch.fixture.manual.consume(case.backend,pair.read_state(),case.settings,case.revision)
        journal=native.journal_read();proofs=journal['vendor_profiles']
        native.journal_write(dict(journal,vendor_profiles=dict(proofs,target=dict(proofs['target'],vendor_generation='c'*32))))
        with patch.object(pair,'network',return_value=[]),patch.object(pair,'configs',return_value={}), \
             patch.object(native,'committed_recovery_decision',return_value={'action':'RESTORE-PRIMARY','reason':'PRIMARY-STABLY-RECOVERED'}), \
             patch('failover_plan.streak',return_value=False),patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False}):
            pair.tick(case.backend,case.settings,case.revision)
        self.assertEqual(case.current,['s','t'])
        self.assertEqual(native.journal_read()['phase'],'ROLLED-BACK')
        self.assertNotIn('manual_hold',pair.read_state(),'the manual hold ended with the return')


if __name__=='__main__':
    unittest.main()
