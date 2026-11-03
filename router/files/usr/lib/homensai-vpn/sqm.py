"""HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE. Optional SQM (cake) on the VPN tunnel egress.

Off by default. The owner switches it on with BOTH options (no automatic rate: a wrong rate either throttles the
VPN or shapes nothing; see docs/architecture/MTU-SQM-2026-11-03.ru.md):

    uci set homensai_vpn.main.sqm_enabled='1'
    uci set homensai_vpn.main.sqm_upload_kbit='18000'    # 1000..1000000, about 85-90 % of the measured VPN upload
    uci commit homensai_vpn

Each monitor pass (both runtimes; twin lua/sqm.lua, shared cases tests/sqm_cases.json) reconciles the root qdisc
of every probed tunnel device (wgclient*/ovpnclient*, the device of the route binding):

    tc qdisc replace dev <tunnel> root cake bandwidth <kbit>kbit besteffort triple-isolate nat

Only a root that is the kernel default (handle 0:, e.g. noqueue/fq_codel) or a cake this app put there (recorded
with the device's ifindex in RAM, RUNTIME/sqm-state.json) is ever replaced; any other root qdisc is the owner's or
the firmware's and is left alone (SQM-ROOT-QDISC-BUSY). WAN, LAN and every other device are never touched.
Back to the kernel default (`tc qdisc del dev <tunnel> root`, only where the root is still cake):
  * setting off / rate cleared or changed: the next monitor pass;
  * service stop (also opkg removal and upgrade, whose prerm runs the stop): the init script (sqm_release, from
    the state file) and the Python monitor at its exit;
  * tunnel restart: the recreated device starts with the kernel default by itself; the record is dropped because
    the ifindex changed, and the next pass applies cake again only while the setting is on.
Readings: status['sqm'] = {'enabled','kbit','code','devices': {device: applied|busy|failed|restore-failed}}.
No process is started while SQM is off and nothing is recorded (the default costs nothing).
"""
import re
import subprocess

STATE_NAME='sqm-state.json'
VERIFY=300            # seconds between re-reads of an applied root qdisc
MIN_KBIT=1000
MAX_KBIT=1000000
DEVICE=re.compile(r'^[A-Za-z0-9_.-]{1,15}$')
CODES={'busy':'SQM-ROOT-QDISC-BUSY','failed':'SQM-APPLY-FAILED','restore-failed':'SQM-RESTORE-FAILED'}


def config(settings):
    """(kbit, None) when SQM is on with a valid rate, else (None, SQM-OFF | SQM-BANDWIDTH-UNSET)."""
    if not isinstance(settings,dict) or settings.get('sqm_enabled') is not True:return None,'SQM-OFF'
    kbit=settings.get('sqm_upload_kbit')
    if type(kbit) is not int or not MIN_KBIT<=kbit<=MAX_KBIT:return None,'SQM-BANDWIDTH-UNSET'
    return kbit,None


def cake_argv(device,kbit):
    return ['tc','qdisc','replace','dev',device,'root','cake','bandwidth','%dkbit'%kbit,'besteffort','triple-isolate','nat']


def delete_argv(device):
    return ['tc','qdisc','del','dev',device,'root']


def show_argv(device):
    return ['tc','qdisc','show','dev',device,'root']


def root_qdisc(text):
    """(kind, handle) of the root line of `tc qdisc show dev X root`, or None."""
    if not isinstance(text,str):return None
    for line in text.splitlines():
        fields=line.split()
        if len(fields)>=4 and fields[0]=='qdisc' and 'root' in fields[3:]:return fields[1],fields[2]
    return None


def live_devices(rows):
    """{device: ifindex} of the probed tunnel rows with a kernel binding (first row wins)."""
    live={}
    for row in rows if isinstance(rows,list) else []:
        if not isinstance(row,dict):continue
        device=row.get('device');ifindex=row.get('ifindex')
        if isinstance(device,str) and DEVICE.fullmatch(device) and type(ifindex) is int and ifindex>0 and device not in live:
            live[device]=ifindex
    return live


def records(state):
    """Valid records of the state file: {device: {device, ifindex, kbit, checked}}."""
    result={}
    for row in (state.get('devices') if isinstance(state,dict) and isinstance(state.get('devices'),list) else []):
        if (isinstance(row,dict) and isinstance(row.get('device'),str) and DEVICE.fullmatch(row['device'])
                and type(row.get('ifindex')) is int and row['ifindex']>0 and type(row.get('kbit')) is int
                and type(row.get('checked')) in (int,float)):
            result[row['device']]={key:row[key] for key in ('device','ifindex','kbit','checked')}
    return result


def state_of(kept):
    return {'schema':1,'devices':[kept[name] for name in sorted(kept)]}


def show(device,execute):
    rc,text=execute(show_argv(device))
    return root_qdisc(text) if rc==0 else None


def restore(device,execute):
    """Our cake back to the kernel default; True when no cake is left there (or the device is gone)."""
    root=show(device,execute)
    if root is None or root[0]!='cake':return True
    rc,_=execute(delete_argv(device))
    after=show(device,execute)
    return rc==0 and (after is None or after[0]!='cake')


def sync(settings,rows,state,execute,now):
    """One reconciliation -> (new state, report). execute(argv) -> (rc, text)."""
    kbit,code=config(settings)
    live=live_devices(rows);known=records(state);kept={};devices={}
    for name in sorted(known):
        record=known[name]
        if name not in live:kept[name]=record;continue          # not probed now: decided when it is seen again
        if live[name]!=record['ifindex']:continue                 # recreated: it already has the kernel default
        if kbit is not None and record['kbit']==kbit:kept[name]=record;continue
        if not restore(name,execute):kept[name]=record;devices[name]='restore-failed'
    if kbit is not None:
        for name in sorted(live):
            record=kept.get(name)
            ours=record is not None and record['ifindex']==live[name]
            if ours and record['kbit']==kbit and 0<=now-record['checked']<VERIFY:devices[name]='applied';continue
            root=show(name,execute)
            if root is None:devices[name]='failed';continue
            if ours and root[0]=='cake':
                kept[name]=dict(record,checked=now);devices[name]='applied';continue
            if ours:kept.pop(name,None)                           # replaced by someone else: no longer ours
            if root[1]!='0:':devices[name]='busy';continue      # the owner's or the firmware's own qdisc
            rc,_=execute(cake_argv(name,kbit))
            after=show(name,execute)
            if rc!=0 or after is None or after[0]!='cake':devices[name]='failed';continue
            kept[name]={'device':name,'ifindex':live[name],'kbit':kbit,'checked':now};devices[name]='applied'
    problems=[CODES[devices[name]] for name in sorted(devices) if devices[name] in CODES]
    report={'enabled':isinstance(settings,dict) and settings.get('sqm_enabled') is True,'kbit':kbit,
            'code':problems[0] if problems else code,'devices':devices}
    return state_of(kept),report


def release(state,execute):
    """Service stop: every recorded cake back to the kernel default -> (state of the failures, failed devices)."""
    known=records(state);failed={name:known[name] for name in sorted(known) if not restore(name,execute)}
    return state_of(failed),sorted(failed)


def execute(argv):
    """The router executor: a bounded tc process (rc 127 when tc is missing)."""
    try:
        done=subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=5)
        return done.returncode,done.stdout.decode('utf-8','replace')
    except FileNotFoundError:return 127,''
    except (OSError,subprocess.SubprocessError):return 255,''


def active(settings,state):
    """True when a pass has anything to do (SQM on, or a record to give back): off costs no process."""
    return config(settings)[0] is not None or bool(records(state))
