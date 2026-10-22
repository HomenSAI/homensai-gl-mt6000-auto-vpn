"""Device preference is metadata, never a platform capability or write permit."""
from pathlib import Path

BOARDS = {'glinet,gl-mt6000': 'mt6000', 'glinet,mt3000-snand': 'mt3000'}
LABELS = {'mt6000': 'GL.iNet GL-MT6000 · Flint 2', 'mt3000': 'GL.iNet GL-MT3000 · Beryl AX'}


def detect(path=None):
    try:
        with (path or Path('/tmp/sysinfo/board_name')).open(encoding='ascii') as stream:
            return BOARDS.get(stream.read(128).strip(), 'unknown')
    except (OSError, UnicodeError):
        return 'unknown'


def validate(value, detected):
    if type(value) is not str or value not in ('auto', 'mt6000', 'mt3000'):
        raise ValueError('DEVICE-MODEL-INVALID')
    if value != 'auto' and value != detected:
        raise ValueError('DEVICE-MODEL-MISMATCH')
    return value
