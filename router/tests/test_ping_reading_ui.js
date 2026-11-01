// Owner rules (31 Oct 2026): a separately configurable ping (Settings, 10 s .. 5 min, default 1 min) and one shared
// ping reading for every table, card and statistics view: the last measured value with its age, "42 ms (12 s ago)".
// A dash only when the router never measured that channel; an old ping keeps its value and age.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{
  constructor(tag,attrs,children){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children||[]).flat().filter(x=>x!=null);this.listeners={};}
  addEventListener(e,f){this.listeners[e]=f;}setAttribute(k,v){this.attrs[k]=v;}removeAttribute(k){delete this.attrs[k];}getAttribute(k){return this.attrs[k];}
  appendChild(c){this.children.push(c);return c;}removeChild(c){this.children.splice(this.children.indexOf(c),1);}get firstChild(){return this.children[0]||null;}
  all(){return [this,...this.children.flatMap(x=>x instanceof N?x.all():[])];}
  text(){return this.children.map(x=>x instanceof N?x.text():String(x)).join('');}
}
const NOW=100000,SOURCE='wireguard:peer_1',TARGET='openvpn:1_1';
const inventory={settings:{plan_source:SOURCE,plan_target:TARGET}};
function profile(id,iface,ping,last){
  return {id,protocol:id.split(':')[0],interface:iface,vendor_tunnel_id:id.split(':')[0]+':'+iface,vendor_generation:'a'.repeat(32),vendor_state:'SETTLED',
    administrative_state:'enabled',time:NOW,code:null,dns_ok:true,https_success:2,rtt_ms:777,ping,ping_last:last===undefined?null:last};
}
function ping(state,extra){return Object.assign({metric:'icmp-rtt-ms',target:'1.1.1.1',state,code:state==='ok'?null:'PING-X',time:NOW-3,rtt_ms:state==='ok'?40:null,valid_for:105,interface:'wgclient1'},extra||{});}
const LAST={rtt_ms:42,time:NOW-12,target:'1.1.1.1'};
function status(profiles,extra){return Object.assign({time:NOW,response_metric:'icmp-1.1.1.1',observation_valid_for:90,profiles},extra||{});}
function context(language){
  const c={console,locale:language,bi:(en,ru)=>language==='ru'?ru:en,E:(...a)=>new N(...a),Date,Math,Number,String,Object,Array,JSON,Promise,calls:[],
    document:{createElementNS:(_,tag)=>new N(tag)},serverTitle:p=>p.name||p.id,protocolLabel:p=>p.protocol,statusNow:()=>NOW,routerWall:()=>NOW,
    ui:{addNotification(){}},localStorage:{getItem:()=>null,setItem(){}},helpLink:(id,label)=>new N('a',{},label)};
  c.rpc={declare:(spec)=>(...args)=>{c.calls.push([spec.method,spec.params].concat(args));return Promise.resolve({saved:true});}};
  vm.createContext(c);
  for(const name of ['ui_logic','channel_guidance','latency_panel','probe_panel'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);
  c.statusNow=()=>NOW;c.profileHealth=()=>({state:'healthy'});
  return c;
}
const DASH=/^\s*—/;
(async()=>{
for(const language of ['en','ru']){
  const c=context(language),ms=language==='ru'?'мс':'ms',ago=language==='ru'?'с назад':'s ago';
  // 1. The shared reading: value with its age in brackets, exactly the owner's example.
  const fresh=profile(SOURCE,'wgclient1',ping('ok'),LAST);
  assert.strictEqual(c.pingReading(fresh,status([fresh]),NOW).text,'40.0 '+ms+' (3 '+ago+')','the newer current answer wins');
  const old=profile(SOURCE,'wgclient1',ping('stale',{time:NOW-500,rtt_ms:null}),LAST);
  assert.strictEqual(c.pingReading(old,status([old]),NOW).text,'42.0 '+ms+' (12 '+ago+')');
  assert.strictEqual(c.pingCellText(profile(SOURCE,'wgclient1',ping('checking'),{rtt_ms:42,time:NOW-600,target:'1.1.1.1'}),status([]),NOW),'42.0 '+ms+' (10 '+(language==='ru'?'мин назад':'min ago')+')','an old value keeps its age');
  assert.strictEqual(c.pingCellText(profile(SOURCE,'wgclient1',ping('checking'),null),status([]),NOW),'—','never measured: a dash');
  assert.strictEqual(c.pingReading(undefined,status([]),NOW),null);
  // 2. No ping cell renders a dash while a measurement exists - in any state of the current check or the monitor.
  const states=[ping('checking'),ping('failed'),ping('unavailable'),ping('stale',{rtt_ms:null}),ping('inactive'),undefined,
    ping('ok',{target:'8.8.8.8'}),ping('ok',{interface:'other'}),ping('ok',{time:NOW-1000})];
  const monitors=[{},{time:NOW-600},{rpc_error:'STATUS-REQUEST-FAILED'},{error:'SYSTEM-001'}];
  for(const current of states)for(const monitor of monitors)for(const disabled of [false,true]){
    const p=profile(SOURCE,'wgclient1',current,LAST);if(disabled)p.administrative_state='disabled';
    const s=status([p,profile(TARGET,'ovpnclient2',ping('checking'),LAST)],monitor),label=JSON.stringify({current,monitor,disabled});
    const cell=c.renderChannelPing(p,s,NOW).text();
    assert(!DASH.test(cell),'channel table/card cell shows a dash while a measurement exists: '+cell+' '+label);
    assert(cell.includes('('+(current&&current.state==='ok'&&current.time>LAST.time?NOW-current.time:12)+' '+ago+')'),'value with its age: '+cell+' '+label);
    assert.notStrictEqual(c.channelDelayModel(p,s,NOW).rtt_ms,null,'shared model keeps the value '+label);
    assert(!DASH.test(c.pingCellText(p,s,NOW)),'ranking cell '+label);
    const table=c.renderLatencyStatistics([],NOW-3600,NOW,s,inventory,NOW),cells=table.all().filter(n=>n.attrs['class']==='hv-last-ping');
    assert.strictEqual(cells.length,2,'statistics table has a Last ping cell per channel');
    cells.forEach(n=>assert(!DASH.test(n.text()),'statistics Last ping cell '+n.text()+' '+label));
  }
  // The age never turns into "the VPN is down": the state is "last", the title says an old ping is only old.
  const stale=profile(SOURCE,'wgclient1',ping('failed'),{rtt_ms:42,time:NOW-4000,target:'1.1.1.1'}),node=c.renderChannelPing(stale,status([stale]),NOW);
  assert.strictEqual(node.attrs['data-ping-state'],'last');assert(node.attrs.title.includes(language==='ru'?'не означает, что VPN не работает':'does not mean the VPN is down'));
  // Never measured since the router started: a dash with the reason, as before.
  const never=profile(SOURCE,'wgclient1',ping('checking'),null);
  assert(DASH.test(c.renderChannelPing(never,status([never]),NOW).text()),'never measured: dash with a reason');
  // Websites metric: unchanged three-site path (no ping value is substituted there).
  assert.strictEqual(c.channelDelayModel(fresh,status([fresh],{response_metric:'websites'}),NOW).kind,undefined);

  // 3. Settings: the ping interval control, every 10 s from 10 s to 5 min, default 1 min, saved with setup_response.
  for(const stored of [undefined,60,'abc',15,10,300,120]){
    c.calls=[];const panel=c.responseSettings({settings:{response_metric:'icmp-1.1.1.1',response_compare:false,ping_interval:stored}}),all=panel.all();
    const select=all.find(n=>n.attrs['class']==='hv-ping-interval'),save=all.find(n=>n.tag==='button');
    const options=select.children.map(o=>Number(o.attrs.value));
    assert.deepStrictEqual(options,Array.from({length:30},(_,i)=>10*(i+1)),'every 10 s from 10 s to 5 min');
    const expected=[10,300,120].includes(stored)?stored:60;
    assert.strictEqual(select.value,String(expected),'stored '+stored+' -> '+expected);
    assert.strictEqual(select.children.filter(o=>'selected' in o.attrs&&o.attrs.selected!==null).map(o=>o.attrs.value).join(),String(expected));
    assert('disabled' in save.attrs);
    if(stored!==undefined)continue;
    const labels=select.children.map(o=>o.text());
    assert.strictEqual(labels[0],language==='ru'?'раз в 10 с':'every 10 s');
    assert.strictEqual(labels[5],language==='ru'?'раз в 1 мин (по умолчанию)':'every 1 min (default)');
    assert.strictEqual(labels[6],language==='ru'?'раз в 1 мин 10 с':'every 1 min 10 s');
    assert.strictEqual(labels[29],language==='ru'?'раз в 5 мин':'every 5 min');
    const text=panel.text();
    assert(text.includes(language==='ru'?'Интервал пинга':'Ping interval'));
    assert(text.includes(language==='ru'?'по умолчанию раз в минуту':'default once a minute'));
    assert(text.includes(language==='ru'?'нагрузка на процессор роутера и трафик':'router a little more CPU and traffic'),'more frequent = more router CPU/traffic');
    select.value='20';select.listeners.change();assert(!('disabled' in save.attrs),'a changed interval can be saved');
    select.value='60';select.listeners.change();assert('disabled' in save.attrs,'back to the stored value');
    select.value='20';select.listeners.change();save.listeners.click();await new Promise(r=>setTimeout(r,0));
    assert.strictEqual(JSON.stringify(c.calls.pop()),JSON.stringify(['setup_response',['metric','compare','fast_switch','ping_interval'],'icmp-1.1.1.1',false,true,20]));
    assert('disabled' in save.attrs,'saved: waits for the next change');
  }
  assert.strictEqual(c.pingIntervalValue('20'),20);assert.strictEqual(c.pingIntervalValue(25),60);assert.strictEqual(c.pingIntervalValue(400),60);
}
// 4. Every page surface that shows a ping or response value reads the shared core, never the strict current-only model.
const sources=fs.readdirSync('router').filter(n=>n.endsWith('.inc.js'));
const strict=[];
for(const name of sources){
  const text=fs.readFileSync('router/'+name,'utf8');
  text.split(/\r?\n/).forEach((line,i)=>{if(/channelPingModel\(/.test(line)&&!/function channelPingModel|channelDelayModel:channelPingModel|var model=channelPingModel\(p,status,now\),id=p&&p.id/.test(line))strict.push(name+':'+(i+1)+': '+line.trim().slice(0,90));});
}
// Allowed strict uses: the status signature (ui_logic), the CSV export of the current check, and the dead journal helper removed by the build.
assert.deepStrictEqual(strict.filter(l=>!/^ui_logic\.inc\.js:\d+: \(status\.profiles\|\|\[\]\)\.map\(function\(p\)\{var ping=channelPingModel|^analytics_panel\.inc\.js:\d+:\s+latency_ms:channelPingModel|^journal_panel\.inc\.js:\d+: function journalCurrentLatency/.test(l)),[],
  'ping display outside the shared reading: '+strict.join(' | '));
for(const [name,needle] of [['live_terminal.inc.js',"(typeof channelDelayModel==='function'?channelDelayModel:channelPingModel)(p,status,now)"],
    ['minimum_channels.inc.js','channelDelayModel(profile,status,now)'],['latency_panel.inc.js','pingCellText(p,status,now)'],
    ['build_sidebar_ui.py',"pingCellText(item.p,status,statusNow(status))"]])
  assert(fs.readFileSync('router/'+name,'utf8').includes(needle),name+' reads the shared ping reading');
// The built page carries the same wiring (ranking column, settings control).
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const built=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+menu['admin/services/homensai-vpn'].action.path.split('/').pop()+'.js','utf8');
for(const needle of ['function pingReading(','pingCellText(item.p,status,statusNow(status))','bi("Last ping","Последний пинг")',"'hv-ping-interval'","params:['metric','compare','fast_switch','ping_interval']"])
  assert(built.includes(needle),'built module: '+needle);
console.log('PASS: owner ping interval control (10 s..5 min, default 1 min, EN/RU) and one shared ping reading with its age on every table; dash only when never measured');
})().catch(e=>{console.error(e);process.exit(1);});
