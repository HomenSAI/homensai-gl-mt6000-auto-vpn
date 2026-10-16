"""Serial command helper for the isolated Docker/QEMU laboratory only."""
import argparse
import re
import socket
import time
import uuid

p=argparse.ArgumentParser();p.add_argument('command');p.add_argument('--timeout',type=int,default=60);a=p.parse_args()
marker='LAB_DONE_'+uuid.uuid4().hex
with socket.create_connection(('127.0.0.1',4555),timeout=5) as s:
    s.settimeout(.5);s.sendall(b'\n');time.sleep(.5)
    try:s.recv(65536)
    except socket.timeout:pass
    # BusyBox ash's interactive input line is bounded; never paste a long command.
    path='/tmp/'+marker.lower()
    quoted=lambda text: "'"+text.replace("'", "'\"'\"'")+"'"
    lines=["umask 077; : > "+path]
    lines += ["printf '%s' "+quoted(a.command[i:i+120])+" >> "+path for i in range(0,len(a.command),120)]
    lines += ["sh "+path+"; result=$?; rm -f "+path+"; printf '\\n"+marker+":%s\\n' \"$result\""]
    for line in lines:
        s.sendall((line+'\n').encode());time.sleep(.03)
    data=b'';end=time.monotonic()+a.timeout
    while time.monotonic()<end:
        try:data+=s.recv(65536)
        except socket.timeout:continue
        match=re.search(rb'\r?\n'+marker.encode()+rb':(\d+)\r?\n',data)
        if match:
            print(data[:match.start()].decode(errors='replace'))
            raise SystemExit(int(match.group(1)))
    print(data.decode(errors='replace'));raise SystemExit('serial command timeout')
