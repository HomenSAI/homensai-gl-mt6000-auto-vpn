"""Invalidate LuCI discovery files and only this application's cached controller."""
from pathlib import Path
import re


def invalidate(root=Path('/tmp')):
    root=Path(root)
    if root.is_symlink() or not root.is_dir():raise ValueError('LUCI-CACHE-ROOT')
    candidates=[root/'luci-indexcache']
    candidates.extend(p for p in root.glob('luci-indexcache.*') if re.fullmatch(r'luci-indexcache\.[A-Za-z0-9_.-]{1,128}\.(?:lua|json)',p.name))
    directory=root/'luci-modulecache'
    if not directory.is_symlink():candidates.append(directory/'luci.controller.homensai_vpn'.encode().hex().upper())
    removed=0
    for p in candidates:
        if p.is_file() and not p.is_symlink():p.unlink();removed+=1
    return removed

if __name__=='__main__':invalidate()
