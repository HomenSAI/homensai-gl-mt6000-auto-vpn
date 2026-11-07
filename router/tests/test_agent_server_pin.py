"""server_pin in the Python monitor (agent.monitor_loop): every pass publishes status.server_keys, a first healthy check
pins the key (history event), the same server with another key is a change. Lua twin: lua/test_monitor_server_pin.lua."""
from contextlib import ExitStack
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import agent  # noqa: E402
import icmp_ping  # noqa: E402
import server_pin  # noqa: E402

KEY_A = 'q3Yp1E6rM2u1Lr0m8X4h6c8w2T5fW1kJ9Zx0bVnAs0E='
KEY_B = 'Bz7Q0mYk4sV8pT2xR6wN1cL5dH9fJ3gA0eU7iO4yK2w='


class AgentServerPin(unittest.TestCase):
    def run_passes(self, keys, config):
        profile = dict(id='wireguard:peer_1', section='peer_1', name='Example', protocol='wireguard', interface='wgclient1',
                       administrative_state='enabled', vendor_tunnel_id='wireguard:wgclient1')
        data = {'profiles': [profile], 'servers': [], 'wan_interfaces': [],
                'settings': {'interval': 30, 'checkpoint': 900, 'probe_limit': 2, 'plan_enabled': False}}
        passes, published = [0], []

        def probe(*args, **kwargs):
            return dict(id=profile['id'], time=time.time(), device='wgclient1', mark=4096, table='1001', ifindex=7,
                        administrative_state='enabled', code=None, dns_ok=True, https_success=3, rtt_ms=25,
                        server_endpoint={'host': '185.1.1.%d' % passes[0], 'port': 51820})
        answers = {'uci -q get network.wgclient1.config': 'peer_1\n',
                   'uci -q show wireguard.peer_1': "wireguard.peer_1=peers\nwireguard.peer_1.name='de1.nordvpn.com'\n"}

        def run(argv):
            if argv[:2] == ['wg', 'show']:
                return keys[min(passes[0], len(keys)-1)]+'\t185.1.1.1:51820\n'
            return answers.get(' '.join(argv))
        real_write = agent.atomic_json

        def write(path, value):
            real_write(path, value)
            if Path(path).name == 'status.json':
                published.append(value)
                passes[0] += 1
                if passes[0] >= len(keys):
                    agent.STOP = True
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory)
            (root/'homensai_vpn').write_text(config)
            real_io = server_pin.router_io()
            stack.enter_context(patch.object(server_pin, 'router_io', return_value=dict(real_io, run=run)))
            stack.enter_context(patch.object(server_pin, 'CONFIG', str(root/'homensai_vpn')))
            for name, value in [('RUNTIME', root), ('PERSIST', root/'flash'), ('STOP', False)]:
                stack.enter_context(patch.object(agent, name, value))
            stack.enter_context(patch('auto_control.RUNTIME', root))
            stack.enter_context(patch('auto_control.PERSIST', root))
            stack.enter_context(patch.object(agent, 'inventory', return_value=data))
            stack.enter_context(patch('website_response.WebsiteSampler'))
            stack.enter_context(patch.object(icmp_ping, 'PingSampler'))
            stack.enter_context(patch.object(agent, 'probe', side_effect=probe))
            stack.enter_context(patch.object(agent, 'restore', return_value=(agent.Accounting(), None)))
            stack.enter_context(patch.object(agent, 'sample_counters'))
            stack.enter_context(patch.object(agent, 'sample_wan_counters', return_value=[]))
            stack.enter_context(patch.object(agent, 'checkpoint'))
            stack.enter_context(patch.object(agent, 'monitor_poll_interval', return_value=0))
            stack.enter_context(patch('telegram_report.deliver', return_value=({'enabled': False}, {}, False)))
            stack.enter_context(patch('system_readiness.snapshot', return_value={}))
            stack.enter_context(patch('server_pick.job'))
            stack.enter_context(patch('speed_test.observe_traffic'))
            stack.enter_context(patch('speed_test.automatic_new', return_value=set()))
            stack.enter_context(patch('speed_test.active_job', return_value=False))
            stack.enter_context(patch('speed_test.cancel'))
            stack.enter_context(patch.object(agent, 'atomic_json', side_effect=write))
            stack.enter_context(patch.object(agent.subprocess, 'run'))  # the syslog line
            try:
                agent.monitor_loop()
            finally:
                agent.STOP = False
            flash = (root/'flash'/server_pin.STATE).is_file()
        return published, flash

    def test_first_use_then_change_are_events_and_status(self):
        published, flash = self.run_passes([KEY_A, KEY_A, KEY_B], "\toption server_key_pin 'enforce'\n")
        self.assertEqual(len(published), 3)
        codes = [[e['code'] for e in status['events'] if e['code'].startswith('SERVER-KEY')] for status in published]
        self.assertEqual(codes[0], ['SERVER-KEY-PINNED'])
        self.assertEqual(codes[2], ['SERVER-KEY-PINNED', 'SERVER-KEY-CHANGED'])
        self.assertEqual(published[0]['server_keys'], {'mode': 'enforce', 'pinned': 1, 'changed': [], 'code': None})
        last = published[2]['server_keys']
        self.assertEqual((last['code'], last['changed'][0]['host'], last['changed'][0]['observed']),
                         ('SERVER-KEY-CHANGED', 'de1.nordvpn.com', 'wg:'+KEY_B))
        self.assertTrue(flash)

    def test_off_publishes_the_mode_only(self):
        published, flash = self.run_passes([KEY_A, KEY_B], "\toption server_key_pin 'off'\n")
        self.assertEqual([status['server_keys'] for status in published], [{'mode': 'off'}, {'mode': 'off'}])
        self.assertFalse(flash)


if __name__ == '__main__':
    unittest.main()
