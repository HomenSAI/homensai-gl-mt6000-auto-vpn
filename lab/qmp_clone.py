"""Private QMP control; mutations require the explicit isolated-copy marker."""
import argparse
import json
from pathlib import Path
import socket

parser=argparse.ArgumentParser();parser.add_argument('action',choices=('status','pause','resume','reset','screen','http-forward','http-unforward'))
args=parser.parse_args()
if args.action!='status':
    marker=Path('/lab/HOMENSAI_ALPHA7_CLONE')
    if not marker.is_file() or marker.is_symlink() or json.loads(marker.read_text()).get('scope')!='isolated-alpha7-copy':
        raise SystemExit('QMP-CLONE-MARKER-REQUIRED')
with socket.socket(socket.AF_UNIX) as sock:
    sock.settimeout(5);sock.connect('/lab/qmp.sock');stream=sock.makefile('rwb',buffering=0)
    greeting=json.loads(stream.readline())
    def call(name,arguments=None):
        row={'execute':name}
        if arguments is not None:row['arguments']=arguments
        stream.write((json.dumps(row)+'\n').encode())
        while True:
            reply=json.loads(stream.readline())
            if 'error' in reply:raise RuntimeError('QMP-COMMAND-REFUSED')
            if 'return' in reply:return reply['return']
    call('qmp_capabilities')
    if args.action in ('http-forward','http-unforward'):
        command='hostfwd_add lan tcp:127.0.0.1:8081-192.168.1.1:80' if args.action=='http-forward' else 'hostfwd_remove lan tcp:127.0.0.1:8081'
        answer=call('human-monitor-command',{'command-line':command})
        if isinstance(answer,str) and ('Error' in answer or 'invalid' in answer.lower()):raise RuntimeError('QMP-LOCAL-HTTP-FORWARD-REFUSED')
    method={'pause':'stop','resume':'cont','reset':'system_reset','screen':'screendump'}.get(args.action)
    if method:call(method,{'filename':'/lab/alpha7-screen.ppm'} if args.action=='screen' else None)
    print(json.dumps({'qemu':greeting['QMP']['version'],'status':call('query-status')}))
