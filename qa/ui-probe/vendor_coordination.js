(async function(){
  const frame=document.getElementById('f'),rows=[];
  const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
  async function until(fn,label){const deadline=Date.now()+20000;while(Date.now()<deadline){const value=fn();if(value)return value;await sleep(75);}throw Error(label);}
  function doc(){return frame.contentDocument;}
  function overflow(){return Math.max(0,doc().documentElement.scrollWidth-frame.contentWindow.innerWidth);}
  async function page(name){frame.contentWindow.location.hash=name;await until(()=>doc().querySelector('[data-hv-page="'+name+'"]:not([hidden])'),'PAGE-'+name);await sleep(75);}
  for(const group of CFG.groups){
    frame.style.width=group.width+'px';frame.style.height='840px';
    localStorage.clear();localStorage.setItem('homensai-vpn-design',group.design);localStorage.setItem('homensai-vpn-theme','light');
    for(const scene of CFG.scenes){
      const checks=[];
      function check(label,value){checks.push({label,pass:!!value});if(!value)throw Error(label);}
      try{
        const previous=doc();frame.src='/?vendor='+scene+'&lang='+group.lang+'&nav='+Math.random().toString(16).slice(2)+'#overview';
        await until(()=>doc()&&doc()!==previous&&doc().readyState==='complete'&&doc().querySelector('[data-vendor-diagnostics="overview"]'),'READY');await sleep(250);
        check('requested design is rendered',doc().querySelector('.hv-app').getAttribute('data-hv-design')===group.design);
        check('owner attribution badge and footer present',!!doc().querySelector('.hv-attribution')&&!!doc().querySelector('.hv-version')&&!!doc().querySelector('.hv-brand-footer'));
        check('overview fits viewport',overflow()===0);
        await page('channels');
        const details=doc().querySelector('[data-vendor-diagnostics="channels"]');check('tunnel diagnostics exist',!!details);details.open=true;await sleep(100);
        const source=details.querySelector('[data-vendor-tunnel="openvpn:vpna"]');check('observed source tunnel is shown',!!source);
        const expected={stable:'stable',pending:'pending',changed:'pending',unknown:'unknown',stale:'unknown',wan:'stable','same-tunnel':'stable'}[scene];
        check('configured-identity state matches evidence',source.getAttribute('data-vendor-state')===expected);
        if(scene==='stale'||scene==='unknown'||scene==='pending'||scene==='changed')check('uncertain identity is never healthy',source.getAttribute('data-vendor-health')==='unknown');
        if(scene==='stable')check('stable exact profile probes may be healthy',source.getAttribute('data-vendor-health')==='healthy');
        if(scene==='changed')check('replacement configured profile is shown',source.textContent.includes('a2')&&!/Current[^:]*:\s*a\s/.test(source.textContent));
        check('vendor cause remains unobserved',!!source.querySelector('[data-vendor-reason="unobserved"]'));
        check('channels expanded geometry fits',overflow()===0);
        const codes=Array.from(details.querySelectorAll('[data-app-coordination]')).map(node=>node.getAttribute('data-app-coordination'));
        const code={stable:'CROSS-TUNNEL-READY',pending:'VENDOR-SETTLING',changed:'VENDOR-SETTLING',unknown:'VENDOR-IDENTITY-UNKNOWN',stale:'UNKNOWN',wan:'UPLINK-LINK-DOWN','same-tunnel':'VENDOR-SAME-TUNNEL'}[scene];
        check('planning reason is advisory and current',codes.includes(code));
        await page('events');const events=doc().querySelector('[data-vendor-diagnostics="events"]');check('bounded identity events section exists',!!events);events.open=true;await sleep(75);
        check('at most eight retained observations rendered',events.querySelectorAll('[data-vendor-event]').length<=8);
        if(scene==='changed')check('configured profile change event visible',!!events.querySelector('[data-vendor-event="VENDOR-PROFILE-CHANGED"]'));
        check('events expanded geometry fits',overflow()===0);
        check('read-only navigation makes no write RPC',!frame.contentWindow.fixtureCalls.some(call=>!['inventory','status','events','priority_preview','setup_check'].includes(call.method)));
        check('no app errors',!(frame.contentWindow.fixtureErrors||[]).length);
        rows.push(Object.assign({},group,{scene,result:'PASS',checks}));
      }catch(error){rows.push(Object.assign({},group,{scene,result:'FAIL',reason:String(error.message||error),checks}));}
    }
  }
  await fetch('/__onboarding/result/'+CFG.id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rows,errors:[],scope:'synthetic diagnostics only; no vendor worker, router, LAN or switch'})});
})().catch(async function(error){await fetch('/__onboarding/result/'+CFG.id,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({rows:[],errors:['HARNESS-'+String(error.message||error)]})});});
