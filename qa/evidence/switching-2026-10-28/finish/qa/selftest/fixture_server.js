/* Loopback-only SYNTHETIC LuCI imitation for self-testing real_click_chain.js.
 * Serves: a LuCI-shaped login form, the exact generated dashboard through qa/ui-preview,
 * and a ubus JSON-RPC endpoint (/ubus/) whose homensai-vpn status/inventory/pair_manual
 * are a small synthetic state machine. No router, controller, QEMU or kernel is involved.
 * Exports start({repo,dashboard,port,user,pass}) -> {url,close,setMode,state}.
 */
'use strict';
const fs=require('fs'),path=require('path'),http=require('http'),crypto=require('crypto');
const hex=()=>crypto.randomBytes(16).toString('hex');
const clone=x=>JSON.parse(JSON.stringify(x));

function start(opt){
  const REPO=path.resolve(opt.repo),PORT=opt.port,USER=opt.user,PASS=opt.pass;
  const assets=path.join(REPO,'router/files/www/luci-static/resources/view/homensai-vpn');
  const moduleBytes=fs.readFileSync(opt.dashboard);
  const version=JSON.parse(fs.readFileSync(path.join(REPO,'VERSION.json'))).application.version;
  const base=JSON.parse(fs.readFileSync(path.join(REPO,'qa/evidence/switching-2026-10-28/browser-copy-final.json'))).steps[0].state.status;
  const SESSION=hex(),COOKIE=hex(),STOK=hex();
  const st={active:'source',hold:null,revision:'3c5704d5369941b5af11be3a2ab8a335',transitioning:false,manual:{state:'IDLE',completed:false},budget:[],mode:{},log:[],timers:[]};
  const src=base.channel_path.source_profile_id,dst=base.channel_path.target_profile_id;
  function frame(){
    const T=Date.now()/1000,f=clone(base);
    f.version=version;f.time=f.server_time=T;f.observation_valid_for=900;
    f.native_failover={...f.native_failover,state:st.active==='target'?'HELD-ON-RESERVE':'OBSERVING',time:T-2,readiness_verified:true};
    f.auto_control={...f.auto_control,requested:'on',requested_at:T-600,pair_phase:st.hold?'HELD':'RUNNING',control_revision:st.revision};
    f.channel_path={...f.channel_path,time:T,checked_at:T,valid_for:15,confirmed:!st.transitioning,kernel_policy_verified:!st.transitioning,transitioning:st.transitioning,
      active_profile_id:st.active==='source'?src:dst};
    f.manual_switch=clone(st.manual);
    const busy=['QUEUED','CLAIMED'].includes(st.manual.state);
    f.manual_switch_control={...f.manual_switch_control,time:T,observation_valid_for:900,control_revision:st.revision,hold:st.hold,
      primary:{allowed:!busy,blockers:busy?['PAIR-MANUAL-BUSY']:[]},reserve:{allowed:!busy,blockers:busy?['PAIR-MANUAL-BUSY']:[]},
      resume:{allowed:!busy&&!!st.hold,blockers:[]}};
    for(const p of f.profiles){p.time=T;p.observation_valid_for=900;p.vendor_changed_at=T-120;p.code=null;p.dns_ok=true;p.https_success=2;if(p.website_response){p.website_response.time=T-5;p.website_response.valid_for=45;}}
    if(f.vendor_observation){f.vendor_observation.time=T;for(const g of f.vendor_observation.groups){g.time=T;g.changed_at=T-120;}}
    return f;
  }
  const inventory=()=>{const f=frame();return {profiles:f.profiles,servers:f.profiles.map((p,i)=>({profile:p.id,name:p.name,priority:i+1,enabled:true})),
    settings:{terms_version:'1',setup_complete:true,onboarding_complete:true,onboarding_version:1,enabled:true,plan_enabled:true,plan_source:src,plan_target:dst,pair_auto_mode:'continuous-pair',native_duration:10,interval:30,checkpoint:900,telegram_enabled:false}};};
  const later=(ms,fn)=>st.timers.push(setTimeout(fn,ms));
  function pairManual(a){
    const now=Date.now()/1000;st.log.push({t:now,args:a});
    if(st.mode.refuse)return {accepted:false,queued:false,completed:false,blockers:['PAIR-MANUAL-COOLDOWN']};
    if(!['primary','reserve','resume'].includes(a.direction)||a.control_revision!==st.revision)return {accepted:false,queued:false,completed:false,blockers:['CONTROL-REVISION-STALE']};
    if(['QUEUED','CLAIMED'].includes(st.manual.state))return {accepted:false,queued:false,completed:false,blockers:['PAIR-MANUAL-BUSY']};
    const id=hex(),role=a.direction==='primary'?'source':a.direction==='reserve'?'target':null;
    st.manual={state:'QUEUED',direction:a.direction,request_id:id,requested_at:now,updated_at:now,request_source:a.request_source||'unknown',completed:false,code:null};
    const upd=(s,extra)=>{st.manual={...st.manual,state:s,updated_at:Date.now()/1000,completed:s==='COMPLETED',...extra};};
    later(2500,()=>upd('CLAIMED'));
    if(role){later(4500,()=>{st.transitioning=true;});later(4000,()=>{st.budget.push(Date.now()/1000);});later(9000,()=>{st.transitioning=false;st.active=role;st.hold=role;upd('COMPLETED');});}
    else later(5000,()=>{st.hold=null;upd('COMPLETED');});
    return {accepted:true,queued:true,completed:false,request_id:id,control_revision:st.revision};
  }
  const BRIDGE=`
window.__qaSeq=0;const qaFallbackRPC=window.rpc;
window.rpc={declare:spec=>{const old=qaFallbackRPC.declare(spec);return(...args)=>{
  if(!['status','inventory','pair_manual'].includes(spec.method))return old(...args);
  const named={};(spec.params||[]).forEach((k,i)=>{if(args[i]!==undefined)named[k]=args[i];});
  return fetch('/ubus/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({jsonrpc:'2.0',id:++window.__qaSeq,method:'call',params:[window.__qaSession,'homensai-vpn',spec.method,named]})})
   .then(r=>r.json()).then(j=>{if(!j.result||j.result[0]!==0)throw Error('UBUS-'+(j.error?j.error.code:'ERR'));return j.result[1];});};}};
setInterval(()=>{if(window.fixturePoll)window.fixturePoll();},3000);
`;
  let stub=fs.readFileSync(path.join(REPO,'qa/ui-preview/stub.js'),'utf8');const anchor="fetch('/preview-module.js',{cache:'no-store'})";
  if(stub.split(anchor).length!==2)throw Error('STUB_ANCHOR');stub=stub.replace(anchor,BRIDGE+anchor);
  const index=fs.readFileSync(path.join(REPO,'qa/ui-preview/index.html'),'utf8').replace('<div id="app">','<script>window.__qaSession='+JSON.stringify(SESSION)+';</script><div id="app">');
  const login='<!doctype html><html><head><meta charset="utf-8"><title>LuCI (synthetic)</title></head><body><form method="post" action=""><input name="luci_username" value=""><input type="password" name="luci_password"><button class="btn cbi-button cbi-button-positive" type="submit">Login</button></form></body></html>';
  const authed=req=>(req.headers.cookie||'').split(/;\s*/).includes('sysauth_http='+COOKIE);
  const prefix='/router/files/www/luci-static/resources/view/homensai-vpn/';
  const server=http.createServer((req,res)=>{
    const url=new URL(req.url,'http://127.0.0.1');let body=[];
    req.on('data',c=>body.push(c));req.on('end',()=>{
      body=Buffer.concat(body).toString();
      try{
        if(req.headers.host!=='127.0.0.1:'+PORT){res.writeHead(403);return res.end();}
        const page=url.pathname==='/cgi-bin/luci/admin/services/homensai-vpn'||url.pathname==='/cgi-bin/luci/;stok='+STOK+'/admin/services/homensai-vpn';
        if(page&&req.method==='POST'){
          const f=new URLSearchParams(body);
          if(f.get('luci_username')===USER&&f.get('luci_password')===PASS){res.writeHead(302,{'Set-Cookie':'sysauth_http='+COOKIE+'; path=/; HttpOnly','Location':'/cgi-bin/luci/;stok='+STOK+'/admin/services/homensai-vpn'});return res.end();}
          res.writeHead(403,{'Content-Type':'text/html'});return res.end(login);
        }
        if(page){res.writeHead(200,{'Content-Type':'text/html','Cache-Control':'no-store'});return res.end(authed(req)?index:login);}
        if(url.pathname==='/__fixture/snapshot'){
          // SYNTHETIC kernel_snapshot.py-shaped JSON derived from fixture state (no kernel exists here).
          const order=st.active==='source'?['rule_primary','rule_reserve','rule_other']:['rule_reserve','rule_primary','rule_other'];
          const h=x=>crypto.createHash('sha256').update(x).digest('hex');const m=st.manual;
          const snap={schema:'homensai-kernel-snapshot/1',label:'synthetic',synthetic:true,uci_route_policy:{order,output_sha256:h(order.join())},
            mangle:{normalized_sha256:h('mangle'+st.active)},ip_rules:{sha256:h('rules')},product_kernel_fingerprint:{value:h('fp'+st.active)},routes:{'51':{sha256:h('r')}},
            owned_guard:{exists:false},journal:{envelope_digest_ok:true,summary:{phase:st.active==='target'?'HELD-ON-RESERVE':'COMMITTED',tx:h('tx'+st.budget.length).slice(0,32)}},
            app_files:{'pair-manual-control.json':{data:m.request_id?{id:m.request_id,state:m.state,direction:m.direction,code:m.code||null}:{}},
              'pair-auto-budget.json':{events_count:st.budget.length,last_event:st.budget.length?st.budget[st.budget.length-1]:null}},
            status_json:{subset:{channel_path:{active_profile_id:st.active==='source'?src:dst,source_profile_id:src,target_profile_id:dst}}}};
          res.writeHead(200,{'Content-Type':'application/json'});return res.end(JSON.stringify(snap));
        }
        if(url.pathname==='/ubus/'||url.pathname==='/ubus'){
          if(!authed(req)){res.writeHead(403);return res.end();}
          const one=c=>{const p=c.params||[];if(p[0]!==SESSION)return {jsonrpc:'2.0',id:c.id,error:{code:-32002,message:'Access denied'}};
            const fn=p[2],a=p[3]||{};const data=p[1]!=='homensai-vpn'?{}:fn==='status'?frame():fn==='inventory'?inventory():fn==='pair_manual'?pairManual(a):{};
            return {jsonrpc:'2.0',id:c.id,result:[0,data]};};
          const j=JSON.parse(body),out=Array.isArray(j)?j.map(one):one(j);
          const isManual=(Array.isArray(j)?j:[j]).some(c=>(c.params||[])[2]==='pair_manual');
          if(isManual&&st.mode.dropAck){st.mode.dropAck=false;req.socket.destroy();return;}
          res.writeHead(200,{'Content-Type':'application/json'});return res.end(JSON.stringify(out));
        }
        let b,type='application/javascript';
        if(url.pathname==='/qa/ui-preview/stub.js')b=stub;
        else if(url.pathname==='/preview-module.js')b=moduleBytes;
        else if(url.pathname==='/preview-router.js')b='window.HOMENSAI_PREVIEW_ROUTER_ORIGIN=null;';
        else if(url.pathname.startsWith(prefix)){const file=path.resolve(assets,url.pathname.slice(prefix.length));if(!file.startsWith(assets+path.sep)||!/\.(css|svg|png|woff2?|ttf|js)$/.test(file))throw Error('REFUSED');b=fs.readFileSync(file);type=file.endsWith('.css')?'text/css':file.endsWith('.svg')?'image/svg+xml':'application/octet-stream';}
        else{res.writeHead(404);return res.end();}
        res.writeHead(200,{'Content-Type':type,'Cache-Control':'no-store'});res.end(b);
      }catch(e){if(!res.headersSent)res.writeHead(500);res.end();}
    });
  });
  return new Promise(resolve=>server.listen(PORT,'127.0.0.1',()=>resolve({url:'http://127.0.0.1:'+PORT,state:st,secrets:[SESSION,COOKIE,STOK],setMode:m=>Object.assign(st.mode,m),
    dashboardSha256:crypto.createHash('sha256').update(moduleBytes).digest('hex'),
    close:()=>{st.timers.forEach(clearTimeout);server.closeAllConnections&&server.closeAllConnections();return new Promise(r=>server.close(r));}})));
}
module.exports={start};
