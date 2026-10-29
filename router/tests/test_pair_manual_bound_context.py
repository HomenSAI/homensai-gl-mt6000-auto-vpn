"""Manual API boundaries use real Linux order, Lua policy parsing and FW3 proof.

Only UCI/kernel effects and physical diagnostics are modelled. order(),
policy_hash(), stock-derived identities, native child/CAS and manual APIs run.
"""
import copy,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,auto_control,native_switch as n,pair_auto as pair,pair_manual as manual,pair_policy
import manual_control,manual_dispatch
from recovery_settings import fingerprint
from test_kernel_policy import fixture,network_fixture
from vendor_fixture import stamp

LUA=shutil.which('lua5.1')
ROOT=Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'
NOW=1792750000
PRELUDE=r'''
local json=require('cjson');FIXTURE=json.decode(io.read('*a'))
local function copy(x)if type(x)~='table'then return x end;local y={};for k,v in pairs(x)do y[k]=copy(v)end;return y end
package.preload['uci']=function()
 return {cursor=function()
  local c={}
  function c:changes()return {}end
  function c:foreach(config,kind,callback)
   local rows=config=='route_policy'and FIXTURE.sections or config=='firewall'and FIXTURE.firewall_defaults or {}
   for _,row in ipairs(rows)do if not kind or row['.type']==kind or config=='firewall'and kind=='defaults'then callback(copy(row))end end
  end
  function c:get_all(config,section)
   if config=='homensai_vpn'then return copy(FIXTURE.settings)end
   if config=='route_policy'then for _,row in ipairs(FIXTURE.sections)do if row['.name']==section then return copy(row)end end end
  end
  function c:get(config,section,key)
   if config=='glipv6'and key=='enabled'then return FIXTURE.ipv6 end
   if config=='network'and section=='lan'then return 'br-lan'end
   local row=self:get_all(config,section);return row and row[key]or nil
  end
  function c:set(config,section,key,value)
   assert(config=='route_policy');for _,row in ipairs(FIXTURE.sections)do if row['.name']==section then row[key]=value;return true end end;return nil
  end
  function c:reorder(config,section,index)
   assert(config=='route_policy');for i,row in ipairs(FIXTURE.sections)do if row['.name']==section then table.remove(FIXTURE.sections,i);table.insert(FIXTURE.sections,index+1,row);return true end end;return nil
  end
  function c:save(config)assert(config=='route_policy');return true end
  function c:commit(config)assert(config=='route_policy');return true end
  return c
 end}
end
'''


@unittest.skipUnless(LUA,'Actual Lua 5.1 runtime required; both approved CI images provide it')
class BoundManualContext(unittest.TestCase):
    def enter(self,context):
        value=context.__enter__();self.addCleanup(context.__exit__,None,None,None);return value

    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name)
        self.runtime=self.root/'run';self.persist=self.root/'persist';self.runtime.mkdir();self.persist.mkdir()
        for module in (agent,n,auto_control):
            self.enter(patch.object(module,'RUNTIME',self.runtime))
            if hasattr(module,'PERSIST'):self.enter(patch.object(module,'PERSIST',self.persist))
        self.enter(patch.object(n,'JOURNAL',self.persist/'native-transaction.json'));self.enter(patch.object(n,'STATE',self.runtime/'native-status.json'))
        self.enter(patch('pair_manual.time.time',return_value=NOW));self.enter(patch.object(n,'STOP',False))
        self.enter(patch.object(n,'PROOF_SCOPE',n.PROOF_SCOPE))  # attempt() updates it; restore after each isolated case.
        self.enter(patch.object(n.os,'killpg'))  # Synthetic child PIDs never reach a real process group.
        self.revision=auto_control.current_revision();self.data,initial,self.mangle,self.ip_rules=fixture()
        self.profiles=[copy.deepcopy(initial[key])for key in ('source','target')]
        for profile in self.profiles:stamp(profile,NOW)
        self.data['settings'].update(pair_auto_mode=pair.MODE,native_trial='a'*32,native_until=str(NOW+180),native_proof_scope=pair.MODE,
                                     recovery_min_dwell='60',recovery_cooldown='60')
        for row in self.data['sections'][-2:]:
            row.update({'.anonymous':True,'.name':'cfg000001'if row['via'].startswith('wg')else'cfg000002','options_in_used':'0',
                        'via_type':'wireguard'if row['via'].startswith('wg')else'openvpn','group_id':'40354'})
            row.update({'peer_id':'2002'}if row['via'].startswith('wg')else{'client_id':'2020'})
        self.data['sections'].insert(2,{'.name':'gl_process_vpn','.type':'rule_process','enabled':'1','from_type':'process_gid',
                                       'from':['8000'],'via':'wgclient1','mark':'0x1000'})
        self.data['firewall_defaults']=[{'.type':'defaults'}]
        self.compiled=copy.deepcopy(self.data['sections']);self.commands=[];self.require_prebound=False;self.in_child=False;self.spawned=0
        self.real_popen=subprocess.Popen
        self.enter(patch.object(n,'command',side_effect=self.command))
        self.enter(patch.object(n,'slot_contract_verified',return_value=True))
        self.enter(patch.object(n.Linux,'diagnostic',self.diagnostic_method()))
        self.enter(patch.object(n.Linux,'guard',return_value=None));self.enter(patch.object(n.Linux,'unguard',return_value=None))
        self.enter(patch.object(n.Linux,'devices',return_value=['wgclient1','tun0']))
        self.enter(patch.object(n.Linux,'health',return_value=True));self.enter(patch.object(n.Linux,'recovery_ready',return_value=True))
        self.enter(patch('device_profile.detect',return_value='mt3000'));self.enter(patch('rtp_boot.prepare',return_value={'prepared':True}))
        self.enter(patch('rtp_boot.assess',return_value={'safe':True,'ready':True,'kernel_verified':False}))
        self.enter(patch('rtp_boot.ready',return_value=True));self.enter(patch('native_platform.wait_quiet'))
        self.enter(patch.object(n,'trace',return_value='9.9.9.9'));self.enter(patch.object(n,'probe',return_value={'code':None,'dns_ok':True,'https_success':2}))
        self.enter(patch.object(n,'forward_dispatch',side_effect=self.dispatch));self.enter(patch.object(n.subprocess,'Popen',side_effect=self.process))
        self.enter(patch.object(pair,'configure_lease',return_value=NOW+180));self.publish=self.enter(patch.object(n,'publish'))
        self.selection=n.choose(self.parse_policy(),self.profiles);self.bindings=self.selection['process_bindings']
        self.network=network_fixture(self.selection);self.enter(patch.object(pair,'network',side_effect=lambda:copy.deepcopy(self.network)))
        identity=pair_policy.proof(self.selection);session=pair_policy.desired_order(identity,self.selection['order'],'target')
        self.state={'id':'a'*32,'phase':'RUNNING','revision':self.revision,'owned':[],
                    'before_flags':{'wgclient1':'0','ovpnclient2':'0'},'interfaces':{'wgclient1':'wgclient','ovpnclient2':'ovpnclient'},
                    'network_identity':pair.normalized_network(self.network,{'wgclient1':'wgclient','ovpnclient2':'ovpnclient'}),
                    'protected':{},'process_bindings':self.bindings,'order':session,'policy_hash':self.selection['hash'],'policy_roles':identity}
        pair.save(self.state);agent.atomic_json(pair.paths()[0],{'mode':'on','id':self.state['id'],'revision':self.revision,'time':NOW})
        previous=dict(self.selection,order=session)
        self.journal={'tx':'b'*32,'phase':'COMMITTED','before':session,'after':self.selection['order'],'hash':self.selection['hash'],
                      'source':self.selection['source']['id'],'target':self.selection['target']['id'],'started':NOW-120,'deadline':NOW+60,
                      'confirmed':NOW-120,'trial_nonce':self.state['id'],'control_revision':self.revision,'process_bindings':self.bindings,
                      'proof_scope':pair.MODE,'vendor_identity':self.selection['vendor_identity'],
                      'pair_transition':pair_policy.transition(previous,session,'source')}
        n.journal_write(self.journal)
        agent.atomic_json(n.STATE,{'state':'COMMITTED','time':NOW,'mode':'continuous-pair','proof_scope':pair.MODE,
                                   'source':self.journal['source'],'target':self.journal['target'],'readiness_verified':True})
        self.fresh_status()

    def lua(self,script=None):
        args=[LUA,'-e',PRELUDE]
        if script is None:args.append(str(ROOT/'native_policy.lua'))
        else:args=[LUA,'-e',PRELUDE+script+"\nprint(json.encode(FIXTURE))"]
        result=subprocess.run(args,input=json.dumps(self.data).encode(),capture_output=True,timeout=5,check=True)
        return json.loads(result.stdout)

    def parse_policy(self):return self.lua()

    def diagnostic_method(self):
        owner=self
        def diagnostic(backend):
            if owner.require_prebound and not owner.in_child:owner.assertEqual(backend.process_bindings,owner.bindings,'API must bind before diagnostic/order')
            chosen=n.choose(backend.policy(),owner.profiles)
            chosen['settings_hash']=fingerprint(backend.policy()['settings'])
            backend.use_process_bindings(chosen.get('process_bindings'))
            return [],chosen
        return diagnostic

    def fresh_status(self,stamp=NOW):
        rows=[dict(profile,time=stamp,code=None,dns_ok=True,https_success=2)for profile in self.profiles]
        agent.atomic_json(self.runtime/'status.json',{'time':stamp,'profiles':rows})

    def kernel_text(self):
        first=[r for r in self.compiled if r.get('.type')=='rule'and r.get('enabled')=='1']
        lines=self.mangle.splitlines();start=next(i for i,line in enumerate(lines)if line.startswith('-A ROUTE_POLICY -m addrtype'))
        lines[start:start+2]=['-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL'+r['tunnel_id']+'_ROUTE_POLICY'for r in first]
        return '\n'.join(lines)+'\n'

    def command(self,args,timeout=5):
        if args[0]=='/usr/bin/lua':return json.dumps(self.parse_policy()).encode()
        if args[0]=='iptables-save':return self.kernel_text().encode()
        if args[:5]==['ip','-4','-j','rule','show']:return json.dumps(self.ip_rules).encode()
        return self.write(args)

    def dispatch(self,args,revision,timeout=5):n.require_control_revision(revision);return self.write(args)

    def write(self,args):
        self.commands.append(list(args))
        if args[:2]==['uci','reorder']:
            name,index=args[2].split('=',1);name=name.split('.',1)[1]
            self.data=self.lua("local c=require('uci').cursor();assert(c:reorder('route_policy',"+json.dumps(name)+','+index+'))')
        elif args[:3]==['uci','commit','route_policy']:pass
        elif args[:2]==['lua','-e']:self.data=self.lua(args[2])
        elif args[:2]==['/usr/bin/rtp2.sh','not_reload_network']:self.compiled=copy.deepcopy(self.data['sections'])
        else:raise AssertionError('Unexpected simulated platform write: '+repr(args))
        return b''

    def process(self,args,**kwargs):
        if len(args)>=4 and args[0]==sys.executable and args[-2]=='apply':
            self.spawned+=1;process=Mock(pid=os.getpid(),returncode=0);executed=[False]
            def wait(**_):
                if executed[0]:return process.returncode
                executed[0]=True;self.in_child=True
                try:n.child(args[-1])
                except n.Refused as error:
                    process.returncode=1;agent.atomic_json(self.runtime/'native-apply-result.json',{'tx':args[-1],'code':str(error)})
                finally:self.in_child=False
                return process.returncode
            process.wait.side_effect=wait;return process
        return self.real_popen(args,**kwargs)

    def test_real_unbound_order_reproduces_the_bug_but_controls_use_bound_context(self):
        raw=n.Linux().order();bound=n.Linux();n.bind_policy_context(bound,self.state)
        self.assertNotEqual(raw[0],bound.order()[0],'options_in_used=0 changes anonymous IDs without the pair context')
        self.assertNotEqual(raw[1],bound.order()[1],'derived process via/mark also changes the unbound hash')
        self.assertTrue(pair_policy.state_order_matches(self.state,self.journal,bound.order()))
        before=copy.deepcopy(self.data);self.require_prebound=True;control=manual.controls()
        self.assertTrue(control['primary']['allowed'],control);self.assertTrue(control['reserve']['allowed'],control)
        self.assertEqual(self.data,before);self.assertEqual(self.commands,[]);self.assertEqual(pair.read_state()['policy_roles'],self.state['policy_roles'])

    def test_selected_primary_noop_request_and_consume_keep_full_budget_without_dispatch(self):
        ledger={'events':[NOW-30,NOW-20,NOW-10]};agent.atomic_json(self.persist/'pair-auto-budget.json',ledger)
        self.require_prebound=True;control=manual.controls();self.assertTrue(control['primary']['allowed']);self.assertFalse(control['reserve']['allowed'])
        self.assertTrue(manual.request('primary',self.revision)['accepted']);before=copy.deepcopy(self.data)
        manual.consume(n.Linux(),pair.read_state(),self.data['settings'],self.revision)
        self.assertEqual(manual.public()['state'],'COMPLETED');self.assertEqual(manual.public()['code'],'MANUAL-ALREADY-SELECTED')
        self.assertEqual(self.spawned,0);self.assertEqual(self.commands,[]);self.assertEqual(self.data,before)
        self.assertEqual(agent.read_json(self.persist/'pair-auto-budget.json'),ledger)
        self.assertTrue(manual.held_reserve(n.Linux(),pair.read_state(),n.journal_read(),self.data['settings'],agent.read_json(self.runtime/'status.json')))

    def test_public_request_dispatch_uses_actual_linux_reorder_lua_cas_and_kernel_roles(self):
        self.require_prebound=True;before_roles=copy.deepcopy(self.state['policy_roles'])
        self.assertTrue(manual.request('reserve',self.revision)['accepted'])
        manual.consume(n.Linux(),pair.read_state(),self.data['settings'],self.revision)
        self.assertEqual(manual.public()['state'],'COMPLETED',manual.public());self.assertEqual(self.spawned,1)
        bound=n.Linux();n.bind_policy_context(bound,pair.read_state());proof=bound.attest_policy()
        self.assertTrue(proof['verified']);self.assertEqual(proof['role'],'target');self.assertEqual(n.journal_read()['after'],bound.order()[0])
        self.assertEqual(pair.read_state()['policy_roles'],before_roles)
        self.assertEqual(sum(args[0]=='/usr/bin/rtp2.sh'for args in self.commands),1)
        self.assertEqual(agent.read_json(self.persist/'pair-auto-budget.json')['events'],[NOW])
        with patch('pair_manual.time.time',return_value=NOW+61):
            self.fresh_status(NOW+61)
            native=agent.read_json(n.STATE);native['time']=NOW+61;agent.atomic_json(n.STATE,native)
            self.assertTrue(manual.request('primary',self.revision)['accepted'])
            manual.consume(n.Linux(),pair.read_state(),self.data['settings'],self.revision)
        self.assertEqual(manual.public()['state'],'COMPLETED');self.assertEqual(self.spawned,2)
        bound=n.Linux();n.bind_policy_context(bound,pair.read_state())
        self.assertEqual(bound.attest_policy()['role'],'source');self.assertEqual(bound.order()[0],self.journal['after'])
        self.assertEqual(pair.read_state()['policy_roles'],before_roles)
        self.assertEqual(agent.read_json(self.persist/'pair-auto-budget.json')['events'],[NOW,NOW+61])

    def test_foreign_hash_is_still_refused_before_public_request_or_any_dispatch(self):
        before=n.JOURNAL.read_bytes();self.data['sections'][-1]['foreign_option']='1'
        bound=n.Linux();n.bind_policy_context(bound,self.state)
        self.assertNotEqual(bound.order()[1],self.state['policy_hash']);control=manual.controls()
        self.assertFalse(control['reserve']['allowed']);self.assertIn('TRANSACTION-IN-PROGRESS',control['reserve']['blockers'])
        self.assertFalse(manual.request('reserve',self.revision)['accepted']);self.assertEqual(self.commands,[])
        self.assertEqual(n.JOURNAL.read_bytes(),before);self.assertEqual(self.spawned,0)

    def test_foreign_kernel_blocks_both_public_choices_before_queueing(self):
        self.mangle=self.mangle.replace('--set-xmark 0x1000/0xf000','--set-xmark 0xb000/0xf000')
        backend=n.Linux();n.bind_policy_context(backend,self.state)
        proof=backend.attest_policy()
        self.assertFalse(proof['verified']);self.assertFalse(proof['repairable_missing'])
        journal=n.JOURNAL.read_bytes();control=manual.controls()
        for direction in ('primary','reserve'):
            with self.subTest(direction=direction):
                self.assertFalse(control[direction]['allowed'])
                self.assertIn('KERNEL-POLICY-UNVERIFIED',control[direction]['blockers'])
                self.assertFalse(manual.request(direction,self.revision)['accepted'])
        self.assertFalse(manual.path().exists());self.assertEqual(self.commands,[])
        self.assertEqual(n.JOURNAL.read_bytes(),journal);self.assertEqual(self.spawned,0)

    def test_unverified_kernel_does_not_prevent_releasing_manual_hold(self):
        state=pair.read_state();state['manual_hold']='source';pair.save(state)
        self.mangle=self.mangle.replace('--set-xmark 0x1000/0xf000','--set-xmark 0xb000/0xf000')
        self.assertTrue(manual.controls()['resume']['allowed'])
        self.assertTrue(manual.request('resume',self.revision)['accepted'])
        manual.consume(n.Linux(),pair.read_state(),self.data['settings'],self.revision)
        self.assertEqual(manual.public()['state'],'COMPLETED');self.assertNotIn('manual_hold',pair.read_state())
        self.assertEqual(self.commands,[]);self.assertEqual(self.spawned,0)

    def test_foreign_change_after_request_cannot_borrow_the_bound_context(self):
        self.assertTrue(manual.request('reserve',self.revision)['accepted']);self.data['sections'][-1]['foreign_option']='1'
        manual.consume(n.Linux(),pair.read_state(),self.data['settings'],self.revision)
        self.assertEqual(manual.public()['state'],'REFUSED');self.assertEqual(manual.public()['code'],'MANUAL-CONFIG-CHANGED')
        self.assertEqual(self.commands,[]);self.assertEqual(self.spawned,0)

    def legacy_pending(self):
        self.assertTrue(manual.request('reserve',self.revision)['accepted'])
        manual.consume(n.Linux(),pair.read_state(),self.data['settings'],self.revision)
        self.assertEqual(manual.public()['state'],'COMPLETED',manual.public())
        journal=n.journal_read()
        record={'schema':1,'state':'APPLYING','direction':'reserve','request_id':journal['manual_request_id'],
                'control_revision':self.revision,'requested_at':journal['started'],'updated_at':NOW,
                'trial':journal['trial_nonce'],'until':NOW+180,'source_id':journal['source'],'target_id':journal['target'],
                'transaction_id':journal['tx'],'selection_hash':journal['hash'],'vendor_identity':journal['vendor_identity'],
                'settings_hash':fingerprint(self.data['settings']),'code':None}
        self.assertTrue(manual_control.valid_record(record));agent.atomic_json(self.runtime/'manual-control.json',record)
        return journal

    def test_standalone_legacy_recovery_binds_confirmed_journal_before_actual_linux_order(self):
        journal=self.legacy_pending();before=copy.deepcopy(self.data);raw=n.JOURNAL.read_bytes();writes=len(self.commands)
        backend=n.Linux();self.assertNotEqual(backend.order(),(journal['after'],journal['hash']))
        manual_dispatch.recover_pending(backend,runtime=self.runtime,persist=self.persist)
        self.assertEqual(backend.process_bindings,journal['process_bindings'])
        self.assertEqual(agent.read_json(self.runtime/'manual-control.json')['state'],'COMPLETED')
        self.assertEqual(self.data,before);self.assertEqual(n.JOURNAL.read_bytes(),raw);self.assertEqual(len(self.commands),writes)

    def test_standalone_legacy_recovery_does_not_accept_foreign_policy_after_binding(self):
        self.legacy_pending();self.data['sections'][-1]['foreign_option']='1';writes=len(self.commands)
        manual_dispatch.recover_pending(n.Linux(),runtime=self.runtime,persist=self.persist)
        result=agent.read_json(self.runtime/'manual-control.json')
        self.assertEqual(result['state'],'UNCONFIRMED');self.assertEqual(result['code'],'MANUAL-SUPERVISOR-RECOVERED')
        self.assertEqual(len(self.commands),writes)


if __name__=='__main__':unittest.main()
