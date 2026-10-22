import json
from pathlib import Path
import sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent,auto_live

class Tests(unittest.TestCase):
    def test_live_view_whitelists_metadata_and_never_probes_or_executes(self):
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory)
            (root/'status.json').write_text(json.dumps({'time':100,'profiles':[{'token':'PRIVATE'}]}))
            (root/'native-status.json').write_text(json.dumps({'time':100,'state':'COMMITTED','proof_scope':'router-probed-ipv4','tx':'PRIVATE','expected_exit':'PRIVATE','trial_nonce':'PRIVATE','source':'wireguard:peer_1','external_lan_verified':False}))
            with patch.object(agent,'RUNTIME',root),patch.object(auto_live.time,'time',return_value=101),patch.object(agent,'command')as command,patch.object(agent,'probe')as probe:
                result=auto_live.snapshot()
            self.assertEqual(result['native_failover']['state'],'COMMITTED')
            self.assertNotIn('PRIVATE',json.dumps(result));command.assert_not_called();probe.assert_not_called()

    def test_corrupt_and_future_evidence_never_looks_fresh(self):
        with patch.object(agent,'read_json',return_value=[]):
            self.assertIn('rpc_error',auto_live.snapshot())
        with tempfile.TemporaryDirectory()as directory:
            root=Path(directory)
            for name in('status.json','native-status.json'):(root/name).write_text(json.dumps({'time':1e30,'state':'COMMITTED'}))
            with patch.object(agent,'RUNTIME',root):
                result=auto_live.snapshot();self.assertIsNone(result['time']);self.assertNotIn('time',result['native_failover'])

if __name__=='__main__':unittest.main()
