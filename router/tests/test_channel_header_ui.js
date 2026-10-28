const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children==null?[]:children).flat().filter(n=>n!=null);}
 all(){return [this,...this.children.flatMap(n=>n instanceof N?n.all():[])];}
 text(){return this.children.map(n=>n instanceof N?n.text():String(n)).join(' ');}
}
for(const language of ['en','ru']){
 const c={locale:language,bi:(en,ru)=>language==='ru'?ru:en,E:(...args)=>new N(...args),Date,protocolLabel:()=> 'OpenVPN',safeCode:()=>false};
 vm.createContext(c);for(const name of ['ui_logic','design_views','vendor_diagnostics'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);
 const profile={id:'reserve',interface:'ovpnclient1',time:1000,dns_ok:true,https_success:2,code:null},status={time:1000,native_failover:{state:'OBSERVING',time:1000}};
 const model={now:1001,selected:'primary',settings:{plan_source:'primary',plan_target:'reserve'}};
 const use=c.dvChannelUse(profile,model,status);
 assert.equal(use.label,language==='ru'?'Запасной канал: Живой, можно переключиться на него вручную':'Reserve channel: Alive; you can switch to it manually','full role-prefixed label remains available outside the badge');
 assert.equal(use.badgeLabel,language==='ru'?'Живой, можно переключиться на него вручную':'Alive; you can switch to it manually','compact badge comes from an explicit model field');
 c.channelDisplayUse=()=>use;
 const header=c.renderChannelHeader(profile,status,{}),role=header.all().find(n=>n.attrs.class==='hv-protocol'),protocol=header.all().find(n=>n.attrs.class==='hv-channel-protocol'),badge=header.all().find(n=>String(n.attrs.class).startsWith('hv-route-badge'));
 assert.equal(role.text(),language==='ru'?'Резервный канал':'Reserve channel','the complete role is a separate text node');assert.equal(protocol.text(),'OpenVPN');assert.equal(badge.text(),use.badgeLabel);
 assert(!badge.text().includes(language==='ru'?'Запасной канал:':'Reserve channel:'),'role is not duplicated in the badge');
 const removed=c.renderVendorChannels(status,{});assert.equal(removed.text(),'');assert(!removed.all().some(n=>n.tag==='details'||n.tag==='summary'||n.attrs['data-vendor-diagnostics']),'the entire named VPN disclosure is removed');
}
assert(fs.readFileSync('router/attribution_panel.inc.js','utf8').includes('Developer · Serhii Khomenko'),'owner attributes remain in their separate renderer');
console.log('PASS: full role/protocol text is structurally separate from an explicit compact status; whole VPN names disclosure removed and owner attribution retained');
