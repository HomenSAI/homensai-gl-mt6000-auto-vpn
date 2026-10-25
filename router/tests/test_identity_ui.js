const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync('router/identity_panel.inc.js','utf8').replace('__UI_BUILD__','dashboard99').replace('__UI_AGENT__','1.2.3-alpha4');
const context={bi:(en)=>en,E:(tag,attrs,text)=>({tag,attrs,text})};vm.createContext(context);vm.runInContext(src,context);
const model=(s)=>context.identityModel(s);
// Matching page, program and package: no notice.
assert.equal(context.renderIdentityNotice({version:'1.2.3-alpha4',package:'1.2.3-alpha4-1'}),null);
// Old cached page or partial upgrade is named, never silent.
assert(model({version:'1.2.2',package:'1.2.2-1'}).pageOld);
assert(/Ctrl\+F5/.test(context.renderIdentityNotice({version:'1.2.2'}).text));
assert(model({version:'1.2.3-alpha4',package:'1.2.2-1'}).packageMismatch);
assert(/differ/.test(context.renderIdentityNotice({version:'1.2.3-alpha4',package:'1.2.2-1'}).text));
// No data or an RPC error never claims a mismatch; hostile strings are ignored.
for(const bad of [{},{rpc_error:'X'},{version:'<img src=x>'},{version:'1'.repeat(80)},{version:null}])assert.equal(context.renderIdentityNotice(bad),null);
assert.equal(model({version:'1.2.3-alpha4',package:'<script>'}).pkg,null);
assert.equal(context.identityLine({version:'1.2.3-alpha4',package:'1.2.3-alpha4-1'}),'Version 1.2.3-alpha4');
assert.equal(context.identityLine({}),'Version 1.2.3-alpha4');
assert.equal(model({version:'1.2.3-alpha4',package:'1.2.3-alpha4-1'}).ui,'dashboard99','technical identity remains available internally');
// Generated dashboard carries real values that agree with the agent and the menu.
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const page=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
const dashboard=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+page+'.js','utf8');
const agent=/^VERSION = '([^']+)'/m.exec(fs.readFileSync('router/files/usr/lib/homensai-vpn/agent.py','utf8'))[1];
assert(dashboard.includes("UI_BUILD='"+page+"'")&&dashboard.includes("UI_AGENT='"+agent+"'"));
assert(!dashboard.includes('__UI_'));assert(dashboard.includes('renderIdentityNotice(status)'));
console.log('PASS: identity notice, mismatch diagnosis and generated build values');
