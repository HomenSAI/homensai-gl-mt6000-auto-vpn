import io,tarfile,zipfile,unittest,tempfile
from pathlib import Path
from privacy_audit import inspect,audit_paths
class PrivacyTests(unittest.TestCase):
    def test_manifest_rejects_escape_git_and_duplicate_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'ok.txt').write_text('safe')
            self.assertEqual(audit_paths(root,['ok.txt']),[])
            for names in (['../private'],['/etc/passwd'],['C:/private'],['.git/config'],['.GIT/config'],['ok.txt','ok.txt'],['bad\\path'],['./ok.txt'],['ok.txt\n'],[None]):
                with self.subTest(names=names),self.assertRaises(ValueError):audit_paths(root,names)

    def test_manifest_rejects_symlink_before_reading_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'safe';target.write_text('safe')
            try:(root/'link').symlink_to(target)
            except OSError:self.skipTest('symlink unavailable')
            with self.assertRaises(ValueError):audit_paths(root,['link'])

    def test_nested_ipk_secret_is_found_without_printing_content(self):
        token=('123456789:'+('a'*40)).encode();inner=io.BytesIO()
        with tarfile.open(fileobj=inner,mode='w:gz') as archive:
            info=tarfile.TarInfo('etc/config/service');info.size=len(token);archive.addfile(info,io.BytesIO(token))
        outer=io.BytesIO();data=inner.getvalue()
        with tarfile.open(fileobj=outer,mode='w:gz') as archive:
            info=tarfile.TarInfo('data.tar.gz');info.size=len(data);archive.addfile(info,io.BytesIO(data))
        failures=[];inspect('candidate.ipk',outer.getvalue(),failures)
        self.assertEqual(len(failures),1);self.assertNotIn(token.decode(),str(failures))
    def test_safe_binary_zip_is_not_a_secret(self):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:archive.writestr('font.bin',bytes([0,1,2,255]))
        failures=[];inspect('assets.zip',stream.getvalue(),failures);self.assertEqual(failures,[])
    def test_traversal_and_invalid_archive_are_rejected(self):
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w') as archive:archive.writestr('../private','data')
        for name,data in [('assets.zip',stream.getvalue()),('broken.ipk',b'invalid')]:
            failures=[];inspect(name,data,failures);self.assertTrue(failures)
    def test_size_depth_and_member_limits(self):
        failures=[];inspect('file',b'abc',failures,budget=[2,1]);self.assertTrue(failures)
        failures=[];inspect('file',b'abc',failures,depth=5);self.assertTrue(failures)
if __name__=='__main__':unittest.main()
