"""Own monitor lifecycle; never starts an uncertified VPN trial."""
import json
import subprocess
from agent import RUNTIME, inventory, read_json
from auto_control import control_lock
from native_switch import journal_read, Refused

ACTIVE={'OBSERVING','ARMED','APPLYING','WAIT-CLIENT','COMMITTED','HELD-ON-RESERVE','RESTORING'}


def change(arguments):
    if set(arguments)!={'enabled'} or type(arguments['enabled']) is not bool:
        return {'accepted':False,'code':'MONITOR-INVALID'}
    with control_lock():
        settings=inventory().get('settings',{})
        status=read_json(RUNTIME/'native-status.json',{})
        intent=read_json(RUNTIME/'auto-control.json',{})
        try:transaction=journal_read()
        except (Refused,OSError,ValueError):return {'accepted':False,'code':'MONITOR-JOURNAL-UNVERIFIED'}
        if (settings.get('native_enabled') or status.get('state') in ACTIVE
                or (transaction and transaction.get('phase')!='ROLLED-BACK')
                or status.get('state')=='STOPPED-ON-RESERVE' or status.get('guard')=='closed'
                or intent.get('mode')=='on'):
            return {'accepted':False,'code':'MONITOR-STOP-AUTO-FIRST'}
        enabled=arguments['enabled']
        result=subprocess.run(['/usr/bin/lua','/usr/lib/homensai-vpn/setup_save.lua'],
            input=json.dumps({'main':{'enabled':'1' if enabled else '0'},'servers':[]}).encode(),
            stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10)
        if result.returncode or result.stdout.strip()!=b'OK':
            return {'accepted':False,'code':'MONITOR-SAVE-FAILED'}
        # Only this application's init script; no network/firewall/VPN services.
        try:
            service=subprocess.run(['/etc/init.d/homensai-vpn','start' if enabled else 'stop'],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=25)
        except subprocess.SubprocessError:
            return {'accepted':False,'configured':enabled,'code':'MONITOR-SERVICE-UNCONFIRMED'}
        return {'accepted':service.returncode==0,'configured':enabled,
                'code':'MONITOR-START-REQUESTED' if enabled and service.returncode==0 else
                       'MONITOR-STOP-REQUESTED' if service.returncode==0 else 'MONITOR-SERVICE-UNCONFIRMED',
                'running_confirmed':False,'auto_started':False}
