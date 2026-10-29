"""Disposable OpenWrt TCG, private serial, no TAP/bridge/host network changes."""
import hashlib,os,shutil,subprocess,zlib
from pathlib import Path
from qa_config import QEMU_ROOT as root,SERIAL_PORT
archive=root/'openwrt.img.gz';kernel=root/'openwrt-kernel.bin';image=root/'openwrt.img'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='39f8e1f629cfe1db985809639c2cd1de88db119544144740d968d0b6784a9d6f'
assert hashlib.sha256(kernel.read_bytes()).hexdigest()=='4c5a50fe3de95b297308c27cf66a858be98fb14d9d85e8f302fa0f6d302fcfdd'
if not image.exists():
    decoder=zlib.decompressobj(16+zlib.MAX_WBITS);image.write_bytes(decoder.decompress(archive.read_bytes())+decoder.flush());assert decoder.eof
toolroot=root/'root'
extracted=toolroot/'usr/bin/qemu-system-x86_64'
executable=str(extracted) if extracted.is_file() else shutil.which('qemu-system-x86_64')
if not executable:raise RuntimeError('qemu-system-x86_64 is required; provide it without installing product packages')
environment=dict(os.environ)
if extracted.is_file():environment.update(LD_LIBRARY_PATH=str(toolroot/'usr/lib/x86_64-linux-gnu'),QEMU_MODULE_DIR=str(toolroot/'usr/lib/x86_64-linux-gnu/qemu'))
firmware=['-L',str(toolroot/'usr/share/qemu'),'-bios',str(toolroot/'usr/share/seabios/bios-256k.bin')] if extracted.is_file() else []
argv=[executable]+firmware+['-accel','tcg,tb-size=128','-m','256','-smp','1',
      '-vga','none','-display','none','-monitor','none','-qmp','unix:'+str(root/'qmp.sock')+',server=on,wait=off',
      '-serial','tcp:127.0.0.1:%d,server=on,wait=off'%SERIAL_PORT,'-drive','file='+str(image)+',format=raw,if=virtio',
      '-netdev','user,id=lan,net=192.168.1.0/24,restrict=on','-device','virtio-net-pci,netdev=lan,romfile=' ,
      '-netdev','user,id=wan,net=10.0.3.0/24','-device','virtio-net-pci,netdev=wan,romfile=' ,
      '-kernel',str(kernel),'-append','root=/dev/vda2 rw rootwait console=ttyS0,115200 console=tty0 reboot=hard']
(root/'qemu-pid.txt').write_text(str(os.getpid()))
os.execve(argv[0],argv,environment)
