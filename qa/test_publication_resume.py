import copy,importlib.util
from pathlib import Path
import unittest
p=Path(__file__).resolve().parents[1]/'scripts/publication_resume.py'
spec=importlib.util.spec_from_file_location('publication_resume',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PowerLoss(BaseException):pass
class FakeRemote:
    def __init__(self,interrupt=None):self.head='old';self.tag_value=None;self.release_value=None;self.assets={};self.counts={};self.interrupt=interrupt
    def effect(self,key,fn):
        self.counts[key]=self.counts.get(key,0)+1;fn()
        if self.interrupt==key:self.interrupt=None;raise PowerLoss()
    def main(self):return self.head
    def push(self):self.effect('push',lambda:setattr(self,'head','new'))
    def tag(self):return self.tag_value
    def create_tag(self):self.effect('tag',lambda:setattr(self,'tag_value','new'))
    def release(self):return self.release_value
    def create_release(self):self.effect('release',lambda:setattr(self,'release_value',{'draft':False,'prerelease':True}))
    def expected_assets(self):return [('package','hash'),('checksum','sum')]
    def asset_hash(self,name):return self.assets.get(name)
    def upload(self,name):self.effect(name,lambda:self.assets.__setitem__(name,dict(self.expected_assets())[name]))
class ResumeTests(unittest.TestCase):
    def ledger(self):return {'parent':'old','public':'new','planned_release':'v1.0.0-alpha1'}
    def test_interrupt_after_each_remote_mutation_resumes_without_duplicates(self):
        for stage in ['push','tag','release','package','checksum']:
            remote=FakeRemote(stage);ledger=self.ledger();receipts=[]
            with self.assertRaises(PowerLoss):m.finish(ledger,remote,lambda row:receipts.append(copy.deepcopy(row)))
            m.finish(ledger,remote,lambda row:receipts.append(copy.deepcopy(row)))
            self.assertTrue(ledger['release_download_verified']);self.assertTrue(all(count==1 for count in remote.counts.values()))
            m.finish(ledger,remote,lambda row:None);self.assertTrue(all(count==1 for count in remote.counts.values()))
    def test_moved_main_tag_asset_and_release_collisions_refuse(self):
        for kind in ['main','tag','asset','release']:
            remote=FakeRemote();remote.head='new'
            if kind=='main':remote.head='unrelated'
            if kind=='tag':remote.tag_value='other'
            if kind=='asset':remote.assets['package']='wrong'
            if kind=='release':remote.release_value={'draft':True,'prerelease':True}
            with self.assertRaises(ValueError):m.finish(self.ledger(),remote,lambda row:None)
