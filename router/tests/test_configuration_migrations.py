from pathlib import Path
import copy
import os
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
from configuration_migrations import PrivateSnapshotStore, migrate, validate,from_uci_snapshot,to_uci_snapshot
from cascade_executor import Refused, digest


def fixture():
    return dict(schema=1,main=dict(enabled='1',native_enabled='1',telegram_token='synthetic-private-value'),
                servers=[dict(profile='a',name='Custom name',channel='Main',priority='2',enabled='1'),
                         dict(profile='b',name='Old removed profile',channel='Reserve',priority='3',enabled='1')],
                statistics={'months':{'2026-10':{'rx':123,'tx':456}},'old_profile_history':{'b':17}})


class MigrationTests(unittest.TestCase):
    def test_full_private_uci_shape_preserves_existing_anonymous_section(self):
        old=fixture()
        sections=[dict({'.name':'main','.type':'main'},**old['main'])]
        for n,row in enumerate(old['servers']):
            sections.append(dict({'.name':'cfg_existing_'+str(n),'.type':'server','.anonymous':True},**row))
        source=from_uci_snapshot('homensai_vpn',sections,old['statistics'])
        candidate=migrate(source,2,['a'])
        exported=to_uci_snapshot(candidate)
        self.assertEqual(exported['config'],'homensai_vpn')
        self.assertEqual(exported['sections'][1]['.name'],'cfg_existing_0')
        self.assertTrue(exported['sections'][1]['.anonymous'])
        self.assertEqual(exported['sections'][0]['telegram_token'],'synthetic-private-value')
        self.assertEqual(exported['sections'][0]['native_enabled'],'0')
        self.assertEqual(exported['sections'][2]['enabled'],'0')
        self.assertEqual(candidate['statistics'],old['statistics'])

    def test_public_inventory_wrong_config_and_unknown_sections_are_refused(self):
        for config,sections in (('network',[{'.name':'main','.type':'main'}]),
                                ('homensai_vpn',[{'id':'redacted','enabled':True}]),
                                ('homensai_vpn',[{'.name':'main','.type':'main'},{'.name':'other','.type':'custom'}])):
            with self.assertRaises(Refused):from_uci_snapshot(config,sections,{})

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store=PrivateSnapshotStore(self.tmp.name)
        self.original=fixture(); self.store.initialize(self.original)

    def test_upgrade_downgrade_preserves_private_fields_names_and_history(self):
        receipt=self.store.commit(digest(self.original),2,['a','b'])
        current=self.store.read()
        self.assertFalse(receipt['auto'])
        self.assertNotIn('synthetic-private-value',str(receipt))
        self.assertEqual(current['servers'][0]['name'],'Custom name')
        self.assertEqual(current['statistics'],self.original['statistics'])
        self.assertEqual(current['main']['telegram_token'],self.original['main']['telegram_token'])
        self.assertEqual(current['main']['enabled'],'1')
        self.store.commit(receipt['revision'],1,['a','b'])
        restored=self.store.read()
        expected=copy.deepcopy(self.original)
        expected['main'].update(native_enabled='0',native_until='0',native_trial='')
        self.assertEqual(restored,expected)

    def test_removed_profile_is_retained_disabled_not_deleted(self):
        result=migrate(self.original,2,['a'])
        self.assertFalse(result['servers'][1]['enabled'])
        self.assertFalse(result['servers'][1]['present'])
        self.assertEqual(result['statistics'],self.original['statistics'])

    def test_failure_before_replace_keeps_original_and_does_not_claim_saved(self):
        original=self.store.io._atomic
        def fail(target,data):
            if target==self.store.path:raise OSError('simulated write failure')
            original(target,data)
        with patch.object(self.store.io,'_atomic',side_effect=fail),self.assertRaises(OSError):
            self.store.commit(digest(self.original),2,['a'])
        self.assertEqual(self.store.read(),self.original)
        self.assertEqual(self.store.read(self.store.backup),self.original)
        self.assertFalse(self.store.lock_path.exists())

    def test_compare_and_swap_and_orphaned_lock_refuse(self):
        with self.assertRaisesRegex(Refused,'EXTERNAL-EDIT'):
            self.store.commit('wrong',2,['a'])
        self.store.lock_path.write_text('orphaned')
        with self.assertRaisesRegex(Refused,'LOCK-BUSY'):
            self.store.commit(digest(self.original),2,['a'])
        self.assertEqual(self.store.read(),self.original)

    def test_rollback_preserves_secret_and_disables_auto(self):
        receipt=self.store.commit(digest(self.original),2,['a','b'])
        self.store.rollback(receipt['revision'],['a','b'])
        result=self.store.read()
        self.assertEqual(result['schema'],1)
        self.assertEqual(result['main']['native_enabled'],'0')
        self.assertEqual(result['main']['telegram_token'],self.original['main']['telegram_token'])

    def test_partial_unknown_duplicate_invalid_fixtures_refuse(self):
        for change in ('partial','version','duplicate','bool-priority','bad-flag'):
            row=fixture()
            if change=='partial':del row['statistics']
            if change=='version':row['schema']=3
            if change=='duplicate':row['servers'].append(copy.deepcopy(row['servers'][0]))
            if change=='bool-priority':row['servers'][0]['priority']=True
            if change=='bad-flag':row['servers'][0]['enabled']='yes'
            with self.subTest(change=change),self.assertRaises(Refused):migrate(row,2,['a'])

    def test_corrupt_snapshot_never_silently_uses_backup(self):
        self.store.commit(digest(self.original),2,['a'])
        self.store.path.write_text('broken')
        with self.assertRaises(Refused):self.store.commit('wrong',1,['a'])
        self.assertEqual(self.store.read(self.store.backup),self.original)

    @unittest.skipUnless(os.name=='posix','POSIX permissions')
    def test_private_files_have_owner_only_permissions(self):
        self.store.commit(digest(self.original),2,['a'])
        for path in (self.store.path,self.store.backup):
            self.assertEqual(path.stat().st_mode&0o777,0o600)


if __name__=='__main__':unittest.main()
