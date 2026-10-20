(async function(){
  const frame=document.getElementById('f'),rows=[],errors=[];
  const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
  const deadline=async(fn,label,seconds=15)=>{const until=Date.now()+seconds*1000;while(Date.now()<until){const value=fn();if(value)return value;await sleep(100);}throw Error(label);};
  function doc(){return frame.contentDocument;}
  function root(){return doc()&&doc().querySelector('[data-hv-onboarding="1"]');}
  function control(key){return root()&&root().querySelector('[data-onboarding-field="'+key+'"]');}
  function action(key){return (root()||doc()).querySelector('[data-onboarding-action="'+key+'"]');}
  function click(key){const node=action(key);if(!node||node.disabled)throw Error('ACTION-UNAVAILABLE-'+key);if(root()&&widthOverflow()>0)throw Error('OVERFLOW-'+root().getAttribute('data-step'));node.click();}
  function fill(key,value){const node=control(key);if(!node)throw Error('FIELD-MISSING-'+key);if(node.type==='checkbox')node.checked=!!value;else node.value=String(value);node.dispatchEvent(new frame.contentWindow.Event('input',{bubbles:true}));node.dispatchEvent(new frame.contentWindow.Event('change',{bubbles:true}));return node;}
  function widthOverflow(){return Math.max(0,doc().documentElement.scrollWidth-frame.contentWindow.innerWidth);}
  async function load(group,params){
    const priorDocument=doc();
    const query=new URLSearchParams(Object.assign({lang:group.lang,onboarding:'first',case:group.id,fixtureBackend:CFG.id},params));
    frame.src='/?'+query+'&navigation='+Math.random().toString(16).slice(2)+'#settings';
    await deadline(()=>doc()&&doc()!==priorDocument&&doc().readyState==='complete'&&doc().querySelector('.hv-app'),'APP-READINESS',20);
    await sleep(300);
  }
  for(let i=0;i<CFG.groups.length;i++){
    const group=Object.assign({id:String(i)},CFG.groups[i]),checks=[];
    function check(label,value){checks.push({label,pass:!!value});if(!value)throw Error(label);}
    try{
      frame.style.width=group.width+'px';frame.style.height='840px';
      localStorage.clear();localStorage.setItem('homensai-vpn-design',group.design);
      localStorage.setItem('homensai-vpn-theme','light');
      await load(group,{profiles:i===CFG.groups.length-1?'none':'all'});
      await deadline(()=>root()&&root().getAttribute('data-step')==='appearance','FIRST-RUN-AUTO');
      check('first run opens automatically',!!root());
      check('identity and footer present',!!doc().querySelector('.hv-attribution')&&!!doc().querySelector('.hv-brand-footer')&&!!doc().querySelector('.hv-version'));
      const escape=action('open-dashboard'),escapeUrl=escape&&new URL(escape.href);
      check('explicit recovery escape is same origin and leaves setup incomplete',escapeUrl&&escapeUrl.origin===location.origin&&escapeUrl.searchParams.get('onboarding')==='defer'&&escapeUrl.hash==='#overview'&&escape.target==='_blank');
      check('escape is offered without writing completion',!frame.contentWindow.fixtureCalls.some(c=>c.method==='setup_onboarding'));
      await load(group,{onboarding:'defer',profiles:i===CFG.groups.length-1?'none':'all'});
      check('recovery dashboard opens while setup remains incomplete',!root()&&!!doc().querySelector('[data-onboarding-incomplete="1"]'));
      check('one-entry escape is consumed without a save',!new URL(frame.contentWindow.location.href).searchParams.has('onboarding')&&!frame.contentWindow.fixtureCalls.some(c=>c.method==='setup_onboarding'));
      const deferredDocument=doc();frame.contentWindow.location.reload();
      await deadline(()=>doc()!==deferredDocument&&doc().readyState==='complete'&&root(),'INCOMPLETE-RELOAD-REOPENS',20);
      check('fresh entry still opens incomplete setup',root().getAttribute('data-step')==='appearance');
      click('cancel');check('cancel pauses without saving',root().getAttribute('data-step')==='paused'&&!frame.contentWindow.fixtureCalls.some(c=>c.method==='setup_onboarding'));
      click('resume');check('resume restores first step',root().getAttribute('data-step')==='appearance');
      fill('appearance.language',group.lang);fill('appearance.design',group.design);fill('appearance.theme','light');
      click('next');await deadline(()=>root().getAttribute('data-step')==='monitor','MONITOR-STEP');
      fill('monitor.interval',0);check('invalid interval prevents navigation',action('next').disabled);
      fill('monitor.interval',47);check('corrected interval unlocks navigation',!action('next').disabled);
      click('back');check('back preserves appearance',control('appearance.design').value===group.design);
      click('next');check('back preserves monitoring draft',control('monitor.interval').value==='47');
      click('next');await deadline(()=>root().getAttribute('data-step')==='system','SYSTEM-STEP');
      if(i===CFG.groups.length-1)fill('system.defer_pair',true);
      click('next');await deadline(()=>root().getAttribute('data-step')==='servers','SERVERS-STEP');
      if(control('servers.0.name'))fill('servers.0.name','Operator example');
      click('next');await deadline(()=>root().getAttribute('data-step')==='recovery','RECOVERY-STEP');
      click('next');await deadline(()=>root().getAttribute('data-step')==='speed','SPEED-STEP');
      check('speed limits available',!!control('speed.budget_mib')&&!!control('speed.daily_mib'));
      click('next');await deadline(()=>root().getAttribute('data-step')==='telegram','TELEGRAM-STEP');
      check('optional Telegram may remain unconfigured',!!control('telegram.configure'));
      click('next');await deadline(()=>root().getAttribute('data-step')==='review','REVIEW-STEP');
      check('review fits viewport',widthOverflow()===0);
      check('review contains edited interval',root().textContent.includes('47'));
      check('first-run flow has no app errors',!(frame.contentWindow.fixtureErrors||[]).length);
      check('wizard never automatically controls Auto or accepts terms',!frame.contentWindow.fixtureCalls.some(c=>/^native_|^terms_accept$/.test(c.method)));
      frame.contentWindow.fixtureOnboardingSaveMode='pending';
      click('save');await sleep(200);
      check('pending save blocks duplicate and back',action('save').disabled&&action('back').disabled);
      action('save').click();action('back').click();await sleep(100);
      check('one aggregate write despite repeated clicks',frame.contentWindow.fixtureCalls.filter(c=>c.method==='setup_onboarding').length===1);
      check('emergency Stop remains available during Save',!!action('emergency-stop')&&!action('emergency-stop').disabled);
      click('emergency-stop');await sleep(100);
      const stops=frame.contentWindow.fixtureCalls.filter(c=>c.method==='native_stop');
      check('explicit emergency Stop sends one independent no-argument RPC',stops.length===1&&stops[0].args.length===0);
      frame.contentWindow.fixturePending.reject(Error('SYNTHETIC-PRIVATE-DETAIL'));
      await deadline(()=>action('save')&&!action('save').disabled,'RETRY-UNLOCK');
      check('failed save keeps review draft',root().getAttribute('data-step')==='review'&&root().textContent.includes('47'));
      check('private failure is not displayed',!doc().body.textContent.includes('SYNTHETIC-PRIVATE-DETAIL'));
      const priorSavedDocument=doc();
      frame.contentWindow.fixtureOnboardingSaveMode='success';click('save');
      await deadline(()=>doc()!==priorSavedDocument&&doc().readyState==='complete'&&doc().querySelector('.hv-app')&&!root(),'SAVE-RELOAD',20);
      localStorage.clear();
      await load(group,{profiles:i===CFG.groups.length-1?'none':'all'});
      await sleep(400);
      check('router marker survives cleared browser storage',!root());
      const opener=doc().querySelector('[data-onboarding-action="open"]');check('Settings can edit completed setup',!!opener);opener.click();
      await deadline(()=>root()&&root().getAttribute('data-step')==='appearance','SETTINGS-REOPEN');
      click('next');check('Settings loads saved values',control('monitor.interval').value==='47');
      check('no automatic Start or terms acceptance',!frame.contentWindow.fixtureCalls.some(c=>/^native_start$|^native_return$|^terms_accept$/.test(c.method)));
      check('no app errors',!(frame.contentWindow.fixtureErrors||[]).length);
      rows.push(Object.assign({},group,{result:'PASS',checks}));
    }catch(error){rows.push(Object.assign({},group,{result:'FAIL',reason:String(error.message||error),step:root()&&root().getAttribute('data-step'),checks}));}
  }
  await fetch('/__onboarding/result/'+CFG.id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rows,errors,scope:'synthetic UI + RAM fixture persistence; no real router'})});
})().catch(async function(error){await fetch('/__onboarding/result/'+CFG.id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({errors:['HARNESS-'+String(error.message||error)],rows:[]})});});
