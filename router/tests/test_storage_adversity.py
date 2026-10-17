import errno,json,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent

class StorageAdversityTests(unittest.TestCase):
    def test_semantically_corrupt_checkpoints_recover_backup(self):
        values=[[],{'months':[]},{'gaps':-1},{'quality':{'a':{'buckets':{'not-an-hour':{}}}}}]
        for value in values:
            with self.subTest(shape=type(value).__name__),tempfile.TemporaryDirectory() as d,patch.object(agent,'PERSIST',Path(d)):
                good={'version':1,'saved':time.time(),'accounting':agent.Accounting().export()}
                agent.atomic_json(Path(d)/'checkpoint.backup.json',{'data':good,'sha256':agent.checksum(good)})
                bad={'version':1,'saved':time.time(),'accounting':value}
                (Path(d)/'checkpoint.json').write_text(json.dumps({'data':bad,'sha256':agent.checksum(bad)}))
                restored,error=agent.restore();self.assertEqual(error,'STORAGE-RECOVERED');self.assertEqual(restored.months,{})
    def test_top_level_array_and_invalid_saved_time_are_not_uncaught(self):
        for value in [[],{'data':{'version':1,'saved':1e300,'accounting':{}},'sha256':None}]:
            with self.subTest(),tempfile.TemporaryDirectory() as d,patch.object(agent,'PERSIST',Path(d)):
                if isinstance(value,dict):value['sha256']=agent.checksum(value['data'])
                (Path(d)/'checkpoint.json').write_text(json.dumps(value))
                restored,error=agent.restore();self.assertEqual(error,'STORAGE-001')
    def test_enospc_before_replace_keeps_known_checkpoint(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'own.json';agent.atomic_json(path,{'known':1})
            with patch.object(agent.os,'fsync',side_effect=OSError(errno.ENOSPC,'synthetic full scratch filesystem')):
                with self.assertRaises(OSError):agent.atomic_json(path,{'new':2})
            self.assertEqual(json.loads(path.read_text()),{'known':1});agent.atomic_json(path,{'new':2});self.assertEqual(json.loads(path.read_text()),{'new':2})
    def test_atomic_replace_failure_keeps_known_data(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'own.json';agent.atomic_json(path,{'known':1})
            with patch.object(agent.os,'replace',side_effect=OSError(errno.ENOSPC,'synthetic full scratch filesystem')):
                with self.assertRaises(OSError):agent.atomic_json(path,{'new':2})
            self.assertEqual(json.loads(path.read_text()),{'known':1})

    def test_corrupt_current_can_be_replaced_without_overwriting_good_backup(self):
        with tempfile.TemporaryDirectory() as d,patch.object(agent,'PERSIST',Path(d)):
            acc=agent.Accounting();agent.checkpoint(acc);acc.gaps=4;agent.checkpoint(acc)
            backup=(Path(d)/'checkpoint.backup.json').read_bytes()
            (Path(d)/'checkpoint.json').write_text('truncated JSON')
            agent.checkpoint(acc)
            self.assertEqual((Path(d)/'checkpoint.backup.json').read_bytes(),backup)
            restored,error=agent.restore();self.assertIsNone(error);self.assertEqual(restored.gaps,5)
