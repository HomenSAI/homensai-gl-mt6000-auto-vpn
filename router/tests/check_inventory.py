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
assert not any(token in result for token in ('PASSWORD_SENTINEL','PRIVATE_KEY_SENTINEL','TOKEN_SENTINEL','PRIVATE_PATH_SENTINEL'))
print('Lua 5.1 syntax and credential-exclusion inventory test passed')
