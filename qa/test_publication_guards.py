import hashlib,importlib.util,os,tempfile
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
    def test_push_sends_the_verified_commit_not_a_movable_branch(self):
        # F-02: the old code pushed refs/heads/feature/github-publication-*; moving that branch changed what was published.
        public='a1'*20
        argv=m.push_arguments(public)
        self.assertEqual(argv[-1],public+':refs/heads/main')
        self.assertFalse(any('github-publication' in item for item in argv))
        for bad in ['feature/github-publication-'+public[:12],public[:12],'HEAD',None]:
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,'PUBLICATION-LEDGER-SHA'):m.push_arguments(bad)
        source=Path(m.__file__).read_text(encoding='utf-8')
        self.assertNotIn("'refs/heads/feature/github-publication-'+public[:12]+':refs/heads/main'",source)
        self.assertIn('def push(self):run(*push_arguments(public))',source)
    def test_resume_validates_full_shas_parent_and_tree(self):
        public,parent,tree='a'*40,'b'*40,'c'*40
        def fake(answers):
            return lambda *args:answers[args[-1]]
        good={public+'^{commit}':public,public:public+' '+parent,public+'^{tree}':tree}
        self.assertEqual(m.checked_public_commit(public,parent,tree,fake(good)),public)
        for key,value in [(public+'^{commit}','d'*40),(public,public+' '+'d'*40),(public,public+' '+parent+' '+'d'*40),(public+'^{tree}','d'*40)]:
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'PUBLICATION-RESUME-TREE'):
                m.checked_public_commit(public,parent,tree,fake(dict(good,**{key:value})))
        for bad in [('feature/x',parent),(public[:12],parent),(public,'main')]:
            with self.subTest(bad=bad),self.assertRaisesRegex(ValueError,'PUBLICATION-LEDGER-SHA'):
                m.checked_public_commit(bad[0],bad[1],tree,fake(good))
    def test_artifact_and_notes_are_snapshotted_after_validation(self):
        # F-03: replacing the original file after its hash was checked must not change the uploaded bytes.
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'pkg_1_all.ipk';source.write_bytes(b'reviewed bytes')
            wanted=hashlib.sha256(b'reviewed bytes').hexdigest()
            copy,digest=m.snapshot_file(source,root/'snap',wanted)
            self.assertEqual(digest,wanted);self.assertEqual(copy.name,source.name);self.assertNotEqual(copy,source)
            source.write_bytes(b'swapped after the check')
            self.assertEqual(copy.read_bytes(),b'reviewed bytes')
            with self.assertRaisesRegex(ValueError,'RELEASE-ARTIFACT-HASH'):m.snapshot_file(source,root/'snap2',wanted)
            with self.assertRaises(FileExistsError):m.snapshot_file(root/'snap'/source.name,root/'snap',None)
            os.chmod(copy,0o600)
        text=Path(m.__file__).read_text(encoding='utf-8')
        body=text[text.index('def publish(a,signing_directory):'):]
        self.assertLess(body.index("a.artifact,_=snapshot_file("),body.index('scan_publication(a.source'))
        self.assertLess(body.index("a.notes,_=snapshot_file("),body.index('scan_publication(a.source'))
