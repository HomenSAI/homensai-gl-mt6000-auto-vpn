"""Combine only completed final QA reports; keep release blockers explicit."""
import hashlib,json,subprocess
from pathlib import Path
from qa_config import OUT,REPO

specs=[('real_kernel_parser','qemu-kernel-final.json','cases'),('browser_backend_kernel','browser-e2e-kernel-final.json','checks'),('browser_presentation','browser-presentation-final.json','checks'),('auto_foreign_kernel','auto-foreign-kernel-final.json','checks'),('copy_only_browser_smoke','browser-copy-final.json','checks')]
reports={name:json.loads((OUT/file).read_text())for name,file,_ in specs}
rows=[]
for name,file,key in specs:
    report=reports[name];checks=report[key]
    rows.append({'name':name,'status':report['verdict'],'passed':sum(x['passed']for x in checks),'assertions':len(checks),'evidence':file,'scope':report['scope']})
full=reports['browser_backend_kernel']['steps'][0]['state']['identity'];copy=reports['copy_only_browser_smoke']['identity']
source=copy['python_source_sha256'];current={name:hashlib.sha256((REPO/'router/files/usr/lib/homensai-vpn'/name).read_bytes()).hexdigest()for name in source}
menu=json.loads((REPO/'router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json').read_text());module=menu['admin/services/homensai-vpn']['action']['path'].split('/')[-1]
asset=REPO/'router/files/www/luci-static/resources/view/homensai-vpn'/(module+'.js')
matched=current==source==full['python_source_sha256']and hashlib.sha256(asset.read_bytes()).hexdigest()==copy['generated_dashboard_sha256']
blocked=[{'gate':'required_handoff','status':'BLOCKED','reason':'docs/handoff/TODO-CLAUDE-SWITCHING-2026-10-28.ru.md is absent from available worktree and all Git-ref history; no replacement obligations were invented.','evidence':'qa-environment-and-handoff.json'},
 {'gate':'canonical_immutable_docker_python39_python311_ci','status':'BLOCKED','reason':'Approved immutable Docker runtimes not executed in this QA environment. Separate local interpreter checks do not replace this gate.'},
 {'gate':'physical_mt3000_private_executor','status':'BLOCKED','reason':'Private runbook/executor and physical target are unavailable. No physical router was contacted.'},
 {'gate':'physical_vendor_firmware_and_lan_acceptance','status':'BLOCKED','reason':'Real vendor RTP/procd/worker behavior, real VPN/LAN DNS/HTTPS/exit, reboot/power-cut and normal package installation require the approved physical-device workflow.'},
 {'gate':'release_and_installation','status':'BLOCKED','reason':'No release/tag/package installation is authorized before the required missing handoff and mandatory device/CI gates are satisfied.'}]
summary={'verdict':'LOCAL_QA_PASS_RELEASE_BLOCKED'if all(r['status']=='PASS'for r in rows)and matched else'FAIL','application_version':copy['version'],
 'head_at_summary':subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
 'validation':rows,'total_assertions':sum(r['assertions']for r in rows),'all_recorded_backend_hashes_match_current':matched,
 'assets':{'full_functional_and_presentation':{'repository_commit':full['repository_commit'],'dashboard_sha256':full['generated_dashboard_sha256'],'scope':'33 full browser/controller/kernel assertions plus 13 explicitly synthetic presentation assertions'},
           'copy_only_recheck':{'repository_commit':copy['repository_commit'],'dashboard_sha256':copy['generated_dashboard_sha256'],'scope':'One neutral Auto instruction changed; targeted real render/click and actual QEMU transaction rechecked. Entire functional matrix was not rerun on this text-only asset.'}},
 'host_isolation':copy['isolation'],'backend_source_sha256':source,'blocked_gates':blocked,
 'independent_findings':[{'case':'accepted manual request plus older status redraw','baseline':'FAIL: second real click sent another RPC before the first terminal result','evidence':'browser-race-baseline.json','final':'PASS: sticky request correlation and lost-ACK recovery in browser-backend-kernel scenario'},
 {'case':'manual hold had no Resume UI','baseline':'FAIL: resume.allowed=true but only primary/reserve buttons rendered','evidence':'browser-resume-missing-baseline.json','final':'PASS: actual Resume click clears hold without apply or budget change'},
 {'case':'Auto failback reused stale reserve kernel proof','baseline':'FAIL: real kernel restored primary but controller entered HELD/BLOCKED SOURCE-NOT-HEALTHY','evidence':'auto-api-kernel-stale-failback-baseline.json','final':'PASS: one restoration, RUNNING/ROLLED-BACK then OBSERVING without another apply'},
 {'case':'DEGRADED sidebar incorrectly claimed Auto OFF','baseline':'Found in actual shared model; UI agent preserved failing regression','final':'PASS: full/Minimum/sidebar agree on the selected-channel problem'},
 {'case':'Auto-on page still instructed the user to turn Auto on','baseline':'Found in actual post-failback screenshot','final':'PASS: final neutral instruction rendered and real click transaction passed on new asset'}],
 'scope_limits':['Disposable OpenWrt x86/64 kernel, not physical GL-MT3000 firmware.','UCI/vendor RTP compilation, tunnel health and worker launch are synthetic adapters. Native child code executes within the fixture, not a separate procd process.','Raw guest netfilter/IP policy is real; no external LAN-client packet path or actual VPN endpoint is certified.','Presentation timer/clock/degraded cases use explicit synthetic RPC/status overlays.'],
 'infrastructure_incident':'qa-isolation-incident.json','release_eligible':False,
 'screenshots':['browser-copy-final.png','browser-presentation-final-degraded-minimum.png']}
cleanup=OUT/'qa-cleanup.json'
if cleanup.exists():summary['cleanup']=json.loads(cleanup.read_text())
(OUT/'qa-real-browser-kernel-summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({'verdict':summary['verdict'],'assertions':summary['total_assertions'],'backend_hashes_match':matched,'matrix':rows},indent=2))
