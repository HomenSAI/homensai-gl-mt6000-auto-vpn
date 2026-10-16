"""Transfer candidate/source over the container-local server and test the guest."""
from pathlib import Path
import subprocess
import time
ssh=['ssh','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/lab/known_hosts','-o','BatchMode=yes','-o','ConnectTimeout=5','-p','2222','root@127.0.0.1']
command="""wget -q -O /tmp/final-alpha2.ipk http://10.0.3.2:8000/final-alpha2.ipk && echo '976a44f3f4dfab0cb75083b39de0257c71424b19a6a439e6230f1e5f31e6e789  /tmp/final-alpha2.ipk' | sha256sum -c - && opkg install --force-reinstall /tmp/final-alpha2.ipk && test "$(uci get homensai_vpn.main.vm_upgrade_marker)" = retained && mkdir -p /tmp/homensai-final && wget -q -O /tmp/final-tests.tar.gz http://10.0.3.2:8000/router-tests-final.tar.gz && tar -xzf /tmp/final-tests.tar.gz -C /tmp/homensai-final && cd /tmp/homensai-final && python3 -m unittest discover -s router/tests -q"""
deadline=time.monotonic()+180
while True:
    try:
        subprocess.run(ssh+['true'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=8)
        break
    except (OSError,subprocess.SubprocessError):
        if time.monotonic()>=deadline:raise SystemExit('Guest SSH readiness timeout')
        time.sleep(3)
run=subprocess.run(ssh+[command],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
Path('/lab/final-suite.log').write_bytes(run.stdout);print(run.stdout.decode(errors='replace')[-5500:]);raise SystemExit(run.returncode)
