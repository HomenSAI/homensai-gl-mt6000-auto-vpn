"""Host-only bounded executor/journal load benchmark, not router performance."""
import argparse
import json
from pathlib import Path
import platform
import resource
import sys
import tempfile
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'router/files/usr/lib/homensai-vpn'))
from cascade_executor import EdgeAuthority, Journal, MemoryBackend, OfflineExecutor
from candidate_runtime import ProbeScheduler


def workload(count, iterations):
    profiles=['p'+str(i) for i in range(count)]
    backend=MemoryBackend(profiles)
    authority=EdgeAuthority()
    replacements=0
    max_files=0
    start=time.perf_counter();cpu=time.process_time()
    with tempfile.TemporaryDirectory() as directory:
        journal=Journal(directory)
        original=journal._atomic
        def counted(target,data):
            nonlocal replacements
            replacements+=1
            return original(target,data)
        journal._atomic=counted
        executor=OfflineExecutor(backend,journal,authority)
        max_pending=0
        for index in range(iterations):
            now=index*10+1
            target=profiles[(index+1)%count]
            before=list(backend.order);after=[target]+[p for p in before if p!=target]
            backend.record_probe(target,now)
            token=executor.prepare(dict(id=index+1,operation='apply',model_only=True,
                                         before=before,after=after),now)
            max_pending=max(max_pending,len(authority.pending))
            executor.apply(token,now+1)
            ctx=executor.pending
            executor.confirm(dict(transaction=ctx['transaction'],target=target,
                                   interface=ctx['expected_interface'],expected_interface=ctx['expected_interface'],
                                   exit=ctx['expected_exit'],expected_exit=ctx['expected_exit'],
                                   dns=True,https=True,time=now+2),now+2)
            assert executor.root==profiles
            assert len(authority.pending)<=64
            max_files=max(max_files,sum(p.stat().st_size for p in Path(directory).iterdir()))
        retained=sum(p.stat().st_size for p in Path(directory).iterdir())
    return dict(profiles=count,transitions=iterations,wall_seconds=time.perf_counter()-start,
                cpu_seconds=time.process_time()-cpu,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                atomic_replacements=replacements,replacements_per_transition=replacements/iterations,
                max_journal_bytes=max_files,retained_journal_bytes=retained,
                max_pending_proofs=max_pending,remaining_proofs=len(authority.pending),
                backend_writes=backend.write_count,retained_backend_write_records=len(backend.writes),result='PASS')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--iterations',type=int,default=1000)
    args=parser.parse_args()
    if not 1<=args.iterations<=20000:parser.error('iterations must be 1..20000')
    # Bound idle reservations separately; these execute no packets.
    scheduler=ProbeScheduler(concurrency=4)
    for i in range(4):
        scheduler.reserve('p'+str(i),dict(profile='p'+str(i),interface='test-tun',
                           namespace='fixture',mark=i+1,isolated=True,revision='r1'),0)
    assert scheduler.expire(10)==4 and not scheduler.active
    reports=[workload(count,args.iterations) for count in (2,16)]
    print(json.dumps(dict(scope='network-disabled Linux host; not router/flash performance',
                          python=platform.python_version(),platform=platform.platform(),
                          rss_scope='process high-water mark; includes prior workload',
                          fsync_enabled=True,workloads=reports),indent=2))


if __name__=='__main__':main()
