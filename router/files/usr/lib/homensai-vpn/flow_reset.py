"""HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE.

flow_reset.py: after a verified move of the LAN traffic from one channel to the other, drop the LAN flows that are
still source-NATed to the channel left, so applications reconnect at once. Twin of lua/flow_reset.lua; the cases in
tests/flow_reset_cases.json are shared by both. The full reasoning is in the Lua module's header; in short:
GL marks TCP packets per packet (ctmark stays 0x0), so after the move an old TCP flow leaves through the new tunnel
with the OLD tunnel's NAT address and hangs until the application's timeout. One bounded command drops exactly the
masqueraded flows whose reply destination is the old tunnel's address:
    conntrack -D -f ipv4 --reply-dst <old address> --src-nat
The router's own (not NATed) flows, inbound flows and the new tunnel's flows are never matched. Routing and the
VPN-only guard are untouched. `option flow_reset '0'` turns it off; no config file -> nothing runs.
The codes (FLOW-RESET-*) are written to the system log; the FLOW-RESET- family row of the page's error table explains them.
"""
import re
import subprocess

CONFIG='/etc/config/homensai_vpn'
TIMEOUT=1
PREFIX='FLOW-RESET-'
# The full codes, written literally (the FLOW-RESET- family row of router/error_rows_extra.inc.js covers them).
OFF,DONE,NONE,NO_TOOL,NO_ADDRESS,SAME_ADDRESS,TIMEOUT_CODE,FAILED=(
    'FLOW-RESET-OFF','FLOW-RESET-DONE','FLOW-RESET-NONE','FLOW-RESET-NO-TOOL','FLOW-RESET-NO-ADDRESS',
    'FLOW-RESET-SAME-ADDRESS','FLOW-RESET-TIMEOUT','FLOW-RESET-FAILED')
_QUAD=re.compile(r'([0-9]+)\.([0-9]+)\.([0-9]+)\.([0-9]+)')  # ASCII digits, as Lua %d


def enabled(text):
    if not isinstance(text,str):return False
    return not any(re.fullmatch(r"\s*option\s+flow_reset\s+'?0'?\s*",line) for line in text.split('\n'))


def ipv4(text):
    if not isinstance(text,str) or len(text)>15:return None
    match=_QUAD.fullmatch(text)
    if not match:return None
    parts=match.groups()
    if any(len(p)>1 and p[0]=='0' for p in parts):return None
    numbers=[int(p) for p in parts]
    if any(n>255 for n in numbers) or numbers[0] in (0,127) or numbers[0]>=224:return None
    return text


def address(status):
    if not isinstance(status,dict) or status.get('up') is not True:return None
    rows=status.get('ipv4-address')
    if not isinstance(rows,list):return None
    for row in rows:
        if isinstance(row,dict):
            found=ipv4(row.get('address'))
            if found:return found
    return None


def argv(old):
    return ['conntrack','-D','-f','ipv4','--reply-dst',old,'--src-nat']


def outcome(rc,out,timed_out):
    deleted=sum(1 for line in (out if isinstance(out,str) else '').split('\n') if line.strip())
    if timed_out or rc in (124,143,137):return TIMEOUT_CODE,deleted
    if rc in (126,127):return NO_TOOL,0
    if rc==0:return DONE,deleted
    if rc==1 and deleted==0:return NONE,0
    return FAILED,deleted


def run(ctx):
    """ctx: config (text|None), old_status/new_status (netifd status|None), exec(argv)->(rc,stdout,timed_out), log(line)."""
    result={'code':OFF,'deleted':0,'address':None}
    if not enabled(ctx.get('config')):return result
    old,new=address(ctx.get('old_status')),address(ctx.get('new_status'))
    result['address']=old
    deleted=0
    if not old or not new:code=NO_ADDRESS
    elif old==new:code=SAME_ADDRESS
    else:
        try:rc,out,timed_out=ctx['exec'](argv(old));code,deleted=outcome(rc,out,timed_out)
        except Exception:code=FAILED  # never a switch failure
    result.update(code=code,deleted=deleted)
    log=ctx.get('log')
    if log:
        try:log('%s: address %s deleted %d'%(result['code'],old or 'none',deleted))
        except Exception:pass
    return result


def execute(args):
    """The router side of ctx.exec: stdout only, bounded by TIMEOUT (a missing tool is rc 127, as under the shell)."""
    try:
        done=subprocess.run(args,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=TIMEOUT)
    except subprocess.TimeoutExpired as error:
        out=error.stdout or b''
        return 124,out.decode('utf8','replace'),True
    except FileNotFoundError:
        return 127,'',False
    return done.returncode,done.stdout.decode('utf8','replace'),False


def read_config():
    try:
        with open(CONFIG,encoding='utf8') as stream:return stream.read()
    except (OSError,UnicodeError):return None
