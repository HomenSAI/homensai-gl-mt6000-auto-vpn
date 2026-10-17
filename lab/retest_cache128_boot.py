"""Retest only the marked private QEMU guest with bounded TCG cache."""
import hashlib,json,shlex,socket,subprocess,time
from pathlib import Path
SSH=['ssh','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/lab/known_hosts','-o','BatchMode=yes','-o','ConnectTimeout=3','-p','2222','root@127.0.0.1']
def remote(command,timeout=15):return subprocess.check_output(SSH+[command],stderr=subprocess.DEVNULL,timeout=timeout).decode()
release=remote("cat /etc/openwrt_release; test -f /tmp/HOMENSAI_VIRTUAL_LAB")
assert "DISTRIB_TARGET='x86/64'" in release
before=hashlib.sha256(remote('uci export network; uci export firewall').encode()).hexdigest()
remote('sync')
with socket.socket(socket.AF_UNIX) as s:
 s.settimeout(5);s.connect('/lab/qmp.sock');stream=s.makefile('rwb',buffering=0);json.loads(stream.readline())
 for command in ('qmp_capabilities','quit'):
  stream.write((json.dumps({'execute':command})+'\n').encode())
  while True:
   row=stream.readline()
   if not row:break
   value=json.loads(row)
   if 'error' in value:raise RuntimeError('Private QMP refused command')
   if 'return' in value:break
end=time.monotonic()+15
while time.monotonic()<end:
 with socket.socket() as probe:
  if probe.connect_ex(('127.0.0.1',2222))!=0:break
 time.sleep(.5)
else:raise SystemExit('Old private guest still listening; refusing second VM')
log=open('/lab/qemu-cache128.log','ab')
subprocess.Popen(['python3','/lab/run-cache128.py','--direct-kernel'],stdout=log,stderr=log,start_new_session=True)
end=time.monotonic()+180
while time.monotonic()<end:
 try:
  remote('true',8);break
 except (OSError,subprocess.SubprocessError):time.sleep(3)
else:raise SystemExit('Cold VM boot not confirmed; preserve disk/log')
after=hashlib.sha256(remote('uci export network; uci export firewall').encode()).hexdigest()
assert before==after
remote('touch /tmp/HOMENSAI_VIRTUAL_LAB')
print(json.dumps({'cold_cache128_boot':True,'network_firewall_unchanged':True,'guest_ram_mib':256,'tcg_cache_mib':128}),flush=True)
result=subprocess.run(['python3','/lab/openwrt_boot_check.py'],capture_output=True,text=True,timeout=230)
print(result.stdout,flush=True)
raise SystemExit(result.returncode)
