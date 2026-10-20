/* "Clueless user" persona run. CFG.tab carries the persona number 0..49, CFG.design the design.
   10 behaviours x 5 variants. Everything happens inside the iframe against the offline fixture; nothing leaves the machine.
   The result lists script errors, every RPC the page would have sent (with its parameter names) and health numbers. */
function foolFrameState(frame){
  try{
    var w=frame.contentWindow,d=frame.contentDocument;
    if(!w||!d)return {ready:false,reason:'navigation-pending'};
    var app=d.querySelector('.hv-app');
    if(d.readyState!=='complete'||!app||!d.querySelector('.hv-app .hv-attribution'))return {ready:false,reason:'app-pending'};
    if(!w.getComputedStyle(app).getPropertyValue('--dv-line').trim())return {ready:false,reason:'stylesheet-pending'};
    return {ready:true,doc:d,win:w};
  }catch(e){if(e&&e.name==='SecurityError')return {ready:false,reason:'navigation-origin-pending'};throw e;}
}
function foolCreateFrame(doc,cfg,host){
  var frame=doc.getElementById('f');
  if(!frame){frame=doc.createElement('iframe');frame.id='f';doc.body.appendChild(frame);}
  var output=doc.getElementById('result');if(output)output.hidden=true;
  doc.documentElement.style.overflow='hidden';doc.body.style.overflow='hidden';doc.body.style.margin='0';
  frame.style.cssText='display:block;border:0;width:'+Math.min(cfg.w,host.innerWidth)+'px;height:'+Math.min(cfg.h,host.innerHeight)+'px';
  return frame;
}
function foolFrameLayout(doc,frame,host){
  var r=frame.getBoundingClientRect();
  return {count:doc.querySelectorAll('iframe').length,left:r.left,top:r.top,width:r.width,height:r.height,viewportWidth:host.innerWidth,viewportHeight:host.innerHeight,
    visible:r.width>0&&r.height>0&&r.right>0&&r.bottom>0&&r.left<host.innerWidth&&r.top<host.innerHeight,
    inside:r.left>=0&&r.top>=0&&r.right<=host.innerWidth+1&&r.bottom<=host.innerHeight+1};
}
function foolReadinessDetails(frame){
  try{
    var w=frame.contentWindow,d=frame.contentDocument;if(!w||!d)return {accessible:false};
    var app=d.querySelector('.hv-app');
    function style(n){return n?{hvLine:w.getComputedStyle(n).getPropertyValue('--hv-line').trim(),dvLine:w.getComputedStyle(n).getPropertyValue('--dv-line').trim()}:null;}
    return {accessible:true,url:String(w.location.href).split('?')[0],readyState:d.readyState,app:!!app,design:app&&app.getAttribute('data-hv-design'),nodes:d.getElementsByTagName('*').length,
      apps:Array.prototype.slice.call(d.querySelectorAll('.hv-app')).map(function(n){var rect=n.getBoundingClientRect?n.getBoundingClientRect():null;return {class:n.getAttribute('class'),design:n.getAttribute('data-hv-design'),visible:rect?rect.width>0&&rect.height>0:null,style:style(n)};}),bodyStyle:style(d.body),stylesheetValue:app?style(app).dvLine:null,
      links:Array.prototype.slice.call(d.querySelectorAll('link[rel="stylesheet"]')).map(function(n){var detail={name:n.href.split('?')[0].split('/').pop(),sheet:!!n.sheet,disabled:n.disabled,media:n.media};try{detail.rules=n.sheet?n.sheet.cssRules.length:null;detail.matching=n.sheet?Array.prototype.slice.call(n.sheet.cssRules).filter(function(rule){return rule.cssText.indexOf('--dv-line')>=0;}).slice(0,3).map(function(rule){return rule.cssText.slice(0,300);}):[];}catch(error){detail.ruleError=error.name;}return detail;}),
      resources:w.performance.getEntriesByType('resource').map(function(r){return {name:r.name.split('?')[0],duration:Math.round(r.duration),bytes:r.transferSize,encodedBytes:r.encodedBodySize,decodedBytes:r.decodedBodySize,status:r.responseStatus||null};}).slice(-15),
      scriptErrors:(w.fixtureErrorDetails||[]).slice(-10)};
  }catch(error){return {accessible:false,error:error.name};}
}
async function foolWaitForReady(frame,timeout,sleep,now,onReady){
  var start=now(),lastDoc=null,state;
  do{
    state=foolFrameState(frame);
    if(state.ready){if(onReady)onReady(state);if(lastDoc===state.doc){state.waitMs=now()-start;return state;}lastDoc=state.doc;}else lastDoc=null;
    var left=timeout-(now()-start);if(left<=0)return {ready:false,reason:state.reason||'navigation-unstable',waitMs:now()-start};
    await sleep(Math.min(100,left));
  }while(true);
}
if(typeof module!=='undefined'&&module.exports){module.exports={frameState:foolFrameState,waitForReady:foolWaitForReady,readinessDetails:foolReadinessDetails,createFrame:foolCreateFrame,frameLayout:foolFrameLayout};}else{
window.addEventListener('error',function(e){try{fetch('/__result/'+CFG.id,{method:'POST',body:JSON.stringify({fatal:'TOP '+String(e.message)+' @'+e.lineno})});}catch(x){}});
(async function(){
  var P=Number(CFG.tab)||0,KINDS=['masher','numbers','vandal','doubleclick','wanderer','wizard','flipper','keys','spammer','resizer'];
  var kind=KINDS[P%10],variant=Math.floor(P/10);
  var seed=(P*7919+13)>>>0;function rnd(){seed=(seed+0x6D2B79F5)>>>0;var t=seed;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;}
  function pick(a){return a[Math.floor(rnd()*a.length)];}
  var res={persona:P,kind:kind,variant:variant,design:CFG.design,errors:[],steps:0,clicks:0,typed:0};
  var sleep=function(ms){return new Promise(function(r){setTimeout(r,ms);});};
  var NUMS=['0','-1','-999999','1e9','1e999','99999999999999999999','3.14','abc','','  12  ','0x10','١٢','-0','1,5','NaN','Infinity','12abc','+5','.5','5.','9'.repeat(400),'1','2','5','7','24','60','300','1000'];
  var TEXTS=['',' ','a'.repeat(10000),'<scr'+'ipt>alert(1)</scr'+'ipt>','"\'`${}','😀'.repeat(50),'‮evil','null','undefined','../../etc/passwd',"Robert');DROP TABLE x;--",'\n\n\n','12345:AAA','@x','-100123456789'];
  var f=foolCreateFrame(document,CFG,window);res.harnessLayout=foolFrameLayout(document,f,window);
  res.layoutReady=res.harnessLayout.count===1&&res.harnessLayout.visible&&res.harnessLayout.inside;
  if(!res.layoutReady){res.error='HARNESS-FRAME-NOT-VISIBLE';fetch('/__result/'+CFG.id,{method:'POST',body:JSON.stringify(res)});return;}
  function W(){return f.contentWindow;}function D(){return f.contentDocument;}
  var lag=0,last=Date.now();var lagTimer=setInterval(function(){var n=Date.now();lag=Math.max(lag,n-last-100);last=n;},100);
  var runStart=Date.now(),t0=null,budget=22000+variant*1500,capturedCalls=[],capturedDetails=[],seenCalls=new WeakSet(),seenErrors=new WeakSet(),seenDetails=new WeakSet();
  try{localStorage.clear();localStorage.setItem('homensai-vpn-design',CFG.design);}catch(e){}
  var attached=null;
  function attach(state){
    var w=state.win,d=state.doc;
    if(attached!==d){attached=d;res.documents=(res.documents||0)+1;if(!w.fixtureErrors){w.addEventListener('error',function(e){res.errors.push(String(e.message||e).slice(0,160));});w.addEventListener('unhandledrejection',function(e){res.errors.push('REJECTION '+String(e.reason&&e.reason.message||e.reason).slice(0,160));});}w.confirm=function(){return rnd()>.5;};w.alert=function(){};}
    // WindowProxy survives reloads; preserve calls and attach errors to each actual document.
    var errors=w.fixtureErrors;if(errors&&!seenErrors.has(errors)){seenErrors.add(errors);Array.prototype.push.apply(res.errors,errors);var errorPush=errors.push;errors.push=function(){Array.prototype.push.apply(res.errors,arguments);return errorPush.apply(this,arguments);};}
    var details=w.fixtureErrorDetails;if(details&&!seenDetails.has(details)){seenDetails.add(details);Array.prototype.push.apply(capturedDetails,details);var detailPush=details.push;details.push=function(){Array.prototype.push.apply(capturedDetails,arguments);return detailPush.apply(this,arguments);};}
    var calls=w.fixtureCalls;
    if(calls&&!seenCalls.has(calls)){seenCalls.add(calls);Array.prototype.push.apply(capturedCalls,calls);var push=calls.push;calls.push=function(){Array.prototype.push.apply(capturedCalls,arguments);return push.apply(this,arguments);};}
  }
  async function ready(phase,timeout){
    var state=await foolWaitForReady(f,timeout,sleep,Date.now,attach);
    res.waits=(res.waits||[]).concat([{phase:phase,ms:state.waitMs,ready:state.ready,reason:state.reason||null}]);
    if(!state.ready){res.errors.push('READINESS '+phase+' '+state.reason);res.readinessFailed=phase;res.readinessDetails=foolReadinessDetails(f);}
    return state.ready;
  }
  f.src='/?lang='+CFG.lang+'#'+pick(['start','overview','channels','settings','tests']);
  if(!await ready('initial',30000)){
    clearInterval(lagTimer);res.appAlive=false;res.attribution=false;res.footer=false;res.ms=Date.now()-runStart;
    fetch('/__result/'+CFG.id,{method:'POST',body:JSON.stringify(res)});return;
  }
  t0=Date.now();last=t0;lag=0;res.initialReadyMs=t0-runStart;res.nodesStart=D().getElementsByTagName('*').length;res.interactionStarted=true;
  function visible(n){if(n.closest&&n.closest('#fixture-banner'))return false;var r=n.getBoundingClientRect();return r.width>0&&r.height>0&&!n.disabled;}
  function all(sel){var state=foolFrameState(f);return state.ready?Array.prototype.slice.call(state.doc.querySelectorAll(sel)).filter(visible):[];}
  function safeClick(n){try{if(n.tagName==='A'&&((n.getAttribute('href')||'')!==''&&(n.getAttribute('href')||'').charAt(0)!=='#'||n.hasAttribute('download')))return;res.recent=(res.recent||[]).slice(-4).concat([(n.tagName+':'+(n.textContent||n.getAttribute('aria-label')||'').trim().slice(0,40)+'|'+(n.getAttribute('href')||''))]);n.click();res.clicks++;}catch(e){res.errors.push('CLICK '+String(e.message).slice(0,120));}}
  function setValue(n,v){try{
    if(n.type==='checkbox'||n.type==='radio'){n.checked=!n.checked;}else if(n.tagName==='SELECT'){var o=n.options;if(o.length)n.selectedIndex=Math.floor(rnd()*o.length);}else{try{n.value=v;}catch(e){}}
    n.dispatchEvent(new (n.ownerDocument.defaultView.Event)('input',{bubbles:true}));n.dispatchEvent(new (n.ownerDocument.defaultView.Event)('change',{bubbles:true}));res.typed++;}catch(e){res.errors.push('TYPE '+String(e.message).slice(0,120));}}
  function numberLike(n){return n.type==='number'||/interval|hour|duration|priority|budget|streams|limit/i.test(n.getAttribute('aria-label')||'');}
  function openSomething(){var l=all('[data-hv-tab]');if(l.length)safeClick(pick(l));}
  var wizardButtons=function(){return all('button').filter(function(b){return /wizard|мастер|setup|настро|telegram|recovery|speed|monitor/i.test(b.textContent);});};
  var lastAction='';
  setInterval(function(){try{fetch('/__result/prog-'+CFG.id,{method:'POST',body:JSON.stringify({step:res.steps,kind:kind,last:lastAction,errors:res.errors.slice(0,3)})});}catch(e){}},2000);
  async function step(){
    lastAction='step '+(res.steps+1);
    var state=foolFrameState(f);
    if(!state.ready){res.reloads=(res.reloads||0)+1;if(!await ready('reload',20000))return false;state=foolFrameState(f);}
    attach(state);
    res.steps++;
    var buttons=all('button'),inputs=all('input,select,textarea'),links=all('a[href^="#"],[data-hv-tab]');
    switch(kind){
      case 'masher': for(var i=0;i<6;i++){var c=buttons.concat(links);if(c.length)safeClick(pick(c));buttons=all('button');}await sleep(rnd()*30);break;
      case 'numbers': inputs.forEach(function(n){if(rnd()<.8)setValue(n,numberLike(n)?pick(NUMS):pick(NUMS.concat(TEXTS)));});if(rnd()<.6&&buttons.length)safeClick(pick(buttons));if(rnd()<.2)openSomething();await sleep(120);break;
      case 'vandal': inputs.forEach(function(n){if(rnd()<.7)setValue(n,pick(TEXTS));});if(buttons.length)safeClick(pick(buttons));await sleep(150);break;
      case 'doubleclick': if(buttons.length){var b=pick(buttons);safeClick(b);safeClick(b);safeClick(b);}await sleep(80);break;
      case 'wanderer': openSomething();var sel=all('select');if(sel.length&&rnd()<.3)setValue(pick(sel),'');if(rnd()<.2)try{W().location.hash='#'+pick(['start','readiness','overview','channels','statistics','settings','help','learn','tests','traffic','services','events','nonsense','']);}catch(e){}await sleep(60+rnd()*100);break;
      case 'wizard': var wb=wizardButtons();if(wb.length&&rnd()<.5)safeClick(pick(wb));else{var mb=all('.modal button, [role=dialog] button, .hv-wizard button');if(mb.length)safeClick(pick(mb));else openSomething();}if(rnd()<.3)D().dispatchEvent(new (W().KeyboardEvent)('keydown',{key:'Escape',bubbles:true}));await sleep(150);break;
      case 'flipper': inputs.filter(function(n){return n.type==='checkbox'||n.tagName==='SELECT'||n.type==='radio';}).forEach(function(n){if(rnd()<.6)setValue(n,'');});if(rnd()<.3)openSomething();await sleep(100);break;
      case 'keys': for(var k=0;k<8;k++){lastAction='key '+k+' step '+res.steps;D().dispatchEvent(new (W().KeyboardEvent)('keydown',{key:pick(['1','2','3','4','5','6','7','8','9','0','/','Escape','Enter','Tab',' ','ArrowDown','a','?']),bubbles:true}));}if(rnd()<.2)openSomething();await sleep(60);break;
      case 'spammer': var danger=buttons.filter(function(b){return /test|тест|auto|start|stop|return|run|check|провер|запуст|стоп|вернуть|speed|скорост|retry|refresh|scan/i.test(b.textContent);});var pool=danger.length?danger:buttons;if(pool.length){var tb=pick(pool);for(var j=0;j<10;j++)safeClick(tb);}if(rnd()<.25)openSomething();await sleep(40);break;
      case 'resizer': try{f.style.width=Math.min(pick([320,360,414,768,1024,1440,2560]),window.innerWidth)+'px';f.style.height=Math.min(pick([300,568,896,1200]),window.innerHeight)+'px';W().scrollTo(0,Math.floor(rnd()*4000));}catch(e){}if(rnd()<.4)openSomething();if(rnd()<.3&&buttons.length)safeClick(pick(buttons));await sleep(100);break;
    }
  }
  try{
    var max=80+variant*30;
    while(res.steps<max&&Date.now()-t0<budget){try{if(await step()===false)break;}catch(error){if(!foolFrameState(f).ready){res.navigationInterrupts=(res.navigationInterrupts||0)+1;if(!await ready('navigation',20000))break;}else throw error;}}
  }catch(e){res.errors.push('PERSONA '+String(e&&e.message||e).slice(0,160));}
  res.interactionMs=Date.now()-t0;
  var finalReady=await ready('final',20000);
  clearInterval(lagTimer);
  res.finalHarnessLayout=foolFrameLayout(document,f,window);
  if(res.finalHarnessLayout.count!==1||!res.finalHarnessLayout.visible||!res.finalHarnessLayout.inside){res.layoutReady=false;res.errors.push('HARNESS-FRAME-NOT-VISIBLE');}
  try{
    var calls=capturedCalls;res.callCount=calls.length;res.callsTruncated=calls.length>400;
    res.calls=calls.slice(0,400).map(function(c){return {m:c.method,p:c.params||null,a:(c.args||[]).map(function(x){return typeof x==='string'&&x.length>80?x.slice(0,80)+'…['+x.length+']':x;})};});
    if(!finalReady){res.appAlive=false;res.attribution=false;res.footer=false;}else{
    res.nodesEnd=D().getElementsByTagName('*').length;
    res.modalOpen=!!D().querySelector('.modal-overlay,.modal,[role=dialog]');
    res.appAlive=!!D().querySelector('.hv-app');
    res.attribution=!!D().querySelector('.hv-attribution');
    res.footer=!!D().querySelector('.hv-footer,.hv-author,footer');
    res.notices=D().querySelectorAll('.alert-message,.notice,.hv-notice').length;
    res.docOverflow=Math.max(0,D().documentElement.scrollWidth-W().innerWidth);
    }
    res.maxLag=lag;res.ms=Date.now()-runStart;
    res.scriptErrorDetails=capturedDetails.slice(-20);
  }catch(e){res.errors.push('COLLECT '+String(e&&e.message||e).slice(0,160));}
  fetch('/__result/'+CFG.id,{method:'POST',body:JSON.stringify(res)});
})();

}
