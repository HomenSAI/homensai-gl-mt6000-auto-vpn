"""Stage 2 of the best-server pick (2.1.0-alpha2): the Auto supervisor changes the idle reserve's server itself, inside
its control lock, and re-binds its own session - no PAIR-EXTERNAL-*/SOURCE-ORDER-MISMATCH, no PAIR-READOPTED (MT3000
02.11.2026: a change from outside the pair cost the working channel a 7.1 s LAN stall). Lua twin:
tests/lua/test_auto_server_pick.lua (the same world and decisions)."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent  # noqa: E402
import auto_control  # noqa: E402
import native_switch as native  # noqa: E402
import pair_auto as pair  # noqa: E402
from pair_policy import proof  # noqa: E402
import server_pick as S  # noqa: E402

H1,H2='ab'*32,'cd'*32
UCI_RULE=("route_policy.cfg0456cd=rule\nroute_policy.cfg0456cd.tunnel_id='4192'\nroute_policy.cfg0456cd.via_type='openvpn'\n"
          "route_policy.cfg0456cd.via='ovpnclient1'\nroute_policy.cfg0456cd.group_id='40354'\nroute_policy.cfg0456cd.client_id='%s'\n"
          "route_policy.cfg0456cd.profiles='/etc/vpn_profiles.d/profile4192'\nroute_policy.cfg0456cd.mark='0xb000'\n"
          "route_policy.cfg0123ab=rule\nroute_policy.cfg0123ab.tunnel_id='5841'\nroute_policy.cfg0123ab.via_type='wireguard'\nroute_policy.cfg0123ab.via='wgclient1'\n"
          "route_policy.cfg0123ab.group_id='10004'\nroute_policy.cfg0123ab.peer_id='2002'\nroute_policy.cfg0123ab.profiles='/etc/vpn_profiles.d/profile5841'\n"
          "route_policy.cfg0123ab.mark='0x1000'\n")


def sha(text):return hashlib.sha256(text.encode()).hexdigest()


class World:
    """The router: uci of the reserve rule and its interface; a commit of route_policy renames the anonymous reserve rule."""
    def __init__(self,clock,fail_commit=False):
        self.clock=clock;self.client='2020';self.config='40354_2020';self.staged={};self.exec=[];self.logs=[];self.files={}
        self.healthy={};self.blockers=[];self.kernel_role='source';self.fail_commit=fail_commit
        self.live=['r1','r2'];self.hash=H1;self.journal={}
        self.selection={'source':{'id':'wireguard:peer_1','protocol':'wireguard','interface':'wgclient1'},
                        'target':{'id':'openvpn:40354_2020','protocol':'openvpn','interface':'ovpnclient1'},
                        'source_rule':'r1','target_rule':'r2','order':['r1','r2'],'generic_rules':['r1','r2'],'hash':H1,'direction':'first',
                        'process_bindings':None,'vendor_identity':'ef'*32}
        self.io={'runtime':'/run','read':self.files.get,'write':self.write,'alive':lambda pid:False,'log':self.logs.append,'exec':self.run}

    def write(self,path,text):self.files[path]=text;return True

    def run(self,argv,seconds):
        line=' '.join(argv);self.exec.append(line)
        if line=='uci -q -X show route_policy':return 0,UCI_RULE%self.client
        if line.startswith('uci set route_policy.cfg0456cd.client_id='):self.staged['client']=line.rsplit('=',1)[1]
        if line.startswith('uci set network.ovpnclient1.config='):self.staged['config']=line.rsplit('=',1)[1]
        if line=='uci commit route_policy':
            if self.fail_commit:self.fail_commit=False;return 1,''
            if 'client' in self.staged:
                self.client=self.staged.pop('client');rule='r2' if self.client=='2020' else 'r2_'+self.client
                self.live=['r1',rule];self.hash=H1 if self.client=='2020' else H2
                self.selection.update(target_rule=rule,order=list(self.live),generic_rules=list(self.live),hash=self.hash)
        if line=='uci commit network' and 'config' in self.staged:
            self.config=self.staged.pop('config');self.selection['target']['id']='openvpn:'+self.config
        return 0,''

    def rows(self):return [{'.name':'wgclient1','config':'peer_2002','disabled':'0'},{'.name':'ovpnclient1','config':self.config,'disabled':'0'}]

    # the backend
    def order(self):return list(self.live),self.hash
    def diagnostic(self):return list(self.blockers),copy.deepcopy(self.selection) if not self.blockers else None
    def attest_policy(self,selection=None):
        order=list(self.live) if self.kernel_role=='source' else list(reversed(self.live))
        return {'verified':True,'role':self.kernel_role,'order':order,'policy_hash':self.hash,'time':self.clock[0],'kernel_fingerprint':'0'*64}
    def health(self,identifier):return self.healthy.get(identifier)
    def use_process_bindings(self,bindings):pass
    def recovery_ready(self,identifier,settings):return False


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name);self.runtime=root/'run';self.persist=root/'persist'
        self.runtime.mkdir();self.persist.mkdir()
        for module in (agent,auto_control,native):
            for name,value in (('RUNTIME',self.runtime),('PERSIST',self.persist)):
                if hasattr(module,name):
                    p=patch.object(module,name,value);p.start();self.addCleanup(p.stop)
        self.revision=auto_control.current_revision()
        self.clock=[1761830400.0]
        p=patch.object(pair.time,'time',side_effect=lambda:self.clock[0]);p.start();self.addCleanup(p.stop)
        self.settings={'pair_auto_mode':pair.MODE,'server_pick':'1','plan_source_tunnel':'wireguard:wgclient1','plan_target_tunnel':'openvpn:ovpnclient1'}
        self.published=[]

    def world(self,fail_commit=False):
        w=World(self.clock,fail_commit)
        pair.request(self.revision)
        state={'id':pair.intent()['id'],'phase':'RUNNING','ran':True,'started':self.clock[0]-1000,'revision':self.revision,
               'network_identity':sha('net:40354_2020'),'interfaces':{'wgclient1':'wgclient','ovpnclient1':'ovpnclient'},
               'protected':{'route_policy':sha('rp:2020'),'wireguard':'0'*64},'owned':[],'before_flags':{'wgclient1':'0','ovpnclient1':'0'},
               'process_bindings':None,'order':['r1','r2'],'policy_hash':H1,'policy_roles':proof(w.selection),
               'selected_policy':{'role':'source','order':['r1','r2'],'hash':H1,'since':self.clock[0]-900}}
        pair.save(state)
        agent.atomic_json(self.runtime/'status.json',{'time':self.clock[0],'samples':[],'profiles':[]})
        patches=[patch.object(pair,'SERVER_IO',w.io),patch.object(pair,'network',side_effect=w.rows),
                 patch.object(pair,'normalized_network',side_effect=lambda rows,managed=None:sha('net:'+next(r['config'] for r in rows if r['.name']=='ovpnclient1'))),
                 patch.object(pair,'configs',side_effect=lambda managed=None:{'route_policy':sha('rp:'+w.client),'wireguard':'0'*64}),
                 patch.object(pair,'client_down',return_value=False),
                 patch.object(native,'journal_read',side_effect=lambda:copy.deepcopy(w.journal)),
                 patch.object(native,'journal_write',side_effect=lambda value:setattr(w,'journal',copy.deepcopy(value))),
                 patch.object(native,'publish',side_effect=lambda value:self.published.append(value)),
                 patch('failover_plan.streak',return_value=False),patch('failure_diagnosis.diagnose',return_value={'suppress_switch':False})]
        for p in patches:p.start();self.addCleanup(p.stop)
        return w

    def request(self,w,**over):
        row={'time':self.clock[0],'tunnel_id':4192,'protocol':'openvpn','interface':'ovpnclient1','section':'cfg0456cd','from':'40354_2020','to':'40354_2016',
             'group_id':'40354','profile_id':'2016','from_ms':48,'to_ms':21,'from_location':'Kyiv','to_location':'Berlin'}
        row.update(over);w.files['/run/'+S.CHANGE]=json.dumps(row)

    def writes(self,w):return sum(1 for line in w.exec if line.startswith(('uci set','ifdown','ifup')))

    def no_readopt(self,state_id):
        self.assertFalse((self.runtime/'pair-readopt.json').exists(),'no readopt')
        self.assertEqual(pair.intent()['id'],state_id,'the same Auto request (no re-arm)');self.assertEqual(pair.read_state()['id'],state_id)

    def tick(self):return pair.tick(self.world_backend,self.settings,self.revision)

    def test_the_idle_reserve_gets_the_new_server_inside_the_session(self):
        w=self.world();self.world_backend=w;sid=pair.intent()['id']
        self.request(w)
        self.assertTrue(self.tick())
        self.assertEqual(w.exec,['uci -q -X show route_policy','uci set route_policy.cfg0456cd.client_id=2016','uci -q delete route_policy.cfg0456cd.peer_id',
                                 'uci set route_policy.cfg0456cd.group_id=40354','uci set network.ovpnclient1.config=40354_2016','uci set network.ovpnclient1.disabled=0',
                                 'uci commit route_policy','uci commit network','ifdown ovpnclient1','ifup ovpnclient1'])
        state=pair.read_state()
        self.assertEqual(state['order'],['r1','r2_2016']);self.assertEqual(state['policy_hash'],H2);self.assertEqual(state['network_identity'],sha('net:40354_2016'))
        self.assertEqual(state['protected'],{'route_policy':sha('rp:2016'),'wireguard':'0'*64})
        self.assertEqual(state['policy_roles'],proof(w.selection),'the roles equal a fresh proof of the new selection')
        self.assertEqual(state['policy_roles']['target_id'],'openvpn:40354_2016')
        self.assertEqual(state['selected_policy']['order'],['r1','r2_2016']);self.assertEqual(state['selected_policy']['hash'],H2)
        self.assertEqual(state['server_change']['phase'],'CONNECTING');self.assertEqual(state['server_change']['to']['id'],'openvpn:40354_2016')
        self.assertEqual(state['server_change']['from'],{'group_id':'40354','profile_id':'2020'})
        self.assertEqual((self.published[-1]['state'],self.published[-1]['reason']),('OBSERVING','SERVER-CHANGING'))
        self.assertEqual(json.loads(w.files['/run/'+S.STATE])['changes']['4192'],[self.clock[0]])
        self.no_readopt(sid)
        before=len(w.exec);self.clock[0]+=5
        self.assertTrue(self.tick());self.assertEqual(len(w.exec),before);self.assertEqual(self.published[-1]['reason'],'SERVER-CHANGING')
        w.healthy['openvpn:40354_2016']=True;self.clock[0]+=5
        self.assertTrue(self.tick());self.assertEqual(pair.read_state()['server_change']['phase'],'SETTLING')
        self.assertEqual(json.loads(w.files['/run/'+S.EVENT])['tunnels'][0]['code'],'SERVER-PICKED')
        self.assertEqual(w.logs[-1],'SERVER-PICKED: server of the channel changed (tunnel 4192 openvpn): Kyiv -> Berlin, 48 -> 21 ms')
        self.assertEqual(json.loads(w.files['/run/'+S.STATE])['last']['4192']['to'],'40354_2016')
        self.clock[0]+=2
        self.assertTrue(self.tick());self.assertNotIn('server_change',pair.read_state(),'the diagnostic is clear: the change is finished')
        last=self.published[-1]
        self.assertEqual((last['state'],last['reason'],last['target']),('OBSERVING','PAIR-WATCHING','openvpn:40354_2016'),'the normal pass, no EXTERNAL code')
        self.assertEqual(pair.read_state()['phase'],'RUNNING');self.no_readopt(sid)
        self.assertEqual(self.writes(w),6,'the hand-off is taken once')

    def test_refused_while_carrying_not_at_rest_over_the_limit_or_off(self):
        w=self.world();self.world_backend=w
        self.request(w,interface='wgclient1',protocol='wireguard',section='cfg0123ab',tunnel_id=5841,**{'from':'10004_2002','to':'10004_2000'},group_id='10004',profile_id='2000')
        self.assertIsNotNone(S.claim(w.io,json.loads(w.files['/run/'+S.CHANGE]),self.clock[0]),'a live hand-off, refused only as carrying')
        self.assertTrue(self.tick());self.assertEqual(self.writes(w),0);self.assertEqual(self.published[-1]['reason'],'PAIR-WATCHING')
        self.request(w);w.kernel_role='target'
        self.assertFalse(pair.server_start(w,pair.read_state(),self.settings,self.revision,{}),'on the reserve: the reserve carries')
        w.kernel_role='source'
        self.assertFalse(pair.server_start(w,pair.read_state(),self.settings,self.revision,{'phase':'APPLYING'}),'a transaction in progress')
        state=pair.read_state();state['manual_hold']='source'
        self.assertFalse(pair.server_start(w,state,self.settings,self.revision,{}),'a manual hold')
        self.assertFalse(pair.server_start(w,pair.read_state(),dict(self.settings,plan_target_tunnel=None),self.revision,{}),'bound by profile id only')
        self.assertFalse(pair.server_start(w,pair.read_state(),dict(self.settings,server_pick='0'),self.revision,{}),'the owner switch off')
        self.request(w,**{'from':'40354_2011'})
        self.assertFalse(pair.server_start(w,pair.read_state(),self.settings,self.revision,{}),'a stale hand-off')
        self.assertEqual(self.writes(w),0)
        now=self.clock[0];self.request(w)
        w.files['/run/'+S.STATE]=json.dumps({'changes':{'4192':[now-100,now-200,now-300,now-400]},'last':{}})
        self.assertFalse(pair.server_start(w,pair.read_state(),self.settings,self.revision,{}));self.assertEqual(self.writes(w),0)
        self.assertEqual(json.loads(w.files['/run/'+S.EVENT])['tunnels'][0]['code'],'SERVER-PICK-LIMIT')
        logs=len(w.logs);self.assertFalse(pair.server_start(w,pair.read_state(),self.settings,self.revision,{}))
        self.assertEqual(len(w.logs),logs,'the same refusal is logged once')

    def test_a_new_server_that_fails_the_check_is_rolled_back(self):
        w=self.world();self.world_backend=w;sid=pair.intent()['id']
        self.request(w);self.assertTrue(self.tick())
        w.healthy['openvpn:40354_2016']=False
        for _ in range(6):
            self.clock[0]+=10;self.assertTrue(self.tick())
        state=pair.read_state()
        self.assertEqual(state['server_change']['phase'],'SETTLING');self.assertTrue(state['server_change']['rolled_back'])
        self.assertEqual(state['order'],['r1','r2']);self.assertEqual(state['policy_hash'],H1);self.assertEqual(state['policy_roles']['target_id'],'openvpn:40354_2020')
        self.assertEqual(state['network_identity'],sha('net:40354_2020'));self.assertEqual(state['protected']['route_policy'],sha('rp:2020'))
        self.assertEqual(w.exec[-9],'uci set route_policy.cfg0456cd.client_id=2020')
        self.assertEqual(w.logs[-1],'SERVER-PICK-FAILED: server change of the channel failed (tunnel 4192 openvpn): Kyiv -> Berlin, 48 -> 21 ms; rolled back')
        self.assertEqual(json.loads(w.files['/run/'+S.EVENT])['tunnels'][0]['code'],'SERVER-PICK-FAILED')
        self.clock[0]+=2;self.assertTrue(self.tick())
        self.assertNotIn('server_change',pair.read_state());self.assertEqual(self.published[-1]['reason'],'PAIR-WATCHING')
        self.no_readopt(sid)

    def test_a_failed_step_is_undone_and_a_rolled_back_journal_follows_the_session(self):
        w=self.world(fail_commit=True);self.world_backend=w
        self.request(w);self.assertTrue(self.tick())
        state=pair.read_state()
        self.assertTrue(state['server_change']['rolled_back']);self.assertEqual(state['order'],['r1','r2']);self.assertEqual(state['policy_hash'],H1)
        self.assertEqual(w.logs[-1],'SERVER-PICK-FAILED: server change of the channel failed (tunnel 4192 openvpn): Kyiv -> Berlin, 48 -> 21 ms; rolled back')
        # a finished return (ROLLED-BACK with its pair context) is renamed with the session: the cleanup's check holds
        from pair_policy import transition,metadata,state_order_matches
        context=transition(w.selection,['r1','r2'],'target')
        journal={'tx':'cc'*16,'phase':'ROLLED-BACK','before':['r1','r2'],'after':['r2','r1'],'restored_order':['r1','r2'],'hash':H1,
                 'source':w.selection['source']['id'],'target':w.selection['target']['id'],'pair_transition':context}
        value,renamed=S.rebind(pair.read_state(),journal,['r1','r2_2016'],H2,'openvpn:40354_2016')
        self.assertEqual(metadata(renamed)['session_order'],value['order']);self.assertEqual(renamed['hash'],value['policy_hash'])
        self.assertEqual(renamed['after'],['r2_2016','r1']);self.assertTrue(state_order_matches(value,renamed,(['r1','r2_2016'],H2)))


if __name__=='__main__':unittest.main()
