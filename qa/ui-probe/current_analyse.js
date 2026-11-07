/* Current shipped .hvx UI, actual clicks and measured geometry; no legacy aliases. */
(async function(){
 const frame=document.getElementById('f'),rows=[],errors=[];let group=null;
 const sleep=ms=>new Promise(r=>setTimeout(r,ms));
 const D=()=>frame.contentDocument,W=()=>frame.contentWindow,$=s=>D().querySelector(s),all=s=>Array.from(D().querySelectorAll(s));
 const check=(value,message)=>{if(!value)throw Error(message);};
 async function until(fn,label,seconds=15){const end=Date.now()+seconds*1000;while(Date.now()<end){const value=fn();if(value)return value;await sleep(80);}throw Error(label);}
 async function settle(){await sleep(140);await new Promise(r=>W().requestAnimationFrame(()=>W().requestAnimationFrame(r)));}
 function scriptErrors(){return W().fixtureErrors||[];}
 function visible(node){if(!node)return false;const r=node.getBoundingClientRect(),s=W().getComputedStyle(node);return r.width>0&&r.height>0&&s.visibility!=='hidden'&&s.display!=='none';}
 function overflow(){return Math.max(0,D().documentElement.scrollWidth-W().innerWidth);}
 function base(){
  const root=$('.hvx');check(visible(root),'current root missing');check(root.lang===group.lang,'locale mismatch');
  check(root.getAttribute('data-theme')===group.theme,'theme mismatch');check(W().innerWidth===group.width,'viewport mismatch');
  check(scriptErrors().length===0,'app errors '+JSON.stringify(scriptErrors()));check(overflow()<=1,'horizontal overflow '+overflow());
  const footer=$('footer.hv-attribution'),badge=$('.hv-version');
  check(visible(footer)&&visible(badge),'identity missing');check(badge.textContent==='v'+CFG.version,'wrong app version');
  check(/Serhii Khomenko/.test(footer.textContent)&&footer.querySelector('a[href="https://homensai.com"]'),'author/link missing');
  check(!/пакет|страница|package|dashboard\d+|ui\d+\.css|\d+-\d+/i.test(footer.textContent),'footer exposes package/page');
  check(($('[data-b="buildline"]')||{}).textContent===(group.lang==='ru'?'Программа ':'Program ')+CFG.version,'wrong program build line');
  return {width:W().innerWidth,overflow:overflow(),rootClass:root.className,footer:footer.textContent,badge:badge.textContent};
 }
 async function row(kind,extra,fn){
  const value=Object.assign({group,kind},extra);try{Object.assign(value,await fn());value.pass=true;}
  catch(error){value.pass=false;value.error=String(error.message||error);value.scriptErrors=scriptErrors();}
  rows.push(value);await fetch('/__row/'+CFG.run,{method:'POST',body:JSON.stringify(value)});
  if(!value.pass)throw Error(value.error);return value;
 }
 function collect(){try{errors.push(...scriptErrors().map(message=>({group,message})));}catch(e){}}
 async function load(scene='ok',extra={},hash='home'){
  if(D()&&$('.hvx'))collect();
  localStorage.setItem('homensai-vpn-view','simple');localStorage.setItem('homensai-vpn-theme',group.theme);
  localStorage.setItem('homensai-vpn-language',group.lang);
  frame.style.width=group.width+'px';frame.style.height='1000px';const previous=D();
  const query=new URLSearchParams(Object.assign({fixture:'pair',scn:scene,lang:group.lang,navigation:Math.random().toString(16).slice(2)},extra));
  frame.src='/?'+query+'#'+hash;
  await until(()=>D()!==previous&&D().readyState==='complete'&&$('.hvx')&&$('link[data-hvx-css]')&&$('link[data-hvx-css]').sheet&&W().getComputedStyle($('.hvx')).getPropertyValue('--line').trim(),'CURRENT-APP/CSS-READINESS');
  await settle();
 }
 async function click(selector){const node=$(selector);check(visible(node),'visible action missing '+selector);check(!node.disabled,'disabled action '+selector);node.click();await settle();}
 async function go(surface){
  const simple=['home','settings'].includes(surface);
  if(!$('.hvx').classList.contains(simple?'v-simple':'v-console'))await click('[data-act="view"][data-v="'+(simple?'simple':'console')+'"]');
  await click(simple?'[data-act="go"][data-p="'+surface+'"]':'[data-act="tab"][data-t="'+surface+'"]');
  check(W().location.hash==='#'+surface,'navigation hash '+surface);
 }
 function gold(){
  const grid=$('.gold')||$('.wiz');if(!grid)return {applicable:false};
  const left=grid.querySelector('.gcol.gl,.wz-side'),right=grid.querySelector('.gcol.gr,.wz-main');
  if(group.width<=900){
   const style=W().getComputedStyle(grid),bounds=grid.getBoundingClientRect();
   check(style.display==='flex'&&style.flexDirection==='column','mobile golden columns must stack');
   const nodes=grid.classList.contains('wiz')?Array.from(grid.children):Array.from(grid.querySelectorAll(':scope > .gcol > *'));
   const boxes=nodes.filter(visible).map(n=>{const r=n.getBoundingClientRect();return {class:n.className,left:r.left,top:r.top,bottom:r.bottom,width:r.width};}).sort((a,b)=>a.top-b.top);
   check(boxes.length>=2,'mobile golden items missing');
   boxes.forEach((box,i)=>{check(Math.abs(box.left-bounds.left)<=2&&Math.abs(box.width-bounds.width)<=2,'mobile item is not full-width '+box.class);if(i)check(box.top>=boxes[i-1].bottom-1,'mobile golden items overlap/are side-by-side');});
   return {applicable:false,mobileStack:true,containerWidth:bounds.width,boxes};
  }
  const a=left.getBoundingClientRect().width,b=right.getBoundingClientRect().width,share=b/(a+b);
  check(Math.abs(share-.618)<=CFG.goldTolerance,'gold column ratio '+share);return {applicable:true,left:a,right:b,rightShare:share,tolerance:CFG.goldTolerance};
 }
 function traffic(role){
  const pair=$('.chpair'),active=pair&&pair.querySelector('.ch.active'),cards=pair&&Array.from(pair.querySelectorAll('.ch'));
  check(pair&&cards.length===2,'two traffic cards missing');check(active&&active.dataset.ch===role,'wrong traffic channel '+role);
  const a=cards[0].getBoundingClientRect(),b=cards[1].getBoundingClientRect();
  const bounds=pair.getBoundingClientRect();
  if(group.width<=900||bounds.width<=520){
   check(b.top>=a.bottom-1,'mobile traffic cards are not vertically stacked');
   check(Math.abs(a.left-bounds.left)<=2&&Math.abs(b.left-bounds.left)<=2&&Math.abs(a.width-bounds.width)<=2&&Math.abs(b.width-bounds.width)<=2,'stacked traffic cards must fill their column');
   return {role,applicable:false,stacked:true,containerWidth:bounds.width,primaryWidth:a.width,reserveWidth:b.width,primaryTop:a.top,primaryBottom:a.bottom,reserveTop:b.top};
  }
  check(Math.abs(a.top-b.top)<=2,'desktop traffic cards unexpectedly stack');
  const share=active.getBoundingClientRect().width/(a.width+b.width);
  check(Math.abs(share-.618)<=CFG.goldTolerance,'traffic share '+role+' '+share);
  return {role,applicable:true,primaryWidth:a.width,reserveWidth:b.width,activeShare:share,tolerance:CFG.goldTolerance};
 }
 async function disclosures(surface){
  const keys=all('details.sec,details.more,details[data-help-sec]').map((n,i)=>({id:n.id,open:n.dataset.open,index:i}));
  for(const key of keys){
   const nodes=all('details.sec,details.more,details[data-help-sec]'),node=key.id?D().getElementById(key.id):key.open?nodes.find(n=>n.dataset.open===key.open):nodes[key.index];
   if(!node||!visible(node))continue;
   node.open=true;await settle();
   await row('disclosure',{surface,section:key.id||key.open||String(key.index)},()=>({geometry:base()}));
   node.open=false;await settle();
  }
 }
 async function pages(){
  const markers={home:'[data-g="status"]',settings:'#sec-pair',ch:'.chpair',auto:'[data-g="auto"]',srv:'.srvpair',log:'#evbox',sys:'#ready'};
  for(const surface of ['home','settings','ch','auto','srv','log','sys']){
   await go(surface);
   await row('page',{surface},()=>{check(visible($(markers[surface])),'surface marker '+surface);
    const nav=$(surface==='home'||surface==='settings'?'[data-act="go"][aria-current="page"]':'[role="tab"][aria-selected="true"]');
    check(nav&&(nav.dataset.p||nav.dataset.t)===surface,'selected navigation '+surface);return {geometry:base(),gold:gold()};});
   if(surface==='home')await row('traffic',{role:'primary'},()=>traffic('primary'));
   if(surface==='ch')await row('traffic-console',{role:'primary'},()=>traffic('primary'));
   await disclosures(surface);
  }
  await go('home');await click('[data-act="helpall"]');
  await until(()=>$('.modal .mb')&&$('.modal .mb').textContent.trim().length>30,'HELP-MODAL');
  await row('modal',{modal:'help'},()=>({geometry:base(),textLength:$('.modal .mb').textContent.length}));
  D().dispatchEvent(new (W().KeyboardEvent)('keydown',{key:'Escape',bubbles:true}));await settle();check(!$('.modal-bg'),'Escape did not close help');
 }
 function step(){const node=$('.wiz .steps li.cur');return node?Array.from(node.parentElement.children).indexOf(node)+1:null;}
 function noControl(){check(!(W().fixtureCalls||[]).some(c=>/^native_|^terms_accept$/.test(c.method)),'wizard silently controls Auto/terms');}
 function fill(selector,value){const node=$(selector);check(node,'field missing '+selector);node.value=value;node.dispatchEvent(new (W().Event)('input',{bubbles:true}));node.dispatchEvent(new (W().Event)('change',{bubbles:true}));}
 async function wizard(){
  await load('first');check($('.hvx.v-wizard'),'natural first-run wizard missing');
  await row('wizard',{step:1},()=>{check(step()===1,'wizard step1');noControl();return {geometry:base(),gold:gold()};});
  await click('[data-act="wnext"]');check(step()===2,'wizard step2');
  const choices=Array.from($('select[data-set="pairP"]').options).filter(n=>n.value).map(n=>n.value);check(choices.length>=2,'fixture requires two configured channels');
  fill('select[data-set="pairP"]',choices[0]);fill('select[data-set="pairR"]',choices[0]);await click('[data-act="wnext"]');
  await row('boundary',{boundary:'same-pair-rejected'},()=>{check(step()===2&&$('.modal-bg'),'same pair advanced');noControl();return {};});
  D().dispatchEvent(new (W().KeyboardEvent)('keydown',{key:'Escape',bubbles:true}));await settle();fill('select[data-set="pairR"]',choices[1]);
  await row('wizard',{step:2},()=>({geometry:base(),gold:gold(),source:choices[0],target:choices[1]}));await click('[data-act="wnext"]');
  await row('wizard',{step:3},()=>{check(step()===3,'wizard step3');noControl();return {geometry:base(),gold:gold()};});await click('[data-act="wnext"]');
  await row('wizard',{step:4},()=>{check(step()===4,'wizard step4');const boxes=all('.wacc');check(boxes.length&&boxes.every(n=>!n.checked),'terms pre-accepted');check($('#wstart').disabled,'Start unlocked without terms');check(visible($('[data-act="wsave"]')),'save-without-start missing');noControl();return {geometry:base(),gold:gold()};});
  await click('[data-act="wprev"]');await click('[data-act="wprev"]');check($('select[data-set="pairR"]').value===choices[1],'wizard back loses draft');
  await click('[data-act="wnext"]');await click('[data-act="wnext"]');await click('[data-act="wskip"]');
  await until(()=>!$('.hvx.v-wizard'),'WIZARD-SKIP');
  await row('boundary',{boundary:'skip-without-start'},()=>{noControl();return {geometry:base()};});
  await load('first');await click('[data-act="wnext"]');
  fill('select[data-set="pairP"]',choices[0]);fill('select[data-set="pairR"]',choices[1]);
  await click('[data-act="wnext"]');await click('[data-act="wnext"]');await click('[data-act="wsave"]');
  await until(()=>!$('.hvx.v-wizard'),'WIZARD-SAVE-WITHOUT-START');
  await row('boundary',{boundary:'save-without-start'},()=>{noControl();check((W().fixtureCalls||[]).filter(c=>c.method==='setup_onboarding').length===1,'duplicate aggregate save');return {geometry:base()};});
  for(const scene of ['ok','off']){
   await load(scene,{incomplete:'1'});
   await row('boundary',{boundary:scene==='ok'?'running-suppresses-first-run':'existing-pair-suppresses-first-run'},()=>{check(!$('.hvx.v-wizard'),'configured/running session covered by wizard');noControl();return {geometry:base()};});
  }
  await load('ok',{wizard:'1'});check($('.hvx.v-wizard'),'explicit wizard missing');await click('[data-act="wnext"]');await click('[data-act="wnext"]');await click('[data-act="wnext"]');
  await row('boundary',{boundary:'explicit-wizard-running'},()=>{check($('[data-wiz-running]')&&!$('#wstart'),'running wizard offers Start');noControl();return {geometry:base()};});
  await click('[data-act="wskip"]');await until(()=>!$('.hvx.v-wizard'),'RUNNING-SKIP');noControl();
 }
 window.addEventListener('error',e=>errors.push({message:String(e.message||e)}));
 for(const current of CFG.groups){group=current;try{
  await load();await pages();await load('reserve');await row('traffic',{role:'reserve'},()=>({geometry:base(),...traffic('reserve')}));
  await go('ch');await row('traffic-console',{role:'reserve'},()=>traffic('reserve'));
  await wizard();collect();
 }catch(error){errors.push({group,message:String(error.message||error)});}}
 await fetch('/__done/'+CFG.run,{method:'POST',body:JSON.stringify({complete:true,rows,errors,userAgent:navigator.userAgent,scope:'synthetic current shipped UI, one Edge process; no real router'})});
})().catch(async error=>{await fetch('/__done/'+CFG.run,{method:'POST',body:JSON.stringify({complete:false,rows:[],errors:[String(error.message||error)]})});});
