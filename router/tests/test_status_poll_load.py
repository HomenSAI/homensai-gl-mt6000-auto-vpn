"""The status poll must stay cheap: kernel attestation is reused for 15 s, per journal/order."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent
import pair_manual


class AttestationCache(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        patcher=patch.object(agent,'RUNTIME',Path(temporary.name));patcher.start();self.addCleanup(patcher.stop)
        self.clock=[100.0]
        patcher=patch.object(pair_manual.time,'monotonic',side_effect=lambda:self.clock[0]);patcher.start();self.addCleanup(patcher.stop)
        self.backend=MagicMock();self.backend.order.return_value=(['a','b'],'h'*64)
        self.backend.attest_policy.return_value={'verified':True,'role':'source','kernel_fingerprint':'f'*64}
        self.journal={'tx':'t1','phase':'COMMITTED'}

    def test_repeated_polls_reuse_one_attestation_within_the_window(self):
        first=pair_manual.attested(self.backend,self.journal)
        self.clock[0]+=10;second=pair_manual.attested(self.backend,self.journal)
        self.assertEqual(self.backend.attest_policy.call_count,1)
        self.assertEqual((first['verified'],first['role']),(second['verified'],second['role']))

    def test_window_expiry_new_journal_phase_or_order_attest_again(self):
        pair_manual.attested(self.backend,self.journal)
        self.clock[0]+=pair_manual.ATTEST_CACHE_SECONDS;pair_manual.attested(self.backend,self.journal)
        self.assertEqual(self.backend.attest_policy.call_count,2)
        pair_manual.attested(self.backend,dict(self.journal,phase='ROLLED-BACK'))
        self.assertEqual(self.backend.attest_policy.call_count,3)
        self.backend.order.return_value=(['b','a'],'h'*64);pair_manual.attested(self.backend,dict(self.journal,phase='ROLLED-BACK'))
        self.assertEqual(self.backend.attest_policy.call_count,4)

    def test_real_process_bindings_still_hit_the_cache(self):
        # alpha77 regression: the key held tuples, the stored JSON key held lists, so every poll attested twice.
        self.backend.process_bindings={'gl_process':('wgclient1',2),'gl_process_vpn':('ovpnclient2',3)}
        pair_manual.attested(self.backend,self.journal);self.clock[0]+=5;pair_manual.attested(self.backend,self.journal)
        self.assertEqual(self.backend.attest_policy.call_count,1)

    def test_channel_path_display_shares_the_same_attestation(self):
        self.backend.process_bindings={'gl_process':('wgclient1',2)}
        self.backend.attest_policy.return_value=dict(self.backend.attest_policy.return_value,profile_id='wireguard:a',time=1.5,order=['a','b'])
        pair_manual.attested(self.backend,self.journal);self.clock[0]+=3
        shared=pair_manual.attested(self.backend,self.journal)
        self.assertEqual(self.backend.attest_policy.call_count,1)
        self.assertEqual((shared['profile_id'],shared['time'],shared['order']),('wireguard:a',1.5,['a','b']))

    def test_damaged_cache_is_ignored(self):
        (agent.RUNTIME/'pair-manual-kernel-cache.json').write_text('{not json')
        self.assertTrue(pair_manual.attested(self.backend,self.journal)['verified'])
        self.assertEqual(self.backend.attest_policy.call_count,1)


if __name__=='__main__':unittest.main()
