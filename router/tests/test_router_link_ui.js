const fs=require('fs'),vm=require('vm'),assert=require('assert');const c={URL};vm.createContext(c);vm.runInContext(fs.readFileSync('router/router_link.inc.js','utf8'),c);
for(const host of ['192.168.8.1','192.168.1.1','10.20.30.1','router.lan','[fd00::1]'])assert.equal(c.resolveRouterVpnUrl('http://'+host+':8080/cgi-bin/luci/'), 'http://'+host+'/#/vpndashboard');
assert.equal(c.resolveRouterVpnUrl('https://router.lan:8443/cgi-bin/luci/'),'https://router.lan/#/vpndashboard');
assert.equal(c.resolveRouterVpnUrl('http://127.0.0.1:18886/','http://192.168.8.1'),'http://192.168.8.1/#/vpndashboard');
assert.equal(c.resolveRouterVpnUrl('http://localhost:18886/','https://router.lan:444'),'https://router.lan:444/#/vpndashboard');
for(const origin of [undefined,'javascript:alert(1)','http://u:secret@router.lan','http://127.0.0.1','http://router.lan/?token=x'])assert.equal(c.resolveRouterVpnUrl('http://localhost:18886/',origin),null);
console.log('PASS: dynamic router IPv4/IPv6/hostname, separate LuCI port, preview gateway and unsafe/missing origins');
