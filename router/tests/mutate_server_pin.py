"""HomenS.AI VPN - (C) 2026 Serhii Khomenko. Mutation check of the server key pinning (server_pin.py/.lua and their
wiring into the monitors and the Auto diagnostic) and of the portable backup encryption (scripts/backupcrypt). It
rewrites source files, so run it ONLY on a copy of the tree, e.g. in the CI container:
  tar -cf - --exclude=.git . | docker run -i --rm --init --tmpfs /tmp homensai-vpn-python39:local sh -c \
    "mkdir -p /work && tar -x -C /work && cd /work && python3 router/tests/mutate_server_pin.py /work all"
Each mutant must make its group's tests fail (exit code != 0). Groups: py, lua, age."""
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(sys.argv[1])
LIB = ROOT/'router/files/usr/lib/homensai-vpn'
PY, LUA = LIB/'server_pin.py', LIB/'lua/server_pin.lua'
NAT, BACK = LIB/'native_switch.py', LIB/'lua/backend.lua'
AGENT, MON = LIB/'agent.py', LIB/'lua/monitor.lua'
AGE = ROOT/'scripts/backupcrypt/age_format.py'
ARC = ROOT/'scripts/backupcrypt/secrets_archive.py'
TOOL = ROOT/'scripts/backupcrypt/agetool.py'

PYM = [
    # the page's accept (2.1.0-alpha9): only the key the administrator checked, only for a real change
    ('accept: any key, observed ignored', PY, "if record['state'] != 'changed' or (seen is not None and record['observed'] != seen):", "if record['state'] != 'changed':"),
    ('rpc: no check of the current key', PY, "and r['state'] == 'changed' and r['observed'] == observed for r in", "and r['state'] == 'changed' for r in"),
    ('rpc: no check of the state', PY, "and r['state'] == 'changed' and r['observed'] == observed for r in", "and r['observed'] == observed for r in"),
    ('rpc: extra fields accepted', PY, "set(arguments) != {'profile', 'observed'}", "not {'profile', 'observed'} <= set(arguments)"),
    ('rpc: observed left out of the request', PY, "'profile': profile, 'observed': observed,\n", "'profile': profile,\n"),
    ('default mode enforce', PY, "DEFAULT_MODE = 'warn'", "DEFAULT_MODE = 'enforce'"),
    ('mode: first line wins', PY, "        if match and match.group(1) in MODES:\n            found = match.group(1)",
     "        if match and match.group(1) in MODES and found == DEFAULT_MODE:\n            found = match.group(1)"),
    ('wg: two peers accepted', PY, '    if len(lines) != 1:\n        return None\n    parts = _TOKEN', '    if len(lines) < 1:\n        return None\n    parts = _TOKEN'),
    ('wg: key not validated', PY, "    if len(parts) != 2 or not _WG_KEY.fullmatch(parts[0]):", "    if len(parts) != 2:"),
    ('pem: broken block skipped', PY, "        if end < 0:\n            return None", "        if end < 0:\n            break"),
    ('pem: hash of base64 text', PY, 'hashlib.sha256(base64.b64decode(body))', "hashlib.sha256(body.encode())"),
    ('pem: no padding check', PY, "        if not _B64.fullmatch(body) or len(body) % 4:", "        if not _B64.fullmatch(body):"),
    ('ovpn: last remote wins', PY, "parts[0] == 'remote' and remote is None and", "parts[0] == 'remote' and"),
    ('ovpn: host case kept', PY, '            remote = parts[1].lower()', '            remote = parts[1]'),
    ('identity without host', PY, "    return '%s|%s' % (profile, host or '-')", "    return profile"),
    ('changed not sticky', PY, "    if fingerprint == record['fingerprint']:\n        return [], None",
     "    if fingerprint == record['fingerprint']:\n        record['state'] = 'pinned'\n        return [], None"),
    ('no event for a second new key', PY, "    if fingerprint != previous:\n        return [_event(CHANGED, record, now)], 'urgent'", ''),
    ('change not urgent', PY, "        record['changed_at'] = now\n        return [_event(CHANGED, record, now)], 'urgent'",
     "        record['changed_at'] = now\n        return [_event(CHANGED, record, now)], 'new'"),
    ('accept keeps old key', PY, "record.update(fingerprint=record['observed'], state='pinned'", "record.update(state='pinned'"),
    ('accept ignores profile', PY, "        if target != '*' and record['profile'] != target:\n            continue", ''),
    ('blocker in warn mode', PY, "    if mode_value != 'enforce' or not isinstance(state, dict):", "    if mode_value == 'off' or not isinstance(state, dict):"),
    ('evict changed records', PY, "        pinned = [key for key in records if records[key]['state'] == 'pinned']", "        pinned = list(records)"),
    ('load accepts bad state', PY, "and record.get('state') in ('pinned', 'changed')", ''),
    ('unhealthy row observed', PY, "                if row.get('code') is not None:\n                    continue", ''),
    ('no recheck limit', PY, "                if last and last[1] == signature and 0 <= now-last[0] < RECHECK:\n                    continue", ''),
    ('binding checked once', PY, "    if fingerprint is None or not bound():", "    if fingerprint is None:"),
    ('flash every new record', PY, "        if self.dirty and (urgency == 'urgent' or due):", "        if self.dirty:"),
    ('flash never for changes', PY, "        if self.dirty and (urgency == 'urgent' or due):", "        if self.dirty and due:"),
    ('request file kept', PY, "            self.io['remove'](request_path)", "            pass"),
    ('corrupt not reported', PY, "            self.notice = CORRUPT", "            self.notice = None"),
    ('gate reads flash first', PY, "    text = read(at(runtime))\n    state, _ = load(text if text is not None else read(at(persist)))",
     "    text = read(at(persist))\n    state, _ = load(text if text is not None else read(at(runtime)))"),
    ('native gate removed', NAT, "    return gate(read,RUNTIME,PERSIST,[x for x in profiles if isinstance(x,str)])", '    return None'),
    ('agent pins not stepped', AGENT, "fresh,status['server_keys']=server_pins.step(rows,server_pin.mode(pin_config),time.time())",
     "fresh,status['server_keys']=[],server_pin.public(server_pins.state,server_pin.mode(pin_config))"),
]
LUAM = [
    ('accept: any key, observed ignored', LUA, "if r.state=='changed' and (seen==nil or r.observed==seen) then", "if r.state=='changed' then"),
    ('default mode enforce', LUA, "M.DEFAULT_MODE='warn'", "M.DEFAULT_MODE='enforce'"),
    ('wg: two peers accepted', LUA, '  if #lines~=1 then return nil end\n  local parts=tokens', '  if #lines<1 then return nil end\n  local parts=tokens'),
    ('wg: key not validated', LUA, "  if #parts~=2 or #parts[1]~=44 or not string.find(parts[1],'^[%w+/]+[AEIMQUYcgkosw048]=$') then return nil end",
     '  if #parts~=2 then return nil end'),
    ('b64: two-byte tail wrong', LUA, '    elseif d==61 then out[#out+1]=string.char(x,y)', '    elseif d==61 then out[#out+1]=string.char(x,y,z)'),
    ('pem: broken block skipped', LUA, '    if not finish then return nil end', '    if not finish then break end'),
    ('pem: hash of base64 text', LUA, '    local digest=canon.sha256(b64decode(body))', '    local digest=canon.sha256(body)'),
    ('ovpn: last remote wins', LUA, "parts[1]=='remote' and remote==nil and", "parts[1]=='remote' and"),
    ('identity without host', LUA, "function M.identity(profile,host) return profile..'|'..(host or '-') end", 'function M.identity(profile,host) return profile end'),
    ('changed not sticky', LUA, "  if fingerprint==r.fingerprint then return {},nil end", "  if fingerprint==r.fingerprint then r.state='pinned';return {},nil end"),
    ('no event for a second new key', LUA, "  if fingerprint~=previous then return {event(M.CHANGED,r,now)},'urgent' end", ''),
    ('accept keeps old key', LUA, "r.fingerprint=r.observed;r.state='pinned'", "r.state='pinned'"),
    ('blocker in warn mode', LUA, "  if mode~='enforce' or type(state)~='table'", "  if mode=='off' or type(state)~='table'"),
    ('evict changed records', LUA, "      if r.state=='pinned' and (victim==nil", "      if (victim==nil"),
    ('unhealthy row observed', LUA, '      if none(row.code) then', '      if true then'),
    ('no recheck limit', LUA, 'if not (last and last[2]==signature and now-last[1]>=0 and now-last[1]<M.RECHECK) then', 'if true then'),
    ('binding checked once', LUA, '  if fingerprint==nil or not bound() then return nil end', '  if fingerprint==nil then return nil end'),
    ('flash every new record', LUA, "  if self.dirty and (urgency=='urgent' or due) then", '  if self.dirty then'),
    ('request file kept', LUA, '    self.io.remove(request_path)', ''),
    ('backend gate removed', BACK, '    if okpin then return pinned end\n', ''),
    ('monitor field missing', MON, '  status.server_keys=okkeys and keys or NULL\n', ''),
    ('monitor events dropped', MON, '    self.events[#self.events+1]=e;status.events[#status.events+1]=e\n', ''),
]
AGEM = [
    ('x25519 clamp missing bit', AGE, '    k[31] |= 64\n', ''),
    ('chacha rotation 12 -> 11', AGE, '        xb = ((xb << 12) | (xb >> 20)) & mask', '        xb = ((xb << 11) | (xb >> 21)) & mask'),
    ('chacha no feed-forward', AGE, '        word = ((x[i] + state[i]) & mask).to_bytes(_LANE * lanes, \'little\')',
     '        word = (x[i] & mask).to_bytes(_LANE * lanes, \'little\')'),
    ('poly1305 no clamp', AGE, "    r = int.from_bytes(key[:16], 'little') & 0x0ffffffc0ffffffc0ffffffc0fffffff", "    r = int.from_bytes(key[:16], 'little')"),
    ('aead tag not checked', AGE, '    if not hmac.compare_digest(_aead_tag(key, nonce, aad, ciphertext), tag):\n        return None\n', ''),
    ('hkdf wrong info', AGE, "key = hkdf(shared, share + self.public, b'age-encryption.org/v1/X25519')\n        return aead_decrypt",
     "key = hkdf(shared, self.public + share, b'age-encryption.org/v1/X25519')\n        return aead_decrypt"),
    ('low-order share accepted', AGE, "        if shared == b'\\0' * 32:\n            raise HeaderError('X25519-LOW-ORDER')", ''),
    ('header mac not checked', AGE, "    if not hmac.compare_digest(_header_mac(file_key, head), mac):\n        raise HmacError('HEADER-MAC')", ''),
    ('base64 not canonical', AGE, "    if b64encode(data) != text:\n        raise HeaderError('BASE64-NOT-CANONICAL')", ''),
    ('stanza line length', AGE, '            if len(chunk) > 64:', '            if len(chunk) > 65:'),
    ('last flag ignored', AGE, "    return counter.to_bytes(11, 'big') + (b'\\x01' if last else b'\\x00')", "    return counter.to_bytes(11, 'big') + b'\\x00'"),
    ('empty last chunk allowed', AGE, '            if remaining == TAG and counter > 0:', '            if False:'),
    ('trailing data allowed', AGE, "            if pos != len(view):\n                raise PayloadError('STREAM-TRAILING-DATA')", ''),
    ('scrypt limit 23', AGE, 'MAX_SCRYPT_LOG_N = 22', 'MAX_SCRYPT_LOG_N = 23'),
    ('scrypt mixed stanzas', AGE, "    if any(s.type == 'scrypt' for s in stanzas) and len(stanzas) != 1:", '    if False:'),
    ('armor not canonical', AGE, "    if base64.b64encode(decoded) != joined:", '    if False:'),
    ('armor line length', AGE, "        if (not last and len(l) != 64) or (last and not 0 < len(l) <= 64):", '        if False:'),
    ('bech32 checksum ignored', AGE, "    if _polymod(_expand(hrp) + words) != 1:\n        raise ValueError('BECH32-CHECKSUM')", ''),
    ('archive includes signing', ARC, "NEVER_TOP = {'signing', 'signing-lab', 'signing-lab-tools'}", 'NEVER_TOP = set()'),
    ('archive escapes private', ARC, "            path.resolve().relative_to(private.resolve())\n        except ValueError:", "            pass\n        except ValueError:"),
    ('dpapi blobs not unwrapped', ARC, "            if rel.endswith('.dpapi'):", '            if False:'),
    ('restore overwrites', ARC, "            if target.exists():\n                raise ArchiveError('RESTORE-EXISTS: %s' % name)", ''),
    ('restore unsafe names', ARC, "            if not member.isfile() or not _safe_name(member.name):", '            if not member.isfile():'),
    ('all router backups', ARC, "    keep = newest if router_backups < 0 else newest[:router_backups]", '    keep = newest'),
    ('recipients not pinned', TOOL, '    if set(pinned) != set(repo):', '    if False:'),
    ('reveal without totp', TOOL, "def cmd_reveal(args, store, console):\n    require_totp(store, console)", 'def cmd_reveal(args, store, console):\n    pass'),
    ('import any identity', TOOL, '    if identity.recipient() not in pinned:', '    if False:'),
]


def run(cmd, env=None, timeout=1800):
    try:
        return subprocess.run(cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
                              env=env).returncode
    except subprocess.TimeoutExpired:
        return 'timeout'


def main():
    import os
    which = sys.argv[2] if len(sys.argv) > 2 else 'all'
    env = dict(os.environ, HOMENSAI_AGE_PURE='1', PYTHONDONTWRITEBYTECODE='1')
    tests = ROOT/'router/tests'
    groups = []
    if which in ('py', 'all'):
        groups.append(('python', PYM, ['python3', '-m', 'unittest', '-f', 'test_server_pin', 'test_agent_server_pin'], tests))
    if which in ('lua', 'all'):
        groups.append(('lua', LUAM, ['sh', '-c', 'cd lua && lua5.1 test_server_pin.lua && lua5.1 test_monitor_server_pin.lua && '
                                     'cd .. && python3 -m unittest -f test_server_pin.BothDiagnostics'], tests))
    if which in ('age', 'all'):
        groups.append(('age', AGEM, ['python3', '-m', 'unittest', '-f', 'qa.test_backupcrypt_age', 'qa.test_backupcrypt_tool'], ROOT))
    total = killed = 0
    survivors = []
    for runtime, mutants, cmd, cwd in groups:
        base = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env).returncode
        print('%s baseline exit %s' % (runtime, base), flush=True)
        if base != 0:
            print('BASELINE FAILS: no mutation verdicts for %s' % runtime)
            continue
        for name, path, old, new in mutants:
            text = path.read_text(encoding='utf-8')
            if text.count(old) != 1:
                print('  %-7s %-34s NOT APPLIED (pattern %d)' % (runtime, name, text.count(old)), flush=True)
                survivors.append(runtime+': '+name+' (not applied)')
                continue
            path.write_text(text.replace(old, new), encoding='utf-8')
            t0 = time.time()
            try:
                code = subprocess.run(cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, timeout=1800).returncode
            except subprocess.TimeoutExpired:
                code = 'timeout'
            finally:
                path.write_text(text, encoding='utf-8')
            total += 1
            dead = code != 0
            killed += dead
            if not dead:
                survivors.append(runtime+': '+name)
            print('  %-7s %-34s %s (%.0f s)' % (runtime, name, 'killed' if dead else 'SURVIVED', time.time()-t0), flush=True)
    print('mutants %d, killed %d' % (total, killed))
    if survivors:
        print('survivors: ' + '; '.join(survivors))
    return 0 if not survivors else 1


raise SystemExit(main())
