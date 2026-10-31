# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""Auto that the owner switched on comes back by itself after a power cut or reboot.

Owner decision 31.10.2026 (soak trial: after sysrq-b Auto stayed off, the tunnels down and the LAN without
internet until somebody pressed Start). The owner's own Start leaves a durable marker on flash
(auto-resume.json); Stop and every give-up leave the stop latch native-stop.json, which is newer and wins.
After a boot the monitor presses Start once for the owner, with the same request and every check Start has
(journal, preparation, pair state): nothing else is bypassed. Programmatic and test starts leave no marker.

Owner decision extension 31.10.2026 (soak: kill -9 of the idle supervisor; procd restarted it, its recovery
revoked the intent and Auto stayed off until somebody pressed Start): an unintended supervisor restart without a
reboot is treated like a power cut. Every supervisor start that finished its recovery writes a fresh token (RAM
supervisor-start.json); a token this monitor has not handled yet starts the same resume once more - the same
marker/stop-latch decision (a deliberate Stop or give-up is newer and wins), every Start check, the monotonic
window - bounded to RESTART_LIMIT resumes per RESTART_WINDOW against a crash loop.

Lua counterpart: lua/boot_resume.lua (same marker, same decision, same state file).
"""
import json
import threading
import time

MARKER='auto-resume.json'
STATE='boot-resume.json'
WINDOW=600        # at least this many seconds after the first attempt
UNTIL_UPTIME=900  # and never before 15 min of uptime (the supervisor settles a held journal after the tunnels are up)
EVERY=15
BOOT_AGE=900
SUPERVISOR='supervisor-start.json'  # runtime: {"id":<hex32>,"time":} written by each supervisor start after recovery
RESTART_LIMIT=3     # resumes after supervisor restarts within RESTART_WINDOW (monotonic seconds)
RESTART_WINDOW=900
FINAL={'JOURNAL-INTEGRITY-FAILED'}


def remember(persist=None,now=None):
    from agent import PERSIST,atomic_json
    atomic_json((persist or PERSIST)/MARKER,{'enabled':True,'time':float(time.time() if now is None else now),'request_source':'manual'})


def wanted(persist=None):
    from agent import PERSIST,read_json
    persist=persist or PERSIST
    try:marker=read_json(persist/MARKER,None)
    except (OSError,ValueError):return False,'AUTO-RESUME-MARKER-INVALID'
    if marker is None:return False,'AUTO-RESUME-NOT-REQUESTED'
    at=marker.get('time') if isinstance(marker,dict) and marker.get('enabled') is True else None
    if type(at) not in (int,float):return False,'AUTO-RESUME-MARKER-INVALID'
    try:latch=read_json(persist/'native-stop.json',None)
    except (OSError,ValueError):return False,'AUTO-RESUME-STOP-UNREADABLE'
    if latch is not None:
        stopped=latch.get('requested') if isinstance(latch,dict) else None
        if type(stopped) not in (int,float) or stopped>=at:return False,'AUTO-RESUME-STOPPED'
    return True,None


def token(runtime=None):
    """The id of the supervisor start that finished its recovery, or None."""
    from agent import RUNTIME,read_json
    try:row=read_json((runtime or RUNTIME)/SUPERVISOR,None)
    except (OSError,ValueError):return None
    value=row.get('id') if isinstance(row,dict) else None
    return value if isinstance(value,str) and len(value)==32 and all(c in '0123456789abcdef' for c in value) else None


def write_token(runtime=None):
    """Called by the supervisor once its recovery is done (the intent fence is behind it)."""
    import uuid
    from agent import RUNTIME,atomic_json
    try:atomic_json((runtime or RUNTIME)/SUPERVISOR,{'id':uuid.uuid4().hex,'time':time.time()})
    except (OSError,ValueError):pass


def _publish(runtime,state,code,attempts,trigger='boot',supervisor=None):
    from agent import atomic_json
    try:atomic_json(runtime/STATE,{'state':state,'code':code,'attempts':attempts,'time':time.time(),
                                   'trigger':trigger,'supervisor':supervisor})
    except (OSError,ValueError):pass


def _resume(runtime,persist,sleep,clock,deadline_after,trigger):
    """The resume itself: marker/latch decision, then Start with every check until RESUMED or the window ends."""
    handled=[token(runtime)]
    def publish(state,code,attempts):
        current=token(runtime)
        if current is not None:handled[0]=current  # a supervisor restart during this run is served by this run
        _publish(runtime,state,code,attempts,trigger,handled[0])
    ok,reason=wanted(persist)
    if not ok:publish('SKIPPED',reason,0);return 'SKIPPED',handled[0]
    from auto_control import start,current_revision
    from pair_auto import intent
    first=clock();attempts=0;code=None
    deadline=first+deadline_after
    while True:
        try:
            if intent().get('mode')=='on':
                state='RESUMED' if attempts else 'RUNNING';publish(state,None,attempts);return state,handled[0]
        except (OSError,ValueError):pass
        if clock()>deadline:publish('FAILED',code or 'AUTO-RESUME-TIMEOUT',attempts);return 'FAILED',handled[0]
        attempts+=1
        try:reply=start(control_revision=current_revision(),request_source='programmatic')
        except Exception:reply={'accepted':False,'blockers':['AUTO-RESUME-UNCONFIRMED']}
        if isinstance(reply,dict) and reply.get('accepted'):publish('RESUMED',None,attempts);return 'RESUMED',handled[0]
        code=(reply.get('blockers') or ['AUTO-RESUME-UNCONFIRMED'])[0] if isinstance(reply,dict) else 'AUTO-RESUME-UNCONFIRMED'
        if code in FINAL:publish('FAILED',code,attempts);return 'FAILED',handled[0]
        publish('WAITING',code,attempts)
        sleep(EVERY)


def run(runtime=None,persist=None,sleep=time.sleep,uptime=None,clock=time.monotonic):
    """Once per boot (the RAM state file marks it); returns the final state.

    The window and the pacing use the monotonic clock: the router has no RTC and NTP steps the wall clock
    forward right after the boot. time.time() is only the published time.
    """
    return _boot(runtime,persist,sleep,uptime,clock)[0]


def _boot(runtime,persist,sleep,uptime,clock):
    """-> (state or None, the supervisor token already handled)."""
    from agent import RUNTIME,read_json
    runtime=runtime or RUNTIME
    if uptime is None:
        try:uptime=float(open('/proc/uptime').read().split()[0])
        except (OSError,ValueError,IndexError):uptime=float('inf')
    if (runtime/STATE).exists():
        try:row=read_json(runtime/STATE,{})
        except (OSError,ValueError):row={}
        return None,row.get('supervisor') if isinstance(row,dict) else None
    if uptime>BOOT_AGE:return None,token(runtime)
    return _resume(runtime,persist,sleep,clock,max(WINDOW,UNTIL_UPTIME-uptime),'boot')


def watch(runtime=None,persist=None,sleep=time.sleep,clock=time.monotonic,handled=None,rounds=None):
    """Resume once for every supervisor start not handled yet (bounded); rounds limits the loop in tests."""
    from agent import RUNTIME
    runtime=runtime or RUNTIME
    restarts=[];count=0
    while rounds is None or count<rounds:
        count+=1
        sleep(EVERY)
        current=token(runtime)
        if current is None or current==handled:continue
        handled=current
        now=clock();restarts=[t for t in restarts if now-t<RESTART_WINDOW]
        if len(restarts)>=RESTART_LIMIT:
            _publish(runtime,'FAILED','AUTO-RESUME-RESTART-LIMIT',0,'supervisor-restart',handled);continue
        restarts.append(now)
        _,handled=_resume(runtime,persist,sleep,clock,WINDOW,'supervisor-restart')


def _thread_main():
    _,handled=_boot(None,None,time.sleep,None,time.monotonic)
    watch(handled=handled)


def start_thread():
    thread=threading.Thread(target=_thread_main,name='boot-resume',daemon=True);thread.start();return thread
