"""App-owned detail retention; count/byte caps remain independent upper bounds."""
import subprocess
import time

_cached=None

def days(settings):
    raw=settings.get('history_days',7) if isinstance(settings,dict) else 7
    if type(raw) is int and 1<=raw<=7:return raw
    if isinstance(raw,str) and raw in tuple(str(n) for n in range(1,8)):return int(raw)
    return 7

def configured_days():
    global _cached
    now=time.monotonic()
    if _cached and 0<=now-_cached[0]<5:return _cached[1]
    try:
        result=subprocess.run(['uci','-q','get','homensai_vpn.main.history_days'],stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=2)
        value=days({'history_days':result.stdout.decode('ascii').strip()}) if result.returncode==0 else 7
    except (OSError,UnicodeError,subprocess.SubprocessError):value=7
    _cached=(now,value)
    return value
