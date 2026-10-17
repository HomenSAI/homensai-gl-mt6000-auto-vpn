"""Isolated TCG OpenWrt laboratory. No host network, TAP or privileged mode."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import zlib

URL='https://downloads.openwrt.org/releases/21.02.7/targets/x86/64/openwrt-21.02.7-x86-64-generic-ext4-combined.img.gz'
SHA256='39f8e1f629cfe1db985809639c2cd1de88db119544144740d968d0b6784a9d6f'
root=Path('/lab');root.mkdir(exist_ok=True)
image=root/'openwrt.img'
if not image.exists():
    archive=root/'openwrt.img.gz'
    subprocess.run(['curl','-fSL','--max-time','120','-o',str(archive),URL],check=True)
    payload=archive.read_bytes()
    if hashlib.sha256(payload).hexdigest()!=SHA256:raise SystemExit('Image checksum mismatch')
    decoder=zlib.decompressobj(16+zlib.MAX_WBITS)
    image.write_bytes(decoder.decompress(payload)+decoder.flush())
    if not decoder.eof:raise SystemExit('Truncated gzip stream')
    if decoder.unused_data:print('Verified upstream archive contains trailing bytes after gzip stream.',flush=True)
args=['qemu-system-x86_64','-accel','tcg,tb-size=128','-m','256','-smp','1','-display','none','-monitor','none','-qmp','unix:/lab/qmp.sock,server=on,wait=off',
      '-serial','tcp:127.0.0.1:4555,server=on,wait=off','-drive','file='+str(image)+',format=raw,if=virtio',
      '-netdev','user,id=lan,net=192.168.1.0/24,host=192.168.1.2,restrict=on,hostfwd=tcp:127.0.0.1:2222-192.168.1.1:22',
      '-device','virtio-net-pci,netdev=lan','-netdev','user,id=wan,net=10.0.3.0/24','-device','virtio-net-pci,netdev=wan']
if '--direct-kernel' in sys.argv:
    kernel=root/'openwrt-kernel.bin'
    if not kernel.exists():
        subprocess.run(['curl','-fSL','--max-time','120','-o',str(kernel),'https://downloads.openwrt.org/releases/21.02.7/targets/x86/64/openwrt-21.02.7-x86-64-generic-kernel.bin'],check=True)
    if hashlib.sha256(kernel.read_bytes()).hexdigest()!='4c5a50fe3de95b297308c27cf66a858be98fb14d9d85e8f302fa0f6d302fcfdd':raise SystemExit('Kernel checksum mismatch')
    args += ['-kernel',str(kernel),'-append','root=/dev/vda2 rootwait console=ttyS0,115200 console=tty0 reboot=hard']
os.execvp(args[0],args)
