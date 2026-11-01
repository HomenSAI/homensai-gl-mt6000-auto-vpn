# HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
"""FALLBACK bridge of the Lua monitor (owner plan items 2/3; kept for the Python line and as a fallback).

Since 2.0.0-alpha14 the Lua monitor computes both fields itself (lua/page_controls.lua: pair_manual.controls /
manual_control.control_status and scan_control.public, differential tests in tests/test_lua_page_controls.py) and
never starts this script on a timer. It is started in the background only when that Lua computation fails (at most
every 10 s, never on the request path); its answer is merged while it is younger than 30 s:

  manual_switch_control  pair_manual.controls() / manual_control.control_status(), chosen like status_reply
  scan
(channel_path is computed by the Lua monitor itself since plan item 4: lua/channel_path.lua; speed_pause and
speed_tests are answered by the Lua monitor itself since plan item 7: lua/speed_pause.lua, lua/speed.lua.)

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
        from scan_control import public as scan_public
        result['scan'] = scan_public(runtime, read_json)
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
