"""Bounded, read-only persistent MT3000 preparation checks.

An installed dependency or disabled runtime hook cannot establish boot readiness.
No configuration values, profile names, addresses or credentials are returned.
This report never grants native or external-client certification.
"""
import hashlib
import json
from pathlib import Path
import subprocess

AUTOLOAD_SHA = '8aad0842bbf4de46c61719fba3237d3127cee632f4312807ff3b591d388b2f49'


def snapshot(root=Path('/'), run=subprocess.run, settings=None):
    checks = []
    def add(code, state):
        checks.append({'code': code, 'state': state})
    def flag(name, expected):
        try:
            reply = run(['uci', '-q', 'get', name], capture_output=True, timeout=2)
            if reply.returncode == 1:
                return 'fail'
            if reply.returncode or len(reply.stdout) > 128:
                return 'unknown'
            value = reply.stdout.decode('ascii').strip()
            return 'pass' if value == expected else 'fail'
        except (OSError, UnicodeError, subprocess.SubprocessError):
            return 'unknown'
    def absent(path):
        # Broken links also remain active configuration, not an absent file.
        return not path.exists() and not path.is_symlink()
    try:
        path = root / 'tmp/sysinfo/board_name'
        if path.is_symlink() or path.stat().st_size > 128:
            raise ValueError('board')
        board = path.read_text(encoding='ascii').strip()
    except (OSError, UnicodeError, ValueError):
        board = None
    if board != 'glinet,mt3000-snand':
        return {'scope': 'persistent-mt3000-preparation', 'state': 'unsupported' if board else 'unknown',
                'checks': [], 'native_permission': False, 'external_lan_verified': False}
    if settings is None and root==Path('/'):
        from agent import inventory
        settings=inventory().get('settings',{})
    add('PREP-HNAT-CONFIG', flag('mtkhnat.global.enable', '0'))
    from pair_interfaces import roles
    try:selected=roles(settings or {})
    except ValueError:selected={'source':None,'target':None}
    for role in ('source','target'):
        name=selected[role]
        code='PREP-'+role.upper()+'-AUTOSTART' if settings is not None else 'PREP-'+str(name).upper()+'-AUTOSTART'
        add(code, flag('network.' + name + '.auto', '0') if name else 'unknown')
    for service, code in (('vpn-client', 'PREP-STOCK-VPN-BOOT'), ('shortcut-fe', 'PREP-SFE-BOOT')):
        try:
            links = list((root / 'etc/rc.d').iterdir())
            active = [p for p in links if p.name.startswith('S') and p.name[1:3].isdigit() and p.name[3:] == service]
            add(code, 'fail' if active else 'pass')
        except OSError:
            add(code, 'unknown')
    autoload = root / 'etc/modules.d/09-shortcut-fe'
    saved = root / 'etc/homensai-vpn/disabled-module-autoload/09-shortcut-fe'
    try:
        if not absent(autoload):
            state = 'fail'
        elif saved.is_symlink() or not saved.is_file() or saved.stat().st_size > 4096:
            state = 'unknown'
        else:
            state = 'pass' if hashlib.sha256(saved.read_bytes()).hexdigest() == AUTOLOAD_SHA else 'unknown'
        add('PREP-SFE-AUTOLOAD', state)
    except OSError:
        add('PREP-SFE-AUTOLOAD', 'unknown')
    try:
        path = root / 'proc/modules'
        if path.is_symlink() or path.stat().st_size > 262144:
            raise ValueError('modules')
        data = path.read_bytes()
        if len(data) > 262144:
            raise ValueError('modules')
        modules = {line.split()[0] for line in data.decode('ascii').splitlines() if line.split()}
        add('PREP-SFE-RUNTIME', 'fail' if modules & {'shortcut_fe', 'shortcut_fe_ipv6', 'fast_classifier'} else 'pass')
    except (OSError, UnicodeError, ValueError):
        add('PREP-SFE-RUNTIME', 'unknown')
    return {'scope': 'persistent-mt3000-preparation',
            'state': 'pass' if all(x['state'] == 'pass' for x in checks) else 'incomplete',
            'checks': checks, 'native_permission': False, 'external_lan_verified': False}


if __name__ == '__main__':
    print(json.dumps(snapshot(), sort_keys=True))
