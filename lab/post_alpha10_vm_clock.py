import json,time
from datetime import datetime,timezone
from pathlib import Path
from serial_clone import require_clone,json_command
require_clone();stamp=datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
code="""import json,time,subprocess
from pathlib import Path
assert Path('/tmp/HOMENSAI_VIRTUAL_LAB').is_file()
assert "DISTRIB_TARGET='x86/64'" in Path('/etc/openwrt_release').read_text()
before=time.time();subprocess.run(['date','-u','-s',"""+repr(stamp)+"""],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
rtc=subprocess.run(['hwclock','-w','-u'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
print('CLONE_JSON:'+json.dumps({'guest_before':before,'guest_after':time.time(),'virtual_rtc_write_rc':rtc.returncode,'scope':'only disposable guest clock aligned after pause; no host/physical clock change'}))"""
r=json_command(code,30);r['host_observed_at']=time.time();r['after_skew_seconds']=round(r['host_observed_at']-r['guest_after'],3)
Path('/lab/post-alpha10-clock.json').write_text(json.dumps(r,indent=2));print(json.dumps(r))
