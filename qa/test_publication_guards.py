import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/'scripts/publish-reviewed.py'
spec=importlib.util.spec_from_file_location('publish_reviewed',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PublicationGuards(unittest.TestCase):
    def matrix(self):return [dict(result='PASS',source='a'*40,sha256='b'*64,runtime_only=x) for x in (True,False)]
    def test_exact_matrix(self):self.assertEqual(m.checked_receipt(self.matrix(),'a'*40),'b'*64)
    def test_manifest_cannot_publish_placeholder_wrong_hash_or_tag(self):
        data={'application':{'sha256':'b'*64,'release_tag':'v0.9.0-alpha9'}}
        self.assertEqual(m.checked_manifest(data,'b'*64,'v0.9.0-alpha9'),data['application'])
        for actual,wanted,tag in [('0'*64,'b'*64,None),('b'*64,'c'*64,None),('0'*64,'0'*64,None),('b'*64,'b'*64,'v0.9.0-alpha8')]:
            with self.subTest(actual=actual,wanted=wanted,tag=tag),self.assertRaises(ValueError):
                m.checked_manifest({'application':{'sha256':actual,'release_tag':'v0.9.0-alpha9'}},wanted,tag)
    def test_refuses_partial_failure_mixed_hash_wrong_source(self):
        for key,value in [('result','FAIL'),('source','c'*40),('sha256','c'*64),('runtime_only',True)]:
            rows=self.matrix();rows[1][key]=value
            with self.assertRaises(ValueError):m.checked_receipt(rows,'a'*40)
        with self.assertRaises(ValueError):m.checked_receipt(self.matrix()[:1],'a'*40)
