"""Pure bounded endurance verdict; unfinished or gapped runs cannot pass."""

def container_name(value):
    import re
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}',value):
        raise ValueError('ENDURANCE-CONTAINER-NAME')
    return value
def sample_errors(sample,expected,baseline):
    errors=[]
    if sample.get('version')!=expected['version']:errors.append('VERSION-MISMATCH')
    if sample.get('error') is not None:errors.append('MONITOR-ERROR')
    if type(sample.get('age')) not in (int,float) or not 0<=sample['age']<=90:errors.append('MONITOR-STALE')
    if sample.get('monitor_instances')!=1:errors.append('MONITOR-INSTANCE-COUNT')
    if sample.get('auto_off') is not True:errors.append('AUTO-NOT-OFF')
    for key in ('protected','own_config'):
        if baseline and sample.get(key)!=baseline.get(key):errors.append(key.upper()+'-CHANGED')
    if sample.get('code_hashes')!=expected['code_hashes']:errors.append('INSTALLED-CODE-MISMATCH')
    return errors


def verdict(elapsed,duration,samples,failures,gaps,interval,stopped=False):
    if stopped:return 'STOPPED'
    if elapsed<duration:return 'RUNNING'
    minimum=max(1,int(duration/interval*.9))
    return 'PASS' if samples>=minimum and failures==0 and gaps==0 else 'FAIL'


def slept(previous,current,interval,tolerance=60):
    """Host sleep or a clock jump: wall time advanced much more (or less) than the monotonic clock.

    previous/current are (wall_seconds, monotonic_seconds). A monotonic clock may or may not count time
    asleep, so only the disagreement with the wall clock is trusted, in both directions."""
    wall=current[0]-previous[0];mono=current[1]-previous[1]
    return abs(wall-mono)>tolerance or wall>interval+tolerance


def pid_alive(pid):
    """Liveness of a process without ever signalling it (os.kill(pid,0) would terminate it on Windows)."""
    import os
    if type(pid) is not int or not 0<pid<=4194304:return False  # Linux pid_max is at most 2**22
    if os.name=='nt':
        import ctypes
        kernel=ctypes.windll.kernel32
        handle=kernel.OpenProcess(0x1000,False,pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:return False
        try:
            code=ctypes.c_ulong()
            return bool(kernel.GetExitCodeProcess(handle,ctypes.byref(code))) and code.value==259
        finally:kernel.CloseHandle(handle)
    try:os.kill(pid,0)
    except ProcessLookupError:return False
    except PermissionError:return True
    except (OverflowError,ValueError,OSError):return False
    return True


def producer_lost(alive_history,confirmations=3):
    """A running status whose producer was seen dead several polls in a row is a lost producer, never a pass."""
    return len(alive_history)>=confirmations and not any(alive_history[-confirmations:])
