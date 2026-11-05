require('./legacy_reference');  // checks the legacy logic the approved page extracts (router/tests/legacy_reference.js)
// Servers of the channels (2.1.0): the optional module renders status.server_pick per channel (current server, the list with
// pings, best marked, last change) and the owner switch "Pick the best server" (default off, one setup_response call). The main
// module carries only the loader and names the module of its own release.
const assert=require('assert'),fs=require('fs');
function node(tag,attrs,children){const n={tag,attrs:attrs||{},children:[],listeners:{},addEventListener(e,f){this.listeners[e]=f;},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this.attrs[k];},appendChild(c){this.children.push(c);}};
  [].concat(children||[]).forEach(c=>{if(c!==null&&c!==undefined&&c!=='')n.children.push(c);});
  n.text=function(){return this.children.map(c=>typeof c==='string'?c:c.text?c.text():'').join('');};
  n.all=function(){return [this].concat(...this.children.filter(c=>c&&c.all).map(c=>c.all()));};return n;}
const version=JSON.parse(fs.readFileSync('VERSION.json','utf8')).application,number=version.ui_module.replace('dashboard','');
const main=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+version.ui_module+'.js','utf8');
const name='pick'+number+'.js',text=fs.readFileSync('router/files/www/luci-static/resources/homensai-vpn/'+name,'utf8');
assert(version.ui_lazy_modules.includes('homensai-vpn/'+name),'VERSION.json lists the module of this release');
assert(main.includes("var LAZY_PICK_NAME='homensai-vpn.pick"+number+"';"),'the main module loads the module of its own release');
assert(main.includes("put('channels',serverPickBox(status,inventory));"),'the Channels page carries the loader');
assert(!main.includes('function serverPickPanel('),'the panel itself is not in the main module');
const pick=new Function('baseclass',text)({extend:o=>o});
const status={time:1000,server_time:1000,profiles:[{id:'openvpn:40354_2020',name:'Reserve OpenVPN',interface:'ovpnclient2'}],
  server_pick:{time:940,enabled:true,tunnels:[
    {tunnel_id:4192,protocol:'openvpn',interface:'ovpnclient2',current:'40354_2016',best:'40354_2016',ordered:false,code:'SERVER-PICKED',
     last_change:{time:970,from:'40354_2020',to:'40354_2016',from_ms:48,to_ms:21,from_location:'Kyiv',to_location:'Berlin'},
     candidates:[{profile:'40354_2020',location:'Kyiv',latency_ms:48,alive:true},{profile:'40354_2016',location:'Berlin',latency_ms:21,alive:true},{profile:'40354_2011',location:null,latency_ms:null,alive:false}]},
    {tunnel_id:5841,protocol:'wireguard',interface:'wgclient1',current:'10004_2002',best:null,ordered:false,code:null,last_change:null,
     candidates:[{profile:'10004_2002',location:'Berlin',latency_ms:null,alive:null}]}]}};
(async()=>{
for(const language of ['en','ru']){
  for(const stored of [undefined,true]){
    const calls=[],notes=[];const bi=(en,ru)=>language==='ru'?ru:en;
    const ctx={E:node,bi,status,inventory:{settings:Object.assign({response_metric:'icmp-8.8.8.8'},stored===undefined?{}:{server_pick:stored})},
      ui:{addNotification(_,n){notes.push(n.text());}},errorCodeLink:code=>node('a',{'data-code':code},[code]),
      rpc:{declare:spec=>(...args)=>{calls.push([spec.method,spec.params].concat(args));return Promise.resolve({saved:true});}}};
    const panel=pick.render(ctx),all=panel.all(),box=all.find(n=>n.attrs['class']==='hv-server-pick-switch');
    assert.strictEqual(box.checked,stored===true,'off unless the owner switched it on');
    assert(panel.text().includes(language==='ru'?'Подбирать лучший сервер':'Pick the best server'));
    const channels=all.filter(n=>n.attrs['class']==='hv-server-pick-channel');
    assert.strictEqual(channels.length,2);assert(channels[0].text().includes('Reserve OpenVPN'),'the channel name of the monitor row');
    assert(channels[1].text().includes('WireGuard · wgclient1'),'a channel without a monitor row is named by protocol and interface');
    const items=channels[0].all().filter(n=>n.tag==='li');
    assert.deepStrictEqual(items.map(n=>n.attrs['data-best']),['false','true','false']);
    assert.deepStrictEqual(items.map(n=>n.attrs['data-current']),['false','true','false']);
    assert(items[1].text().includes(language==='ru'?'21 мс':'21 ms')&&items[2].text().includes(language==='ru'?'нет ответа':'no answer'));
    assert(channels[1].text().includes(language==='ru'?'не измерен':'not measured'));
    assert(channels[0].text().includes('Kyiv → Berlin, 48 → 21'),'the last change with both pings');
    assert(channels[0].all().some(n=>n.attrs['data-code']==='SERVER-PICKED'),'the code links to the table');
    box.checked=!box.checked;box.listeners.change();await new Promise(r=>setTimeout(r,0));
    assert.deepStrictEqual(calls,[['setup_response',['metric','server_pick'],'icmp-8.8.8.8',stored!==true]],'one setup_response with the current metric');
    assert.strictEqual(notes.length,1);
  }
  const empty=pick.render({E:node,bi:(en,ru)=>language==='ru'?ru:en,status:{},inventory:{},rpc:{},ui:{}});
  assert(empty.text().includes(language==='ru'?'Данных о серверах от роутера пока нет.':'No server data from the router yet.'));
}
console.log('PASS: server pick module (lazy, own release name), per-channel servers with pings, best and current marked, last change, owner switch default off');
})().catch(error=>{console.error(error);process.exitCode=1;});
