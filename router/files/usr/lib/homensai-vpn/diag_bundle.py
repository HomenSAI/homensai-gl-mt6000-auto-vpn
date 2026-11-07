# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Masked diagnostic bundle for a support analysis (GL-SENSORS-2026-11-04.ru.md, item 5; GL's export_logs/net_dbg.sh).

`homensai-vpn-diag` (usr/sbin) collects read-only outputs (routes, rules, nft, wg, tc, uci of the VPN policy and of
this app, logread lines, crash log, our status files), masks every secret line by line (keys, passwords, tokens,
Wi-Fi keys and names, endpoints, exit address, user names, chat ids; WireGuard keys, Telegram bot tokens, free-text
password=/token=/psk= values, every public IPv4 (stable label pub-xxxxxx), IPv6 addresses and the last three octets of
MAC addresses anywhere) and packs /tmp/homensai-vpn-diag.tar.gz (mode 0600). The GL download whitelist
/usr/share/gl-download.d/homensai-vpn lets the logged-in GL page download exactly that file. Nothing is uploaded or
sent anywhere, nothing on the router is changed. The Lua twin (lua/diag_bundle.lua) is the one the CLI runs; this one
is the fallback without Lua. Shared masking cases: router/tests/gl_sensors_cases.json.
"""
import os
import re
import shutil
import subprocess
import tarfile
import tempfile

OUTPUT='/tmp/homensai-vpn-diag.tar.gz'
LIMIT=2*1024*1024
MASK='***'
SECRET_PARTS=('private','preshared','password','passwd','passphrase','secret','token','psk','key','auth','telegram_chat',
              'endpoint','exit_ip','ssid','bssid','user','login','cookie','bearer','chat','description','comment','label',
              'session_id','sessionid')
# A public address is replaced by pub-<6 hex of djb2(SALT+address)>: the same address keeps the same label in every file
# of one bundle, so routes, rules and status still correlate; collect() draws a fresh SALT per bundle.
SALT=''
# F-14 (owner decision 07.11.2026): the stored Telegram recipient and bot token never reach the bundle in full, also
# where no key name or "chat id" prefix marks them (a bare id in a log line). collect() reads them once per bundle
# (read_known) and every occurrence becomes *** before the other rules run; restored afterwards like SALT.
KNOWN=()
KNOWN_OPTIONS=('telegram_chat','telegram_token')
# whole names that are secrets although no secret word is inside (URL signature, session id, one-time code)
EXACT_SECRET=('sig','sid','signature','otp','jwt')
WG_NAMES=('private key','preshared key','public key','peer','endpoint')
UCI_SHOW=re.compile(r'^([A-Za-z0-9_.@\[\]-]+)\.([A-Za-z0-9_]+)=(.*)$')
UCI_FILE=re.compile(r'^(\s*(?:option|list)\s+)([^\s]+)(\s+)(.*)$')
JSON_PAIR=re.compile(r'"([A-Za-z0-9_-]+)"(\s*:\s*)"([^"]*)"')
JSON_NUMBER=re.compile(r'"([A-Za-z0-9_-]+)"(\s*:\s*)(-?[0-9]{5,})(?![0-9.])')
FREE_PAIR=re.compile(r'([A-Za-z0-9_.@\[\]-]+)(\s*=\s*)([\'"]?)([^\s&"\',;]+)')
CHAT_ID=re.compile(r'(chat[_ ]?id)(\s*[=:]?\s*)(-?[0-9]{5,})',re.I)
SSID_TEXT=re.compile(r"(ssid)(\s+)'[^']*'",re.I)
IPV4=re.compile(r'(?<![0-9.])([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})(?![0-9])(?!\.[0-9])')
IPV6=re.compile(r'[0-9A-Fa-f:]+')
WG_LINE=re.compile(r'^(\s*)([A-Za-z ]+):(\s+)(.+)$')
B64=re.compile(r'[A-Za-z0-9+/]+=')
TOKEN=re.compile(r'[0-9]+:[A-Za-z0-9_-]+')
MAC=re.compile(r'[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]:[0-9A-Fa-f][0-9A-Fa-f]')

COMMANDS=(
    ('system.txt',('cat','/etc/openwrt_release','/etc/glversion','/proc/uptime','/proc/loadavg')),
    ('package.txt',('cat','/usr/lib/opkg/info/homensai-auto-vpn.control')),
    ('memory.txt',('free',)),
    ('ip-rule.txt',('ip','-4','rule','show')),
    ('ip-route.txt',('ip','-4','route','show','table','all')),
    ('ip-addr.txt',('ip','-4','addr','show')),
    ('nft.txt',('nft','list','ruleset')),
    ('iptables-mangle.txt',('iptables-save','-t','mangle')),
    ('wg.txt',('wg','show','all')),
    ('tc.txt',('tc','-s','qdisc','show')),
    ('uci-route_policy.txt',('uci','show','route_policy')),
    ('uci-network.txt',('uci','show','network')),
    ('uci-homensai_vpn.txt',('uci','show','homensai_vpn')),
    ('uci-gl_timer.txt',('uci','show','gl_timer')),
    ('uci-kmwan.txt',('uci','show','kmwan')),
    ('kmwan.txt',('cat','/proc/gl-kmwan/config')),
    ('repeater.txt',('ubus','call','repeater','status')),
    ('logread-homensai.txt',('logread','-e','homensai')),
    ('logread-wireguard.txt',('logread','-e','wireguard')),
    ('dmesg.txt',('dmesg',)),
    ('crash_log.txt',('cat','/tmp/log/crash_log')),
    ('status.json',('cat','/var/run/homensai-vpn/status.json')),
    ('native-status.json',('cat','/var/run/homensai-vpn/native-status.json')),
    ('wg-events.log',('cat','/var/run/homensai-vpn/wg-events.log')),
    ('service-run.json',('cat','/etc/homensai-vpn/service-run.json')),
    ('boot-resume.json',('cat','/var/run/homensai-vpn/boot-resume.json')),
    ('lua-monitor-crashes.json',('cat','/var/run/homensai-vpn/lua-monitor-crashes.json')),
)


def secret_name(name):
    lowered=name.lower()
    return lowered in EXACT_SECRET or any(part in lowered for part in SECRET_PARTS)


def _b64(match):
    return '<key>' if len(match.group(0))==44 else match.group(0)


def _token(match):
    digits,rest=match.group(0).split(':',1)
    return '<token>' if 6<=len(digits)<=12 and len(rest)>=30 else match.group(0)


def _json(match):
    if secret_name(match.group(1)):return '"%s"%s"%s"'%(match.group(1),match.group(2),MASK)
    return match.group(0)


def _public(a,b,c,d):
    return not (a==10 or a==127 or a==0 or a>=224 or (a==172 and 16<=b<=31) or (a==192 and b==168)
                or (a==100 and 64<=b<=127) or (a==169 and b==254))


def _label(text):
    h=5381
    for byte in (SALT+text).encode('utf-8'):h=(h*33+byte)&0xFFFFFFFF
    return 'pub-%06x'%(h&0xFFFFFF)


def _ipv4(match):
    parts=[int(x) for x in match.groups()]
    if max(parts)>255 or not _public(*parts):return match.group(0)
    return _label(match.group(0))


def _ipv6(match):
    token=match.group(0)
    if '::' not in token and token.count(':')!=7:return token
    if token in ('::','::1') or token.lower().startswith('ff0'):return token
    return '<ipv6>'


def _free(match):
    name,eq,quote,value=match.groups()
    if not secret_name(name.rsplit('.',1)[-1]) or value==MASK:return match.group(0)
    return name+eq+quote+MASK


def _number(match):
    if secret_name(match.group(1)):return '"%s"%s"%s"'%(match.group(1),match.group(2),MASK)
    return match.group(0)


def known_values(values):
    """The stored secrets worth masking verbatim: Telegram destinations (numeric id, @name) and bot tokens, longest first."""
    found=set()
    for value in values:
        value=value.strip() if isinstance(value,str) else ''
        if re.fullmatch(r'-?[0-9]{5,20}|@[A-Za-z][A-Za-z0-9_]{4,31}|[0-9]{6,15}:[A-Za-z0-9_-]{30,100}',value):found.add(value)
    return tuple(sorted(found,key=lambda v:(-len(v),v)))


def read_known():
    """telegram_chat and telegram_token from uci (read only); nothing when uci is missing or refuses."""
    values=[]
    for option in KNOWN_OPTIONS:
        try:
            result=subprocess.run(['uci','-q','get','homensai_vpn.main.'+option],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=5)
            values.append(result.stdout.decode('utf-8','replace') if result.returncode==0 else '')
        except (OSError,subprocess.SubprocessError):values.append('')
    return known_values(values)


def mask_line(line):
    for value in KNOWN:line=line.replace(value,MASK)
    found=UCI_SHOW.match(line)
    if found and secret_name(found.group(2)):line='%s.%s=%s'%(found.group(1),found.group(2),"'"+MASK+"'")
    else:
        found=UCI_FILE.match(line)
        if found and secret_name(found.group(2)):line=found.group(1)+found.group(2)+found.group(3)+"'"+MASK+"'"
        else:
            found=WG_LINE.match(line)
            if found and found.group(2).strip().lower() in WG_NAMES:line=found.group(1)+found.group(2)+':'+found.group(3)+MASK
    line=JSON_PAIR.sub(_json,line)
    line=JSON_NUMBER.sub(_number,line)
    line=FREE_PAIR.sub(_free,line)
    line=CHAT_ID.sub(lambda m:m.group(1)+m.group(2)+MASK,line)
    line=SSID_TEXT.sub(lambda m:m.group(1)+m.group(2)+"'"+MASK+"'",line)
    line=B64.sub(_b64,line)
    line=TOKEN.sub(_token,line)
    line=IPV4.sub(_ipv4,line)
    line=IPV6.sub(_ipv6,line)
    line=MAC.sub(lambda m:m.group(0)[:8]+':xx:xx:xx',line)
    return line


def mask(text):
    return '\n'.join(mask_line(line) for line in text.split('\n'))


def collect(output=OUTPUT,work=None,commands=COMMANDS,run=None,known=None):
    """Collect, mask and pack; returns the archive path. Never changes the router.

    Everything is written inside one private folder (mode 0700): a fresh unique one beside the output, or `work` when
    given, created exclusively (an existing path or a planted symlink is an error, never reused). The archive is built
    there, verified, then published by one rename(2) onto `output`, which replaces a symlink itself instead of following
    it; an output that is a symlink or a folder is refused. On any failure nothing is left behind (R3-01)."""
    def default_run(argv):
        try:
            result=subprocess.run(list(argv),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=5)
            return result.stdout[:LIMIT].decode('utf-8','replace')
        except (OSError,subprocess.SubprocessError) as error:
            return 'unavailable: %s\n'%type(error).__name__
    # the stored recipient/token: read from uci with the real collector; a test collector passes them (or nothing)
    if known is None:known=read_known() if run is None else ()
    run=run or default_run
    global SALT,KNOWN
    previous,SALT=SALT,os.urandom(8).hex()
    previous_known,KNOWN=KNOWN,known_values(known)
    try:return _collect(output,work,commands,run)
    finally:SALT,KNOWN=previous,previous_known


def _collect(output,work,commands,run):
    if work is None:private=tempfile.mkdtemp(prefix=os.path.basename(output)+'.',dir=os.path.dirname(output) or '.')
    else:
        os.mkdir(work,0o700)  # exclusive: raises when anything (a folder, a file, a symlink) is already there
        private=work
    try:
        os.chmod(private,0o700)
        folder=os.path.join(private,'homensai-vpn-diag')
        os.mkdir(folder,0o700)
        for name,argv in commands:
            path=os.path.join(folder,name)
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
            with open(fd,'w',encoding='utf-8') as handle:handle.write(mask(run(argv)))
        temporary=os.path.join(private,'bundle.tar.gz')
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,'O_NOFOLLOW',0),0o600)
        with open(fd,'wb') as raw,tarfile.open(fileobj=raw,mode='w:gz') as archive:archive.add(folder,arcname='homensai-vpn-diag')
        with tarfile.open(temporary,'r:gz') as archive:
            if 'homensai-vpn-diag' not in archive.getnames():raise OSError('DIAG-BUNDLE-UNVERIFIED')
        os.chmod(temporary,0o600)
        if os.path.islink(output) or os.path.isdir(output):raise OSError('DIAG-BUNDLE-UNSAFE-OUTPUT')
        os.replace(temporary,output)
    finally:shutil.rmtree(private,ignore_errors=True)
    return output


if __name__=='__main__':
    print(collect())
