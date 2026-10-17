"""Validate terminal synthetic protocol evidence; never promotes intermediate observations."""
import argparse,json,math,re
from datetime import datetime
from pathlib import Path

PROFILES=('wga','wgb','ova','ovb')
REQUIRED=('failed-primary-DNS-TLS-refused','same-protocol-reserve-healthy','same-protocol-route-switch','cross-protocol-route-switch','restored-primary-bound-healthy','actual-return-and-rollback','DNS-failure-distinct','DNS-fault-reserve-unaffected','kill-switch-blocks-direct-underlay','real-conntrack-TCP-observed','scoped-TCP-cleanup-keeps-UDP','root-network-unchanged-after-faults')

def verify(observation,start,cleanup):
    def require(ok,code):
        if not ok:raise ValueError(code)
    p=observation['producer'];s=observation['series'];sha=start['source_sha256']
    age=observation.get('observation_age',{});require(observation.get('fresh') is True and set(age)=={'producer_seconds','collector_seconds'} and all(type(v) is int and 0<=v<=90 for v in age.values()),'SOAK-STALE-OBSERVATION')
    require(isinstance(sha,str) and re.fullmatch('[a-f0-9]{64}',sha) is not None,'SOAK-SOURCE-FORMAT')
    require(p.get('state')=='PASS' and s.get('producer_state')=='PASS','SOAK-NOT-TERMINAL-PASS')
    require(p.get('source_sha256')==s.get('source_sha256')==sha,'SOAK-SOURCE-MISMATCH')
    require(p.get('error') is None and p.get('cleanup_confirmed') is True and p.get('root_namespace_network_changed') is False,'SOAK-CLEANUP-UNVERIFIED')
    elapsed=p.get('elapsed_seconds');duration=p.get('duration_seconds')
    require(type(duration) is int and duration==start.get('duration_seconds') and duration>=7200,'SOAK-DURATION')
    require(type(elapsed) in (int,float) and math.isfinite(elapsed) and elapsed>=duration,'SOAK-ELAPSED')
    counts=p.get('counts',{});require(set(counts)<={'PASS','FAIL'} and all(type(v) is int and v>=0 for v in counts.values()) and counts.get('PASS',0)>0 and counts.get('FAIL',0)==0,'SOAK-COUNTERS')
    require(s.get('counts')==counts and s.get('cycles')==p.get('cycles'),'SOAK-COLLECTOR-LAG')
    total=sum(counts.values());require(type(s.get('missing_events')) is int and s.get('missing_events')==0 and s.get('coverage_complete') is True and s.get('observed_events')==total,'SOAK-EVIDENCE-GAP')
    by_check=s.get('by_check',{});require(all(isinstance(v,dict) and set(v)=={'PASS','FAIL'} and type(v['PASS']) is int and v['PASS']>=0 and type(v['FAIL']) is int and v['FAIL']==0 for v in by_check.values()) and sum(v['PASS'] for v in by_check.values())==total,'SOAK-EVENT-COUNTERS')
    for name in REQUIRED:require(by_check.get(name,{}).get('PASS',0)>=2,'SOAK-FAULT-COVERAGE:'+name)
    for profile in PROFILES:require(by_check.get('real-'+profile+'-bound-DNS-TLS-ready',{}).get('PASS',0)>=1,'SOAK-TRANSPORT-COVERAGE')
    cycles=p.get('cycles');require(type(cycles) is int and cycles>=4,'SOAK-CYCLES')
    for key in ('selected_verified','standby_verified'):
        rows=s.get(key,{});require(set(rows)==set(PROFILES) and all(type(v) is int and v>0 for v in rows.values()) and sum(rows.values())==cycles,'SOAK-PROFILE-COVERAGE:'+key)
    require(cleanup.get('result')=='PASS' and cleanup.get('root_checkpoint_unchanged') is True and cleanup.get('owned_namespaces_remaining')==[] and cleanup.get('private_key_files_remaining')==0 and cleanup.get('children')==[] and cleanup.get('cohort_processes')==[],'SOAK-INDEPENDENT-CLEANUP')
    begin=datetime.fromisoformat(start['host_started_at_utc']);end=datetime.fromisoformat(observation['host_observed_at_utc'])
    require(begin.tzinfo is not None and end.tzinfo is not None,'SOAK-HOST-CLOCK-ZONE')
    host_seconds=(end-begin).total_seconds();require(host_seconds>=7200,'SOAK-HOST-DURATION')
    return {'result':'PASS','source_sha256':sha,'host_elapsed_seconds':round(host_seconds,2),'guest_elapsed_seconds':elapsed,'cycles':cycles,'passed_checks':counts['PASS'],'coverage_complete':True,'scope':'synthetic real local tunnels and selector; not physical GL.iNet native acceptance','physical_router_access':False}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--observation',required=True);parser.add_argument('--start',required=True);parser.add_argument('--cleanup',required=True);parser.add_argument('--output',required=True);a=parser.parse_args()
    result=verify(*(json.loads(Path(getattr(a,key)).read_text()) for key in ('observation','start','cleanup')));Path(a.output).write_text(json.dumps(result,indent=2));print(json.dumps(result))
if __name__=='__main__':main()