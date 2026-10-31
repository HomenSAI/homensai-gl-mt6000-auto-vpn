"""MIT. HomenS.AI / Serhii Khomenko. FALLBACK probe bridge of the Lua Auto supervisor (2.0.0-lua, plan items 1 and 4).

Since plan item 4 the Lua supervisor probes natively (lua/live_probe.lua over sys.probe_io) with the same fields
and codes as this file. It still runs this bridge for the three places that need a live probe of one profile -
health(), the WAIT-CLIENT confirmation and the exit trace - when `option lua_probe '0'` is set, when the router
lacks nixio/curl, or when the native probe hits a Lua fault (logged as "hv-auto: native ... failed"):

    python3 /usr/lib/homensai-vpn/lua_bridge.py probe|trace <request.json>

The request is the profile row written by the Lua backend into the RAM directory (0600). The answer is one
JSON line: agent.probe(profile), or {"exit": "<ipv4>"} / {"code": "<REFUSAL>"} for native_switch.trace.
Read-only: no route, UCI, journal or state file is written. tests/test_lua_live_probe.py compares this contract
with the native probe.
"""
import json
import re
import sys

sys.path.insert(0, '/usr/lib/homensai-vpn')

RUNTIME_FILE = re.compile(r'^/(?:var/run|tmp/run)/homensai-vpn/\.bridge-[0-9a-f-]{1,80}\.json$')


def main(argv):
    if len(argv) != 3 or argv[1] not in ('probe', 'trace') or not RUNTIME_FILE.fullmatch(argv[2]):
        print(json.dumps({'code': 'BRIDGE-REQUEST-INVALID'}))
        return 2
    try:
        with open(argv[2], encoding='utf-8') as stream:
            profile = json.load(stream)
    except (OSError, ValueError):
        print(json.dumps({'code': 'BRIDGE-REQUEST-INVALID'}))
        return 2
    if not isinstance(profile, dict) or not isinstance(profile.get('id'), str):
        print(json.dumps({'code': 'BRIDGE-REQUEST-INVALID'}))
        return 2
    if argv[1] == 'probe':
        from agent import probe
        print(json.dumps(probe(profile), sort_keys=True))
        return 0
    import native_switch as n
    try:
        print(json.dumps({'exit': n.trace(profile)}))
    except n.Refused as error:
        code = str(error)
        print(json.dumps({'code': code if re.fullmatch(r'[A-Z][A-Z0-9_-]{0,95}', code) else 'NATIVE-SYSTEM-001'}))
    except (OSError, ValueError):
        print(json.dumps({'code': 'NATIVE-SYSTEM-001'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
