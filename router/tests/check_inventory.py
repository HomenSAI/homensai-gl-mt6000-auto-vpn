import json
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
inventory=root/'files/usr/lib/homensai-vpn/inventory.lua'
controller=root/'files/usr/lib/lua/luci/controller/homensai_vpn.lua'
for file in (inventory,controller):
    subprocess.run(['luac5.1','-p',str(file)],check=True)
result=subprocess.check_output(['lua5.1',str(root/'tests/test_inventory.lua'),str(inventory)],text=True)
data=json.loads(result)
assert len(data['profiles'])==2
assert data['profiles'][0]['interface']=='ovpnclient3'
assert data['profiles'][1]['id']=='wireguard:peer_56'
assert [v['id'] for v in data['native_candidates']]==['openvpn:12_34','wireguard:peer_56']
assert [v['order'] for v in data['native_candidates']]==[2,3]
assert not any(token in result for token in ('PASSWORD_SENTINEL','PRIVATE_KEY_SENTINEL','TOKEN_SENTINEL','PRIVATE_PATH_SENTINEL','SENSITIVE_DOMAIN_SENTINEL'))
assert data['settings']['appearance_design']=='b'
assert data['settings']['fast_switch'] is True  # default on; only the explicit '0' turns the fast channel switch off
for choice in ('a','b','c','','invalid','A'):
    configured=json.loads(subprocess.check_output(['lua5.1',str(root/'tests/test_inventory.lua'),str(inventory),choice],text=True))
    assert configured['settings']['appearance_design']==(choice if choice in ('a','b','c') else 'b'),choice
assert "option appearance_design 'b'" in (root/'files/etc/config/homensai_vpn').read_text()
print('Lua 5.1 syntax and credential-exclusion inventory test passed')
