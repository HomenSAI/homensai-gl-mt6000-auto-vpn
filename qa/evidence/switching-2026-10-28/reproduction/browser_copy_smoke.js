/* Targeted render/real-click regression after a copy-only generated-asset change.
 * This does not claim to rerun the complete functional/fault matrix. */
const fs=require('fs'),path=require('path'),{chromium}=require(process.env.QA_PLAYWRIGHT||(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES?process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES+'/playwright':'playwright'));
const OUT=process.env.QA_OUTPUT||__dirname,BASE='http://127.0.0.1:'+(process.env.QA_HTTP_PORT||18988),report={scope:'Targeted copy-only asset recheck: actual Chromium render/click -> production manual queue/consume/native child -> disposable QEMU kernel. Full prior matrix remains separately identified by its asset hash.',checks:[],steps:[],errors:[]};
const check=(name,value)=>report.checks.push({name,passed:!!value});
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.QA_CHROMIUM||path.join(__dirname,'../qa-browsers/chrome-linux64/chrome'),headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1100}});page.on('pageerror',e=>report.errors.push(e.message));
  const raw=await(await page.request.get(BASE+'/__qa/state')).json();report.identity=raw.identity;report.browser=browser.version();
  await page.addInitScript(epoch=>{Date.now=()=>epoch*1000;localStorage.setItem('homensai-vpn-design','b');localStorage.setItem('homensai-vpn-theme','light');localStorage.setItem('homensai-vpn-language','en');},raw.status.time);
  await page.goto(BASE+'/#overview',{waitUntil:'networkidle'});
  async function snap(name){const state=await page.evaluate(()=>__qaSnapshot()),text=await page.locator('body').innerText();const s={name,state,text};report.steps.push(s);return s;}
  const before=await snap('render-before-click');
  check('current asset renders with Auto initially running',before.state.pair.phase==='RUNNING'&&before.state.model_kernel.verified&&/Two-channel Auto is on|Auto works/.test(before.text));
  check('running Auto no longer asks the operator to turn it on',!before.text.includes('Step 2: turn on Auto with the button in this card'));
  if(process.env.QA_COPY_TEXT)check('new neutral Auto hint is visible',before.text.includes(process.env.QA_COPY_TEXT));
  check('both channel responses remain visible',before.text.includes('110.0 ms')&&before.text.includes('210.0 ms'));
  await page.screenshot({path:OUT+'/browser-copy-final.png',fullPage:true});
  const direction=before.state.model_kernel.role==='source'?'reserve':'primary';const ack=page.waitForResponse(r=>r.url().endsWith('/__qa/rpc/pair_manual'));
  await page.locator('[data-manual-direction="'+direction+'"]').filter({visible:true}).first().click();const answer=await(await ack).json();await page.evaluate(()=>fixturePoll());
  const queued=await snap('real-click-queued');check('real click creates one correlated queue request',answer.accepted===true&&answer.queued===true&&queued.state.status.manual_switch.state==='QUEUED'&&queued.state.status.manual_switch.request_id===answer.request_id);
  check('queue acknowledgment does not change real kernel role',queued.state.model_kernel.role===before.state.model_kernel.role);
  const consumed=await page.request.post(BASE+'/__qa/consume',{data:[]});if(!consumed.ok())throw Error('consume HTTP '+consumed.status());await page.evaluate(()=>fixturePoll());const after=await snap('native-consume-completed');
  check('current asset correlates completed actual transaction',after.state.status.manual_switch.state==='COMPLETED'&&after.state.status.manual_switch.request_id===answer.request_id);
  check('actual QEMU kernel changes to the requested role once',after.state.model_kernel.verified&&after.state.model_kernel.role!==before.state.model_kernel.role&&after.state.kernel_applications.length===before.state.kernel_applications.length+1);
  check('no browser script exceptions',report.errors.length===0);report.verdict=report.checks.every(c=>c.passed)?'PASS':'FAIL';
 }catch(error){report.verdict='FAIL';report.failure={name:error.name,message:error.message};process.exitCode=1;}
 finally{fs.writeFileSync(OUT+'/browser-copy-final.json',JSON.stringify(report,null,2));console.log(JSON.stringify({verdict:report.verdict,checks:report.checks,errors:report.errors,failure:report.failure},null,2));await browser.close();}
})();
