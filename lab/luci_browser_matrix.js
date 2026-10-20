/* Actual isolated LuCI only. Never collect cookies, CSRF/session values or RPC bodies. */
(async function(){
  const f=document.getElementById('lab-frame'),rows=[],errors=[],bootstrap=[],documents=new WeakSet();
  let step='initial',navigationSequence=0;
  const rpcDocuments=new WeakSet(),rpcMetrics={requests:0,timeouts:0,overDefault:0,maxDurationMs:0,samples:[]};
  let consent=null;
  const sleep=ms=>new Promise(r=>setTimeout(r,ms));
  const tabs=['start','readiness','overview','channels','statistics','traffic','services','events','settings','tests','help','learn'];
  function state(){try{return {w:f.contentWindow,d:f.contentDocument};}catch(e){return {};}}
  function watch(w,d){
    if(!w||!d||documents.has(d))return;documents.add(d);
    w.addEventListener('error',ev=>{bootstrap.push({kind:'error',line:ev.lineno||0});errors.push('ACTUAL-APP-SCRIPT-ERROR');});
    w.addEventListener('unhandledrejection',()=>{bootstrap.push({kind:'rejection'});errors.push('ACTUAL-APP-UNHANDLED-REJECTION');});
  }
  function acceptTermsGate(gate,requiredVersion){
    if(!requiredVersion)throw new Error('ACTUAL-CONSENT-REQUIRED');
    const version=gate.getAttribute('data-terms-gate'),boxes=Array.from(gate.querySelectorAll('.hv-terms-check input[type="checkbox"]')),button=gate.querySelector('.hv-terms-accept');
    if(requiredVersion!=='1'||version!==requiredVersion||boxes.length!==2||!button)throw new Error('ACTUAL-CONSENT-CONTROLS-INVALID');
    boxes.forEach(box=>{if(!box.checked)box.click();});
    if(!boxes.every(box=>box.checked===true)||button.disabled)throw new Error('ACTUAL-CONSENT-CONTROLS-INVALID');
    const record={version,acceptedBefore:false,clickedAt:Date.now(),acceptedAfter:false,verifiedAt:null};
    button.click();return record;
  }
  function localRpc(raw,base){
    try{const u=new URL(raw,base),origin=new URL(base).origin;
      return u.origin===origin&&(u.pathname==='/ubus'||u.pathname.startsWith('/ubus/')||u.pathname==='/cgi-bin/luci/admin/ubus'||u.pathname.startsWith('/cgi-bin/luci/admin/ubus/'));
    }catch(e){return false;}
  }
  function installRpcDeadline(w,d){
    if(rpcDocuments.has(d))return;rpcDocuments.add(d);
    const prototype=w.XMLHttpRequest.prototype,open=prototype.open,send=prototype.send,metadata=new WeakMap();
    prototype.open=function(method,url,...args){
      const result=open.call(this,method,url,...args);
      if(String(method).toUpperCase()==='POST'&&localRpc(url,w.location.href)){
        const item={started:null,timedOut:false,previousMs:null};metadata.set(this,item);
        this.addEventListener('timeout',()=>{item.timedOut=true;},{once:true});
        this.addEventListener('loadend',()=>{
          if(item.started===null)return;
          const duration=Math.round(w.performance.now()-item.started),sample={durationMs:duration,timeout:item.timedOut,status:this.status,previousMs:item.previousMs,deadlineMs:this.timeout};
          rpcMetrics.requests++;rpcMetrics.timeouts+=item.timedOut?1:0;rpcMetrics.overDefault+=duration>20000?1:0;
          rpcMetrics.maxDurationMs=Math.max(rpcMetrics.maxDurationMs,duration);rpcMetrics.samples.push(sample);
          if(rpcMetrics.samples.length>256)rpcMetrics.samples.shift();
        },{once:true});
      }else metadata.delete(this);
      return result;
    };
    prototype.send=function(...args){
      const item=metadata.get(this);
      if(item){item.started=w.performance.now();item.previousMs=this.timeout;if(CFG.rpcTimeout===60)this.timeout=60000;}
      return send.apply(this,args);
    };
  }
  function safeName(raw){
    try{const path=new URL(raw,location.href).pathname,base=path.split('/').pop()||'';
      if(/^[A-Za-z0-9_.-]{1,100}\.(?:js|css|woff2?|ttf|svg|png|jpe?g|gif|ico)$/.test(base))return base;
      return /\/ubus\/?$/.test(path)?'rpc':'document-or-other';
    }catch(e){return 'unknown';}
  }
  function navigationKind(raw){
    try{const u=new URL(raw,location.href);
      if(u.protocol==='about:')return 'aboutblank';
      if(['chrome-error:','edge-error:','chrome:','edge:'].includes(u.protocol))return 'browsererror';
      if(u.origin===location.origin)return u.pathname.startsWith('/cgi-bin/luci')?'local-luci':'local-other';
      return 'other';
    }catch(e){return 'unavailable';}
  }
  function diagnostics(){
    const {w,d}=state();if(!w||!d)return {accessible:false};
    const app=d.querySelector('.hv-app'),brand=w.HomenS||{};
    const resources=w.performance.getEntriesByType('resource');
    const messages=Array.from(d.querySelectorAll('h1,.alert-message,.cbi-section-error,#maincontent h2,#view h2,.modal h4,#maincontent pre,#view pre')).slice(0,6).map(n=>(n.innerText||'')
      .replace(/https?:\/\/\S+|\/cgi-bin\/luci\/;stok=\S+/g,'[url]')
      .replace(/[A-Za-z0-9_+/=-]{24,}/g,'[redacted]').slice(0,240));
    let navigation='unavailable';try{navigation=navigationKind(w.location.href);}catch(e){}
    return {accessible:true,navigation,iframeSource:navigationKind(f.src),state:d.readyState,login:!!d.querySelector('[name=luci_password]'),app:!!app,
      attribution:!!d.querySelector('.hv-attribution'),css:!!(app&&w.getComputedStyle(app).getPropertyValue('--dv-line').trim()),hasL:!!w.L,
      terms:!!d.querySelector('.hv-terms'),languageControls:d.querySelectorAll('.hv-app select[aria-label="Language"],.hv-app select[aria-label="Язык"]').length,startTab:!!d.querySelector('[data-hv-tab="start"]'),
      main:!!d.querySelector('#maincontent'),view:!!d.querySelector('#view'),loading:d.querySelectorAll('.loading,.spinning').length,
      errorCount:d.querySelectorAll('.alert-message.error,.alert-message.danger,.cbi-section-error').length,
      frames:d.querySelectorAll('iframe').length,brand:!!brand.brand,robot:!!brand.robot,brandUi:!!brand.brandUi,
      brandScripts:Array.from(d.querySelectorAll('script[data-homensai-style]')).map(n=>n.getAttribute('data-homensai-style')).filter(n=>['brand','robot','brand-ui'].includes(n)),
      resources:resources.slice(-8).map(r=>({name:safeName(r.name),kind:r.initiatorType||'unknown',start:Math.round(r.startTime),duration:Math.round(r.duration),status:Number.isInteger(r.responseStatus)?r.responseStatus:null})),
      navigationStatus:(w.performance.getEntriesByType('navigation')[0]||{}).responseStatus||null,
      resourceCount:resources.length,viewModules:resources.map(r=>safeName(r.name)).filter(n=>/^dashboard[0-9]+\.js$/.test(n)).slice(-2),messages};
  }
  function ready(){const {w,d}=state();if(!w||!d||d.readyState!=='complete')return false;const app=d.querySelector('.hv-app');return !!(app&&d.querySelector('.hv-attribution')&&w.getComputedStyle(app).getPropertyValue('--dv-line').trim());}
  function uiLanguage(d){const select=d&&d.querySelector('.hv-app select[aria-label="Language"],.hv-app select[aria-label="Язык"]');return select&&['en','ru'].includes(select.value)?select.value:null;}
  function termsLanguage(d){
    const headings=Array.from(d.querySelectorAll('.hv-terms-card h1,.hv-terms-card h2')).map(node=>node.textContent||'');
    if(headings.some(text=>text.includes('Экспериментальное ПО: прочитайте, пожалуйста')))return 'ru';
    if(headings.some(text=>text.includes('Experimental software: please read')))return 'en';
    return null;
  }
  function renderedLanguage(d){return CFG.termsOnly?termsLanguage(d):uiLanguage(d);}
  function visible(node,w){if(!node)return false;const rect=node.getBoundingClientRect(),style=w.getComputedStyle(node);return rect.width>0&&rect.height>0&&style.display!=='none'&&style.visibility!=='hidden'&&style.opacity!=='0';}
  async function waitFor(check,ms){const end=Date.now()+ms;while(Date.now()<end){try{if(check())return true;}catch(e){}await sleep(200);}return false;}
  function navigationTarget(lang){
    if(!['en','ru'].includes(lang))throw new Error('ACTUAL-LANGUAGE-INVALID');
    // A repeated URL with a fragment may retain the same Document. Every
    // requested view needs a real navigation before its DOM can be accepted.
    return '/cgi-bin/luci/admin/services/homensai-vpn?lang='+lang+'&hv_lab_nav='+(++navigationSequence)+'#overview';
  }
  async function load(group){
    step='navigation';
    const prior=state();if(prior.w&&prior.d){try{prior.w.localStorage.setItem('homensai-vpn-design',group.design);prior.w.localStorage.setItem('homensai-vpn-language',group.lang);}catch(e){}}
    f.style.width=group.width+'px';f.style.height=group.height+'px';
    f.src=navigationTarget(group.lang);
    let logged=false,phaseAt=0,lastProgress=Date.now(),lastScore='',extended=false,previousDocument=prior.d,restoredLanguage=false;
    const began=Date.now();let deadline=began+90000;
    const inspect=()=>{
      const {d}=state();if(!d)return false;
      // Assigning iframe.src does not replace its document synchronously.
      // An already-ready previous group must never satisfy this navigation.
      if(d===previousDocument)return false;
      installRpcDeadline(state().w,d);
      watch(state().w,d);
      const user=d.querySelector('[name=luci_username]'),password=d.querySelector('[name=luci_password]');
      if(user&&password&&!logged){logged=true;user.value='root';password.value='';user.form.submit();return false;}
      const gate=d.querySelector('.hv-terms');
      if(gate){
        if(CFG.termsOnly){
          if(ready()&&termsLanguage(d)!==group.lang&&!restoredLanguage){restoredLanguage=true;previousDocument=d;f.src=navigationTarget(group.lang);return false;}
          return ready();
        }
        if(consent&&consent.acceptedAfter)throw new Error('ACTUAL-CONSENT-REGRESSED');
        if(!consent){
          bootstrap.push({kind:'consent-before',version:gate.getAttribute('data-terms-gate'),accepted:false});
          consent=acceptTermsGate(gate,CFG.acceptTermsVersion);
          bootstrap.push({kind:'consent-clicked',...consent});
          deadline=Math.min(began+360000,Date.now()+180000);extended=true;
        }
        return false;
      }
      if(CFG.termsOnly&&ready())throw new Error('ACTUAL-TERMS-ALREADY-ACCEPTED');
      if(ready()&&uiLanguage(d)!==group.lang&&!restoredLanguage){
        // Authentication may redirect without the original query. Restore the
        // explicit locale only if the rendered application's control disagrees.
        restoredLanguage=true;previousDocument=d;f.src=navigationTarget(group.lang);
        bootstrap.push({kind:'restore-language-navigation',lang:group.lang});return false;
      }
      return ready();
    };
    let ok=false;
    while(true){
      if(inspect()){ok=true;break;}
      const now=Date.now(),phase=diagnostics();
      const score=JSON.stringify([phase.state,phase.hasL,phase.resourceCount,phase.brandScripts,phase.app]);
      if(score!==lastScore){lastScore=score;lastProgress=now;}
      if(now-phaseAt>=15000){bootstrap.push({kind:'phase',elapsed:now-began,design:group.design,lang:group.lang,width:group.width,...phase});phaseAt=now;}
      if(now>=deadline){
        if(!extended&&phase.accessible&&now-lastProgress<30000&&!phase.login&&!phase.errorCount){
          extended=true;deadline+=90000;bootstrap.push({kind:'progress-extension',elapsed:now-began,additionalMs:90000});
        }else break;
      }
      await sleep(200);
    }
    if(!ok){bootstrap.push({kind:'readiness',elapsed:Date.now()-began,...diagnostics()});throw new Error('ACTUAL-LUCI-READINESS-TIMEOUT');}
    bootstrap.push({kind:'ready',elapsed:Date.now()-began,design:group.design,lang:group.lang,width:group.width,...diagnostics()});
    step='browser-preferences';
    const {w,d}=state();w.localStorage.setItem('homensai-vpn-design',group.design);w.localStorage.setItem('homensai-vpn-language',group.lang);
    const app=d.querySelector('.hv-app');
    if(app.getAttribute('data-hv-design')!==group.design){
      const previous=d;w.location.reload();
      if(!await waitFor(()=>state().d!==previous&&ready(),90000))throw new Error('ACTUAL-DESIGN-RELOAD-TIMEOUT');
    }
    const current=state();watch(current.w,current.d);
    if(renderedLanguage(current.d)!==group.lang)throw new Error('ACTUAL-LANGUAGE-NAVIGATION-MISMATCH');
    step='identity-rpc';
    bootstrap.push({kind:'identity-api',require:typeof current.w.L.require==='function',rpc:!!current.w.L.rpc,declare:!!(current.w.L.rpc&&typeof current.w.L.rpc.declare==='function')});
    let status;
    try{status=await Promise.race([current.w.L.require('rpc').then(rpc=>rpc.declare({object:'homensai-vpn',method:'status',expect:{}})()),sleep(CFG.rpcTimeout===60?65000:45000).then(()=>{throw new Error('ACTUAL-IDENTITY-RPC-TIMEOUT');})]);}
    catch(error){bootstrap.push({kind:'identity-rpc-failed',type:['TypeError','Error','NetworkError','TimeoutError','RPCError'].includes(error.name)?error.name:'other'});throw new Error(error.message==='ACTUAL-IDENTITY-RPC-TIMEOUT'?error.message:'ACTUAL-IDENTITY-RPC-FAILED');}
    step='verify-identity';
    function version(value){return typeof value==='string'&&/^[0-9A-Za-z.+~_-]{1,48}$/.test(value)?value:null;}
    const identity={agent:version(status&&status.version),package:version(status&&status.package)};
    bootstrap.push({kind:'installed-identity',...identity});
    if(CFG.expectedAgent&&identity.agent!==CFG.expectedAgent||CFG.expectedPackage&&identity.package!==CFG.expectedPackage)throw new Error('ACTUAL-INSTALLED-VERSION-MISMATCH');
    if(consent&&!consent.acceptedAfter){
      step='verify-consent';
      const inventory=await Promise.race([current.w.L.require('rpc').then(rpc=>rpc.declare({object:'homensai-vpn',method:'inventory',expect:{}})()),sleep(65000).then(()=>{throw new Error('ACTUAL-CONSENT-VERIFY-TIMEOUT');})]);
      if(!inventory.settings||inventory.settings.terms_version!==consent.version)throw new Error('ACTUAL-CONSENT-NOT-SAVED');
      consent.acceptedAfter=true;consent.verifiedAt=Date.now();bootstrap.push({kind:'consent-verified',...consent});
    }
  }
  try{
    for(const group of CFG.groups){
      await load(group);
      if(CFG.termsOnly){
        step='readonly-terms-view';
        if(!await waitFor(()=>{const node=state().d.querySelector('.hv-terms .hv-attribution-version'),text=node&&node.textContent||'';return (!CFG.expectedAgent||text.includes(CFG.expectedAgent))&&(!CFG.expectedPackage||text.includes(CFG.expectedPackage));},65000))throw new Error('ACTUAL-TERMS-IDENTITY-TIMEOUT');
        const {w,d}=state(),gate=d.querySelector('.hv-terms'),boxes=gate?Array.from(gate.querySelectorAll('.hv-terms-check input[type="checkbox"]')):[],accept=gate&&gate.querySelector('.hv-terms-accept');
        const language=termsLanguage(d),design=gate&&gate.getAttribute('data-hv-design'),attribution=gate&&gate.querySelector('.hv-attribution'),badge=gate&&gate.querySelector('.hv-version'),footer=gate&&gate.querySelector('.hv-brand-footer');
        const targetModelLine=!!(attribution&&attribution.textContent.includes('GL.iNet GL-MT6000')),developer=attribution&&attribution.querySelector('a[href="https://homensai.com"]');
        const attributesVisible=visible(attribution,w)&&visible(badge,w)&&visible(footer,w)&&visible(developer,w);
        const overflow=Math.max(0,d.documentElement.scrollWidth-w.innerWidth),unchanged=boxes.length===2&&boxes.every(box=>box.checked===false)&&accept&&accept.disabled===true;
        rows.push({...group,tab:'terms',language,design,innerWidth:w.innerWidth,innerHeight:w.innerHeight,attribution:visible(attribution,w),badge:visible(badge,w),footer:visible(footer,w),developer:visible(developer,w),targetModelLine,checks:boxes.length,unchecked:boxes.every(box=>box.checked===false),acceptDisabled:!!(accept&&accept.disabled),overflow,
          result:gate&&language===group.lang&&design===group.design&&attributesVisible&&targetModelLine&&unchanged&&w.innerWidth===group.width&&w.innerHeight===group.height&&overflow<=2?'PASS':'FAIL'});
        continue;
      }
      for(const tab of tabs){
        step='tab-'+tab;
        const {w,d}=state();const link=d.querySelector('[data-hv-tab="'+tab+'"]');
        if(!link){rows.push({...group,tab,result:'FAIL',reason:'TAB-MISSING'});continue;}
        link.click();
        const opened=await waitFor(()=>{const page=d.querySelector('[data-hv-page="'+tab+'"]');return page&&!page.hidden&&w.getComputedStyle(page).display!=='none';},5000);
        await sleep(150);
        const app=d.querySelector('.hv-app'),badge=d.querySelector('.hv-app .hv-version'),footer=d.querySelector('.hv-app .hv-brand-footer');
        const overflow=Math.max(0,d.documentElement.scrollWidth-w.innerWidth);
        const author=!!d.querySelector('.hv-attribution'),design=app&&app.getAttribute('data-hv-design');
        const language=uiLanguage(d),startLink=d.querySelector('[data-hv-tab="start"]');
        const languageLabel=!!(startLink&&startLink.textContent.includes(group.lang==='ru'?'Начало работы':'Getting started'));
        rows.push({...group,tab,innerWidth:w.innerWidth,innerHeight:w.innerHeight,language,languageLabel,opened,attribution:author,footer:!!footer,badge:!!badge,design,overflow,
                   result:opened&&author&&footer&&badge&&design===group.design&&language===group.lang&&languageLabel&&w.innerWidth===group.width&&w.innerHeight===group.height&&overflow<=2?'PASS':'FAIL'});
      }
    }
  }catch(e){bootstrap.push({kind:'matrix-error',step,type:['TypeError','ReferenceError','SyntaxError','Error','SecurityError','QuotaExceededError','NetworkError','TimeoutError','AbortError','RPCError'].includes(e.name)?e.name:'other'});errors.push(/^ACTUAL-[A-Z0-9-]+$/.test(e.message)?e.message:'ACTUAL-LUCI-MATRIX-ERROR');}
  await fetch('/__lab/result/'+CFG.id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scope:CFG.termsOnly?'actual isolated x86 read-only unaccepted terms views; no consent or normal-page acceptance':'actual isolated x86 LuCI DOM/CSS; no native hardware acceptance',rows,errors,bootstrap,consent,rpcMetrics,rpcDeadlineSeconds:CFG.rpcTimeout,defaultPerformanceAcceptance:CFG.rpcTimeout===60?'NOT-ACCEPTED-OVERRIDE-IN-USE':'DEFAULT-DEADLINE',expected:CFG.groups.length*(CFG.termsOnly?1:tabs.length)})});
})();
