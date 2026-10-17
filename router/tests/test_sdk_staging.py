from pathlib import Path
import importlib.util,io,sys,tarfile,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import build_ipk,stage_files
class StagingTests(unittest.TestCase):
    def test_sdk_payload_matches_actual_ipk_names_bytes_and_modes(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory);stage_files.stage(base/'stage');package=build_ipk.build(base/'package').read_bytes()
            with tarfile.open(fileobj=io.BytesIO(package),mode='r:gz') as outer:payload=outer.extractfile('./data.tar.gz').read()
            with tarfile.open(fileobj=io.BytesIO(payload),mode='r:gz') as archive:
                files=[m for m in archive.getmembers() if m.isfile()]
                self.assertEqual(len(files),len(list((base/'stage').rglob('*')))-len([p for p in (base/'stage').rglob('*') if p.is_dir()]))
                for member in files:
                    target=base/'stage'/member.name
                    self.assertEqual(target.read_bytes(),archive.extractfile(member).read())
                    self.assertEqual(target.stat().st_mode&0o777,member.mode)
    def test_existing_staging_tree_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'important').write_text('preserve')
            with self.assertRaisesRegex(ValueError,'NONEMPTY'):stage_files.stage(root)
            self.assertEqual((root/'important').read_text(),'preserve')
if __name__=='__main__':unittest.main()
