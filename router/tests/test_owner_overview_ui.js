const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children==null?[]:children).flat().filter(node=>node!=null);}
 all(){return [this,...this.children.flatMap(node=>node instanceof N?node.all():[])];}
 text(){return this.children.map(node=>node instanceof N?node.text():String(node)).join(' ');}
}
for(const language of ['en','ru']){
 const context={locale:language,bi:(en,ru)=>language==='ru'?ru:en,E:(...args)=>new N(...args)};
 vm.createContext(context);vm.runInContext(fs.readFileSync('router/design_views.inc.js','utf8'),context);
 const control=new N('section',{'data-real-auto-control':'1'},[new N('section',{'data-manual-controls':'1'},'Actual manual channel controls')]);
 // The removed list must not inspect, name or build any profile cards on Overview.
 const rows=new Proxy([],{get(){throw Error('Overview must not rebuild the removed duplicate VPN list');}});
 const overview=context.renderDesignB({controlCard:control,rows,status:{},inventory:{}},{counts:{connected:2,working:2},passPercent:100,traffic:'3 GB'});
 assert.equal(overview.all().filter(node=>node===control).length,1,'the actual Auto/manual card remains once');
 assert.equal(overview.all().filter(node=>node.attrs['data-manual-controls']==='1').length,1);
 assert(!/Your VPNs|Ваши VPN/.test(overview.text()),'removed section heading absent');
 assert(!overview.all().some(node=>node.attrs['data-profile']||/hv-dv-list|hv-dv-item|hv-vpn-more|hv-dv-statuscol|hv-dv-flag/.test(node.attrs.class||'')),'no duplicate profile/country cards remain');
 for(const href of ['#statistics','#help','#learn','#events'])assert(overview.all().some(node=>node.tag==='a'&&node.attrs.href===href),'Overview navigation retained '+href);
 assert.equal(typeof context.renderChannelHeader,'function','Channels and servers information renderer remains available');
 assert.equal(typeof context.dvServerRows,'function','other existing appearances retain their server renderer');
}
const builder=fs.readFileSync('router/build_sidebar_ui.py','utf8');
assert(builder.includes('renderAttribution(data[1])')&&builder.includes('panel,settingsHost'),'owner attribution and persistent page structure remain');
console.log('PASS: entire duplicate Your VPNs section removed from Calm Overview EN/RU; actual manual controls, navigation, Channels information and attribution retained');
