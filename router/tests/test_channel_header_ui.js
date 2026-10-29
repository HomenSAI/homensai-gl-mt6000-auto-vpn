const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children==null?[]:children).flat().filter(n=>n!=null);}
 all(){return [this,...this.children.flatMap(n=>n instanceof N?n.all():[])];}
 text(){return this.children.map(n=>n instanceof N?n.text():String(n)).join(' ');}
}
for(const language of ['en','ru']){
 const c={locale:language,bi:(en,ru)=>language==='ru'?ru:en,E:(...args)=>new N(...args),Date,protocolLabel:()=> 'OpenVPN',safeCode:()=>false};
 vm.createContext(c);for(const name of ['ui_logic','manual_panel','design_views','vendor_diagnostics'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);
 const profile={id:'reserve',interface:'ovpnclient1',time:1000,dns_ok:true,https_success:2,code:null},status={time:1000,native_failover:{state:'OBSERVING',time:1000},manual_switch_control:{time:1000,available:true,control_revision:'b'.repeat(32),reserve:{allowed:true,blockers:[]},primary:{allowed:false,blockers:['PAIR-MANUAL-COOLDOWN']}}};
 const model={now:1001,selected:'primary',settings:{plan_source:'primary',plan_target:'reserve'}};
 const use=c.dvChannelUse(profile,model,status);
 const alive=language==='ru'?'Живой, можно переключиться на него вручную':'Live, you can switch to it manually';
 assert.equal(use.label,alive,'owner P3 wording for an available unselected live channel');
 assert.equal(use.badgeLabel,alive,'compact badge carries the same owner wording; the role stays a separate node');
 const blocked=c.dvChannelUse(profile,model,Object.assign({},status,{manual_switch_control:Object.assign({},status.manual_switch_control,{reserve:{allowed:false,blockers:['PAIR-MANUAL-COOLDOWN']}})}));
 assert.equal(blocked.label,language==='ru'?'Живой; ручное переключение сейчас недоступно':'Live; manual switching is unavailable now','a live channel never promises a manual switch the router currently refuses');
 c.channelDisplayUse=()=>use;
 const header=c.renderChannelHeader(profile,status,{}),role=header.all().find(n=>n.attrs.class==='hv-protocol'),protocol=header.all().find(n=>n.attrs.class==='hv-channel-protocol'),badge=header.all().find(n=>String(n.attrs.class).startsWith('hv-route-badge'));
 assert.equal(role.text(),language==='ru'?'Резервный канал':'Reserve channel','the complete role is a separate text node');assert.equal(protocol.text(),'OpenVPN');assert.equal(badge.text(),use.badgeLabel);
 assert(!badge.text().includes(language==='ru'?'Запасной канал:':'Reserve channel:'),'role is not duplicated in the badge');
 assert(/hv-route-badge-long/.test(badge.attrs.class),'the long status wraps inside the card on narrow screens');
 const removed=c.renderVendorChannels(status,{});assert.equal(removed.text(),'');assert(!removed.all().some(n=>n.tag==='details'||n.tag==='summary'||n.attrs['data-vendor-diagnostics']),'the entire named VPN disclosure is removed');
}
assert(fs.readFileSync('router/attribution_panel.inc.js','utf8').includes('Developer · Serhii Khomenko'),'owner attributes remain in their separate renderer');
console.log('PASS: full role/protocol text is structurally separate from an explicit compact status; whole VPN names disclosure removed and owner attribution retained');
