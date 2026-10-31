# HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
"""TEMPORARY bridge of the Lua monitor (owner plan items 2/3, removed with plan items 1/4).

The Lua monitor answers the page without Python, except for the fields that need the Python Linux backend's
kernel attestation or modules not ported yet. It starts this script in the background (never on the request
path, at most every 10 s and only while the page polls) and merges the answer while it is younger than 30 s:

  manual_switch_control  pair_manual.controls() / manual_control.control_status(), chosen like status_reply
  channel_path           channel_path.public_status(status)
  speed_pause, scan, speed_tests

Input: the Lua monitor's status.json and native-status.json (the same files agent.status_reply reads).
Output: one RAM file, written atomically: /var/run/homensai-vpn/status-bridge.json. Usage:
    python3 status_bridge.py /var/run/homensai-vpn/status-bridge.json
Every field is computed independently; a failing one is left out (the Lua side then uses its fail-safe value).
"""
import sys
import time


def compute(runtime, read_json):
    status = read_json(runtime/'status.json', {})
    if not isinstance(status, dict):
        status = {}
    status['native_failover'] = read_json(runtime/'native-status.json', {'state': 'SERVICE-STOPPED'})
    result = {'time': time.time(), 'source': 'status_bridge.py'}
    try:
        from manual_control import control_status
        from pair_manual import controls as pair_controls, public_for_status
        pair_control = pair_controls()
        use_pair, _ = public_for_status(status['native_failover'], available=pair_control.get('available', False))
        result['manual_switch_control'] = pair_control if use_pair else control_status()
    except Exception:
        pass
    try:
        from channel_path import public_status as path_status
        result['channel_path'] = path_status(status)
    except Exception:
        pass
    try:
        from speed_pause import public as speed_pause_status
        result['speed_pause'] = speed_pause_status()
    except Exception:
        pass
    try:
        from scan_control import public as scan_public
        result['scan'] = scan_public(runtime, read_json)
    except Exception:
        pass
    try:
        from speed_test import public_status as speed_status
        result['speed_tests'] = speed_status()
    except Exception:
        pass
    return result


def main(argv):
    from agent import RUNTIME, read_json, atomic_json
    if len(argv) != 2 or argv[1] != str(RUNTIME/'status-bridge.json'):
        return 2
    atomic_json(RUNTIME/'status-bridge.json', compute(RUNTIME, read_json))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
