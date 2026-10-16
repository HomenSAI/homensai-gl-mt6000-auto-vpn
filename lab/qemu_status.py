"""Read QEMU state through the private lab-only QMP socket."""
import json
import socket
import sys
with socket.socket(socket.AF_UNIX) as sock:
    sock.settimeout(5);sock.connect('/lab/qmp.sock');stream=sock.makefile('rwb',buffering=0)
    print(json.loads(stream.readline()))
    for name in ('qmp_capabilities','query-status','screendump') if '--screen' in sys.argv else ('qmp_capabilities','query-status'):
        request={'execute':name}
        if name=='screendump':request['arguments']={'filename':'/lab/guest-screen.ppm'}
        stream.write((json.dumps(request)+'\n').encode())
        while True:
            value=json.loads(stream.readline())
            if 'return' in value or 'error' in value:print(value);break
