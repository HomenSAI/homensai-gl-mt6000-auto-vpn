/* Real Chromium, exact generated dashboard, explicitly synthetic delayed RPC.
 * This test starts only a loopback static preview; no controller or router calls. */
'use strict';
const fs=require('fs'),path=require('path'),http=require('http'),crypto=require('crypto'),cp=require('child_process');
const {chromium}=require(process.env.QA_PLAYWRIGHT||(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES?process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES+'/playwright':'playwright'));
const REPO=path.resolve(process.env.QA_REPO),OUT=path.resolve(process.env.QA_OUTPUT),LABEL=process.env.QA_LABEL||'delayed-status',PORT=Number(process.env.QA_HTTP_PORT||18987);
const evidence=path.join(REPO,'qa/evidence/switching-2026-10-28'),assets=path.join(REPO,'router/files/www/luci-static/resources/view/homensai-vpn');
const menu=JSON.parse(fs.readFileSync(path.join(REPO,'router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json')));
const name=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
const modulePath=path.resolve(process.env.QA_DASHBOARD||path.join(assets,name+'.js')),moduleBytes=fs.readFileSync(modulePath),hash=x=>crypto.createHash('sha256').update(x).digest('hex');
const clone=x=>JSON.parse(JSON.stringify(x));
const original=JSON.parse(fs.readFileSync(path.join(evidence,'browser-copy-final.json'))).steps[0].state.status;
const frame=clone(original),T=1000;frame.version=process.env.QA_APP_VERSION||JSON.parse(fs.readFileSync(path.join(REPO,'VERSION.json'))).application.version;frame.time=frame.server_time=T;frame.observation_valid_for=900;
frame.native_failover={...frame.native_failover,state:'OBSERVING',time:T-10,readiness_verified:true};
frame.auto_control={...frame.auto_control,requested:'on',requested_at:T-20,pair_phase:'RUNNING'};
frame.channel_path={...frame.channel_path,time:T,checked_at:T,valid_for:15,confirmed:true,kernel_policy_verified:true,transitioning:false};
frame.manual_switch={state:'IDLE',completed:false};frame.manual_switch_control={...frame.manual_switch_control,time:T,observation_valid_for:900,hold:null};
for(const p of frame.profiles){p.time=T;p.observation_valid_for=900;p.vendor_changed_at=T-120;p.code=null;p.dns_ok=true;p.https_success=2;p.website_response.time=T-25;p.website_response.valid_for=45;}
if(frame.vendor_observation){frame.vendor_observation.time=T;for(const g of frame.vendor_observation.groups){g.time=T;g.changed_at=T-120;}}
const inventory={profiles:clone(frame.profiles),servers:frame.profiles.map((p,i)=>({profile:p.id,name:p.name,priority:i+1,enabled:true})),settings:{terms_version:'1',setup_complete:true,onboarding_complete:true,onboarding_version:1,enabled:true,plan_enabled:true,plan_source:frame.channel_path.source_profile_id,plan_target:frame.channel_path.target_profile_id,pair_auto_mode:'continuous-pair',native_duration:10,interval:30,checkpoint:900,telegram_enabled:false}};
const BRIDGE=`\nconst qaFallbackRPC=window.rpc;window.rpc={declare:spec=>{const old=qaFallbackRPC.declare(spec);return(...args)=>{if(['status','inventory','pair_manual'].includes(spec.method)){window.fixtureCalls.push({method:spec.method,args});return fetch('/__qa/rpc/'+spec.method,{method:'POST'}).then(r=>r.json());}return old(...args);};}};\n`;
let stub=fs.readFileSync(path.join(REPO,'qa/ui-preview/stub.js'),'utf8');const anchor="fetch('/preview-module.js',{cache:'no-store'})";
if(stub.split(anchor).length!==2)throw Error('STUB_ANCHOR');stub=stub.replace(anchor,BRIDGE+anchor);
const report={scope:'Actual Chromium and exact generated dashboard. RPC/inventory/probe/kernel status are synthetic frozen frames; only browser clocks and RPC delivery are controlled. No backend transaction, QEMU, physical router or network rules are invoked.',identity:{head:process.env.QA_HEAD,version:frame.version,dashboard_file:path.basename(modulePath),dashboard_sha256:hash(moduleBytes)},fixture:{server_time:T,native_time:T-10,kernel_checked_at:T,kernel_valid_for:15,website_time:T-25,website_valid_for:45,health_valid_for:900,delay_ms:24000,raw_frame_sha256:hash(JSON.stringify(frame))},checks:[],steps:[],errors:[]};
report.identity.isolation={etc_readonly:false,run_readonly:false,effective_capabilities:'windows-host-not-applicable'};
const check=(name,passed)=>report.checks.push({name,passed:!!passed});
const prefix='/router/files/www/luci-static/resources/view/homensai-vpn/';
const server=http.createServer((req,res)=>{let body,type='application/javascript';const url=new URL(req.url,'http://127.0.0.1');
 try{if(req.headers.host!=='127.0.0.1:'+PORT){res.writeHead(403);res.end();return;}
  if(url.pathname==='/'||url.pathname==='/qa/ui-preview/index.html'){body=fs.readFileSync(path.join(REPO,'qa/ui-preview/index.html'));type='text/html';}
  else if(url.pathname==='/qa/ui-preview/stub.js')body=stub;
  else if(url.pathname==='/preview-module.js')body=moduleBytes;
  else if(url.pathname==='/preview-router.js')body='window.HOMENSAI_PREVIEW_ROUTER_ORIGIN=null;';
  else if(url.pathname.startsWith(prefix)){const file=path.resolve(assets,url.pathname.slice(prefix.length));if(!file.startsWith(assets+path.sep)||!(/\.(css|svg|png|woff2?|ttf|js)$/.test(file)))throw Error('REFUSED');body=fs.readFileSync(file);type=file.endsWith('.css')?'text/css':file.endsWith('.svg')?'image/svg+xml':'application/octet-stream';}
  else{res.writeHead(404);res.end();return;}res.writeHead(200,{'Content-Type':type,'Cache-Control':'no-store','X-HomenSAI-Preview':'synthetic-only'});res.end(body);
 }catch(e){res.writeHead(404);res.end();}});
const save=()=>fs.writeFileSync(path.join(OUT,'browser-delayed-status-'+LABEL+'.json'),JSON.stringify(report,null,2)+'\n');
(async()=>{let browser;
 try{await new Promise(resolve=>server.listen(PORT,'127.0.0.1',resolve));browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM,headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});report.browser=browser.version();
  let page=await browser.newPage({viewport:{width:1440,height:1100}});page.on('pageerror',e=>report.errors.push(e.message));
  await page.clock.install({time:new Date(T*1000)});await page.clock.pauseAt(new Date((T+1)*1000));
  await page.addInitScript(()=>{localStorage.setItem('homensai-vpn-design','b');localStorage.setItem('homensai-vpn-theme','light');localStorage.setItem('homensai-vpn-language','en');});
  let statusCount=0,delayed,manualCalls=0;const statusSeen=new Promise(resolve=>{delayed={seen:resolve};});
  await page.route('**/__qa/rpc/status',async route=>{statusCount++;if(statusCount===1)return route.fulfill({json:clone(frame)});if(statusCount===2){delayed.route=route;delayed.tick=await page.evaluate(()=>performance.now());delayed.seen();return;}return route.abort();});
  await page.route('**/__qa/rpc/inventory',route=>route.fulfill({json:clone(inventory)}));
  await page.route('**/__qa/rpc/pair_manual',route=>{manualCalls++;return route.fulfill({json:{accepted:false,code:'SYNTHETIC-NO-CONTROLLER'}});});
  async function snapshot(name){const dom=await page.evaluate(()=>({tick:performance.now(),full:[...document.querySelectorAll('.hv-light-title')].map(n=>n.innerText),side:[...document.querySelectorAll('.hv-side-lamp-link')].map(n=>({text:n.innerText,title:n.title,green:!!n.querySelector('.hv-lamp-on')})),simple:[...document.querySelectorAll('[data-simple-home]')].map(n=>({state:n.dataset.simpleHome,text:n.innerText})),responses:[...document.querySelectorAll('[data-home-response] .hv-channel-ping')].map(n=>({text:n.innerText,state:n.dataset.pingState,coverage:n.dataset.coverage})),manual:[...document.querySelectorAll('[data-manual-direction]')].map(n=>({direction:n.dataset.manualDirection,disabled:n.disabled,selected:n.dataset.selected,class:n.className})),power:[...document.querySelectorAll('.hv-auto-state')].map(n=>({text:n.innerText,class:n.className})),lastResults:[...document.querySelectorAll('[data-manual-diagnostic="last-request"]')].map(n=>n.innerText),operation:[...document.querySelectorAll('[data-manual-operation]')].map(n=>n.dataset.manualOperation)}));report.steps.push({name,dom});save();return dom;}
  await page.goto('http://127.0.0.1:'+PORT+'/#overview',{waitUntil:'networkidle'});await page.locator('[data-manual-direction="reserve"]').first().waitFor();
  const initial=await snapshot('initial-fresh');check('fresh initial frame selects the verified primary',initial.manual.some(x=>x.direction==='primary'&&x.selected==='true'&&x.class.includes('hv-manual-green')));
  await page.evaluate(()=>{window.__qaPendingPoll=fixturePoll();return true;});await statusSeen;
  await page.clock.runFor(24000);const waiting=await snapshot('waiting-before-delivery');
  report.fixture.observed_browser_delay_ms=waiting.tick-delayed.tick;check('status reply is held for 24 browser seconds below 30 second deadline',waiting.tick-delayed.tick>=24000&&waiting.tick-delayed.tick<30000);
  check('existing kernel proof expires while the reply is in flight',waiting.manual.every(x=>x.selected!=='true'));
  await delayed.route.fulfill({json:clone(frame)});await page.evaluate(()=>window.__qaPendingPoll);
  const delivered=await snapshot('delayed-reply-delivered');
  check('delayed reply does not renew expired kernel proof',delivered.manual.every(x=>x.selected!=='true'&&!x.class.includes('hv-manual-green')));
  check('delayed reply does not renew expired controller heartbeat',delivered.power.every(x=>!x.class.includes('hv-auto-state-on')));
  check('sidebar Auto lamp stays non-green after expired proof',delivered.side.length>0&&delivered.side.every(x=>!x.green));
  await page.locator('[data-simple-shortcut]').first().click();const minimum=await snapshot('minimum-after-real-click');
  check('Minimum agrees that automatic operation is unconfirmed',minimum.simple.length>0&&minimum.simple.every(x=>x.state!=='on'));
  check('both expired website responses are visibly stale without a current mean',minimum.responses.length===2&&minimum.responses.every(x=>x.state==='stale'&&!/\d+(?:\.\d+)?\s*ms/.test(x.text)));
  check('same frozen raw response is delivered without server timestamp refresh',hash(JSON.stringify(frame))===report.fixture.raw_frame_sha256);
  check('delayed-response scenario sends no switch command',manualCalls===0);report.status_rpc_count=statusCount;
  check('host /etc and /run remain readonly with no effective capabilities',report.identity.isolation.etc_readonly&&report.identity.isolation.run_readonly&&/^0+$/.test(report.identity.isolation.effective_capabilities));
  await page.screenshot({path:path.join(OUT,'browser-delayed-status-'+LABEL+'.png'),fullPage:true});
  if(process.env.QA_CROSS_TAB==='1'){
   await page.close();page=await browser.newPage({viewport:{width:1440,height:1100}});page.on('pageerror',e=>report.errors.push(e.message));
   await page.clock.install({time:new Date(T*1000)});await page.clock.pauseAt(new Date((T+1)*1000));
   await page.addInitScript(()=>{localStorage.setItem('homensai-vpn-design','b');localStorage.setItem('homensai-vpn-theme','light');localStorage.setItem('homensai-vpn-language','en');});
   function at(epoch){const s=clone(frame);s.server_time=s.time=s.channel_path.time=s.channel_path.checked_at=s.manual_switch_control.time=epoch;s.native_failover.time=epoch-10;s.auto_control.requested_at=epoch-20;for(const p of s.profiles){p.time=epoch;p.vendor_changed_at=epoch-120;p.website_response.time=epoch-25;}if(s.vendor_observation){s.vendor_observation.time=epoch;for(const g of s.vendor_observation.groups){g.time=epoch;g.changed_at=epoch-120;}}return s;}
   let cross=at(T),crossCalls=0;const oldId='c'.repeat(32),newId='d'.repeat(32);
   await page.route('**/__qa/rpc/status',route=>route.fulfill({json:clone(cross)}));
   await page.route('**/__qa/rpc/inventory',route=>route.fulfill({json:{...clone(inventory),profiles:clone(cross.profiles)}}));
   await page.route('**/__qa/rpc/pair_manual',route=>{crossCalls++;cross.manual_switch={state:'REFUSED',completed:false,request_id:oldId,direction:'reserve',requested_at:T,updated_at:T,code:'SOURCE-NOT-HEALTHY'};return route.fulfill({json:{accepted:true,queued:true,completed:false,request_id:oldId}});});
   await page.goto('http://127.0.0.1:'+PORT+'/#overview',{waitUntil:'networkidle'});
   await Promise.all([page.waitForResponse('**/__qa/rpc/pair_manual'),page.locator('[data-manual-direction="reserve"]').filter({visible:true}).first().click()]);
   await page.clock.runFor(1);await page.evaluate(()=>fixturePoll());
   const refused=await snapshot('cross-tab-old-correlated-refusal');
   check('real click and matching refused terminal establish saved feedback',crossCalls===1&&refused.operation.length===0&&refused.lastResults.some(x=>x.includes('SOURCE-NOT-HEALTHY')));
   cross=at(100);cross.manual_switch={state:'COMPLETED',completed:true,request_id:newId,direction:'reserve',requested_at:100,updated_at:100};
   await page.clock.setSystemTime(new Date(100000));await page.evaluate(()=>fixturePoll());
   const completed=await snapshot('cross-tab-new-completed-after-clockback');
   check('new request ID completion supersedes saved refusal after clockback',completed.lastResults.length===0&&completed.operation.length===0);
   check('other-tab completion never invents a different kernel-selected route',completed.manual.some(x=>x.direction==='primary'&&x.selected==='true')&&completed.manual.every(x=>x.direction!=='reserve'||x.selected==='false'));
   cross.manual_switch={...cross.manual_switch,state:'REFUSED',completed:false,code:'PAIR-MANUAL-TARGET-UNHEALTHY'};await page.evaluate(()=>fixturePoll());
   const currentRefusal=await snapshot('cross-tab-current-refusal-after-clockback');
   check('new backend refusal replaces old request feedback without another click',crossCalls===1&&currentRefusal.lastResults.some(x=>x.includes('PAIR-MANUAL-TARGET-UNHEALTHY'))&&currentRefusal.lastResults.every(x=>!x.includes('SOURCE-NOT-HEALTHY')));
   report.cross_tab_fixture={synthetic_manual_rpc_calls:crossCalls,old_request_id:oldId,old_updated_at:1000,new_request_id:newId,new_updated_at:100,backend_commands:0};
  }
  check('no Chromium script exceptions',report.errors.length===0);
  report.verdict=report.checks.every(c=>c.passed)?'PASS':'FAIL';
 }catch(e){report.verdict='FAIL';report.failure={name:e.name,message:e.message};}
 finally{save();if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));console.log(JSON.stringify({verdict:report.verdict,checks:report.checks,failure:report.failure,errors:report.errors},null,2));if(report.verdict!=='PASS')process.exitCode=1;}
})();
