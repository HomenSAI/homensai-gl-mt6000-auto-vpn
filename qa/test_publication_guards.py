import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/'scripts/publish-reviewed.py'
spec=importlib.util.spec_from_file_location('publish_reviewed',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PublicationGuards(unittest.TestCase):
    def matrix(self):return [dict(result='PASS',source='a'*40,sha256='b'*64,runtime_only=x) for x in (True,False)]
    def test_exact_matrix(self):self.assertEqual(m.checked_receipt(self.matrix(),'a'*40),'b'*64)
    def test_refuses_partial_failure_mixed_hash_wrong_source(self):
        for key,value in [('result','FAIL'),('source','c'*40),('sha256','c'*64),('runtime_only',True)]:
            rows=self.matrix();rows[1][key]=value
            with self.assertRaises(ValueError):m.checked_receipt(rows,'a'*40)
        with self.assertRaises(ValueError):m.checked_receipt(self.matrix()[:1],'a'*40)
