/* HomenS.AI Auto VPN - one physical browser click, end-to-end chain recorder.
 *
 * Scope: REAL installed LuCI page (or the loopback self-test fixture). Exactly ONE
 * Playwright mouse click on the real rendered element; never a JS function call,
 * console call, curl or direct RPC. Everything after the click is observation only.
 *
 * Env (required): QA_BASE_URL  e.g. http://192.168.12.1
 *                 QA_LUCI_PASS (QA_LUCI_USER defaults to root) - read from env, never logged or saved
 *                 QA_ACTION    to-reserve | to-primary | reselect-current | resume
 *                 QA_OUT       new or empty directory for the evidence
 * Env (optional): QA_PLAYWRIGHT (path to playwright package), QA_CHROMIUM (chrome.exe),
 *                 QA_TIMEOUT_S=180 (observation after the click), QA_SETTLE_S=15 (after terminal),
 *                 QA_PRECONDITION_WAIT_S=90, QA_NO_COMMAND_WINDOW_S=30 (reselect-current),
 *                 QA_DRY_RUN=1 (everything except the click), QA_OBSERVER=0 (disable Minimum tab),
 *                 QA_LANG=en|ru (default en; written to the fresh browser profile only), QA_DESIGN=a|b|c,
 *                 QA_EXPECT_VERSION (refuse if status.version differs), QA_MASK_PUBLIC_IP=1 (default),
 *                 QA_PAGE_PATH=/cgi-bin/luci/admin/services/homensai-vpn, QA_HEADED=1,
 *                 QA_ALLOW_PUBLIC_HOST=1 (otherwise only RFC1918/loopback base URLs are accepted),
 *                 QA_SNAPSHOT_CMD: optional local shell command that prints kernel_snapshot.py JSON
 *                   (e.g. your SSH helper piping it to python3 -). It runs with QA_SNAPSHOT_LABEL=before|after,
 *                   without QA_LUCI_PASS in its env; output saved as kernel-<label>.json. A failed 'before'
 *                   snapshot refuses the click. This script itself never opens SSH.
 *                 QA_HARD_LIMIT_S (default timeout+settle+precondition+600): watchdog that saves evidence and exits.
 * Never set DEBUG=pw:api while running: Playwright would then print the fill() value.
 * Terms are never accepted by this script; Auto is never started or stopped by it.
 */
'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto'),cp=require('child_process');
const PW_PATH=process.env.QA_PLAYWRIGHT||'playwright';
const {chromium}=require(PW_PATH);

const ACTIONS={'to-reserve':'reserve','to-primary':'primary','reselect-current':null,'resume':'resume'};
const TERMINAL=['COMPLETED','REFUSED','CANCELLED','UNCONFIRMED'],PENDING=['QUEUED','CLAIMED','APPLYING','WAIT-CLIENT'];
const env=k=>process.env[k];
const num=(k,d)=>{const v=Number(env(k));return Number.isFinite(v)&&v>0?v:d;};
const CFG={
  base:env('QA_BASE_URL'),user:env('QA_LUCI_USER')||'root',action:env('QA_ACTION'),out:env('QA_OUT'),
  pagePath:env('QA_PAGE_PATH')||'/cgi-bin/luci/admin/services/homensai-vpn',
  timeoutS:num('QA_TIMEOUT_S',180),settleS:num('QA_SETTLE_S',15),preWaitS:num('QA_PRECONDITION_WAIT_S',90),
  noCommandS:num('QA_NO_COMMAND_WINDOW_S',30),dryRun:env('QA_DRY_RUN')==='1',observer:env('QA_OBSERVER')!=='0',
  lang:env('QA_LANG')||'en',design:env('QA_DESIGN')||null,expectVersion:env('QA_EXPECT_VERSION')||null,
  maskIp:env('QA_MASK_PUBLIC_IP')!=='0',headed:env('QA_HEADED')==='1',allowPublic:env('QA_ALLOW_PUBLIC_HOST')==='1',
};
const PASS=env('QA_LUCI_PASS');
const SNAP_CMD=env('QA_SNAPSHOT_CMD')||null;
const T0=Date.now();
const rel=()=>Date.now()-T0;
const iso=t=>new Date(t).toISOString();
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
/* Every browser observation is bounded: a hung renderer must not freeze the evidence loop. */
const within=(promise,ms,label)=>Promise.race([promise,new Promise((_,rej)=>setTimeout(()=>rej(Error('TIMEOUT-'+label+'-'+ms+'MS')),ms))]);
async function shot(page,name){
  if(!page||!OUT)return;
  try{await within(page.screenshot({path:path.join(OUT,name),fullPage:true,timeout:15000}),20000,'SCREENSHOT');report.screenshots.push(name);}
  catch(e){report.errors.push('SCREENSHOT-FAILED:'+name+':'+String(e.message).split(String.fromCharCode(10))[0].slice(0,160));}
}

/* ---------- redaction ---------- */
const SECRET_KEY=/^(?:.*[_-])?(?:token|secret|password|passwd|psk|private_?key|preshared_?key|cookie|sysauth\w*|stok|ubus_rpc_session|sessionid|api_?key|auth_?key|bot_?token|chat_?id)$/i;
const SCRUB=new Set();
function publicV4(a){const p=a.split('.').map(Number);if(p.some(x=>x>255))return false;const [x,y]=p;
  return !(x===10||x===127||x===0||x>=224||x===169&&y===254||x===172&&y>=16&&y<=31||x===192&&y===168||x===100&&y>=64&&y<=127);}
function maskString(s){
  if(typeof s!=='string')return s;
  s=s.replace(/;stok=[^/?#\s"']+/g,';stok=[redacted]');
  for(const v of SCRUB)if(v&&v.length>=4)s=s.split(v).join('[redacted]');
  if(CFG.maskIp)s=s.replace(/\b(\d{1,3}(?:\.\d{1,3}){3})\b/g,m=>publicV4(m)?'pubip-'+sha('homensai-qa:'+m).slice(0,10):m);
  return s;
}
function redact(v,depth=0){
  if(depth>40)return '[depth]';
  if(Array.isArray(v))return v.map(x=>redact(x,depth+1));
  if(v&&typeof v==='object'){const o={};for(const [k,x] of Object.entries(v))o[k]=SECRET_KEY.test(k)?(x==null||x===''?x:'[redacted]'):redact(x,depth+1);return o;}
  return maskString(v);
}

/* ---------- output ---------- */
function prepareOut(){
  if(!CFG.out)throw Error('QA_OUT-REQUIRED');
  const out=path.resolve(CFG.out);
  if(fs.existsSync(out)&&fs.readdirSync(out).length)throw Error('QA_OUT-MUST-BE-NEW-OR-EMPTY (failed evidence is never overwritten)');
  fs.mkdirSync(out,{recursive:true});return out;
}
let OUT=null;
const report={schema:'homensai-real-click-chain/1',
  scope:'Playwright Chromium on the page served by QA_BASE_URL; one physical mouse click on the rendered element; RPC/status recorded from the browser network; kernel truth must come from kernel_snapshot.py before/after.',
  started_at:iso(T0),config:null,identity:{},login:{},precondition:null,click:null,rpc:{commands:[],request_id:null,correlation:null},
  chain:{},timeline:[],network:[],screenshots:[],checks:[],outcome:null,verdict:null,errors:[],page_errors:[]};
function save(){
  if(!OUT)return;
  const text=JSON.stringify(redact(report),null,2)+'\n';
  fs.writeFileSync(path.join(OUT,'report.json'),text);
}
const statusLog=[];let statusStream=null;
function appendFrame(row){if(statusStream)statusStream.write(JSON.stringify(redact(row))+'\n');}

/* ---------- network capture (ubus JSON-RPC) ---------- */
let netSeq=0;const pendingRpc=new Map();
let lastStatus=null,lastStatusAt=null;const statusHistory=[];
function ubusPath(u){return /\/ubus\/?$/.test(u.pathname)||/\/admin\/ubus\/?$/.test(u.pathname);}
function summarizeStatus(s){
  if(!s||typeof s!=='object')return null;
  const pick=(o,keys)=>{if(!o||typeof o!=='object')return o==null?null:'[non-object]';const r={};for(const k of keys)if(k in o)r[k]=o[k];return r;};
  const msc=s.manual_switch_control||{};
  return {version:s.version,package:s.package,time:s.time,server_time:s.server_time,
    manual_switch:s.manual_switch||null,
    manual_switch_control:{...pick(msc,['available','mode','time','control_revision','hold','observation_valid_for','blockers']),
      primary:msc.primary||null,reserve:msc.reserve||null,resume:msc.resume||null},
    channel_path:pick(s.channel_path,['time','checked_at','valid_for','confirmed','kernel_policy_verified','transitioning','active_profile_id','source_profile_id','target_profile_id','configured_profile_id','mode','selection_proof','code']),
    native_failover:pick(s.native_failover,['state','reason','time','mode','source','target','original_restored','blockers','proof_scope']),
    auto_control:pick(s.auto_control,['requested','requested_at','pair_phase','control_revision','failure']),
    profiles:Array.isArray(s.profiles)?s.profiles.map(p=>({id:p.id,time:p.time,code:p.code,dns_ok:p.dns_ok,https_success:p.https_success,
      website_response:p.website_response?pick(p.website_response,['time','valid_for','mean_ms','coverage','state']):null})):null};
}
function roleOf(s){
  const p=s&&s.channel_path;if(!p)return null;
  if(p.transitioning===true)return 'moving';
  if(p.confirmed!==true||p.kernel_policy_verified!==true)return 'unverified';
  return p.active_profile_id===p.source_profile_id?'primary':p.active_profile_id===p.target_profile_id?'reserve':'unknown';
}
function attachNetwork(context,origin,tabOf){
  context.on('request',req=>{
    let u;try{u=new URL(req.url());}catch(e){return;}
    const tab=tabOf(req);
    if(u.origin!==origin){report.network.push({seq:++netSeq,t_ms:rel(),tab,kind:'external',host:u.host,method:req.method()});return;}
    const row={seq:++netSeq,t_ms:rel(),wall:iso(Date.now()),tab,method:req.method(),path:maskString(u.pathname),resource:req.resourceType()};
    if(req.method()==='POST'&&ubusPath(u)){
      row.kind='ubus';let body=null;try{body=JSON.parse(req.postData()||'null');}catch(e){row.parse_error=true;}
      const calls=(Array.isArray(body)?body:[body]).filter(Boolean).map(c=>{
        const p=Array.isArray(c.params)?c.params:[];if(typeof p[0]==='string')SCRUB.add(p[0]);
        const app=p[1]==='homensai-vpn';
        return {id:c.id,jsonrpc_method:c.method,object:typeof p[1]==='string'?p[1]:null,fn:typeof p[2]==='string'?p[2]:null,args:app?redact(p[3]):undefined};
      });
      row.calls=calls;pendingRpc.set(req,row);
      for(const c of calls)if(c.object==='homensai-vpn'&&!['status','inventory'].includes(c.fn)){
        const cmd={seq:row.seq,t_ms:row.t_ms,wall:row.wall,tab,fn:c.fn,args:c.args,response:null};report.rpc.commands.push(cmd);row.command=cmd;
        if(!report.chain.rpc_sent_ms&&c.fn==='pair_manual')report.chain.rpc_sent_ms=row.t_ms;
      }
    }else if(req.method()!=='GET'){row.kind='other-post';}
    report.network.push(row);
  });
  context.on('requestfailed',req=>{
    const row=pendingRpc.get(req);const f=req.failure();
    const rec={seq:++netSeq,t_ms:rel(),tab:tabOf(req),kind:'failed',path:(()=>{try{return maskString(new URL(req.url()).pathname);}catch(e){return null;}})(),error:f&&f.errorText,of_seq:row?row.seq:null};
    report.network.push(rec);
    if(row&&row.command){row.command.response={failed:true,error:f&&f.errorText,t_ms:rec.t_ms};}
  });
  context.on('response',async res=>{
    const req=res.request();let u;try{u=new URL(res.url());}catch(e){return;}
    if(u.origin!==origin)return;
    const row=pendingRpc.get(req);
    if(!row){
      if(/homensai-vpn\/[^/]+\.(?:js|css)$/.test(u.pathname)){
        try{const b=await res.body();(report.identity.served_assets=report.identity.served_assets||[]).push({path:u.pathname.split('/').slice(-2).join('/'),status:res.status(),bytes:b.length,sha256:sha(b),t_ms:rel()});}catch(e){}
      }
      return;
    }
    pendingRpc.delete(req);
    const resp={seq:++netSeq,t_ms:rel(),wall:iso(Date.now()),tab:row.tab,kind:'ubus-response',of_seq:row.seq,http_status:res.status(),results:[]};
    let body=null;try{body=JSON.parse(await res.text());}catch(e){resp.parse_error=true;}
    const list=Array.isArray(body)?body:[body];
    for(const call of row.calls){
      const r=list.find(x=>x&&x.id===call.id)||(list.length===1?list[0]:null);
      const result=r&&Array.isArray(r.result)?r.result:null,data=result?result[1]:undefined,code=result?result[0]:(r&&r.error?r.error.code:null);
      const out={id:call.id,object:call.object,fn:call.fn,ubus_code:code};
      if(call.object==='homensai-vpn'){
        if(call.fn==='status'&&data&&typeof data==='object'){
          const sum=summarizeStatus(data);out.status=sum;out.role=roleOf(data);
          lastStatus=data;lastStatusAt=resp.t_ms;statusHistory.push({t_ms:resp.t_ms,tab:row.tab,summary:sum,role:out.role});
          appendFrame({t_ms:resp.t_ms,wall:resp.wall,tab:row.tab,status:data});
          if(!report.identity.status_version){report.identity.status_version=data.version;report.identity.status_package=data.package;}
        }else if(call.fn==='inventory'){out.inventory_keys=data&&typeof data==='object'?Object.keys(data):null;}
        else{out.data=redact(data);if(r&&r.error)out.error=redact(r.error);}
      }
      resp.results.push(out);
      if(row.command&&call.object==='homensai-vpn'&&call.fn===row.command.fn)row.command.response={t_ms:resp.t_ms,http_status:resp.http_status,ubus_code:code,data:out.data,error:out.error};
    }
    report.network.push(resp);
  });
}

/* ---------- DOM snapshot (read-only page.evaluate) ---------- */
async function zones(page){
  return page.evaluate(()=>{
    const vis=n=>{if(!n)return false;const r=n.getBoundingClientRect(),s=getComputedStyle(n);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden';};
    const txt=(n,l=400)=>n?(n.innerText||n.textContent||'').replace(/\s+/g,' ').trim().slice(0,l):null;
    const all=(sel,f)=>[...document.querySelectorAll(sel)].map(f);
    const page=document.querySelector('[data-hv-page]:not([hidden])');
    return {
      url_hash:location.hash,visible_page:page?page.getAttribute('data-hv-page'):null,
      terms_gate:!!document.querySelector('.hv-terms'),login_form:!!document.querySelector('[name=luci_password]'),
      version:txt(document.querySelector('.hv-side-version')),design:(document.querySelector('.hv-app')||{getAttribute:()=>null}).getAttribute('data-hv-design'),
      manual:all('[data-manual-direction]',n=>{const reasonId=n.getAttribute('aria-describedby');return {direction:n.dataset.manualDirection,visible:vis(n),disabled:n.disabled,selected:n.dataset.selected||null,
        pressed:n.getAttribute('aria-pressed'),class:n.className,text:txt(n,300),reason:reasonId?txt(document.getElementById(reasonId)):null};}),
      manual_operation:all('[data-manual-operation]',n=>({state:n.dataset.manualOperation,text:txt(n)})),
      manual_last_result:all('[data-manual-diagnostic="last-request"]',n=>txt(n)),
      manual_recorded:all('[data-manual-result]',n=>({kind:n.dataset.manualResult,text:txt(n)})),
      manual_hold:all('[data-manual-hold]',n=>({hold:n.dataset.manualHold,visible:vis(n),text:txt(n)})),
      auto_state:all('.hv-auto-state',n=>({text:txt(n),class:n.className,visible:vis(n)})),
      auto_power:all('.hv-auto-power',n=>({operation:n.dataset.autoOperation||null,disabled:n.disabled,label:n.getAttribute('aria-label'),busy:n.getAttribute('aria-busy'),class:n.className,visible:vis(n),in_minimum:n.hasAttribute('data-simple-home-auto')})),
      auto_action_timer:all('.hv-auto-action',n=>txt(n)),
      countdowns:all('[class*="countdown"]',n=>({class:n.className,text:txt(n,120)})).filter(x=>x.text),
      light_title:all('.hv-light-title',n=>txt(n)),
      path_nodes:all('[data-path-node]',n=>({node:n.dataset.pathNode,state:n.dataset.pathState,tone:n.dataset.nodeTone})),
      sidebar:all('.hv-side-lamp',n=>{const k=n.querySelector('.hv-auto-pill-knob');return {text:txt(n.querySelector('.hv-auto-pill-text')),title:n.getAttribute('title'),lamp:k?(k.className.match(/hv-lamp-(\w+)/)||[])[1]||null:null};}),
      minimum:all('[data-simple-home]',n=>({state:n.dataset.simpleHome,visible:vis(n),title:txt(n.querySelector('.hv-simple-state')),route:txt(n.querySelector('.hv-simple-route')),
        monitor:txt(n.querySelector('.hv-simple-monitor')),action:txt(n.querySelector('.hv-simple-action')),
        roles:[...n.querySelectorAll('[data-simple-role]')].map(r=>({role:r.dataset.simpleRole,tone:r.dataset.nodeTone,selection:txt(r.querySelector('.hv-simple-selection'))}))})),
      responses:all('.hv-channel-ping',n=>({where:n.closest('[data-home-response]')?'minimum':n.closest('[data-manual-controls]')?'manual':'other',text:txt(n,120),state:n.dataset.pingState||null,coverage:n.dataset.coverage||null})),
      notifications:all('.alert-message,.qa-notice,#qa-modal,.modal',n=>txt(n,300)).filter(Boolean).slice(0,6),
    };
  });
}
function selectedDirection(z){const s=(z.manual||[]).filter(m=>m.visible&&m.selected==='true'&&(m.direction==='primary'||m.direction==='reserve'));return s.length===1?s[0].direction:s.length?'multiple':null;}
function card(z,d){return (z.manual||[]).find(m=>m.visible&&m.direction===d)||null;}

/* ---------- precondition ---------- */
function precondition(z,status){
  const sel=selectedDirection(z),role=roleOf(status),reasons=[];
  const pendingUi=(z.manual_operation||[]).length>0,ms=(status&&status.manual_switch)||{};
  if(z.terms_gate)reasons.push('TERMS-GATE-SHOWN-NOT-ACCEPTING');
  if(!status)reasons.push('NO-STATUS-RPC-SEEN');
  if(pendingUi)reasons.push('UI-OPERATION-PENDING');
  if(PENDING.includes(ms.state))reasons.push('BACKEND-REQUEST-PENDING:'+ms.state);
  if(CFG.expectVersion&&status&&status.version!==CFG.expectVersion)reasons.push('VERSION-MISMATCH:'+status.version);
  if(status&&sel&&role!==sel)reasons.push('DOM-STATUS-DISAGREE:dom='+sel+',status='+role);
  let direction=ACTIONS[CFG.action],force=false;
  if(CFG.action==='to-reserve'||CFG.action==='to-primary'){
    const other=direction==='reserve'?'primary':'reserve',c=card(z,direction);
    if(sel!==other)reasons.push('EXPECTED-'+other.toUpperCase()+'-SELECTED:dom='+sel);
    if(!c)reasons.push('BUTTON-NOT-VISIBLE:'+direction);else if(c.disabled)reasons.push('BUTTON-DISABLED:'+direction+(c.reason?':'+c.reason:''));
  }else if(CFG.action==='reselect-current'){
    if(sel!=='primary'&&sel!=='reserve')reasons.push('NO-SINGLE-SELECTED-CHANNEL:dom='+sel);
    direction=sel;force=true;
    const c=sel&&card(z,sel);if(c&&!c.disabled)reasons.push('SELECTED-CARD-UNEXPECTEDLY-ENABLED');
  }else if(CFG.action==='resume'){
    const h=(z.manual_hold||[]).filter(x=>x.visible);if(!h.length)reasons.push('NO-MANUAL-HOLD-SHOWN');
    const c=card(z,'resume');if(!c)reasons.push('RESUME-BUTTON-NOT-VISIBLE');else if(c.disabled)reasons.push('RESUME-BUTTON-DISABLED');
  }
  return {ok:reasons.length===0,reasons,direction,force,dom_selected:sel,status_role:role};
}

/* ---------- optional kernel snapshots through an operator-provided command ---------- */
function runSnapshot(label){
  if(!SNAP_CMD)return Promise.resolve(null);
  const t=rel(),childEnv={...process.env,QA_SNAPSHOT_LABEL:label};delete childEnv.QA_LUCI_PASS;
  return new Promise(resolve=>cp.exec(SNAP_CMD,{env:childEnv,timeout:120000,maxBuffer:64*1024*1024,windowsHide:true},(err,stdout,stderr)=>{
    const row={label,t_ms:t,ms:rel()-t,file:'kernel-'+label+'.json',ok:false};
    try{fs.writeFileSync(path.join(OUT,row.file),stdout||'');}catch(e){}
    if(err)row.error=maskString(String(err.message).slice(0,300));
    try{row.json=JSON.parse(stdout);row.ok=!err&&!!row.json&&row.json.schema==='homensai-kernel-snapshot/1';}catch(e){row.parse_error=true;}
    if(stderr)row.stderr=maskString(String(stderr).slice(0,400));
    resolve(row);
  }));
}
function kernelSummary(j){
  if(!j)return null;const f=(j.app_files||{}),pm=(f['pair-manual-control.json']||{}).data||{},b=f['pair-auto-budget.json']||{},js=(j.journal||{}).summary||{};
  const sub=((j.status_json||{}).subset||{}).channel_path||{};
  return {uci_order:(j.uci_route_policy||{}).order,uci_sha256:(j.uci_route_policy||{}).output_sha256,mangle_normalized_sha256:(j.mangle||{}).normalized_sha256,
    ip_rules_sha256:(j.ip_rules||{}).sha256,product_kernel_fingerprint:(j.product_kernel_fingerprint||{}).value,
    routes_sha256:Object.fromEntries(Object.entries(j.routes||{}).map(([k,v])=>[k,v.sha256])),guard_exists:(j.owned_guard||{}).exists,
    journal:{phase:js.phase,tx:js.tx,manual_request_id:js.manual_request_id,envelope_ok:(j.journal||{}).envelope_digest_ok},
    pair_manual:{id:pm.id,state:pm.state,direction:pm.direction,code:pm.code},budget_events:b.events_count,budget_last_event:b.last_event,
    status_json_active:sub.active_profile_id,status_json_source:sub.source_profile_id,status_json_target:sub.target_profile_id};
}

/* ---------- main ---------- */
const HARD_S=num('QA_HARD_LIMIT_S',CFG.timeoutS+CFG.settleS+CFG.preWaitS+600);
setTimeout(()=>{report.errors.push('HARD-LIMIT-'+HARD_S+'S-REACHED');report.outcome=report.outcome||'ERROR-HARD-LIMIT';report.verdict='FAIL';try{save();}catch(e){}process.exit(3);},HARD_S*1000).unref();
(async()=>{
  let browser,actor,observer;
  const check=(name,passed,detail)=>report.checks.push({name,passed:!!passed,detail:detail===undefined?null:detail});
  try{
    OUT=prepareOut();statusStream=fs.createWriteStream(path.join(OUT,'status-frames.jsonl'));
    if(!(CFG.action in ACTIONS))throw Error('QA_ACTION-INVALID');
    if(!CFG.base)throw Error('QA_BASE_URL-REQUIRED');
    if(!PASS)throw Error('QA_LUCI_PASS-REQUIRED');
    SCRUB.add(PASS);
    const base=new URL(CFG.base),origin=base.origin;
    if(!/^https?:$/.test(base.protocol))throw Error('QA_BASE_URL-PROTOCOL');
    const host=base.hostname;
    if(!CFG.allowPublic&&!(host==='localhost'||/^(127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(host)))throw Error('QA_BASE_URL-NOT-PRIVATE (set QA_ALLOW_PUBLIC_HOST=1 deliberately)');
    report.config={base:origin,page_path:CFG.pagePath,user_set:!!env('QA_LUCI_USER'),password_set:true,action:CFG.action,timeout_s:CFG.timeoutS,settle_s:CFG.settleS,
      precondition_wait_s:CFG.preWaitS,no_command_window_s:CFG.noCommandS,dry_run:CFG.dryRun,observer:CFG.observer,lang:CFG.lang,design:CFG.design,expect_version:CFG.expectVersion,mask_public_ip:CFG.maskIp};
    report.identity.script_sha256=sha(fs.readFileSync(__filename));
    try{report.identity.playwright=require(path.join(path.dirname(require.resolve(PW_PATH+'/package.json')),'package.json')).version;}catch(e){}
    browser=await chromium.launch({executablePath:env('QA_CHROMIUM')||undefined,headless:!CFG.headed});
    report.identity.browser=browser.version();
    const context=await browser.newContext({viewport:{width:1440,height:1100},ignoreHTTPSErrors:true,serviceWorkers:'block'});
    await context.addInitScript(([lang,design])=>{try{if(lang)localStorage.setItem('homensai-vpn-language',lang);if(design)localStorage.setItem('homensai-vpn-design',design);}catch(e){}},[CFG.lang,CFG.design]);
    const tabs=new Map();const tabOf=req=>{try{return tabs.get(req.frame().page())||'other';}catch(e){return 'worker';}};
    attachNetwork(context,origin,tabOf);
    actor=await context.newPage();tabs.set(actor,'actor');
    actor.on('pageerror',e=>report.page_errors.push({tab:'actor',t_ms:rel(),message:maskString(String(e.message).slice(0,500))}));
    actor.on('dialog',d=>{report.errors.push('UNEXPECTED-DIALOG:'+d.type());d.dismiss().catch(()=>{});});

    /* login */
    const pageUrl=origin+CFG.pagePath;
    await actor.goto(pageUrl,{waitUntil:'domcontentloaded',timeout:60000});
    const pw=actor.locator('input[name="luci_password"]');
    if(await pw.count()){
      const user=actor.locator('input[name="luci_username"]');
      if(await user.count()&&await user.first().isVisible())await user.first().fill(CFG.user);
      await pw.first().fill(PASS);
      report.login.form_seen=true;report.login.submitted_at_ms=rel();
      await Promise.all([actor.waitForNavigation({waitUntil:'domcontentloaded',timeout:60000}).catch(()=>null),pw.first().press('Enter')]);
    }else report.login.form_seen=false;
    try{await actor.waitForSelector('.hv-app, .hv-terms, input[name="luci_password"]',{timeout:120000});}catch(e){throw Error('APP-NOT-RENDERED-120S');}
    if(await actor.locator('input[name="luci_password"]').count()&&!(await actor.locator('.hv-app').count()))throw Error('LOGIN-FAILED');
    if(await actor.locator('.hv-terms').count()){report.outcome='NOT-RUN-TERMS-GATE';throw Error('TERMS-GATE-SHOWN: this script never accepts terms');}
    report.login.ok=true;report.login.app_ready_ms=rel();
    for(const c of await context.cookies())SCRUB.add(c.value);
    /* open the Auto/overview page with the manual panel */
    const urlNoHash=actor.url().split('#')[0];
    // Navigation only (no command): design B keeps manual selection under Channels in a
    // remembered <details>; designs A/C keep it on the overview page.
    report.login.design=await actor.locator('.hv-app').first().getAttribute('data-hv-design').catch(()=>null);
    report.login.navigation=[];
    const manualVisible=()=>actor.locator('[data-manual-controls]').filter({visible:true}).count();
    await actor.waitForTimeout(3000);
    // Same path a person uses: Minimum "Advanced menu" -> Overview tab (A/B legacy layout) or
    // Channels tab + "Manual channel selection" disclosure (minimum composition). View-only clicks.
    const tryClick=async(sel,label)=>{const l=actor.locator(sel).filter({visible:true});if(!(await l.count()))return false;
      await l.first().click({timeout:10000});report.login.navigation.push({click:label,t_ms:rel()});await actor.waitForTimeout(1500);return true;};
    for(let round=0;round<3&&!(await manualVisible());round++){
      await tryClick('[data-simple-open-menu]','advanced-menu');
      if(!(await manualVisible()))await tryClick('[data-hv-tab="overview"]','tab-overview');
      if(!(await manualVisible()))await tryClick('[data-hv-tab="channels"]','tab-channels');
      const d=actor.locator('details[data-minimum-disclosure="manual-selection"]').filter({visible:true});
      if(await d.count()&&!(await d.first().evaluate(n=>n.open))){await d.first().locator('summary').first().click();report.login.navigation.push({click:'manual-selection-disclosure',t_ms:rel()});}
      try{await actor.locator('[data-manual-controls]').filter({visible:true}).first().waitFor({timeout:15000});}catch(e){}
      if(!(await manualVisible())){await actor.goto(urlNoHash+'#overview',{waitUntil:'domcontentloaded'});report.login.navigation.push({goto:'#overview',t_ms:rel()});await actor.waitForTimeout(3000);}
    }
    if(!(await manualVisible()))throw Error('MANUAL-PANEL-NOT-REACHABLE');
    report.login.manual_panel_page=await actor.evaluate(()=>{const n=document.querySelector('[data-manual-controls]');const p=n&&n.closest('[data-hv-page]');return {page:p?p.getAttribute('data-hv-page'):null,hash:location.hash};});
    report.login.manual_panel_ms=rel();
    if(CFG.observer){
      observer=await context.newPage();tabs.set(observer,'observer');
      observer.on('pageerror',e=>report.page_errors.push({tab:'observer',t_ms:rel(),message:maskString(String(e.message).slice(0,500))}));
      await observer.goto(urlNoHash+'#home',{waitUntil:'domcontentloaded'});await observer.waitForSelector('.hv-app',{timeout:120000});
      // Minimum view is display-only; its shortcut button changes only the local view.
      const sc=observer.locator('[data-simple-shortcut]').filter({visible:true});
      try{await observer.locator('[data-simple-home]').filter({visible:true}).first().waitFor({timeout:10000});}
      catch(e){if(await sc.count())await sc.first().click().catch(()=>{});}
    }

    /* precondition: must hold on two consecutive 1 s samples, and both DOM and status agree */
    let pre=null,okRuns=0,samples=0;const preDeadline=Date.now()+CFG.preWaitS*1000;
    while(Date.now()<preDeadline){
      await actor.waitForTimeout(1000);samples++;
      const z=await within(zones(actor),15000,'DOM');pre=precondition(z,lastStatus);pre.dom=z;pre.status=summarizeStatus(lastStatus);pre.status_age_ms=lastStatusAt==null?null:rel()-lastStatusAt;
      okRuns=pre.ok?okRuns+1:0;if(okRuns>=2)break;
    }
    pre.samples=samples;report.precondition=pre;save();
    await shot(actor,'actor-01-start.png');
    {await shot(observer,'observer-01-start.png');}
    if(!pre||okRuns<2){report.outcome='NOT-RUN-PRECONDITION';report.verdict='NOT-RUN';check('precondition matches action',false,pre&&pre.reasons);return;}
    check('precondition matches action',true,{dom_selected:pre.dom_selected,status_role:pre.status_role});
    if(SNAP_CMD){
      const b=await runSnapshot('before');report.kernel={before:{...b,json:undefined,summary:kernelSummary(b.json)}};save();
      if(!b.ok){report.outcome='NOT-RUN-SNAPSHOT-BEFORE-FAILED';report.verdict='NOT-RUN';return;}
      // The snapshot took time; the UI precondition must still hold right before the click.
      const z=await within(zones(actor),15000,'DOM'),again=precondition(z,lastStatus);report.precondition.recheck_after_snapshot={ok:again.ok,reasons:again.reasons};
      if(!again.ok){report.outcome='NOT-RUN-PRECONDITION-CHANGED';report.verdict='NOT-RUN';return;}
    }
    if(CFG.dryRun){report.outcome='DRY-RUN-PRECONDITION-OK';report.verdict='NOT-RUN';return;}

    /* THE click */
    const preStatus=lastStatus,preRole=roleOf(preStatus),preMs=(preStatus&&preStatus.manual_switch)||{},preRev=((preStatus||{}).manual_switch_control||{}).control_revision;
    const preServer=Number.isFinite((preStatus||{}).server_time)?preStatus.server_time:(preStatus||{}).time;
    const commandsBefore=report.rpc.commands.length;
    const target=actor.locator('[data-manual-direction="'+pre.direction+'"]').filter({visible:true}).first();
    // Playwright's locator.click() waits for a "stable" box; the cards animate and are replaced on
    // every status poll, so it can retry for >10 s (seen in self-test). Instead: scroll into view,
    // hit-test the exact point with elementFromPoint, then one real mouse press/release at that point.
    report.click={action:CFG.action,direction:pre.direction,selector:'[data-manual-direction="'+pre.direction+'"] (visible, first)',
      method:'page.mouse.click at the hit-tested centre of the rendered element (real input events; no JS click, no force dispatch)',
      pre_status_role:preRole,pre_request_id:preMs.request_id||null,pre_control_revision:preRev,pre_server_time:preServer,attempts:[]};
    let clicked=false;const clickDeadline=Date.now()+15000;
    while(!clicked&&Date.now()<clickDeadline){
      try{
        // Scrolling only (view change, like a person scrolling); Playwright's own scroll waits for stability too.
        const geo=await within(actor.evaluate(dir=>{
          const vis=n=>{const r=n.getBoundingClientRect(),s=getComputedStyle(n);return r.width>0&&r.height>0&&s.display!=='none'&&s.visibility!=='hidden';};
          const el=[...document.querySelectorAll('[data-manual-direction="'+dir+'"]')].find(vis);if(!el)return null;
          const r0=el.getBoundingClientRect();if(r0.top<0||r0.bottom>innerHeight)el.scrollIntoView({block:'center',inline:'nearest'});
          const r=el.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+Math.min(r.height/2,40),box:{x:r.left,y:r.top,width:r.width,height:r.height}};},pre.direction),3000,'GEO');
        if(!geo){report.click.attempts.push({t_ms:rel(),miss:'NO-VISIBLE-ELEMENT'});await actor.waitForTimeout(200);continue;}
        const x=geo.x,y=geo.y,box=geo.box;
        const hit=await within(actor.evaluate(([x,y])=>{const n=document.elementFromPoint(x,y),b=n&&n.closest('[data-manual-direction]');
          return {dir:b?b.dataset.manualDirection:null,disabled:b?b.disabled:null,selected:b?b.dataset.selected||null:null,tag:n?n.tagName:null};},[x,y]),3000,'HIT');
        const okHit=hit.dir===pre.direction&&(pre.force?true:hit.disabled===false);
        report.click.attempts.push({t_ms:rel(),x:Math.round(x),y:Math.round(y),hit});
        if(!okHit){await actor.waitForTimeout(200);continue;}
        report.click.at_ms=rel();report.click.wall=iso(Date.now());report.click.bounding_box=box;report.chain.click_ms=report.click.at_ms;
        await actor.mouse.click(x,y);clicked=true;
      }catch(e){report.click.attempts.push({t_ms:rel(),error:String(e.message).slice(0,160)});await actor.waitForTimeout(200);}
    }
    if(!clicked){report.outcome='NOT-RUN-CLICK-TARGET-UNSTABLE';report.verdict='NOT-RUN';return;}
    report.click.returned_ms=rel();save();

    /* observation */
    const dir=pre.direction,isSwitch=dir==='primary'||dir==='reserve';
    const deadline=Date.now()+(CFG.action==='reselect-current'?CFG.noCommandS:CFG.timeoutS)*1000;
    let terminalAt=null,rid=null,midShot=false,pendingShot=false,i=0,refusedAtRpc=false;
    const stateOf=s=>{const m=(s&&s.manual_switch)||{};return rid&&m.request_id===rid?m.state:null;};
    while(Date.now()<deadline&&(terminalAt===null||Date.now()<terminalAt+CFG.settleS*1000)){
      await actor.waitForTimeout(1000);i++;
      const cmds=report.rpc.commands.slice(commandsBefore).filter(c=>c.fn==='pair_manual');
      const ack=cmds[0]&&cmds[0].response;
      if(!rid&&ack&&ack.data&&typeof ack.data.request_id==='string'&&/^[a-f0-9]{32}$/.test(ack.data.request_id)){rid=ack.data.request_id;report.rpc.request_id=rid;report.rpc.correlation='ack';report.chain.rpc_ack_ms=ack.t_ms;}
      if(!rid&&ack&&ack.data&&ack.data.accepted===false&&!refusedAtRpc){refusedAtRpc=Date.now();report.chain.rpc_refused_ms=ack.t_ms;}
      // A refusal may be the answer to a transparent network-stack retry of the POST while the first copy was queued: keep watching 15 s.
      if(refusedAtRpc&&!rid&&terminalAt===null&&Date.now()-refusedAtRpc>15000)terminalAt=Date.now();
      if(!rid&&cmds.length&&lastStatus){
        // Lost/odd ACK: same correlation fence as the UI (new id, same direction, requested after the pre-click server time).
        const m=lastStatus.manual_switch||{};
        if(typeof m.request_id==='string'&&m.request_id!==preMs.request_id&&m.direction===dir&&Number.isFinite(m.requested_at)&&m.requested_at>=(preServer||0)-5){rid=m.request_id;report.rpc.request_id=rid;report.rpc.correlation=refusedAtRpc?'status-fence (RPC answered REFUSED, but backend queued a new request for this direction: possible duplicate POST delivery)':'status-fence (ACK not received)';if(refusedAtRpc)report.rpc.refusal_contradicted_by_backend=true;}
      }
      const st=stateOf(lastStatus);
      if(st&&!report.chain['first_'+st.toLowerCase()+'_ms'])report.chain['first_'+st.toLowerCase()+'_ms']=lastStatusAt;
      if(lastStatus&&lastStatus.channel_path&&lastStatus.channel_path.transitioning===true&&!report.chain.first_transitioning_ms)report.chain.first_transitioning_ms=lastStatusAt;
      if(st&&TERMINAL.includes(st)&&terminalAt===null){terminalAt=Date.now();report.chain.terminal_ms=lastStatusAt;report.chain.terminal_state=st;}
      let z;try{z=await within(zones(actor),15000,'DOM');}catch(e){report.errors.push('ACTOR-DOM-SNAPSHOT:'+e.message);continue;}
      const oz=observer?await within(zones(observer),10000,'DOM').catch(e=>({error:String(e.message)})):null;
      const row={i,t_ms:rel(),wall:iso(Date.now()),since_click_ms:rel()-report.click.at_ms,status_age_ms:lastStatusAt==null?null:rel()-lastStatusAt,
        backend:{request_state:st,manual_switch:lastStatus&&lastStatus.manual_switch,role:roleOf(lastStatus),hold:((lastStatus||{}).manual_switch_control||{}).hold||null,
          revision:((lastStatus||{}).manual_switch_control||{}).control_revision||null,native:lastStatus&&lastStatus.native_failover&&lastStatus.native_failover.state},
        ui:{selected:selectedDirection(z),operation:(z.manual_operation[0]||{}).state||null},actor:z,observer:oz};
      report.timeline.push(row);
      if(row.ui.operation&&!report.chain.ui_pending_first_ms)report.chain.ui_pending_first_ms=row.t_ms;
      if(isSwitch&&row.ui.selected===dir&&!report.chain.ui_selected_target_ms)report.chain.ui_selected_target_ms=row.t_ms;
      if(row.ui.operation&&!pendingShot){pendingShot=true;await shot(actor,'actor-02-pending.png');}
      if(!midShot&&(i===20||(st==='CLAIMED'))){midShot=true;await shot(actor,'actor-03-mid.png');
        {await shot(observer,'observer-03-mid.png');}}
      if(i%5===0)save();
    }
    await shot(actor,'actor-04-end.png');
    {await shot(observer,'observer-04-end.png');}

    let kb=null,ka=null;
    if(SNAP_CMD){const a=await runSnapshot('after');report.kernel.after={...a,json:undefined,summary:kernelSummary(a.json)};kb=report.kernel.before.summary;ka=report.kernel.after.summary;save();}
    /* evaluation */
    const cmds=report.rpc.commands.slice(commandsBefore),pm=cmds.filter(c=>c.fn==='pair_manual');
    const otherCommands=cmds.filter(c=>c.fn!=='pair_manual').map(c=>c.fn);
    check('no other app command RPC (native_start/native_stop/...) was sent',otherCommands.length===0,otherCommands);
    const last=report.timeline[report.timeline.length-1];
    const endStatus=lastStatus,endRole=roleOf(endStatus),endHold=((endStatus||{}).manual_switch_control||{}).hold||null;
    if(CFG.action==='reselect-current'){
      check('disabled selected card sends no pair_manual RPC',pm.length===0,pm.length);
      check('kernel-selected role unchanged in status',endRole===preRole,{before:preRole,after:endRole});
      check('UI still selects the same channel',last&&last.ui.selected===dir,last&&last.ui.selected);
      report.outcome=pm.length===0?'NO-COMMAND-SENT':'UNEXPECTED-COMMAND-SENT';
    }else{
      check('exactly one pair_manual RPC (both tabs)',pm.length===1,pm.length);
      const a=pm[0]&&pm[0].args||{};
      check('RPC args: direction/request_source/revision match the clicked state',a.direction===dir&&a.request_source==='manual'&&a.control_revision===preRev,{direction:a.direction,request_source:a.request_source,revision_matches:a.control_revision===preRev});
      check('RPC sent by the actor tab within 5 s of the click',pm[0]&&pm[0].tab==='actor'&&pm[0].t_ms-report.click.at_ms<=5000,pm[0]&&pm[0].t_ms-report.click.at_ms);
      if(refusedAtRpc&&!rid){report.outcome='REFUSED-AT-RPC';report.rpc.refusal=pm[0].response.data;}
      else{
        check('request_id correlated',!!rid,report.rpc.correlation);
        const st=report.chain.terminal_state||null;
        check('terminal result observed for the same request_id within timeout',!!st,st);
        report.outcome=st||(rid?'NO-TERMINAL-WITHIN-TIMEOUT':pm.length?'NO-REQUEST-ID':'NO-RPC-AFTER-CLICK');
        // While the backend row for this request is pending (or not yet visible), the UI must not claim the target as selected and green.
        const premature=report.timeline.filter(r=>(r.backend.request_state===null||PENDING.includes(r.backend.request_state))&&isSwitch&&
          (r.actor.manual||[]).some(m=>m.visible&&m.direction===dir&&m.selected==='true'&&/hv-manual-green/.test(m.class)));
        check('no green selected target while request pending/unknown',premature.length===0,premature.map(r=>r.i));
        const dupWindow=report.timeline.filter(r=>r.backend.request_state&&PENDING.includes(r.backend.request_state)&&(r.actor.manual||[]).some(m=>m.visible&&(m.direction==='primary'||m.direction==='reserve')&&!m.disabled&&m.selected!=='true'));
        check('no enabled switch button while request pending (duplicate guard)',dupWindow.length===0,dupWindow.map(r=>r.i));
        if(st==='COMPLETED'&&isSwitch){
          check('status role equals requested direction after COMPLETED',endRole===dir,{before:preRole,after:endRole});
          check('UI selected channel equals status role at end',last&&last.ui.selected===endRole,{ui:last&&last.ui.selected,status:endRole});
        }
        if(st==='COMPLETED'&&dir==='resume'){
          check('resume cleared manual hold',endHold===null,endHold);
          check('resume did not change the kernel-selected role',endRole===preRole,{before:preRole,after:endRole});
          check('hold banner gone in UI at end',last&&!(last.actor.manual_hold||[]).some(h=>h.visible),null);
        }
      }
    }
    if(SNAP_CMD){
      check('kernel snapshot after the observation parsed',!!report.kernel.after.ok,report.kernel.after.error||null);
      if(kb&&ka){
        const same=kb.product_kernel_fingerprint===ka.product_kernel_fingerprint&&kb.uci_sha256===ka.uci_sha256&&kb.mangle_normalized_sha256===ka.mangle_normalized_sha256&&kb.ip_rules_sha256===ka.ip_rules_sha256;
        report.kernel.diff={rules_unchanged:same,uci_order_changed:JSON.stringify(kb.uci_order)!==JSON.stringify(ka.uci_order),fingerprint_changed:kb.product_kernel_fingerprint!==ka.product_kernel_fingerprint,
          budget_before:kb.budget_events,budget_after:ka.budget_events,budget_last_before:kb.budget_last_event,budget_last_after:ka.budget_last_event,journal_before:kb.journal,journal_after:ka.journal,
          pair_manual_after:ka.pair_manual,guard_before:kb.guard_exists,guard_after:ka.guard_exists,routes_changed:JSON.stringify(kb.routes_sha256)!==JSON.stringify(ka.routes_sha256)};
        check('product kernel fingerprint readable before and after',!!kb.product_kernel_fingerprint&&!!ka.product_kernel_fingerprint,null);
        if(CFG.action==='reselect-current'||CFG.action==='resume'){
          check('kernel rules, mangle and UCI route_policy unchanged',same,report.kernel.diff);
          check('pair budget not charged',kb.budget_last_event===ka.budget_last_event,{before:kb.budget_last_event,after:ka.budget_last_event});
        }else if(report.outcome==='COMPLETED'){
          check('kernel fingerprint and UCI order changed',report.kernel.diff.fingerprint_changed&&report.kernel.diff.uci_order_changed,report.kernel.diff);
          check('router pair-manual-control.json holds this request_id as COMPLETED',ka.pair_manual.id===rid&&ka.pair_manual.state==='COMPLETED',ka.pair_manual);
          check('router status.json active profile equals requested role',ka.status_json_active===(dir==='primary'?ka.status_json_source:ka.status_json_target),{active:ka.status_json_active});
        }else if(['REFUSED','CANCELLED','REFUSED-AT-RPC'].includes(report.outcome)){
          check('refused/cancelled request left kernel rules unchanged',same,report.kernel.diff);
        }
      }
    }
    check('no Chromium page errors',report.page_errors.length===0,report.page_errors.length);
    const expected=CFG.action==='reselect-current'?'NO-COMMAND-SENT':'COMPLETED';
    report.verdict=report.checks.every(c=>c.passed)&&report.outcome===expected?'PASS':'FAIL';
  }catch(e){
    report.errors.push(maskString(String(e&&e.message||e)));if(!report.outcome)report.outcome='ERROR';if(!report.verdict)report.verdict=report.outcome.startsWith('NOT-RUN')?'NOT-RUN':'FAIL';
    await shot(actor,'actor-99-error.png');
  }finally{
    report.finished_at=iso(Date.now());report.status_frames=statusHistory.length;
    report.status_history=statusHistory.map(h=>({t_ms:h.t_ms,tab:h.tab,role:h.role,manual_switch:h.summary&&h.summary.manual_switch,hold:h.summary&&h.summary.manual_switch_control&&h.summary.manual_switch_control.hold}));
    try{save();}catch(e){console.error('SAVE-FAILED',e.message);}
    if(statusStream)await new Promise(r=>statusStream.end(r));
    if(browser)await browser.close().catch(()=>{});
    console.log(JSON.stringify(redact({verdict:report.verdict,outcome:report.outcome,request_id:report.rpc.request_id,correlation:report.rpc.correlation,chain:report.chain,
      checks:report.checks.map(c=>(c.passed?'PASS ':'FAIL ')+c.name),errors:report.errors,precondition_reasons:report.precondition&&report.precondition.reasons,out:OUT}),null,2));
    if(report.verdict!=='PASS')process.exitCode=report.verdict==='NOT-RUN'?2:1;
  }
})();
