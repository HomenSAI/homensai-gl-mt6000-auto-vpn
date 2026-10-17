"""Bounded read-only resource observations of marked x86 clone, no physical claims."""
import argparse,json,time
from datetime import datetime,timezone
from pathlib import Path
from serial_clone import require_clone,json_command
require_clone()
p=argparse.ArgumentParser();p.add_argument('--samples',type=int,default=3);p.add_argument('--interval',type=int,default=30);a=p.parse_args()
if not 1<=a.samples<=96 or not 10<=a.interval<=300:raise ValueError('RESOURCE-BOUNDS')
code="""import json,time,os,resource
from pathlib import Path
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
assert "DISTRIB_TARGET='x86/64'" in Path('/etc/openwrt_release').read_text()
m={}
for line in Path('/proc/meminfo').read_text().splitlines():
 k,v=line.split(':',1)
 if k in ('MemTotal','MemAvailable','MemFree'):m[k]=int(v.split()[0])*1024
f=os.statvfs('/etc')
pids=[]
for entry in list(Path('/proc').iterdir())[:256]:
 if not entry.name.isdigit():continue
 try:
  cmd=(entry/'cmdline').read_bytes()
  parts=cmd.split(bytes([0]))
  if b'/usr/lib/homensai-vpn/agent.py' not in parts or b'daemon' not in parts:continue
  values={}
  for line in (entry/'status').read_text().splitlines():
   if line.startswith('VmRSS:'):values['rss_bytes']=int(line.split()[1])*1024
  pids.append(values)
 except OSError:pass
print('CLONE_JSON:'+json.dumps({'guest_time':time.time(),'memory':m,'config_free_bytes':f.f_bavail*f.f_frsize,'monitor_instances':pids[:8]}))"""
rows=[]
for i in range(a.samples):
 row=json_command(code,60);row['host_observed_at_utc']=datetime.now(timezone.utc).isoformat();rows.append(row)
 if i+1<a.samples:time.sleep(a.interval)
result={'scope':'isolated virtual x86 guest; not physical flash wear or hardware performance','samples':rows,'router_changes':False}
Path('/lab/clone-resource-observations.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
