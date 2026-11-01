"""A primary the vendor keeps rebuilding must not block a verified reserve forever (MT3000 soak, 31.10.2026).

Soak cycle 10 (alpha13): both tunnels failed; the reserve recovered, but GL netifd tore wgclient1 down and set it
up again every ~2 min ("Try again: endpoint", REKEY-GIVEUP). Each re-setup gave the primary a new vendor
generation, so the Auto diagnostic refused VENDOR-SETTLING / PROFILE-IDENTITY-CHANGED on every tick and the
generation-scoped failure streak restarted each time: Auto stayed BLOCKED with the order primary-first while the
reserve was healthy.

The sequence is replayed here through the real VendorObserver (generations, PENDING/SETTLED, changed_at),
the real failure_diagnosis.resolve_pair and the real Linux.diagnostic on a fake router; every step is also
evaluated by the Lua core (diagnosis.lua / backend.lua) and must give the identical decision.
"""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
sys.path.insert(0,str(HERE))
import failure_diagnosis as fd
from vendor_observation import VendorObserver
import test_lua_backend as lb

NOW=lb.NOW
P_ID='wireguard:peer_2002';R_ID='openvpn:40354_2020'
P_TUN='wireguard:wgclient1';R_TUN='openvpn:ovpnclient2'
INTERVAL=10;MAX_AGE=30;SETTLE=30          # the diagnostic: interval*3, max(30,interval*2)
WINDOW=fd.flap_window(SETTLE)             # 120 s
START=NOW-190                             # step 190 of the replay is NOW (the fake router's clock)
IDENTITY_GAP=(200,)                       # a pass where the vendor rebound the primary mid-measurement


def inventory(primary=True):
    rows=[{'id':R_ID,'section':'40354_2020','protocol':'openvpn','interface':'ovpnclient2','vendor_tunnel_id':R_TUN}]
    if primary:rows.insert(0,{'id':P_ID,'section':'peer_2002','protocol':'wireguard','interface':'wgclient1','vendor_tunnel_id':P_TUN})
    return {'profiles':rows,'settings':{'plan_source':P_ID,'plan_target':R_ID}}


def healthy(kernel):return dict(zip(('device','mark','table','ifindex'),kernel),code=None,dns_ok=True,https_success=2)
def failing(kernel,code='VPN-003'):return dict(zip(('device','mark','table','ifindex'),kernel),code=code,dns_ok=True,https_success=0)
DOWN=(None,None,None,None)


def primary_at(s,recover_at=None):
    """Healthy, then from 40 s rebuilt every 40 s by the vendor: 10 s down, 30 s up but failing (new ifindex)."""
    if s<40 or (recover_at is not None and s>=recover_at):
        return healthy(('wgclient1',4096,'1001',10 if s<40 else 300))
    k,phase=divmod(s-40,40)
    return failing(DOWN,'VPN-001') if phase<10 else failing(('wgclient1',4096,'1001',100+k))


def reserve_at(s):
    """Fails with the primary, is rebuilt once at 150 s and is healthy (new ifindex) from 160 s."""
    if s<40:return healthy(('ovpnclient2',45056,'1012',11))
    if s<150:return failing(('ovpnclient2',45056,'1012',11))
    if s<160:return failing(DOWN,'VPN-001')
    return healthy(('ovpnclient2',45056,'1012',21))


def replay(until=400,recover_at=None,primary=primary_at,reserve=reserve_at,start=START):
    """Monitor passes every 10 s: [(step, status.json)] exactly as the agent publishes them."""
    observer=VendorObserver();samples=[];out=[];uid=[0]
    def uuid4():
        uid[0]+=1;return type('U',(),{'hex':'%032x'%uid[0]})()
    with patch('vendor_observation.uuid.uuid4',side_effect=uuid4):
        for s in range(0,until+1,10):
            now=start+s
            measured=[dict(primary(s,recover_at) if primary is primary_at else primary(s),id=P_ID,time=now),dict(reserve(s),id=R_ID,time=now)]
            observation,rows=observer.observe(inventory(),inventory(s not in IDENTITY_GAP),measured,now)
            by_id={row['id']:row for row in rows}
            profiles=[dict(p,**by_id[p['id']]) for p in inventory()['profiles']]
            for row in rows:
                samples.append({key:row.get(key) for key in ('id','time','code','dns_ok','https_success','interface','vendor_tunnel_id','vendor_generation')})
            status={'time':now,'profiles':profiles,'samples':copy.deepcopy(samples),'vendor_observation':observation,'observation_valid_for':MAX_AGE}
            out.append((s,json.loads(json.dumps(status))))
    return out


SETTINGS={'plan_source':P_ID,'plan_target':R_ID,'interval':str(INTERVAL)}


def decide(status,window):
    pair=fd.resolve_pair(copy.deepcopy(status),SETTINGS,status['time'],MAX_AGE,SETTLE,window)
    return pair['coordination']['state'],pair['coordination']['code'],pair


class FlappingPrimary(unittest.TestCase):
    def test_strict_resolution_never_ends_while_the_vendor_keeps_rebuilding_the_primary(self):
        """The soak failure: without the bounded window no decision is ever possible."""
        codes=set()
        for s,status in replay():
            if s<40:continue
            state,code,_=decide(status,None)
            self.assertNotEqual(state,'READY',(s,code));codes.add(code)
        self.assertLessEqual({'VENDOR-SETTLING'},codes)

    def test_bounded_window_releases_the_healthy_reserve_and_keeps_short_settling(self):
        seen={}
        for s,status in replay():
            state,code,pair=decide(status,WINDOW)
            seen[s]=code
            if s<40:self.assertIn(code,('VENDOR-SETTLING','CROSS-TUNNEL-READY'),s)  # first observation settles
            elif s<190:
                # the primary has not yet been unhealthy for the whole window, or the reserve still settles
                self.assertNotEqual(state,'READY',(s,code))
            elif s in IDENTITY_GAP:
                self.assertEqual(code,'VENDOR-IDENTITY-UNKNOWN','an unknown binding is never acted on')
            else:
                self.assertEqual((state,code),('READY',fd.SOURCE_UNSTABLE),s)
                self.assertEqual(pair['source']['id'],P_ID);self.assertEqual(pair['target']['id'],R_ID)
                self.assertEqual(pair['target']['vendor_state'],'SETTLED')
                self.assertGreaterEqual(status['time'],pair['coordination']['settle_until'],'the reserve settled')
        self.assertEqual(seen[180],'VENDOR-SETTLING','the rebuilt reserve settles first')
        self.assertEqual(seen[190],fd.SOURCE_UNSTABLE)

    def test_a_recovered_primary_restores_the_strict_meaning_at_once(self):
        result={s:decide(status,WINDOW)[1] for s,status in replay(until=330,recover_at=260)}
        self.assertEqual(result[250],fd.SOURCE_UNSTABLE)
        self.assertEqual(result[260],'VENDOR-SETTLING','a healthy observation ends the unstable window immediately')
        self.assertEqual(result[280],'VENDOR-SETTLING')
        self.assertEqual(result[290],'CROSS-TUNNEL-READY')

    def test_one_rebuild_of_a_failing_primary_is_still_only_settling(self):
        def once(s):
            if s<40:return healthy(('wgclient1',4096,'1001',10))
            if s<60:return failing(('wgclient1',4096,'1001',10))
            if s<70:return failing(DOWN,'VPN-001')
            return failing(('wgclient1',4096,'1001',50))
        steady=lambda s:healthy(('ovpnclient2',45056,'1012',11))
        result={s:decide(status,WINDOW)[1] for s,status in replay(until=200,primary=once,reserve=steady)}
        self.assertEqual(result[60],'VENDOR-SETTLING');self.assertEqual(result[90],'VENDOR-SETTLING')
        # settled again: the ordinary path (generation-scoped streak) decides, not the unstable window
        self.assertEqual(result[100],'CROSS-TUNNEL-READY');self.assertEqual(result[190],'CROSS-TUNNEL-READY')

    def test_unstable_needs_continuous_fresh_unhealthy_evidence(self):
        statuses=dict(replay())
        status=statuses[250];row=next(p for p in status['profiles'] if p['id']==P_ID)
        samples=status['samples'];now=status['time']
        self.assertTrue(fd.source_unstable(samples,row,P_TUN,now,MAX_AGE,WINDOW))
        cases={
            'stale newest':[x for x in samples if not (x['id']==P_ID and x['time']>now-40)],
            'gap':[x for x in samples if not (x['id']==P_ID and now-120<x['time']<now-60)],
            'healthy inside':[dict(x,code=None) if x['id']==P_ID and x['time']==now-50 else x for x in samples],
            'unverified inside':[dict(x,code='CHECK-LIMIT') if x['id']==P_ID and x['time']==now-50 else x for x in samples],
            'conflicting duplicate':samples+[dict(next(x for x in samples if x['id']==P_ID and x['time']==now-50),code='DNS-001')],
            'other tunnel':[dict(x,vendor_tunnel_id='wireguard:wgclient2') if x['id']==P_ID else x for x in samples],
            'too short':[x for x in samples if x['time']>now-100],
            'no probe failure':[dict(x,code='VENDOR-IDENTITY-CHANGED') if x['id']==P_ID else x for x in samples],
        }
        for name,values in cases.items():
            self.assertFalse(fd.source_unstable(values,row,P_TUN,now,MAX_AGE,WINDOW),name)
        self.assertEqual([fd.flap_window(x) for x in (30,40,60,200,600,True,None)],[120,120,180,600,900,None,None])


@unittest.skipUnless(lb.LUA,'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class LuaDecidesTheSame(unittest.TestCase):
    def check(self,cases):
        results=lb.run_lua(cases)
        failures=[(k,p,l) for (k,_,fn),l in zip(cases,results) for p in [lb.outcome(fn)] if not lb.same(k,p,l)]
        self.assertEqual(len(results),len(cases))
        self.assertFalse(failures,json.dumps(failures[:3])[:3000])
        return results

    def test_every_replayed_step_resolves_identically(self):
        cases=[]
        for run in (replay(),replay(until=330,recover_at=260)):
            for s,status in run:
                for window in (None,WINDOW,0,'x'):
                    data={'status':status,'settings':SETTINGS,'now':status['time'],'max_age':MAX_AGE,'settle':SETTLE,'source_window':window}
                    cases.append(('resolve_pair',data,lambda st=status,w=window:fd.resolve_pair(copy.deepcopy(st),SETTINGS,st['time'],MAX_AGE,SETTLE,w)))
        results=self.check(cases)
        codes={r['ok']['coordination']['code'] for r in results}
        self.assertLessEqual({fd.SOURCE_UNSTABLE,'VENDOR-SETTLING','CROSS-TUNNEL-READY','VENDOR-IDENTITY-UNKNOWN'},codes)

    def test_source_unstable_and_window_identically(self):
        statuses=dict(replay());cases=[]
        for s in (150,190,200,250,300):
            status=statuses[s];now=status['time']
            for row in status['profiles']:
                for anchor in (P_TUN,R_TUN):
                    for window in (WINDOW,60,600):
                        data={'samples':status['samples'],'row':row,'anchor':anchor,'now':now,'max_age':MAX_AGE,'window':window}
                        cases.append(('source_unstable',data,lambda st=status,r=row,a=anchor,w=window,t=now:fd.source_unstable(st['samples'],r,a,t,MAX_AGE,w)))
        for settle in (30,40,60,200,600,1.5,'x'):
            cases.append(('flap_window',{'settle':settle},lambda x=settle:[fd.flap_window(x)]))
        results=self.check(cases)
        self.assertIn({'ok':True},results);self.assertIn({'ok':False},results)

    def test_linux_diagnostic_on_the_flapping_router(self):
        """The whole Auto diagnostic (Python Linux.diagnostic and Lua backend) at NOW of the replay."""
        statuses=dict(replay());status=statuses[190]
        self.assertEqual(status['time'],NOW)
        world=lambda **over:lb.base_world(status=status,ifindex={'wgclient1':10,'ovpnclient2':21},**over)
        worlds={
            'primary bound now (another ifindex than measured)':world(),
            'primary down now':world(ifaces={'wgclient1':lb.ubus_iface(False),'ovpnclient2':lb.ubus_iface(True,'ovpnclient2')}),
            'primary half built (no route)':world(routes=[{'dst':'default','dev':'ovpnclient2','table':'1012'}]),
            'strict before the window':lb.base_world(status=dict(replay(until=150,start=NOW-150))[150],ifindex={'wgclient1':10,'ovpnclient2':11}),
        }
        cases=[('diagnostic',{'world':lb.lua_world(w)},lambda w=w:lb.py_diagnostic(w)) for w in worlds.values()]
        results=dict(zip(worlds,self.check(cases)))
        blockers,selection=results['primary bound now (another ifindex than measured)']['ok']
        self.assertEqual(blockers,[]);self.assertEqual(selection['coordination']['code'],fd.SOURCE_UNSTABLE)
        self.assertEqual(selection['source']['kernel_binding']['ifindex'],10)
        self.assertRegex(selection['vendor_identity'],'^[a-f0-9]{64}$')
        blockers,selection=results['primary down now']['ok']
        self.assertEqual(blockers,[]);self.assertEqual(selection['source']['kernel_binding']['code'],'VPN-001')
        self.assertEqual(results['primary half built (no route)']['ok'][0],['VENDOR-SETTLING'])
        self.assertNotEqual(results['strict before the window']['ok'][0],[])


class PairTickLeavesTheUnstablePrimary(unittest.TestCase):
    """pair_auto.tick with the real decision, transaction child, journal and budget (test_auto_decision_regressions)."""
    def setUp(self):
        import test_auto_decision_regressions as dr
        self.dr=dr;dr.Decisions.setUp(self)

    def flapping_status(self,now):
        import agent
        from vendor_fixture import attach
        case=self.case
        rows=[copy.deepcopy(case.selection[role]) for role in ('source','target')]
        rows[0].update(code='VPN-003',dns_ok=True,https_success=0);rows[1].update(code=None,dns_ok=True,https_success=2)
        status=attach(dict(profiles=rows,samples=[]),now)
        source,target=status['profiles']
        # the vendor rebuilt the primary a moment ago again: its row settles, its generation is new
        source.update(vendor_state='PENDING',vendor_changed_at=now-5,vendor_generation='f'*32)
        groups={group['id']:group for group in status['vendor_observation']['groups']}
        groups[source['vendor_tunnel_id']].update(state='PENDING',stable_samples=1,changed_at=now-5,generation='f'*32)
        target['vendor_changed_at']=groups[target['vendor_tunnel_id']]['changed_at']=self.dr.fixture.NOW-10000
        case.selection['source'].update(vendor_changed_at=now-5,vendor_generation='f'*32)
        status['samples']=[dict(id=source['id'],time=now-i*10,code='VPN-001' if i%4==0 else 'VPN-003',dns_ok=True,https_success=0,
                                interface=source['interface'],vendor_tunnel_id=source['vendor_tunnel_id'],vendor_generation='%032x'%(i//4))
                           for i in range(16)]
        status['samples']+=[dict(id=target['id'],time=now-i*10,code=None,dns_ok=True,https_success=2,interface=target['interface'],
                                 vendor_tunnel_id=target['vendor_tunnel_id'],vendor_generation=target['vendor_generation']) for i in range(3)]
        agent.atomic_json(case.runtime/'status.json',status)

    def tick(self,now):self.dr.Decisions.tick(self,now)

    def test_without_the_unstable_proof_the_rebuilt_primary_is_never_left(self):
        import native_switch as native
        now=self.dr.fixture.NOW
        self.flapping_status(now);self.tick(now)
        self.assertEqual(self.attempt.call_count,0)
        self.assertEqual(self.case.current,['s','t'])
        published=self.case.publish.call_args.args[0]
        self.assertEqual((published['state'],published['source_failures']),('OBSERVING',False))
        self.assertEqual(published['reason'],'VENDOR-SETTLING')
        self.assertIsNone(native.journal_read().get('phase'))

    def test_the_unstable_proof_moves_traffic_to_the_verified_reserve(self):
        import native_switch as native
        import agent
        now=self.dr.fixture.NOW
        self.case.selection['coordination']={'state':'READY','code':fd.SOURCE_UNSTABLE}
        self.flapping_status(now);self.tick(now)
        self.assertEqual(self.attempt.call_count,1)
        journal=native.journal_read()
        self.assertEqual(journal['phase'],'COMMITTED');self.assertEqual(self.case.current,['t','s'])
        self.assertEqual(journal['pair_transition']['destination_role'],'target')
        self.assertEqual(len(agent.read_json(self.case.persist/'pair-auto-budget.json')['events']),1)
        # still unstable on the next tick: the reserve is kept (no return to a primary that is not healthy)
        self.case.backend.recovery_ready.side_effect=None;self.case.backend.recovery_ready.return_value=False
        self.flapping_status(now+10);self.tick(now+10)
        self.assertEqual(self.case.current,['t','s']);self.assertEqual(self.attempt.call_count,1)
        published=self.case.publish.call_args.args[0]
        self.assertEqual((published['state'],published['reason']),('COMMITTED','CLIENT-CONFIRMED'),'the held reserve stays verified')
        status=agent.read_json(self.case.runtime/'status.json')
        self.assertEqual(fd.resolve_pair(status,dict(self.case.settings,interval=10),now+10,30,30)['coordination']['code'],'VENDOR-SETTLING')


if __name__=='__main__':
    unittest.main()
