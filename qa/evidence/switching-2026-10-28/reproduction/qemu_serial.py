"""Bounded private-serial commands to disposable QEMU fixture."""
import re,socket,time,uuid
from qa_config import SERIAL_PORT
BASE='test -e /tmp/HOMENSAI_VIRTUAL_LAB || exit 99; . /etc/openwrt_release; [ "$DISTRIB_TARGET" = x86/64 ] || exit 98; '
def execute(command,timeout=30):
    marker=uuid.uuid4().hex;start='QA_BEGIN_'+marker;end='QA_END_'+marker
    data=BASE+command;path='/tmp/qa-serial-'+marker
    with socket.create_connection(('127.0.0.1',SERIAL_PORT),timeout=5)as sock:
        sock.settimeout(.05);sock.sendall(b'\n')
        until=time.monotonic()+.1
        while time.monotonic()<until:
            try:sock.recv(65536)
            except socket.timeout:pass
        quoted=lambda value:"'"+value.replace("'","'\"'\"'")+"'"
        lines=["umask 077; : > "+path]+["printf '%s' "+quoted(data[i:i+120])+" >> "+path for i in range(0,len(data),120)]
        lines.append("printf '\\n"+start+"\\n'; sh "+path+"; result=$?; rm -f "+path+"; printf '\\n"+end+":%s\\n' \"$result\"")
        for line in lines:sock.sendall((line+'\n').encode());time.sleep(.003)
        output=b'';deadline=time.monotonic()+timeout
        regex=re.compile(rb'\r?\n'+start.encode()+rb'\r?\n(.*?)\r?\n'+end.encode()+rb':(\d+)\r?\n',re.S)
        while time.monotonic()<deadline:
            try:output+=sock.recv(65536)
            except socket.timeout:continue
            match=regex.search(output)
            if match:
                value=match[1].decode(errors='replace').replace('\r','')
                if int(match[2]):raise RuntimeError('guest command returned '+match[2].decode()+': '+value)
                return value
        raise TimeoutError('private serial timeout; tail='+output[-300:].decode(errors='replace'))
def upload(path,content):
    encoded=''.join('\\x%02x'%byte for byte in content)
    execute("printf '%b' '"+encoded+"' > '"+path+"'",timeout=45)
