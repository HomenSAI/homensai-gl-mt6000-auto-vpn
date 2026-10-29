"""Download pinned public guest files; bootstrap only the QEMU launched by us.

Host packages/network/routing are never installed or configured. QEMU, Lua5.1
with lua-cjson, Python and Playwright/Chromium are external QA prerequisites.
"""
import argparse,functools,hashlib,json,os,shlex,socket,threading,time,urllib.request
from http.server import HTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from qa_config import QEMU_ROOT,SERIAL_PORT
import qemu_serial

HERE=Path(__file__).resolve().parent
FILES=[('openwrt.img.gz','https://downloads.openwrt.org/releases/21.02.7/targets/x86/64/openwrt-21.02.7-x86-64-generic-ext4-combined.img.gz','39f8e1f629cfe1db985809639c2cd1de88db119544144740d968d0b6784a9d6f'),
       ('openwrt-kernel.bin','https://downloads.openwrt.org/releases/21.02.7/targets/x86/64/openwrt-21.02.7-x86-64-generic-kernel.bin','4c5a50fe3de95b297308c27cf66a858be98fb14d9d85e8f302fa0f6d302fcfdd')]
PACKAGES=json.loads((HERE/'openwrt-package-manifest.json').read_text())

def download():
    (QEMU_ROOT/'guest-ipks').mkdir(parents=True,exist_ok=True)
    for name,url,wanted in FILES+[(str(Path('guest-ipks')/p['filename']),p['url'],p['sha256'])for p in PACKAGES]:
        dest=QEMU_ROOT/name
        if not dest.exists():
            with urllib.request.urlopen(url,timeout=60)as response:dest.write_bytes(response.read())
        if hashlib.sha256(dest.read_bytes()).hexdigest()!=wanted:raise RuntimeError('SHA256 mismatch: '+str(dest))
        print('verified',name,flush=True)

def own_qemu():
    pid=int((QEMU_ROOT/'qemu-pid.txt').read_text());args=Path('/proc',str(pid),'cmdline').read_bytes().split(b'\0')
    expected=('file='+str(QEMU_ROOT/'openwrt.img')+',format=raw,if=virtio').encode()
    serial=('tcp:127.0.0.1:%d,server=on,wait=off'%SERIAL_PORT).encode()
    if expected not in args or serial not in args or b'qemu-system-x86_64'not in Path('/proc',str(pid),'exe').resolve().name.encode():
        raise RuntimeError('Private QEMU process/drive/serial ownership mismatch')

def bootstrap():
    own_qemu()
    # This single bootstrap call may create the marker only after matching the
    # recorded QEMU PID, disk and private serial, plus the exact guest version.
    original=qemu_serial.BASE
    qemu_serial.BASE='. /etc/openwrt_release; [ "$DISTRIB_TARGET" = x86/64 ] && [ "$DISTRIB_RELEASE" = 21.02.7 ] && [ "$(uname -r)" = 5.4.238 ] || exit 98; '
    try:print(qemu_serial.execute('touch /tmp/HOMENSAI_VIRTUAL_LAB; uname -a'))
    finally:qemu_serial.BASE=original
    handler=functools.partial(SimpleHTTPRequestHandler,directory=str(QEMU_ROOT/'guest-ipks'))
    with HTTPServer(('127.0.0.1',18989),handler)as server:
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        try:
            qemu_serial.execute('ip addr add 10.0.3.15/24 dev eth1 2>/dev/null || :; ip link set eth1 up; mkdir -p /tmp/qa-ipks')
            for package in PACKAGES:
                filename=package['filename'];digest=package['sha256']
                script='cd /tmp/qa-ipks; wget -q -O '+shlex.quote(filename)+' '+shlex.quote('http://10.0.3.2:18989/'+filename)+' && echo '+shlex.quote(digest+'  '+filename)+' | sha256sum -c - && opkg install '+shlex.quote(filename)
                print(qemu_serial.execute(script,timeout=45),flush=True)
            print(qemu_serial.execute('ip -4 -j rule show; iptables -V'),flush=True)
        finally:server.shutdown();worker.join(timeout=2)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--download',action='store_true');parser.add_argument('--bootstrap',action='store_true');options=parser.parse_args()
    if not options.download and not options.bootstrap:parser.error('choose --download and/or --bootstrap')
    if options.download:download()
    if options.bootstrap:bootstrap()
