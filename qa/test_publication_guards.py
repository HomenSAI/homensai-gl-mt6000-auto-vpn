import importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/'scripts/publish-reviewed.py'
spec=importlib.util.spec_from_file_location('publish_reviewed',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PublicationGuards(unittest.TestCase):
    def matrix(self):return [dict(result='PASS',source='a'*40,sha256='b'*64,runtime_only=x,lua_available=True,lua_tests=13) for x in (True,False)]
    def test_exact_matrix(self):self.assertEqual(m.checked_receipt(self.matrix(),'a'*40),'b'*64)
    def test_numeric_runtime_markers_do_not_bypass_lua(self):
        rows=self.matrix()
        for row in rows:row['runtime_only']=int(row['runtime_only']);row.pop('lua_tests');row.pop('lua_available')
        with self.assertRaisesRegex(ValueError,'PUBLICATION-CI-RUNTIMES'):m.checked_receipt(rows,'a'*40)
    def test_non_dictionary_receipt_rows_refused(self):
        for row in [None,False,1,'row',[]]:
            for index in (0,1):
                rows=self.matrix();rows[index]=row
                with self.subTest(row=row,index=index),self.assertRaisesRegex(ValueError,'PUBLICATION-CI-ROW'):
                    m.checked_receipt(rows,'a'*40)
    def test_requires_actual_lua_tests_on_full_runtime(self):
        for key,value in [('lua_available',False),('lua_available',None),('lua_tests',0),('lua_tests',None),('lua_tests',True),('lua_tests',-1)]:
            rows=self.matrix();rows[1][key]=value
            with self.subTest(key=key,value=value),self.assertRaisesRegex(ValueError,'PUBLICATION-CI-LUA'):
                m.checked_receipt(rows,'a'*40)
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
