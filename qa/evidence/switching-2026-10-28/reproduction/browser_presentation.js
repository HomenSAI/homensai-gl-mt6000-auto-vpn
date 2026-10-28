/* Real Chromium presentation checks, with explicitly synthetic RPC/status overlays.
 * No switch command in this script reaches the Python/QEMU controller. */
const fs=require('fs'),path=require('path'),{chromium}=require(process.env.QA_PLAYWRIGHT||(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES?process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES+'/playwright':'playwright'));
const OUT=process.env.QA_OUTPUT||__dirname,BASE='http://127.0.0.1:'+(process.env.QA_HTTP_PORT||18988),LABEL=process.env.QA_LABEL||'final';
const report={scope:'Real Chromium and actual generated dashboard; synthetic status and RPC overlays for deterministic presentation/timer checks. No native controller/kernel command is issued by these tests.',checks:[],steps:[],errors:[]};
const check=(name,passed)=>report.checks.push({name,passed:!!passed}),clone=x=>JSON.parse(JSON.stringify(x));
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM||path.join(__dirname,'../qa-browsers/chrome-linux64/chrome'),headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  const request=await browser.newContext();const raw=await(await request.request.get(BASE+'/__qa/state')).json();
  const inventory=await(await request.request.post(BASE+'/__qa/rpc/inventory',{data:[]})).json();report.identity=raw.identity;report.browser=browser.version();
  function fresh(epoch=1792750000){
   const s=clone(raw.status);s.time=epoch;s.server_time=epoch;
   s.native_failover={state:'OBSERVING',time:epoch,source:s.channel_path.source_profile_id,target:s.channel_path.target_profile_id,mode:'continuous-pair',proof_scope:'router-probed-ipv4',readiness_verified:true};
   s.auto_control={requested:'on',requested_at:epoch-10,control_revision:s.auto_control.control_revision,pair_phase:'RUNNING'};
   s.manual_switch={state:'IDLE',completed:false};s.manual_switch_control={...s.manual_switch_control,time:epoch,available:true,hold:null,primary:{allowed:true,blockers:[]},reserve:{allowed:true,blockers:[]},resume:{allowed:false,blockers:[]},blockers:[]};
   s.channel_path={...s.channel_path,time:epoch,checked_at:epoch,confirmed:true,transitioning:false,kernel_policy_verified:true,code:null,active_profile_id:s.channel_path.source_profile_id,configured_profile_id:s.channel_path.source_profile_id};
   for(const p of s.profiles){p.time=epoch;p.code=null;p.dns_ok=true;p.https_success=2;p.vendor_state='SETTLED';p.vendor_changed_at=epoch-120;if(p.website_response)p.website_response.time=epoch;}
   if(s.vendor_observation){s.vendor_observation.time=epoch;s.vendor_observation.groups.forEach(g=>{g.time=epoch;g.changed_at=epoch-120;g.state='SETTLED';});}
   return s;
  }
  async function setup(getStatus,{clock=false,epoch=1792750000}={}){
   const page=await browser.newPage({viewport:{width:1440,height:1100}});page.on('pageerror',e=>report.errors.push(e.message));
   if(clock)await page.clock.install({time:new Date(epoch*1000)});else await page.addInitScript(t=>Date.now=()=>t*1000,epoch);
   await page.addInitScript(()=>{localStorage.setItem('homensai-vpn-design','b');localStorage.setItem('homensai-vpn-theme','light');localStorage.setItem('homensai-vpn-language','en');});
   await page.route('**/__qa/rpc/status',route=>route.fulfill({json:clone(getStatus())}));
   await page.route('**/__qa/rpc/inventory',route=>route.fulfill({json:{...clone(inventory),profiles:clone(getStatus().profiles)}}));
   await page.route('**/__qa/rpc/pair_manual',route=>route.fulfill({json:{accepted:true,queued:true,completed:false,request_id:'e'.repeat(32)}}));
   await page.goto(BASE+'/#overview',{waitUntil:'networkidle'});return page;
  }
  async function save(page,name){
   const dom=await page.evaluate(()=>({full:[...document.querySelectorAll('.hv-light-title')].map(n=>n.innerText),side:[...document.querySelectorAll('.hv-side-lamp-link')].map(n=>({text:n.innerText,title:n.title,green:!!n.querySelector('.hv-lamp-on')})),simple:[...document.querySelectorAll('[data-simple-home]')].map(n=>({state:n.dataset.simpleHome,text:n.innerText})),responses:[...document.querySelectorAll('[data-home-response] .hv-channel-ping')].map(n=>({text:n.innerText,state:n.dataset.pingState,coverage:n.dataset.coverage})),manual:[...document.querySelectorAll('[data-manual-direction]')].map(n=>({direction:n.dataset.manualDirection,disabled:n.disabled,selected:n.dataset.selected,class:n.className})),operation:[...document.querySelectorAll('[data-manual-operation]')].map(n=>n.dataset.manualOperation),power:[...document.querySelectorAll('.hv-auto-power')].map(n=>({operation:n.dataset.autoOperation,disabled:n.disabled,label:n.getAttribute('aria-label'),countdownVisible:!!n.querySelector('.hv-auto-countdown:not([hidden])')})),durations:localStorage.getItem('hv-auto-durations')}));
   report.steps.push({name,dom});fs.writeFileSync(OUT+'/browser-presentation-'+LABEL+'.json',JSON.stringify(report,null,2));await page.screenshot({path:OUT+'/browser-presentation-'+LABEL+'-'+name+'.png',fullPage:true});return dom;
  }
  let s=fresh();s.native_failover.state='DEGRADED-ON-RESERVE';s.native_failover.reason='RESERVE-FAILED';s.channel_path.active_profile_id=s.channel_path.target_profile_id;s.channel_path.configured_profile_id=s.channel_path.target_profile_id;
  const target=s.profiles.find(p=>p.id===s.channel_path.target_profile_id);target.code='VPN-003';target.https_success=0;target.website_response={...target.website_response,state:'partial',code:'WEBSITE-PARTIAL',successes:2,avg_ms:null};
  let page=await setup(()=>s);const degraded=await save(page,'degraded-full');
  check('full Auto reports selected reserve failure',degraded.full.some(t=>/fail|problem|attention|нуж|работает/i.test(t)));
  check('sidebar describes the actual problem without claiming Auto OFF',degraded.side.some(x=>!x.green&&!/Auto OFF|Auto выкл/.test(x.text)&&/fail|problem|attention|нуж|работает/i.test(x.text)));
  check('selected failed reserve is red',degraded.manual.some(x=>x.direction==='reserve'&&x.selected==='true'&&x.class.includes('hv-manual-red')));
  await page.locator('[data-simple-shortcut]').first().click();const minimum=await save(page,'degraded-minimum');
  check('Minimum requires attention for the same selected reserve',minimum.simple.some(x=>x.state==='error'&&/Reserve|reserve/.test(x.text)));
  check('Minimum exposes both complete and partial responses',minimum.responses.length===2&&minimum.responses.some(x=>x.text.includes('110.0 ms'))&&minimum.responses.some(x=>x.coverage==='2/3'&&x.state==='partial'&&x.text.includes('Incomplete check')));
  await page.close();
  s=fresh();page=await setup(()=>s,{clock:true});await page.clock.pauseAt(new Date(await page.evaluate(()=>Date.now())+1000));
  await page.locator('.hv-auto-power').filter({visible:true}).first().click();await page.clock.runFor(600);
  const start=await save(page,'stop-pending');check('real Stop click begins a visible estimate',start.power.some(x=>x.operation==='stopping'&&x.countdownVisible));
  await page.clock.fastForward(121000);await page.clock.runFor(1000);const timeout=await save(page,'stop-unconfirmed');
  check('independent browser heartbeat ends expired countdown',timeout.power.some(x=>x.operation==='unconfirmed'&&!x.countdownVisible));
  check('timeout stays unconfirmed and Stop remains usable',timeout.power.some(x=>x.operation==='unconfirmed'&&!x.disabled&&/not confirmed/.test(x.label)));
  check('unconfirmed timeout does not train successful durations',timeout.durations===null);await page.close();
  s=fresh(1000);page=await setup(()=>s,{clock:true,epoch:1000});
  await page.locator('[data-manual-direction="reserve"]').filter({visible:true}).first().click();await page.waitForTimeout(100);
  const pending=await save(page,'clock-step-pending');check('clock-step test starts pending request',pending.operation.includes('pending'));
  s=fresh(100);s.channel_path.active_profile_id=s.channel_path.target_profile_id;s.channel_path.configured_profile_id=s.channel_path.target_profile_id;s.manual_switch={state:'COMPLETED',completed:true,direction:'reserve',request_id:'e'.repeat(32),requested_at:1000,updated_at:100};
  await page.clock.setSystemTime(new Date(100000));await page.evaluate(()=>fixturePoll());const corrected=await save(page,'clock-step-completed');
  check('exact terminal ID clears pending across backwards router clock',corrected.operation.length===0&&corrected.manual.some(x=>x.direction==='primary'&&!x.disabled));
  check('clock correction selects only the freshly proved reserve',corrected.manual.some(x=>x.direction==='reserve'&&x.selected==='true'));
  await page.close();await request.close();
  check('no browser script exceptions',report.errors.length===0);report.verdict=report.checks.every(c=>c.passed)?'PASS':'FAIL';
 }catch(e){report.verdict='FAIL';report.failure={name:e.name,message:e.message};process.exitCode=1;}
 finally{fs.writeFileSync(OUT+'/browser-presentation-'+LABEL+'.json',JSON.stringify(report,null,2));console.log(JSON.stringify({verdict:report.verdict,checks:report.checks,errors:report.errors,failure:report.failure},null,2));await browser.close();}
})();
