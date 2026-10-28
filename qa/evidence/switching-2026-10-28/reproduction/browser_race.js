const fs=require('fs'),{chromium}=require(process.env.QA_PLAYWRIGHT||(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES?process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES+'/playwright':'playwright'));
const OUT=(process.env.QA_OUTPUT||__dirname),LABEL=process.env.QA_LABEL||'baseline';
const report={scope:'Real Chromium click -> actual Python manual queue, simulated device/kernel',case:'ack plus stale pre-ack status response',errors:[],steps:[]};
(async()=>{
 const b=await chromium.launch({executablePath:(process.env.QA_CHROMIUM||require('path').join(__dirname,'../qa-browsers/chrome-linux64/chrome')),headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  const p=await b.newPage({viewport:{width:1440,height:1200}});
  p.on('pageerror',e=>report.errors.push(e.message));
  await p.addInitScript(()=>{Date.now=()=>1792750000*1000;localStorage.setItem('homensai-vpn-design','b');localStorage.setItem('homensai-vpn-theme','light');localStorage.setItem('homensai-vpn-language','en');});
  await p.goto('http://127.0.0.1:'+(process.env.QA_HTTP_PORT||18988)+'/#overview',{waitUntil:'networkidle'});
  const button=()=>p.locator('[data-manual-direction="primary"]').filter({visible:true}).first();
  await button().waitFor();
  await p.evaluate(()=>fetch('/__qa/capture',{method:'POST',body:'[]'}));
  report.steps.push({name:'before',enabled:await button().isEnabled(),state:await p.evaluate(()=>__qaSnapshot())});
  await button().click();await p.waitForTimeout(200);
  report.steps.push({name:'ack',calls:await p.evaluate(()=>fixtureCalls.filter(c=>c.method==='pair_manual')),state:await p.evaluate(()=>__qaSnapshot())});
  await p.evaluate(()=>fetch('/__qa/replay',{method:'POST',body:JSON.stringify({count:1})}));
  await p.evaluate(()=>fixturePoll());
  report.steps.push({name:'stale-redraw',enabled:await button().isEnabled(),buttons:await p.locator('[data-manual-direction]').allTextContents()});
  await p.screenshot({path:OUT+'/browser-race-'+LABEL+'.png',fullPage:true});
  if(await button().isEnabled()){await button().click();await p.waitForTimeout(200);}
  report.calls=await p.evaluate(()=>fixtureCalls.filter(c=>c.method==='pair_manual'));
  report.actual=await p.evaluate(()=>__qaSnapshot());
  report.assertions={single_browser_rpc:report.calls.length===1,still_queued:report.actual.status.manual_switch.state==='QUEUED',no_script_errors:report.errors.length===0};
  console.log(JSON.stringify({assertions:report.assertions,calls:report.calls,steps:report.steps.map(s=>({name:s.name,enabled:s.enabled})),errors:report.errors},null,2));
 }catch(e){report.failure=e.message;console.error(e);process.exitCode=1;}
 finally{fs.writeFileSync(OUT+'/browser-race-'+LABEL+'.json',JSON.stringify(report,null,2));await b.close();}
})()
