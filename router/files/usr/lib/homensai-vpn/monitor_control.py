"""Own monitor lifecycle; never starts an uncertified VPN trial."""
import json
import subprocess
from auto_control import control_lock
from uci_result import failure_code

# Owner main rule (07.11.2026): "The monitor must ALWAYS run. We must never turn it off. It may stop only because of an
# error, and it cannot switch itself back on." There is no user, page or API path that stops it: a stop request
# (enabled=false) is refused with MONITOR-ALWAYS-ON before any lock, file, config or service is touched, with Auto on or
# off. Only the start (recovery of an error stop) is allowed. Stop Auto never reaches this module. The service stops
# only through the package scripts (opkg remove / upgrade call the init script directly), never through this RPC.


def change(arguments):
    if set(arguments)!={'enabled'} or type(arguments['enabled']) is not bool:
        return {'accepted':False,'code':'MONITOR-INVALID'}
    if arguments['enabled'] is not True:
        return {'accepted':False,'code':'MONITOR-ALWAYS-ON','configured':True,'auto_started':False}
    with control_lock():
        # IR-01 (integration review 07.11.2026): while the package hooks hold the maintenance marker (prerm stopped the
        # service, opkg unpacks), a start would run the old/half-unpacked tree and stall or bypass the lifecycle guard
        # (F-16/F-17). Refused under the control lock the hooks write the marker under; postinst (or the refusal paths)
        # starts the service again when the package operation ends, so monitoring still comes back by itself.
        from auto_control import maintenance_blocker
        maintenance=maintenance_blocker()
        if maintenance:return {'accepted':False,'code':maintenance,'configured':False,'auto_started':False}
        from rpc_throttle import allow
        if not allow('monitor_control',3):return {'accepted':False,'code':'RPC-RATE-LIMIT'}
        try:
            result=subprocess.run(['/usr/bin/lua','/usr/lib/homensai-vpn/setup_save.lua'],
                input=json.dumps({'main':{'enabled':'1'},'servers':[]}).encode(),
                stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=10)
        except (OSError,subprocess.SubprocessError):
            return {'accepted':False,'code':'SETUP-SAVE-UNCONFIRMED'}
        if result.returncode or result.stdout.strip()!=b'OK':
            return {'accepted':False,'code':failure_code(result,'MONITOR-SAVE-FAILED')}
        # Only this application's init script; no network/firewall/VPN services.
        try:
            service=subprocess.run(['/etc/init.d/homensai-vpn','start'],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=25)
        except subprocess.SubprocessError:
            return {'accepted':False,'configured':True,'code':'MONITOR-SERVICE-UNCONFIRMED'}
        return {'accepted':service.returncode==0,'configured':True,
                'code':'MONITOR-START-REQUESTED' if service.returncode==0 else 'MONITOR-SERVICE-UNCONFIRMED',
                'running_confirmed':False,'auto_started':False}
