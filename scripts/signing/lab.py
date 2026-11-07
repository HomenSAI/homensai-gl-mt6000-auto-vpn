"""The signing test lab: local web page and headless drills. Guide: docs/architecture/SIGNING-LAB-2026-11-04.ru.md.

  py -3.14 scripts/signing/lab.py                 start the page on 127.0.0.1 and open it (test keys only)
  py -3.14 scripts/signing/lab.py --run-all-drills  every drill without the page; exit 1 if any drill failed
  options: --lab DIR  --only a,b,c  --no-network (skip OpenTimestamps)  --no-browser  --reset
"""
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_mode  # noqa: E402


def parser():
    p = argparse.ArgumentParser(description='HomenS.AI signing test lab (test keys only)')
    p.add_argument('--lab', help='lab directory (default private/signing-lab of the main checkout, or %s)' % lab_mode.ENV_DIR)
    p.add_argument('--run-all-drills', action='store_true', help='run every drill headless, with the test-only TOTP path')
    p.add_argument('--only', help='comma-separated drill letters')
    p.add_argument('--no-network', action='store_true', help='skip the OpenTimestamps calendars')
    p.add_argument('--no-browser', action='store_true', help='print the one-time link instead of opening it')
    p.add_argument('--reset', action='store_true', help='delete the lab directory and exit')
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.run_all_drills and os.name != 'nt':
            os.environ[lab_mode.TEST_ENV] = '1'  # no DPAPI here: the lab's test-only wrapper
        lab = lab_mode.LabDir(args.lab or os.environ.get(lab_mode.ENV_DIR) or lab_mode.default_lab_root())
        if args.reset:
            if lab.root.is_dir():
                lab.reset()
            print('LAB-RESET %s' % lab.root)
            return 0
        lab.ensure()
        if args.run_all_drills:
            import lab_drills
            only = set(args.only.split(',')) if args.only else None

            def show(event):
                if event['type'] == 'drill':
                    print('--- %s. %s' % (event['id'], event['en']), flush=True)
                elif event['type'] == 'result':
                    print('    %s %s' % (event['status'], event['message']), flush=True)
            results = lab_drills.run_all(lab, only, show, network=not args.no_network)
            print(json.dumps({'report': str(lab.report), 'results': {row['id']: row['status'] for row in results}}, sort_keys=True))
            return 1 if any(row['status'] in (lab_drills.FAIL, lab_drills.BLOCKED) for row in results) else 0
        import lab_web
        return lab_web.serve(lab, not args.no_browser)
    except ValueError as error:
        print('STOP: %s' % error, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
