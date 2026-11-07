import copy
import json
from pathlib import Path
import unittest
from current_gate import problems,SURFACES,release_source
from source_identity import freeze_preview

ROOT=Path(__file__).resolve().parents[2]
class CurrentGateContracts(unittest.TestCase):
    def result(self):
        group=dict(width=1440,lang='en',theme='light')
        rows=[dict(group=group,kind='page',surface=s,**{'pass':True}) for s in SURFACES]
        rows += [dict(group=group,kind='wizard',step=s,**{'pass':True}) for s in range(1,5)]
        rows += [dict(group=group,kind='traffic',role=r,**{'pass':True}) for r in ('primary','reserve')]
        rows += [dict(group=group,kind='boundary',boundary=b,**{'pass':True}) for b in ('same-pair-rejected','skip-without-start','save-without-start','running-suppresses-first-run','existing-pair-suppresses-first-run','explicit-wizard-running')]
        rows += [dict(group=group,kind='modal',modal='help',**{'pass':True}),dict(group=group,kind='traffic-console',role='reserve',**{'pass':True}),dict(group=group,kind='traffic-console',role='primary',**{'pass':True})]
        return group,dict(complete=True,rows=rows,errors=[])
    def test_release_identity_refuses_unknown_dirty_and_untracked(self):
        clean=dict(git_head='a'*40,git_tracked_dirty=False,git_untracked_paths=[])
        self.assertTrue(release_source(clean))
        for fields in (dict(git_head=None),dict(git_tracked_dirty=True),dict(git_tracked_dirty=None),dict(git_untracked_paths=None),dict(git_untracked_paths=['qa/new.js'])):
            self.assertFalse(release_source(dict(clean,**fields)))
    def test_complete_contract_and_missing_sections(self):
        group,result=self.result()
        self.assertEqual(problems(result,[group]),[])
        for i in range(len(result['rows'])):
            altered=copy.deepcopy(result);altered['rows'].pop(i)
            self.assertTrue(problems(altered,[group]),i)
    def test_incomplete_errors_failure_duplicates_and_wrong_group_refuse(self):
        group,result=self.result()
        for change in (lambda r:r.update(complete=False),lambda r:r.update(errors=['boom']),
                       lambda r:r['rows'][0].update(**{'pass':False}),lambda r:r['rows'].append(r['rows'][0]),
                       lambda r:r['rows'][0]['group'].update(width=390)):
            altered=copy.deepcopy(result);change(altered);self.assertTrue(problems(altered,[group]))
    def test_frozen_assets_include_actual_entry_fixture_and_lazy_modules(self):
        files,identity,manifest=freeze_preview(ROOT)
        app=json.loads((ROOT/'VERSION.json').read_text(encoding='utf-8-sig'))['application']
        prefix='/router/files/www/luci-static/resources/view/homensai-vpn/'
        self.assertEqual(files['/preview-module.js'],files[prefix+app['ui_module']+'.js'])
        self.assertEqual(files['/qa/ui-preview/fixture-pair.js'],(ROOT/'qa/ui-preview/fixture-pair.js').read_bytes())
        lazy=ROOT/'router/files/www/luci-static/resources/homensai-vpn'
        for p in lazy.rglob('*.js'):
            self.assertEqual(files['/router/files/www/luci-static/resources/homensai-vpn/'+p.relative_to(lazy).as_posix()],p.read_bytes())
        self.assertIn('qa/ui-probe/current_analyse.js',manifest['harness_files'])
        self.assertIn('qa/ui-probe/current_gate.py',manifest['harness_files'])
        self.assertIn('scripts/ui-probe.ps1',manifest['harness_files'])
        self.assertTrue(identity['git_head'])
        self.assertEqual(files['/preview-router.js'],b'window.HOMENSAI_PREVIEW_ROUTER_ORIGIN=null;')
        self.assertFalse(any('/private/' in p or '/.git/' in p for p in files))

if __name__=='__main__':unittest.main()
