"""Read-only environment snapshot; never authorizes native activation."""
import re
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


def snapshot(now=None,settings=None):
    now=time.time() if now is None else now
    checks=[{'code':'PYTHON-39-MINIMUM','state':'pass' if sys.version_info >= (3,9) else 'fail'}]
    for binary in ('ubus','uci','lua','ip'):
        checks.append({'code':'DEPENDENCY-'+binary.upper(),'state':'pass' if shutil.which(binary) else 'fail'})
    for name,path in [('RPC-PLUGIN','/usr/libexec/rpcd/homensai-vpn'),('CA-BUNDLE','/etc/ssl/certs/ca-certificates.crt')]:
        checks.append({'code':name,'state':'pass' if Path(path).is_file() else 'fail'})
    board={'model':'unknown','board_name':'unknown','firmware':'unknown','openwrt':'unknown'}
    try:
        reply=subprocess.run(['ubus','call','system','board'],capture_output=True,timeout=3,check=True)
        if len(reply.stdout)>32768:raise ValueError('BOARD-OVERSIZE')
        data=json.loads(reply.stdout)
        for key in ('model','board_name'):board[key]=str(data.get(key,'unknown'))[:96]
        board['openwrt']=str(data.get('release',{}).get('version','unknown'))[:64]
    except (OSError,ValueError,subprocess.SubprocessError,AttributeError,TypeError):pass
    try:
        vendor=Path('/etc/glversion')
        if vendor.stat().st_size<=256:
            text=vendor.read_text(encoding='utf8').strip()
            if re.fullmatch(r'[A-Za-z0-9 ._+~-]{1,96}',text):board['firmware']=text
    except (OSError,ValueError,UnicodeError):pass
    try:free=shutil.disk_usage('/etc/config').free
    except OSError:free=None
    try:writable=not bool(os.statvfs('/etc/config').f_flag&getattr(os,'ST_RDONLY',1)) and os.access('/etc/config',os.W_OK)
    except (OSError,AttributeError):writable=None
    checks.append({'code':'CONFIG-STORAGE-FREE','state':'fail' if writable is False else 'unknown' if free is None or writable is None else 'pass' if free>=1048576 else 'fail'})
    from preparation_status import snapshot as preparation_snapshot
    return {'time':now,'board':board,'checks':checks,'config_free_bytes':free,'config_storage_writable':writable,
            'preparation':preparation_snapshot(settings=settings),
            'native_permission':'not_assessed','scope':'Dependencies only; native Start performs authoritative certification and lease checks.'}
