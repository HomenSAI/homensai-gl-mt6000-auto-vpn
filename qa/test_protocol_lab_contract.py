"""Offline protocol-lab parser, scope and private-file contracts."""
import importlib.util
from pathlib import Path
import socket,struct,tempfile,unittest,json,subprocess
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('protocol_lab',Path(__file__).resolve().parents[1]/'lab/protocol_namespace_lab.py')
lab=importlib.util.module_from_spec(spec);spec.loader.exec_module(lab)

class ProtocolLabTests(unittest.TestCase):
    def query(self):return struct.pack('!HHHHHH',1234,0x100,1,0,0,0)+b'\x03vpn\x03lab\x04test\x00\x00\x01\x00\x01'
    def test_dns_identity_question_and_answer_preserved(self):
        query=self.query();reply=lab.dns_reply(query)
        self.assertEqual(reply[:2],query[:2]);self.assertEqual(reply[12:12+len(query)-12],query[12:])
        self.assertEqual(reply[-4:],socket.inet_aton(lab.VIP));self.assertEqual(reply[6:8],b'\x00\x01')
    def test_truncation_compressed_or_wrong_type_refused(self):
        good=self.query()
        for size in range(len(good)):
            with self.subTest(size=size),self.assertRaises(ValueError):lab.dns_reply(good[:size])
        for query in (good[:12]+b'\xc0\x0c'+good[-4:],good[:-4]+b'\x00\x1c\x00\x01',good+b'extra'):
            with self.assertRaises(ValueError):lab.dns_reply(query)
    def test_non_lab_target_refused_before_commands(self):
        with patch.object(lab.Path,'read_text',return_value="DISTRIB_TARGET='mediatek/mt7986'\nDISTRIB_RELEASE='21.02.7'"),patch.object(lab.subprocess,'run') as run:
            with self.assertRaisesRegex(RuntimeError,'ISOLATED-X86'):lab.require_guest()
            run.assert_not_called()
    def test_periodic_faults_repeat_without_unbounded_time(self):
        with tempfile.TemporaryDirectory() as directory:
            clock=[0.0]
            with patch.object(lab.time,'monotonic',side_effect=lambda:clock[0]),patch.object(lab.time,'sleep',side_effect=lambda seconds:clock.__setitem__(0,clock[0]+seconds)):
                value=lab.Lab(Path(directory),130);faults=[];value.faults=lambda:faults.append(value.cycles)
                value.route=lambda p:setattr(value,'selected',p)
                value.measure=lambda p=None:{'profile':p or value.selected}
                value.check=lambda name,condition:self.assertTrue(condition)
                value.status=lambda *args:None
                value.soak();self.assertEqual(faults,[25]);self.assertEqual(value.cycles,26)
    def test_timeout_does_not_invent_bootstrap_cause(self):
        with tempfile.TemporaryDirectory() as directory:
            value=lab.Lab(Path(directory),0)
            with patch.object(lab.subprocess,'run',side_effect=subprocess.TimeoutExpired(['nft'],15)):
                with self.assertRaisesRegex(RuntimeError,'DEADLINE:UNCLASSIFIED'):
                    value.ns(value.client,['nft','-j','list','ruleset'])
            row=json.loads((Path(directory)/'last-timeout.json').read_text())
            self.assertEqual(row['command_prefix'][-1],'nft');self.assertEqual(row['timeout_seconds'],15)
    def test_timeout_preserves_observed_probe_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            value=lab.Lab(Path(directory),0)
            with patch.object(lab.subprocess,'run',side_effect=subprocess.TimeoutExpired(['python'],34,stderr=b'LABPROBE:START\nLABPROBE:TLS\n')):
                with self.assertRaisesRegex(RuntimeError,'DEADLINE:TLS'):value.cmd(['python','-c','private-value'],timeout=34)
            row=json.loads((Path(directory)/'last-timeout.json').read_text());self.assertEqual(row['command_prefix'],['python'])
    def test_failed_probe_detail_is_retained_without_credentials(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            value=lab.Lab(Path(directory),0);value.selected='ova'
            sample={'dns':True,'https':False,'profile':None,'error':'HTTPS-TimeoutError','phase':'TLS','elapsed_ms':3001}
            value.ns=lambda *args,**kw:SimpleNamespace(stdout=json.dumps(sample).encode())
            self.assertFalse(value.measure('ova')['https'])
            with self.assertRaises(AssertionError):value.check('synthetic-failed-transport',False)
            row=value.rows[-1]['detail'];self.assertEqual(row['expected_profile'],'ova');self.assertEqual(row['sample']['phase'],'TLS')
            self.assertEqual(row['socket_timeout_seconds'],lab.NETWORK_TIMEOUT)
            self.assertEqual(len((Path(directory)/'probe-observations.jsonl').read_text().splitlines()),1)
    def test_nft_owned_file_checked_applied_and_removed_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            value=lab.Lab(Path(directory),0);seen=[]
            def ns(name,args,**kw):
                path=Path(args[-1]);self.assertEqual(path.parent,Path(directory));self.assertTrue(path.is_file());seen.append(args)
            value.ns=ns;value.nft('table inet synthetic {}\n')
            self.assertEqual(len(seen),2);self.assertEqual(seen[0][1],'-c');self.assertEqual(list(Path(directory).glob('*.nft')),[])
            def failed(*args,**kw):raise RuntimeError('SYNTHETIC-NFT-REFUSAL')
            value.ns=failed
            with self.assertRaises(RuntimeError):value.nft('table inet synthetic {}\n')
            self.assertEqual(list(Path(directory).glob('*.nft')),[])
if __name__=='__main__':unittest.main()
