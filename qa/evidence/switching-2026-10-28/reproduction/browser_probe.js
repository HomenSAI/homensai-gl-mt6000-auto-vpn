const fs=require('fs');
const {chromium}=require(process.env.QA_PLAYWRIGHT||(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES?process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES+'/playwright':'playwright'));
const ROOT=(process.env.QA_OUTPUT||__dirname);
const report={scope:'Real Chromium clicks on frozen generated dashboard; real Python manual request/consume/native child; model device/kernel/probes',steps:[],errors:[]};
(async()=>{
 const browser=await chromium.launch({executablePath:(process.env.QA_CHROMIUM||require('path').join(__dirname,'../qa-browsers/chrome-linux64/chrome')),headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  report.browser=browser.version();
  const page=await browser.newPage({viewport:{width:1440,height:1200}});
  page.on('pageerror',e=>report.errors.push(e.message));
  await page.addInitScript(()=>{window.__qaEpoch=1792750000;Date.now=()=>window.__qaEpoch*1000;localStorage.setItem('homensai-vpn-design','c');localStorage.setItem('homensai-vpn-theme','light');localStorage.setItem('homensai-vpn-lang','en');});
  await page.goto('http://127.0.0.1:'+(process.env.QA_HTTP_PORT||18988)+'/#overview',{waitUntil:'networkidle'});
  await page.waitForSelector('[data-manual-direction]');
  const snapshot=async name=>{
   const state=await page.evaluate(()=>window.__qaSnapshot());
   const dom=await page.evaluate(()=>({page:location.hash,manual:[...document.querySelectorAll('[data-manual-direction]')].map(b=>({direction:b.dataset.manualDirection,disabled:b.disabled,class:b.className,text:b.innerText,selected:b.dataset.selected})),notices:[...document.querySelectorAll('.qa-notice,[data-manual-diagnostic]')].map(n=>n.innerText),autos:[...document.querySelectorAll('.hv-auto-power')].map(n=>({text:n.innerText,class:n.className})),calls:window.fixtureCalls.filter(c=>c.method==='pair_manual')}));
   report.steps.push({name,state,dom});
   fs.writeFileSync(ROOT+'/browser-probe-baseline.json',JSON.stringify(report,null,2));
   await page.screenshot({path:ROOT+'/browser-'+name+'.png',fullPage:true});
   return {state,dom};
  };
  const initial=await snapshot('initial');
  const primary=page.locator('[data-manual-direction="primary"]').filter({visible:true}).first();
  report.steps.push({name:'primary-visible-count',count:await primary.count()});
  await primary.click();
  await page.waitForFunction(()=>window.fixtureCalls.some(c=>c.method==='pair_manual'));
  await page.waitForTimeout(250);
  await page.evaluate(()=>window.fixturePoll());
  const queued=await snapshot('queued-primary');
  await page.evaluate(()=>fetch('/__qa/consume',{method:'POST',body:'[]'}).then(r=>r.json()));
  await page.evaluate(()=>window.fixturePoll());
  const completed=await snapshot('completed-primary');
  report.assertions={queued_request:queued.state.status.manual_switch.state==='QUEUED',
   queue_did_not_change_modeled_kernel:JSON.stringify(initial.state.model_order)===JSON.stringify(queued.state.model_order),
   request_origin_is_manual:queued.state.status.manual_switch.request_source==='manual',
   completed:completed.state.status.manual_switch.state==='COMPLETED',
   model_kernel_primary:completed.state.model_kernel.role==='source',
   no_script_errors:report.errors.length===0};
  report.page_text=(await page.locator('body').innerText()).slice(0,26000);
  console.log(JSON.stringify({assertions:report.assertions,errors:report.errors,steps:report.steps.map(s=>({name:s.name,manual:s.dom?.manual,state:s.state?.status?.manual_switch}))},null,2));
 }catch(e){report.failure={name:e.name,message:e.message};console.error(e);process.exitCode=1;}
 finally{fs.writeFileSync(ROOT+'/browser-probe-baseline.json',JSON.stringify(report,null,2));await browser.close();}
})()
