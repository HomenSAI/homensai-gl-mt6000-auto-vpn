(async function(){
  var res={cfg:CFG,steps:[],fail:[]};
  function ok(name,cond,info){res.steps.push((cond?'PASS ':'FAIL ')+name+(info?' '+info:''));if(!cond)res.fail.push(name+(info?' '+info:''));}
  var sleep=function(ms){return new Promise(function(r){setTimeout(r,ms);});};
  var f=document.getElementById('f');
  try{localStorage.setItem('homensai-vpn-design',CFG.design);localStorage.setItem('homensai-vpn-theme','light');}catch(e){}
  function load(hash){return new Promise(function(resolve){f.onload=function(){resolve();};f.src='/?lang=en#'+(hash||'overview');if(f.contentWindow&&f.contentWindow.location.pathname==='/'){try{f.contentWindow.location.reload();}catch(e){}}});}
  function W(){return f.contentWindow;}function D(){return f.contentDocument;}
  function root(){return D().querySelector('.hv-app');}
  function visiblePage(){var p=D().querySelector('[data-hv-page]:not([hidden])');return p?p.getAttribute('data-hv-page'):null;}
  try{
    await load('overview');await sleep(5000);
    ok('app renders',!!root());
    ok('design from storage',root().getAttribute('data-hv-design')===CFG.design,root().getAttribute('data-hv-design'));
    ok('overview built by design view',!!D().querySelector('[data-hv-page="overview"][data-hv-dv] .hv-dv-'+CFG.design));
    ok('real Auto power button inside the design view',!!D().querySelector('.hv-dv .hv-auto-power'));
    ok('attribution present',!!D().querySelector('.hv-attribution'));
    // S2 navigation: every section link opens its page
    var adv=D().querySelector('.hv-advanced-toggle');if(adv&&D().querySelector('.hv-advanced-links[hidden]'))adv.click();
    var links=Array.prototype.slice.call(D().querySelectorAll('[data-hv-tab]'));
    ok('section links found',links.length>=11,String(links.length));
    var tabKeys=links.map(function(l){return l.getAttribute('data-hv-tab');});ok('Getting started is the first section',tabKeys[0]==='start',tabKeys.join(','));ok('no separate Server ranking section',tabKeys.indexOf('ranking')<0);
    for(var i=0;i<links.length;i++){
      var key=links[i].getAttribute('data-hv-tab'),cs=W().getComputedStyle(links[i]);
      if(cs.display==='none'){res.steps.push('SKIP link '+key+' (hidden in this design)');continue;}
      links[i].click();await sleep(400);
      ok('open '+key,visiblePage()===key&&W().location.hash==='#'+key&&links[i].getAttribute('aria-current')==='page',visiblePage()+' '+W().location.hash);
    }
    // S3 keys (design C only)
    await load('overview');await sleep(3000);
    var ev=new (W().KeyboardEvent)('keydown',{key:'3',bubbles:true});D().dispatchEvent(ev);await sleep(400);
    if(CFG.design==='c')ok('key 3 opens the 3rd section (Channels)',visiblePage()==='channels',visiblePage());
    else ok('key 3 does nothing outside design C',visiblePage()==='overview',visiblePage());
    // S1 picker: choose every design in Settings, check apply + storage + overview view + survives reload
    await load('settings');await sleep(3500);
    var radios=D().querySelectorAll('input[name="hv-design"]');ok('picker has 3 radios',radios.length===3);
    ok('picker preselects the stored design',D().querySelector('#hv-design-'+CFG.design).checked);
    for(var d of ['b','c','a']){
      var r=D().querySelector('#hv-design-'+d);r.checked=true;r.dispatchEvent(new (W().Event)('change',{bubbles:true}));await sleep(600);
      ok('pick '+d+' applies at once',root().getAttribute('data-hv-design')===d);
      ok('pick '+d+' stored',localStorage.getItem('homensai-vpn-design')===d,String(localStorage.getItem('homensai-vpn-design')));
      ok('pick '+d+' note shown',/is on/.test((D().querySelector('.hv-design-note')||{}).textContent||''));
      W().location.hash='#overview';await sleep(500);
      ok('pick '+d+' redraws the overview in that design',!!D().querySelector('[data-hv-page="overview"] .hv-dv-'+d),'');
    }
    await load('settings');await sleep(3500);
    ok('after reload the last pick (a) is still active',root().getAttribute('data-hv-design')==='a');
    // Failure scenario on the fixture: normal -> primary fails (reserve carries traffic) -> primary recovered (back on the primary).
    function press(text){var b=Array.prototype.slice.call(D().querySelectorAll('#fixture-banner button')).filter(function(x){return x.textContent.indexOf(text)>=0;})[0];if(b)b.click();return !!b;}
    function node(key){var n=D().querySelector('[data-path-node="'+key+'"]');return n?n.getAttribute('data-node-tone'):null;}
    W().location.hash='#overview';await sleep(600);
    if(press('Scenario: normal')){await sleep(1500);
      ok('normal: primary green, reserve red',node('source')==='green'&&node('target')==='red',node('source')+'/'+node('target'));
      ok('normal: round Auto button is green',!!D().querySelector('.hv-auto-power.hv-auto-lit-on'));
      ok('normal: no Return button',!Array.prototype.slice.call(D().querySelectorAll('button')).some(function(x){return /Вернуться на основной|Return to primary/.test(x.textContent);}));
    }else ok('fixture scenario buttons exist',false);
    if(press('Scenario: primary fails')){await sleep(1500);
      ok('failure: primary red, reserve green',node('source')==='red'&&node('target')==='green',node('source')+'/'+node('target'));
      ok('failure: Return to primary is offered',Array.prototype.slice.call(D().querySelectorAll('button')).some(function(x){return /Вернуться на основной|Return to primary/.test(x.textContent);}));
      ok('failure: the overview names the reserve',/reserve|резерв/i.test((D().querySelector('.hv-dv-strip,.hv-dv-stack,.hv-dv-a,.hv-dv-b,.hv-dv-c')||{}).textContent||''));
    }
    if(press('Scenario: primary recovered')){await sleep(1500);
      ok('recovered: primary green again',node('source')==='green',node('source'));
      ok('recovered: Return button is gone',!Array.prototype.slice.call(D().querySelectorAll('button')).some(function(x){return /Вернуться на основной|Return to primary/.test(x.textContent);}));
    }
  }catch(e){ok('scenario ran to the end',false,String(e&&e.message||e));}
  fetch('/__result/'+CFG.id,{method:'POST',body:JSON.stringify(res)});
})();
