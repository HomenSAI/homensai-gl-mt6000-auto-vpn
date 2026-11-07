import bz2,gzip,io,lzma,tarfile,zipfile,unittest,tempfile
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
# Synthetic values assembled at run time, so this file itself never matches the patterns it tests.
TOKEN=('123456789:'+('a'*40)).encode()
KEY_NAME='telegram_'+'chat'
GROUP='-100'+'1234567890'
HANDLE='@'+'example_channel'
def tar_bytes(name,payload,mode='w'):
    stream=io.BytesIO()
    with tarfile.open(fileobj=stream,mode=mode) as archive:
        info=tarfile.TarInfo(name);info.size=len(payload);archive.addfile(info,io.BytesIO(payload))
    return stream.getvalue()
class FormatAndPatternBypasses(unittest.TestCase):
    """Audit 06.11.2026 (F-09): containers by signature, decoded text, wider patterns."""
    def found(self,name,data):
        failures=[];inspect(name,data,failures);return failures
    def test_compressed_tar_with_an_innocent_name_is_opened(self):
        for mode in ('w:gz','w:bz2','w:xz'):
            with self.subTest(mode=mode):self.assertTrue(self.found('evidence.dat',tar_bytes('etc/config/service',TOKEN,mode)))
    def test_nested_compression_is_opened(self):
        data=gzip.compress(gzip.compress(TOKEN))
        self.assertTrue(self.found('blob.bin',data))
        self.assertTrue(self.found('blob.bin',bz2.compress(lzma.compress(TOKEN))))
        self.assertTrue(self.found('broken.dat',b'\x1f\x8b\x08\x00broken'))
    def test_utf16_text_is_decoded(self):
        for data in ((b'\xff\xfe'+('x '+TOKEN.decode()).encode('utf-16-le')),('x '+TOKEN.decode()).encode('utf-16-le'),
                     (b'\xfe\xff'+('x '+TOKEN.decode()).encode('utf-16-be'))):
            with self.subTest(data=data[:4]):self.assertTrue(self.found('notes.txt',data))
    def test_telegram_recipient_forms(self):
        for text in ('{"%s": "%s"}'%(KEY_NAME,GROUP),'{"%s":"%s"}'%(KEY_NAME,HANDLE),"option %s '%s'"%(KEY_NAME,GROUP),
                     "option %s '%s'"%(KEY_NAME,HANDLE),'%s=%s'%(KEY_NAME,GROUP),'{"%s": %s}'%(KEY_NAME,GROUP)):
            with self.subTest(text=text[:20]):self.assertTrue(self.found('config.json',text.encode()))
        for text in (KEY_NAME+' is configured','"%s": ""'%KEY_NAME,'"%s": null'%KEY_NAME,'%s_configured: true'%KEY_NAME):
            with self.subTest(text=text):self.assertEqual(self.found('docs.md',text.encode()),[])
    def test_every_private_key_flavour(self):
        for kind in ('','RSA ','EC ','OPENSSH ','DSA ','ENCRYPTED ','PGP '):
            header=('-----BEGIN '+kind+'PRIVATE KEY'+(' BLOCK' if kind=='PGP ' else '')+'-----\n').encode()
            with self.subTest(kind=kind):self.assertTrue(self.found('key.txt',header))
        self.assertEqual(self.found('cert.pem',('-----BEGIN '+'CERTIFICATE-----\n').encode()),[])
if __name__=='__main__':unittest.main()
