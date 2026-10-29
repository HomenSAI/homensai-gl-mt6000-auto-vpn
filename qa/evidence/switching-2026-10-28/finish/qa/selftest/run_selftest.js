/* Self-test of real_click_chain.js against the loopback SYNTHETIC LuCI fixture.
 * Env: QA_REPO (checkout or exact tree export), QA_DASHBOARD (default: dashboard from the menu in QA_REPO),
 *      QA_PLAYWRIGHT, QA_CHROMIUM, QA_SELFTEST_OUT (new dir), QA_HTTP_PORT (default 18993).
 * Proves selectors, login handling, ubus capture/redaction, click/timeline/terminal logic and the
 * refuse-to-click precondition. It does NOT prove anything about the router, controller or kernel.
 */
'use strict';
const fs=require('fs'),path=require('path'),cp=require('child_process'),crypto=require('crypto');
const {start}=require('./fixture_server');
const REPO=path.resolve(process.env.QA_REPO),OUT=path.resolve(process.env.QA_SELFTEST_OUT),PORT=Number(process.env.QA_HTTP_PORT||18993);
const menu=JSON.parse(fs.readFileSync(path.join(REPO,'router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json')));
const DASH=path.resolve(process.env.QA_DASHBOARD||path.join(REPO,'router/files/www/luci-static/resources/view/homensai-vpn',menu['admin/services/homensai-vpn'].action.path.split('/').pop()+'.js'));
const SCRIPT=path.join(__dirname,'..','real_click_chain.js');
const USER='root',PASS='selftest-'+crypto.randomBytes(6).toString('hex');
if(fs.existsSync(OUT)&&fs.readdirSync(OUT).length)throw Error('QA_SELFTEST_OUT must be new or empty');
fs.mkdirSync(OUT,{recursive:true});

const scenarios=[
  {name:'01-dry-run-to-reserve',action:'to-reserve',env:{QA_DRY_RUN:'1'},expect:{verdict:'NOT-RUN',outcome:'DRY-RUN-PRECONDITION-OK',exit:2,commands:0}},
  {name:'02-refuse-to-primary-when-primary-selected',action:'to-primary',env:{QA_PRECONDITION_WAIT_S:'8'},expect:{verdict:'NOT-RUN',outcome:'NOT-RUN-PRECONDITION',exit:2,commands:0}},
  {name:'03-to-reserve',action:'to-reserve',expect:{verdict:'PASS',outcome:'COMPLETED',exit:0,commands:1,active:'target',hold:'target'}},
  {name:'04-reselect-current-reserve',action:'reselect-current',env:{QA_NO_COMMAND_WINDOW_S:'12'},expect:{verdict:'PASS',outcome:'NO-COMMAND-SENT',exit:0,commands:0,active:'target'}},
  {name:'05-resume',action:'resume',expect:{verdict:'PASS',outcome:'COMPLETED',exit:0,commands:1,active:'target',hold:null}},
  {name:'06-to-primary',action:'to-primary',expect:{verdict:'PASS',outcome:'COMPLETED',exit:0,commands:1,active:'source',hold:'source'}},
  {name:'07-resume-again',action:'resume',expect:{verdict:'PASS',outcome:'COMPLETED',exit:0,commands:1,active:'source',hold:null}},
  {name:'08-refused-at-rpc',action:'to-reserve',mode:{refuse:true},expect:{verdict:'FAIL',outcome:'REFUSED-AT-RPC',exit:1,commands:1,active:'source'}},
  {name:'10-snapshot-hook-to-reserve',action:'to-reserve',snap:true,expect:{verdict:'PASS',outcome:'COMPLETED',exit:0,commands:1,active:'target',hold:'target'}},
  {name:'11-snapshot-hook-reselect-current',action:'reselect-current',snap:true,env:{QA_NO_COMMAND_WINDOW_S:'10'},expect:{verdict:'PASS',outcome:'NO-COMMAND-SENT',exit:0,commands:0,active:'target'}},
  {name:'12-snapshot-hook-resume',action:'resume',snap:true,expect:{verdict:'PASS',outcome:'COMPLETED',exit:0,commands:1,active:'target',hold:null}},
  {name:'13-lost-ack-to-primary',action:'to-primary',mode:{dropAck:true},note:'fixture resets the socket of the first pair_manual POST; Chromium transparently re-sends it, the backend answers PAIR-MANUAL-BUSY to the copy while the original is queued',expect:{verdict:'PASS',outcome:'COMPLETED',exit:0,commands:2,active:'source',correlation:/^status-fence/}},
];

(async()=>{
  const fx=await start({repo:REPO,dashboard:DASH,port:PORT,user:USER,pass:PASS});
  const summary={scope:'SYNTHETIC loopback LuCI imitation + exact generated dashboard; validates the recorder only',dashboard:path.basename(DASH),dashboard_sha256:fx.dashboardSha256,
    script_sha256:crypto.createHash('sha256').update(fs.readFileSync(SCRIPT)).digest('hex'),results:[]};
  try{
    const only=process.env.QA_SELFTEST_ONLY?new RegExp(process.env.QA_SELFTEST_ONLY):null;
    for(const s of scenarios.filter(x=>!only||only.test(x.name))){
      fx.setMode({refuse:false,dropAck:false,...(s.mode||{})});
      const before=fx.state.log.length,out=path.join(OUT,s.name),t=Date.now();
      const r=await new Promise(resolve=>{const c=cp.spawn(process.execPath,[SCRIPT],{env:{...process.env,QA_BASE_URL:fx.url,QA_LUCI_USER:USER,QA_LUCI_PASS:PASS,QA_ACTION:s.action,QA_OUT:out,
        QA_TIMEOUT_S:'40',QA_SETTLE_S:'5',QA_PRECONDITION_WAIT_S:'30',...(s.snap?{QA_SNAPSHOT_CMD:JSON.stringify(process.execPath)+' -e "fetch(\'http://127.0.0.1:'+PORT+'/__fixture/snapshot\').then(r=>r.text()).then(t=>process.stdout.write(t))"'}:{}),...(s.env||{})}});let err='';c.stderr.on('data',d=>err+=d);c.stdout.on('data',()=>{});const k=setTimeout(()=>c.kill(),400000);c.on('close',code=>{clearTimeout(k);resolve({status:code,stderr:err});});});
      fx.setMode({refuse:false,dropAck:false});
      let rep=null;try{rep=JSON.parse(fs.readFileSync(path.join(out,'report.json'),'utf8'));}catch(e){}
      const text=fs.existsSync(out)?fs.readdirSync(out).filter(f=>/\.(json|jsonl)$/.test(f)).map(f=>fs.readFileSync(path.join(out,f),'utf8')).join('\n'):'';
      const got={exit:r.status,verdict:rep&&rep.verdict,outcome:rep&&rep.outcome,commands:fx.state.log.length-before,active:fx.state.active,hold:fx.state.hold,correlation:rep&&rep.rpc&&rep.rpc.correlation,
        password_leaked:text.includes(PASS),session_leaked:fx.secrets.some(x=>text.includes(x)),checks:rep&&rep.checks.map(c=>(c.passed?'PASS ':'FAIL ')+c.name),
        precondition_reasons:rep&&rep.precondition&&rep.precondition.reasons,chain:rep&&rep.chain,timeline_rows:rep&&rep.timeline.length,seconds:Math.round((Date.now()-t)/1000)};
      const e=s.expect,fails=[];
      for(const k of ['exit','verdict','outcome','commands','active'])if(k in e&&e[k]!==got[k])fails.push(k+': expected '+e[k]+' got '+got[k]);
      if('hold' in e&&e.hold!==got.hold)fails.push('hold: expected '+e.hold+' got '+got.hold);
      if(e.correlation&&!e.correlation.test(String(got.correlation)))fails.push('correlation '+got.correlation);
      if(got.password_leaked)fails.push('PASSWORD LEAKED INTO EVIDENCE');if(got.session_leaked)fails.push('SESSION/COOKIE/STOK LEAKED INTO EVIDENCE');
      summary.results.push({name:s.name,action:s.action,expected:{...e,correlation:e.correlation&&String(e.correlation)},got,passed:fails.length===0,fails,stderr:r.stderr&&r.stderr.slice(-800)});
      console.log((fails.length?'FAIL ':'PASS ')+s.name+' '+JSON.stringify({outcome:got.outcome,verdict:got.verdict,exit:got.exit,commands:got.commands,s:got.seconds})+(fails.length?' '+fails.join('; '):''));
    }
  }finally{
    await fx.close();
    summary.only=process.env.QA_SELFTEST_ONLY||null;summary.verdict=!summary.only&&summary.results.length===scenarios.length&&summary.results.every(r=>r.passed)?'PASS':'FAIL';
    fs.writeFileSync(path.join(OUT,'selftest-summary.json'),JSON.stringify(summary,null,2)+'\n');
    console.log('SELFTEST '+summary.verdict+' '+summary.results.filter(r=>r.passed).length+'/'+scenarios.length);
    if(summary.verdict!=='PASS')process.exitCode=1;
  }
})();
