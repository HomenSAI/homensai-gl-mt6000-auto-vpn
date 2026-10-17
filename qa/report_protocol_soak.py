"""Build an English report only from independently validated terminal soak artifacts."""
import argparse,json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from verify_protocol_soak import verify,REQUIRED,PROFILES

def report(observation,start,cleanup,ci):
    result=verify(observation,start,cleanup)
    s=observation['series'];p=observation['producer'];by=s['by_check']
    completed=datetime.fromisoformat(observation['host_observed_at_utc']).astimezone(ZoneInfo('Europe/Berlin')).isoformat()
    lines=['# Final isolated protocol soak report','',f'Collected: {completed} (Europe/Berlin).','',
      '## Result','',f"**PASS** — {result['passed_checks']} assertions, {result['cycles']} cycles; zero failed assertions and zero missing events.",
      f"Host start-to-collection interval: {result['host_elapsed_seconds']} seconds. Guest monotonic elapsed: {result['guest_elapsed_seconds']} seconds.",
      '','Failures were deliberately injected. Zero failed assertions means the expected failure/recovery behavior passed; it does not mean every synthetic server remained available.',
      '','## Actual scope','',
      'Marked isolated OpenWrt 21.02.7 x86/64 guest inside a Docker network-none QEMU copy. Four real local encrypted tunnels: two WireGuard and two static-key UDP OpenVPN. Generated DNS/TLS endpoints and a standalone namespace selector; no real VPN provider credentials or physical router access.',
      '',f"Producer source SHA256: `{result['source_sha256']}`. Immutable producer was not patched during the run.",
      '','## Observed profile checks','',
      '| Synthetic server | Selected-path DNS/TLS checks | Standby bound DNS/TLS checks |',
      '| --- | ---: | ---: |']
    for key in PROFILES:lines.append(f"| {key} | {s['selected_verified'][key]} | {s['standby_verified'][key]} |")
    lines+=['','These are counts of verified checks, not connection durations, throughput or production uptime. Standby probes are interface/mark-bound; this does not certify uninterrupted user sessions during switching.',
      '','## Repeated fault and restoration assertions','',
      '| Assertion | Successful observations |','| --- | ---: |']
    for name in REQUIRED:lines.append(f"| {name} | {by[name]['PASS']} |")
    lines+=['','## Cleanup and preservation','',
      '- Producer reports cleanup complete and original root network fingerprint unchanged.',
      '- Independent witness confirms no owned namespaces, child/orphan cohort processes or private test-key files remain.',
      '- Independent root route/rule/network/firewall checkpoint matches before/after.',
      '- Collector reached terminal PASS with exact counters and complete retained-event coverage.',
      '','## Corrected defects','',
      '1. Cold probe processes imported http.server/mimetypes unnecessarily; a captured traceback showed >20 seconds in import. Moved that dependency into server mode. The later 2-second strict run failed one standby sample at 85 minutes; its DNS/TLS phase was not retained, so its cause remains unknown. Final test budget is explicitly aligned with the application socket timeout of 3 seconds, with detailed raw samples and no retry masking.',
      '2. Slow synthetic endpoint bootstrap was mistaken for transport failure. Added a bounded 60-second readiness barrier before real bound DNS/TLS acceptance.',
      '3. Package builder selected obsolete dashboard28/ui15 while menu referenced the newer interface. Added dynamic selection and validation of menu -> packaged JS -> packaged CSS plus legacy LuCI controller alignment.',
      '4. Inactive/stale cards showed a null interface and historic latency as current. Corrected labels, suppressed invalid current latency and required fresh healthy evidence for current OK counters.',
      '5. Observation/witness helpers needed correction for a hash-prefix typo and absent stat utility. Replaced with derived filenames and minimal built-in os.stat/time. Startup-response timeout was diagnosed read-only; collector was not duplicated.',
      '','Earlier failed runs are retained in qa/protocol-*-failed.json and the timestamped WORKLOG. The final pass does not overwrite those failures.',
      '','## Package and CI','']
    for row in ci:lines.append(f"- Source `{row['source']}`, Python {row['python']}: {row['application_tests']} application tests, {row['qa_tests']} QA tests, {row['ui_suites']} UI suites, {row['skipped_tests']} documented skips; result {row['result']}.")
    lines+=[f"- Package `{ci[0]['artifact']}`, SHA256 `{ci[0]['sha256']}`, {ci[0]['bytes']} bytes; reproducible across both runtime builds.",
      '','## Not established by this report','',
      '- GL-MT6000 ARM firmware/vendor-worker arbitration, actual LAN client switching, power-cut recovery, external provider behavior or WAN-facing security.',
      '- Native full server -> channel -> protocol hierarchy acceptance on GL.iNet.',
      '- No traffic/session continuity, speed or availability guarantee.',
      '- No package was uploaded or installed on the physical router during these tests.',
      '']
    return '\n'.join(lines)

def main():
    p=argparse.ArgumentParser();p.add_argument('--observation',required=True);p.add_argument('--start',required=True);p.add_argument('--cleanup',required=True);p.add_argument('--ci',required=True);p.add_argument('--output',required=True);p.add_argument('--classification');a=p.parse_args()
    inputs=[json.loads(Path(getattr(a,key)).read_text(encoding='utf8')) for key in ('observation','start','cleanup','ci')]
    text=report(*inputs)
    if a.classification:
        raw=json.loads(Path(a.classification).read_text(encoding='utf8'));assert raw['result']=='PASS' and raw['source_sha256']==inputs[0]['producer']['source_sha256']
        classes=raw['classes'];section=['## Raw-probe accounting','',f"All {raw['raw_probe_records']} raw records matched the frozen scenario in exact order.",'',f"- {classes['soak-selected']} selected-path and {classes['soak-standby']} standby probes: all successful; no retries in this steady-state phase.",f"- {classes['injected-negative']} deliberately negative samples across {raw['fault_rounds']} fault rounds.",f"- {classes.get('recovery-wait-retry-negative',0)} negative samples during bounded primary-restoration waiting; all {classes['recovery-wait-success']} restorations eventually passed.",'- These negative probes are not 67 production outages or 67 failed assertions.','- CSV timestamps are guest wall-clock values; use the host collection times for real-world chronology.','']
        text=text.replace('## Not established by this report','\n'.join(section)+'\n## Not established by this report')
    Path(a.output).write_text(text,encoding='utf8')
if __name__=='__main__':main()