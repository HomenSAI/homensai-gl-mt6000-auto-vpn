"""Real native API/Lua state/transaction code + actual disposable QEMU kernel.

UCI inventory, vendor RTP compilation, tunnel health and worker launch are test
adapters. iptables/IP rules/readback and the production kernel attestor are real.
"""
import json,shlex,time
from unittest.mock import patch
from test_pair_manual_bound_context import BoundManualContext,NOW
import native_switch as native,pair_auto
from qemu_serial import execute
ORIGINAL_RECOVERY_READY=native.Linux.recovery_ready

class QemuFixture(BoundManualContext):
    def setUp(self):
        self.kernel_applications=[]
        super().setUp()
        for name,filename in (('CERT','native-certificate.json'),('ATTEMPTS','native-attempts.json'),('PREPARE','acceleration-prepare.json')):
            self.enter(patch.object(native,name,self.persist/filename))
        self.backend=native.Linux();native.bind_policy_context(self.backend,pair_auto.read_state())
        execute('while ip rule del priority 6000 2>/dev/null; do :; done; ip rule add priority 6000 fwmark 0x1000/0xf000 table 1001; ip rule add priority 6000 fwmark 0xb000/0xf000 table 1012')
        self.health_values={profile['id']:True for profile in self.profiles}
        self.enter(patch.object(pair_auto,'configs',return_value={}))
        self.enter(patch.object(pair_auto,'client_down',return_value=False))
        self.enter(patch.object(pair_auto,'configure_lease',side_effect=self.renew_lease))
        self.enter(patch.object(native.Linux,'health',side_effect=lambda identifier:self.health_values[identifier]))
        self.enter(patch.object(native.Linux,'recovery_ready',ORIGINAL_RECOVERY_READY))
        self.enter(patch.object(native,'probe',side_effect=self.probe))
        import speed_pause
        self.enter(patch.object(speed_pause,'RUNTIME',self.runtime))
        self.install_kernel()

    def renew_lease(self,state):
        pair_auto.require_running(state['revision'])
        until=time.time()+180
        self.data['settings']['native_until']=str(until)
        return until

    def probe(self,profile):
        good=self.health_values[profile['id']]
        return {'code':None if good else 'VPN-003','dns_ok':True,'https_success':2 if good else 0}

    @property
    def settings(self):
        return self.data['settings']

    def install_kernel(self):
        expected=super().kernel_text()
        execute("printf '%s' "+shlex.quote(expected)+" >/tmp/qa-pair-kernel; iptables-restore </tmp/qa-pair-kernel")
        self.kernel_applications.append({'journal':native.journal_read(),'iptables_save':execute('iptables-save -t mangle'),'ip_rules':json.loads(execute('ip -4 -j rule show'))})

    def command(self,args,timeout=5):
        if args[0]=='iptables-save':return execute('iptables-save -t mangle').encode()
        if args[:5]==['ip','-4','-j','rule','show']:return execute('ip -4 -j rule show').encode()
        return super().command(args,timeout)

    def write(self,args):
        answer=super().write(args)
        if args[:2]==['/usr/bin/rtp2.sh','not_reload_network']:self.install_kernel()
        return answer

    def kernel_proof(self):
        native.bind_policy_context(self.backend,pair_auto.read_state())
        return self.backend.attest_policy()

    @property
    def current(self):
        native.bind_policy_context(self.backend,pair_auto.read_state())
        return self.backend.order()[0]
