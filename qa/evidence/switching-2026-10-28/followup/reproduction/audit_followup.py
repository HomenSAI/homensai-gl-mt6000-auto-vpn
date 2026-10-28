"""Read-only local availability and source/evidence audit; never contact a router."""
import datetime, hashlib, json, os, pathlib, shutil, subprocess

repo=pathlib.Path(os.environ['QA_REPO']).resolve()
out=pathlib.Path(os.environ['QA_OUTPUT']).resolve()
evidence=repo/'qa/evidence/switching-2026-10-28'
old=json.loads((evidence/'qa-real-browser-kernel-summary.json').read_text())
digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
names=('docker','dockerd','dockerd-rootless.sh','rootlesskit','podman','crun','runc','containerd','nerdctl','buildah','skopeo','fuse-overlayfs','slirp4netns','newuidmap','newgidmap','pwsh','unshare','bwrap')
paths=('/var/run/docker.sock','/run/docker.sock','/run/podman/podman.sock','/run/user/0/docker.sock','/run/user/0/podman/podman.sock','/var/lib/docker','/var/lib/containers','/dev/fuse','/sys/fs/cgroup/cgroup.controllers','/sys/fs/cgroup/cgroup.subtree_control')
runtime={'binaries':{name:shutil.which(name)for name in names},'paths':{p:{'exists':os.path.exists(p),'writable':os.access(p,os.W_OK)}for p in paths},'docker_environment_configured':bool(os.environ.get('DOCKER_HOST')or os.environ.get('DOCKER_CONTEXT'))}
for p in ('/sys/fs/cgroup/cgroup.controllers','/sys/fs/cgroup/cgroup.subtree_control','/proc/self/uid_map','/proc/self/gid_map'):
 try:runtime[p]=pathlib.Path(p).read_text().strip()
 except OSError as error:runtime[p]=type(error).__name__
source=[]
for name,expected in old['backend_source_sha256'].items():
 current=digest(repo/'router/files/usr/lib/homensai-vpn'/name)
 committed=hashlib.sha256(subprocess.check_output(['git','-C',str(repo),'show','HEAD:router/files/usr/lib/homensai-vpn/'+name])).hexdigest()
 source.append({'module':name,'recorded_sha256':expected,'current_worktree_sha256':current,'current_worktree_match':current==expected,'committed_head_sha256':committed,'committed_head_match':committed==expected})
menu_path='router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json'
selected=json.loads((repo/menu_path).read_text())['admin/services/homensai-vpn']['action']['path'].split('/')[-1]
dashboard=repo/'router/files/www/luci-static/resources/view/homensai-vpn'/(selected+'.js')
committed_selected=json.loads(subprocess.check_output(['git','-C',str(repo),'show','HEAD:'+menu_path],text=True))['admin/services/homensai-vpn']['action']['path'].split('/')[-1]
committed_dashboard=hashlib.sha256(subprocess.check_output(['git','-C',str(repo),'show','HEAD:router/files/www/luci-static/resources/view/homensai-vpn/'+committed_selected+'.js'])).hexdigest()
certificate=pathlib.Path('/etc/homensai-vpn/native-certificate.json')
cert={'action':'Read-only metadata/hash verification; never modified, removed, or moved.'}
try:
 stat=certificate.stat();cert.update(exists=True,bytes=stat.st_size,mtime_utc=datetime.datetime.fromtimestamp(stat.st_mtime,datetime.timezone.utc).isoformat(),sha256=digest(certificate),matches_previous_incident=digest(certificate)=='773aaf1eeb8c289b8a3b46d8a12d282a0fbcd41f04c108df8831c00331b0cb3b')
except OSError as error:cert.update(exists=certificate.exists(),read_error=type(error).__name__)
report={
 'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'head':git('rev-parse','HEAD'),
 'scope':'Read-only local filesystem/tool availability and prior evidence provenance audit; no physical router, registry, container daemon or guest was contacted.',
 'isolation':{'etc_readonly':bool(os.statvfs('/etc').f_flag&os.ST_RDONLY),'run_readonly':bool(os.statvfs('/run').f_flag&os.ST_RDONLY),'effective_capabilities':next(x.split(':',1)[1].strip()for x in pathlib.Path('/proc/self/status').read_text().splitlines()if x.startswith('CapEff:'))},
 'prior_evidence':{'backend_modules':source,'all_16_committed_backend_hashes_match':all(x['committed_head_match']for x in source),'all_16_current_worktree_backend_hashes_match':all(x['current_worktree_match']for x in source),'worktree_changes_in_progress':git('status','--porcelain').splitlines(),'current_selected_dashboard':dashboard.name,'dashboard_sha256':digest(dashboard),'dashboard_matches_final_copy_smoke':digest(dashboard)==old['assets']['copy_only_recheck']['dashboard_sha256'],'committed_selected_dashboard':committed_selected+'.js','committed_dashboard_sha256':committed_dashboard,'committed_dashboard_matches_final_copy_smoke':committed_dashboard==old['assets']['copy_only_recheck']['dashboard_sha256'],'changes_since_copy_smoke':git('diff','--name-only','3a3b5949a3d2186d087307163f703b79cfcea93c','HEAD').splitlines()},
 'required_handoff':{'path':'docs/handoff/TODO-CLAUDE-SWITCHING-2026-10-28.ru.md','exists':(repo/'docs/handoff/TODO-CLAUDE-SWITCHING-2026-10-28.ru.md').exists(),'history':git('log','--all','--format=%H','--','docs/handoff/TODO-CLAUDE-SWITCHING-2026-10-28.ru.md').splitlines()},
 'physical_gate':{'status':'BLOCKED','private_directory_exists':(repo/'private').exists(),'active_executor_exists':(repo/'private/ACTIVE-EXECUTOR.local.json').exists(),'contact_attempts':0},
 'pinned_docker_gate':{'status':'BLOCKED','runner':'scripts/offline-ci.ps1','runtime_entrypoint':'qa/run_offline_ci.py','runner_sha256':digest(repo/'scripts/offline-ci.ps1'),'runtime_entrypoint_sha256':digest(repo/'qa/run_offline_ci.py'),
  'required_isolation':['immutable committed source archive','--pull=never','--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user=65534:65534','--pids-limit=128','--memory=512m','--cpus=2','bounded private /work and /tmp tmpfs','matching package SHA256 from both runtimes'],
  'image_inputs':{'full_tag':'homensai-vpn-python311:local','runtime_tag':'homensai-vpn-python39:local','reviewed_python39_image_id':'sha256:077393380406ae72cf73ce67ed8b0352e10ff7827330b1241631010d6112f150','reviewed_tools_image_id':'sha256:0b4418ddd722b07b92fe44d180df10fe252e105cd85ff830040e77b0fb34e3a7','python39_base_manifest':'python:3.9.15-slim-bullseye@sha256:ffc6cb648d6993e7c90abb95c2481eb688a6842dfac29bf19e3755454632daa2','python311_recipe':'qa/runtime-python311/Dockerfile','python39_recipe':'qa/runtime-python39/Dockerfile'},
  'local_runtime_availability':runtime,
  'findings':['No Docker/Podman/OCI executable, daemon socket, or standard image store exists in the current environment. A separate read-only host-view check confirmed absence outside the execution sandbox too.','The cgroup filesystem is not writable and no delegated controller subtree is configured; reviewed CPU/memory/PID container limits cannot be claimed enforced by an ad hoc extracted-Python run.','The Python3.11 recipe composes two already-local reviewed images; their exact bytes are not available here. The Python3.9 recipe has an unpinned apt-get install step, so rebuilding from the public base is not proof of the previously approved final image.','The orchestration script hardcodes a Windows Git path and PowerShell is absent. Porting the launcher would also require review; it does not solve missing approved image bytes.'],
  'safe_completion_prerequisite':'Use the existing approved runner with its exact images, or first supply SHA-verified docker-save/OCI exports and a reviewed isolated runtime capable of every required resource/UID/network/rootfs flag. A new rootless daemon/VM was not installed without those inputs.',
  'not_performed':['system Docker/Podman installation','/etc/subuid or /etc/subgid edits','cgroup writes','daemon or registry probing','container runs with substitute images','claiming portable Python as approved Docker CI']},
 'baseline_crash_scope':{'evidence':'real-child-crash-baseline.json','script':'lab/test_process_crash.py','actual':['a separate helper process receives SIGKILL','atomic JSON writes/fsync/rename occur on disk'],'synthetic':['kernel is a JSON file','recovery chooses primary/backup in test code','no production native_switch.child, rollback recovery, UCI or real kernel graph is executed'],'remaining_risk':'Backend review is investigating a concrete partial UCI move crash; any new production-process/kernel run is recorded separately.'},
 'previous_host_certificate':cert,
 'release_eligible':False}
(out/'qa-followup-availability.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'head':report['head'],'prior_committed_backend_matches':report['prior_evidence']['all_16_committed_backend_hashes_match'],'prior_dashboard_matches':report['prior_evidence']['dashboard_matches_final_copy_smoke'],'docker_gate':'BLOCKED','physical_gate':'BLOCKED','certificate_unchanged':cert.get('matches_previous_incident')},indent=2))
