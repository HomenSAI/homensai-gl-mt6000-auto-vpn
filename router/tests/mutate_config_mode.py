"""Mutation check of the root-only config file (security audit 04.11.2026, F7): every mutant must make
tests/test_config_mode.py or the setup_save test in tests/test_lua_contracts.py fail. Each mutant is applied in place, the
suite runs, the file is restored (also on error). Run on a COPY (docker python39 image, Lua 5.1 needed):
  python3 router/tests/mutate_config_mode.py   -> one line per mutant, exit 1 when a mutant survives
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUTER = HERE.parent
SUITE = [sys.executable, '-m', 'unittest', 'test_config_mode', 'test_lua_contracts', '-q']

MUTANTS = [
    ('build_ipk.py', "0o600 if name in CONFFILES else 0o644", "0o644"),
    ('package_hooks.py', "[ ! -f /etc/config/homensai_vpn ] || chmod 0600 /etc/config/homensai_vpn\\n", ""),
    ('package_hooks.py', "chmod 0600 /etc/config/homensai_vpn", "chmod 0644 /etc/config/homensai_vpn"),
    ('Makefile', "chmod 0600 $(1)/etc/config/homensai_vpn", "chmod 0644 $(1)/etc/config/homensai_vpn"),
    ('files/usr/lib/homensai-vpn/setup_save.lua', "os.execute('chmod 0600 '", "os.execute('chmod 0644 '"),
    ('files/usr/lib/homensai-vpn/setup_save.lua', "if not ok then c:revert('homensai_vpn');os.exit(1) end\n", "if not ok then c:revert('homensai_vpn');os.exit(1) end\nif true then os.exit(0) end\n"),
    ('files/usr/lib/homensai-vpn/setup_save.lua', "(testroot and (testroot..'/config/homensai_vpn') or '/etc/config/homensai_vpn')", "'/etc/config/homensai_vpn'"),
    ('files/usr/lib/homensai-vpn/setup_config.py', "    try:os.chmod(path or CONFIG,0o600)", "    try:os.chmod(path or CONFIG,0o644)"),
    ('files/usr/lib/homensai-vpn/setup_config.py', "    harden_config()\n    if kind=='speed' and not arguments['enabled']:", "    if kind=='speed' and not arguments['enabled']:"),
    ('files/usr/lib/homensai-vpn/setup_config.py', "            return {'saved':False,'code':failure_code(result,'SETUP-SAVE-FAILED')}\n    harden_config()", "            return {'saved':False,'code':failure_code(result,'SETUP-SAVE-FAILED')}\n    pass"),
]


def run(mutant):
    name, old, new = mutant
    path = ROUTER / name
    raw = path.read_bytes().decode('utf-8')
    text = raw.replace('\r\n', '\n')
    if text.count(old) != 1:
        return 'BROKEN (pattern found %d times)' % text.count(old)
    try:
        path.write_bytes(text.replace(old, new, 1).encode('utf-8'))
        result = subprocess.run(SUITE, cwd=str(HERE), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
        return 'killed' if result.returncode != 0 else 'SURVIVED'
    finally:
        path.write_bytes(raw.encode('utf-8'))


def main():
    bad = 0
    for mutant in MUTANTS:
        verdict = run(mutant)
        print('%-9s %s: %s' % (verdict.split()[0], mutant[0], mutant[1][:60].replace('\n', ' ')))
        if verdict != 'killed':
            bad += 1
    print('mutants %d, not killed %d' % (len(MUTANTS), bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
