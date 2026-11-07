"""Owner decision 07.11.2026 15:10: "Monitoring is always started, regardless of any conditions."

init.d start_service opens the monitor instance whatever option enabled, the integrity mode (except stopped), the
maintenance marker or an unreadable config say; the Auto supervisor (native instance, hv-core) keeps its old gates and
option enabled other than 1 is recorded as SERVICE-AUTO-OFF so Start is refused instead of queued. MONITOR-BOOT-NOTE.md.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT/'files/etc/init.d/homensai-vpn'
LIB = ROOT/'files/usr/lib/homensai-vpn'

STUBS = r'''
chmod() { :; }
logger() { printf 'LOG %s\n' "$*" >>"$QA_LOG"; }
uci() { [ "$QA_UCI_OK" = 1 ]; }
config_load() {
    unset CONFIG_main_monitor_only CONFIG_main_monitor_only_LENGTH CONFIG_main_lua_core_process
    [ "$QA_MODE" = ABSENT ] || CONFIG_main_monitor_only=$QA_MODE
    [ "$QA_CORE" != 1 ] || CONFIG_main_lua_core_process=1
}
config_get_bool() { eval "$1=\${QA_ENABLED}"; }
config_get() { eval "$1=\${4}"; }
procd_open_instance() { printf 'OPEN %s\n' "$1"; }
procd_set_param() { printf 'PARAM %s\n' "$*"; }
procd_close_instance() { printf 'CLOSE\n'; }
integrity_gate() { echo "$QA_INTEGRITY"; }
ubus() { printf 'BOARD\n'; }
jsonfilter() { cat >/dev/null; printf '%s\n' "$QA_BOARD"; }
start_service
'''


@unittest.skipUnless(os.name == 'posix' and shutil.which('sh'), 'POSIX procd harness required')
class MonitorBootTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.gate = self.tmp/'run'/'service-auto.json'
        self.marker = self.tmp/'maintenance.json'

    def start(self, enabled='1', integrity='normal', mode='0', board='glinet,mt3000-snand', core=False, uci_ok=True):
        body = INIT.read_text().split('\n', 1)[1]
        body = body.replace('auto_gate=/var/run/homensai-vpn/service-auto.json', 'auto_gate=%s' % self.gate)
        body = body.replace('marker=/etc/homensai-vpn/maintenance.json', 'marker=%s' % self.marker)
        # every Lua file and /usr/bin/lua present, as on the router
        body = re.sub(r'\[ -f /usr/lib/homensai-vpn/lua/[a-z_]+\.lua \]', '[ -f /bin/sh ]', body.replace('[ -x /usr/bin/lua ]', '[ -x /bin/sh ]'))
        body = body.replace('rm -f /var/run/homensai-vpn/lua-monitor.ready', ':')
        log = self.tmp/'syslog'
        log.write_text('')
        result = subprocess.run(['sh', '-c', body+STUBS], capture_output=True, text=True, timeout=30,
                                env=dict(os.environ, QA_LOG=str(log), QA_ENABLED=enabled, QA_INTEGRITY=integrity, QA_MODE=mode,
                                         QA_BOARD=board, QA_CORE='1' if core else '0', QA_UCI_OK='1' if uci_ok else '0'))
        self.assertEqual(result.returncode, 0, result.stderr)
        instances = {}
        for block in result.stdout.split('OPEN ')[1:]:
            name, rest = block.split('\n', 1)
            instances[name] = [line[6:] for line in rest.splitlines() if line.startswith('PARAM ')]
        return instances, result.stderr+log.read_text()

    @staticmethod
    def command(params):
        return next(p for p in params if p.startswith('command '))

    def gate_code(self):
        return json.loads(self.gate.read_text())['code'] if self.gate.exists() else None

    def test_disabled_flag_starts_the_monitor_but_no_auto_supervisor(self):
        for enabled in ('0', '', 'x'):
            with self.subTest(enabled=enabled):
                instances, text = self.start(enabled=enabled)
                self.assertEqual(list(instances), ['monitor'])
                self.assertIn('lua/monitor.lua daemon', self.command(instances['monitor']))
                self.assertIn('respawn 3600 5 0', instances['monitor'])
                self.assertIn('SERVICE-AUTO-OFF', text)
                self.assertEqual(self.gate_code(), 'SERVICE-AUTO-OFF')

    def test_disabled_flag_never_starts_hv_core(self):
        """hv-core carries the Auto supervisor: with enabled != 1 the plain Lua monitor runs instead."""
        instances, _ = self.start(enabled='0', core=True)
        self.assertEqual(list(instances), ['monitor'])
        self.assertIn('lua/monitor.lua daemon', self.command(instances['monitor']))
        self.assertFalse(any('hv_core' in p for p in instances['monitor']))
        instances, _ = self.start(enabled='1', core=True)
        self.assertIn('hv_core.lua daemon', self.command(instances['monitor']))
        self.assertIn('hv_core.lua standby', self.command(instances['native']))

    def test_enabled_flag_keeps_monitor_and_native_and_clears_a_stale_gate(self):
        self.gate.parent.mkdir(parents=True)
        self.gate.write_text('{"code":"SERVICE-AUTO-OFF","time":1}')
        instances, text = self.start(enabled='1')
        self.assertEqual(list(instances), ['monitor', 'native'])
        self.assertIn('lua/auto.lua daemon', self.command(instances['native']))
        self.assertNotIn('SERVICE-AUTO-OFF', text)
        self.assertFalse(self.gate.exists())

    def test_every_integrity_mode_but_stopped_starts_the_monitor(self):
        for enabled in ('0', '1'):
            for mode, monitor in (('normal', 'lua/monitor.lua'), ('no-c', 'lua/monitor.lua'), ('python', 'agent.py'),
                                  ('no-auto', 'lua/monitor.lua'), ('', 'lua/monitor.lua'), ('garbage', 'lua/monitor.lua')):
                with self.subTest(enabled=enabled, mode=mode):
                    instances, _ = self.start(enabled=enabled, integrity=mode)
                    self.assertIn(monitor, self.command(instances['monitor']))
                    auto_allowed = enabled == '1' and mode in ('normal', 'no-c', 'python')
                    self.assertEqual('native' in instances, auto_allowed)

    def test_integrity_stopped_still_starts_nothing(self):
        for enabled in ('0', '1'):
            instances, text = self.start(enabled=enabled, integrity='stopped')
            self.assertEqual(instances, {})
            self.assertIn('INTEGRITY-SERVICE-STOPPED', text)

    def test_maintenance_marker_does_not_hold_the_monitor_back(self):
        self.marker.write_text('{"operation":"upgrade","time":1}')
        for enabled in ('0', '1'):
            instances, _ = self.start(enabled=enabled)
            self.assertIn('monitor', instances)

    def test_unreadable_config_runs_the_monitor_without_auto(self):
        instances, text = self.start(enabled='0', uci_ok=False)
        self.assertEqual(list(instances), ['monitor'])
        self.assertIn('HOMENSAI-CONFIG-UNREADABLE', text)
        self.assertIn('monitoring runs, Auto is not started', text)
        self.assertEqual(self.gate_code(), 'SERVICE-AUTO-OFF')

    def test_monitor_only_with_disabled_flag_runs_the_monitor(self):
        instances, _ = self.start(enabled='0', mode='1')
        self.assertEqual(list(instances), ['monitor'])

    def test_unsupported_board_without_marker_keeps_the_hardware_refusal(self):
        for enabled in ('0', '1'):
            instances, text = self.start(enabled=enabled, mode='0', board='unknown')
            self.assertEqual(instances, {})
            self.assertIn('MONITOR-ONLY-DEPLOYMENT', text)
            self.assertEqual(list(self.start(enabled=enabled, mode='1', board='unknown')[0]), ['monitor'])


class MonitorRuntimeIgnoresEnabledTests(unittest.TestCase):
    """The monitor processes never treat main option enabled as an off switch (no reader exists; pinned here)."""
    def test_no_monitor_runtime_reads_the_service_flag(self):
        patterns = (r"settings\.get\(\s*'enabled'", r"settings\[\s*'enabled'\s*\]", r"settings\.enabled\b", r"main\.enabled\b",
                    r"main_enabled", r"homensai_vpn\.main\.enabled")
        for name in ('agent.py', 'status_server.py', 'lua/monitor.lua', 'lua/hv_core.lua', 'lua/monitor_io.lua', 'lua/monitor_status.lua'):
            text = (LIB/name).read_text()
            for pattern in patterns:
                self.assertIsNone(re.search(pattern, text), (name, pattern))


if __name__ == '__main__':
    unittest.main()
