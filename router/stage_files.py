"""Stage the same selected bytes/modes as the custom IPK builder for OpenWrt SDK.

Requires host Python 3. Refuses a nonempty destination; never deletes source,
existing payloads or arbitrary directories. The SDK owns PKG_BUILD_DIR cleanup.
"""
from pathlib import Path
import argparse
from build_ipk import selected_files

def stage(destination,source=None):
    destination=Path(destination)
    if destination.is_symlink() or (destination.exists() and any(destination.iterdir())):raise ValueError('STAGING-NONEMPTY-REFUSED')
    destination.mkdir(parents=True,exist_ok=True)
    selected=selected_files(source)
    for name,payload,mode in selected:
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(payload);target.chmod(mode)
    return len(selected)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('destination');args=p.parse_args();print('Staged files:',stage(args.destination))
