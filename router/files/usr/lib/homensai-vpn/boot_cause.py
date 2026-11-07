# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Why the previous boot ended: kernel crash, planned reboot, plain reboot or power cut (GL-SENSORS-2026-11-04.ru.md, item 5).

Kernel crash. GL loads mtdoops (gl_logread, START=01: panic records go straight to the MTD partition 'log') and
gl_crash_log (START=99) merges /sys/fs/pstore/dmesg-ramoops-* into that partition at boot, DELETES pstore and writes
/tmp/log/crash_log = `strings` of the whole partition (old records included). Our service is also START=99; procd
runs the S* scripts one after another in name order, so S99gl_crash_log has finished before S99homensai-vpn starts.
Evidence, in order: a dmesg-ramoops-* file still in pstore (gl_crash_log missing or later) -> crash; otherwise the
crash_log fingerprint (length and a 32-bit hash) differs from the one remembered at the previous boot -> crash (a new
record was merged or written by mtdoops); no remembered fingerprint (first boot after install) -> unknown; an empty
log after a firmware upgrade (one_click_upgrade erases the partition) -> none. The fingerprint is remembered in
PERSIST/boot-cause.json (one small write per boot, only when it changed) and refreshed once later in the boot
(refresh), so a merge that ran after our start is never mistaken for the next boot's crash.
Planned reboot. GL's timer turns gl_timer.reboot (enable, hour, min, week) into the crontab line
`$min $hour * * $week reboot` (init.d/gl_timer:75-87). A reboot runs the init scripts' shutdown -> our stop_service,
which asks `lua boot_cause.lua shutdown-reason` and stores reason planned-reboot (the schedule matches the local time
within MATCH_MINUTES) or reboot in service-run.json; interruption.classify reports RESTART-PLANNED-REBOOT for it.
Lua twin: lua/boot_cause.lua (shared cases router/tests/gl_sensors_cases.json).
"""
import json
import os
import re

STATE='boot-cause.json'
CRASH_LOG='/tmp/log/crash_log'
PSTORE='/sys/fs/pstore'
MATCH_MINUTES=3
LIMIT=1024*1024
RAMOOPS=re.compile(r'^dmesg-ramoops-[0-9]+$')


def fingerprint(data):
    """'' for no log; otherwise '<length>:<hash>' (h = h*31 + byte mod 2^32, the same in Lua's doubles)."""
    if not data:return ''
    if isinstance(data,str):data=data.encode('latin-1','replace')
    h=0
    for b in data:h=(h*31+b)%4294967296
    return '%d:%08x'%(len(data),h)


def crash_evidence(pstore_names,crash_data,remembered):
    """('crash' | 'none' | 'unknown', current fingerprint)."""
    fp=fingerprint(crash_data)
    if any(isinstance(n,str) and RAMOOPS.match(n) for n in pstore_names or []):return 'crash',fp
    if not isinstance(remembered,str):return 'unknown',fp
    if fp!='' and fp!=remembered:return 'crash',fp
    return 'none',fp


def _int(value):
    if isinstance(value,str) and re.fullmatch(r'[0-9]{1,2}',value):return int(value)
    return None


def planned(timer,wday,hour,minute):
    """gl_timer.reboot matches the local time: enabled, today in `week` (cron 0 = Sunday), 0..MATCH_MINUTES after."""
    if not isinstance(timer,dict) or timer.get('enable')!='1':return False
    h,m=_int(timer.get('hour')),_int(timer.get('min'))
    week=timer.get('week')
    if h is None or m is None or not isinstance(week,str):return False
    days=set()
    for part in week.replace(',',' ').split():
        value=_int(part)
        if value is None:return False
        days.add(7 if value==0 else value)  # cron accepts 0 and 7 for Sunday
    today=7 if wday==0 else wday
    if today not in days:return False
    delta=hour*60+minute-(h*60+m)
    return 0<=delta<=MATCH_MINUTES


def shutdown_reason(timer,wday,hour,minute):
    return 'planned-reboot' if planned(timer,wday,hour,minute) else 'reboot'


def _read(path,limit=LIMIT):
    try:
        with open(path,'rb') as handle:return handle.read(limit)
    except OSError:return None


def evaluate(persist,pstore=PSTORE,crash_log=CRASH_LOG,write=None):
    """The crash verdict of the boot that ended; remembers the current fingerprint. Never raises."""
    try:names=os.listdir(pstore)
    except OSError:names=[]
    try:
        remembered=json.loads((_read(os.path.join(str(persist),STATE)) or b'null').decode('utf-8')).get('crash_fp')
    except (ValueError,AttributeError,UnicodeDecodeError):remembered=None
    verdict,fp=crash_evidence(names,_read(crash_log),remembered)
    if fp!=remembered:
        try:
            if write is not None:write(os.path.join(str(persist),STATE),{'crash_fp':fp})
        except (OSError,ValueError):pass
    return verdict


def refresh(persist,crash_log=CRASH_LOG,write=None):
    """Later in the same boot: remember a crash_log that changed after our start (no new crash can appear meanwhile
    without a reboot). Returns True when it wrote."""
    try:
        remembered=json.loads((_read(os.path.join(str(persist),STATE)) or b'null').decode('utf-8')).get('crash_fp')
    except (ValueError,AttributeError,UnicodeDecodeError):return False
    fp=fingerprint(_read(crash_log))
    if not isinstance(remembered,str) or fp==remembered:return False
    try:
        if write is not None:write(os.path.join(str(persist),STATE),{'crash_fp':fp});return True
    except (OSError,ValueError):pass
    return False
