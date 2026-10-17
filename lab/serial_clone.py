"""Bounded serial commands only inside the marked isolated QEMU copy."""
import json
from pathlib import Path
import re
import shlex
import socket
import time
import uuid


def require_clone():
    path=Path('/lab/HOMENSAI_ALPHA7_CLONE')
    if not path.is_file() or path.is_symlink() or json.loads(path.read_text()).get('scope')!='isolated-alpha7-copy':
        raise RuntimeError('CLONE-MARKER-REQUIRED')


def run(command,timeout=15):
    require_clone()
    if not isinstance(command,str) or len(command.encode())>32768 or not 1<=timeout<=120:
        raise ValueError('CLONE-COMMAND-BOUNDS')
    marker='CLONE_DONE_'+uuid.uuid4().hex;path='/tmp/'+marker.lower()
    with socket.create_connection(('127.0.0.1',4555),timeout=3) as sock:
        sock.settimeout(.3);sock.sendall(b'\nstty -echo\n');time.sleep(.2)
        try:sock.recv(65536)
        except socket.timeout:pass
        lines=['umask 077; : > '+path]
        lines.extend("printf '%s' "+shlex.quote(command[i:i+120])+' >> '+path for i in range(0,len(command),120))
        lines.append('sh '+path+'; rc=$?; rm -f '+path+"; printf '\\n"+marker+":%s\\n' \"$rc\"; stty echo")
        for line in lines:sock.sendall((line+'\n').encode());time.sleep(.02)
        data=b'';until=time.monotonic()+timeout
        while time.monotonic()<until:
            try:data+=sock.recv(65536)
            except socket.timeout:continue
            if len(data)>1024*1024:raise RuntimeError('CLONE-OUTPUT-LIMIT')
            match=re.search(rb'\r?\n'+marker.encode()+rb':(\d+)\r?\n',data)
            if match:
                if int(match.group(1)):
                    error=RuntimeError('CLONE-GUEST-COMMAND-FAILED')
                    error.output=data[:match.start()].decode(errors='replace').replace('\r','')
                    raise error
                return data[:match.start()].decode(errors='replace').replace('\r','')
        raise TimeoutError('CLONE-SERIAL-TIMEOUT')


def json_command(code,timeout=15):
    output=run('python3 -c '+shlex.quote(code),timeout)
    for line in reversed(output.splitlines()):
        if line.startswith('CLONE_JSON:'):return json.loads(line[len('CLONE_JSON:'):])
    raise ValueError('CLONE-JSON-MISSING')
