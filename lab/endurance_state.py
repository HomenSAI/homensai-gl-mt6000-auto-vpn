"""Pure bounded endurance verdict; unfinished or gapped runs cannot pass."""
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
