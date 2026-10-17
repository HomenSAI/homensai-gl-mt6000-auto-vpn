"""Terminal evidence validator must reject incomplete, contradictory or short runs."""
import copy,unittest
from verify_protocol_soak import verify,REQUIRED,PROFILES
class SoakAcceptanceTests(unittest.TestCase):
 def fixture(self):
  checks={name:{'PASS':2,'FAIL':0} for name in REQUIRED}
  for profile in PROFILES:
   checks['real-'+profile+'-bound-DNS-TLS-ready']={'PASS':1,'FAIL':0}
   checks['soak-selected-'+profile]={'PASS':1,'FAIL':0};checks['soak-parallel-reserve-'+profile]={'PASS':1,'FAIL':0}
  counts={'PASS':sum(v['PASS'] for v in checks.values())}
  producer={'state':'PASS','source_sha256':'a'*64,'error':None,'cleanup_confirmed':True,'root_namespace_network_changed':False,'duration_seconds':7200,'elapsed_seconds':7201,'counts':counts,'cycles':4}
  series={'producer_state':'PASS','source_sha256':'a'*64,'counts':copy.deepcopy(counts),'cycles':4,'missing_events':0,'coverage_complete':True,'observed_events':sum(counts.values()),'by_check':checks,'selected_verified':dict.fromkeys(PROFILES,1),'standby_verified':dict.fromkeys(PROFILES,1)}
  return ({'producer':producer,'series':series,'fresh':True,'observation_age':{'producer_seconds':1,'collector_seconds':1},'host_observed_at_utc':'2026-10-17T00:00:01+00:00'},{'source_sha256':'a'*64,'duration_seconds':7200,'host_started_at_utc':'2026-10-16T22:00:00+00:00'},{'result':'PASS','root_checkpoint_unchanged':True,'owned_namespaces_remaining':[],'private_key_files_remaining':0,'children':[],'cohort_processes':[]})
 def test_complete_synthetic_validator_fixture_passes(self):self.assertEqual(verify(*self.fixture())['result'],'PASS')
 def test_intermediate_short_failed_and_contradictory_runs_refused(self):
  changes=[lambda o,s,c:o.update(fresh=False),lambda o,s,c:o['observation_age'].update(collector_seconds=91),lambda o,s,c:o['producer'].update(state='RUNNING'),lambda o,s,c:o['producer'].update(elapsed_seconds=7199),lambda o,s,c:o['producer'].update(cleanup_confirmed=False),lambda o,s,c:o['producer'].update(root_namespace_network_changed=True),lambda o,s,c:o['producer'].update(error='FAIL'),lambda o,s,c:o['producer'].update(duration_seconds=0),lambda o,s,c:o['series'].update(source_sha256='b'*64),lambda o,s,c:o['series'].update(counts={'PASS':1}),lambda o,s,c:o['series'].update(missing_events=1),lambda o,s,c:o['series'].update(coverage_complete=False),lambda o,s,c:o['series'].update(observed_events=0),lambda o,s,c:o['series']['selected_verified'].update(wga=0),lambda o,s,c:o['series']['by_check'].pop(REQUIRED[0]),lambda o,s,c:c.update(children=[123]),lambda o,s,c:c.update(cohort_processes=[456]),lambda o,s,c:c.update(private_key_files_remaining=1),lambda o,s,c:c.update(owned_namespaces_remaining=['owned']),lambda o,s,c:c.update(root_checkpoint_unchanged=False),lambda o,s,c:o.update(host_observed_at_utc='2026-10-16T22:30:00+00:00')]
  for change in changes:
   with self.subTest(change=change):
    data=self.fixture();change(*data)
    with self.assertRaises(ValueError):verify(*data)
if __name__=='__main__':unittest.main()