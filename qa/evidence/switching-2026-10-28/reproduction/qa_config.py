"""Portable path/port configuration for isolated switching reproduction."""
import os
from pathlib import Path
HERE=Path(__file__).resolve().parent

def repository():
    explicit=os.environ.get('QA_REPO')
    if explicit:return Path(explicit).resolve()
    for root in (Path.cwd(),HERE,*HERE.parents):
        for candidate in (root,root/'auto-vpn'):
            if (candidate/'VERSION.json').is_file()and(candidate/'router/tests').is_dir():return candidate
    raise RuntimeError('Set QA_REPO to the project checkout')

REPO=repository()
OUT=Path(os.environ.get('QA_OUTPUT',str(HERE))).resolve();OUT.mkdir(parents=True,exist_ok=True)
HTTP_PORT=int(os.environ.get('QA_HTTP_PORT','18988'))
SERIAL_PORT=int(os.environ.get('QA_QEMU_SERIAL_PORT','14555'))
QEMU_ROOT=Path(os.environ.get('QA_QEMU_ROOT',str(HERE.parent/'qa-qemu'))).resolve()
