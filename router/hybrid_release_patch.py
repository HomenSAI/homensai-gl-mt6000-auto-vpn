"""Owner-selected legacy expanded shell with the current always-available Minimum."""
from pathlib import Path


def apply(source):
    def replace(old,new):
        nonlocal source
        assert source.count(old)==1,'HYBRID-ANCHOR '+old[:90]
        source=source.replace(old,new,1)
    gate="    if(!inventory.error&&!onboardingComplete(inventory)&&!simpleHomeAutoEnabled(data[1],statusNow(data[1]))&&languageViewContext(window.location.href)!=='full'&&!onboardingEntryDeferred())return renderOnboardingGate(inventory,data[1]);"
    replace(gate,'    // Minimum remains accessible; terms and backend Start checks still apply.')
    replace('    var homeShortcut=null;',"""    var homeShortcut=null,hybridControls=null,hybridRenderedState='',hybridUiState='';
    function hybridPage(key){
      var aliases={'diagnostics':'tests','diagnostics/checks':'tests','diagnostics/speed':'tests','diagnostics/recovery':'overview','diagnostics/technical':'services','diagnostics/readiness':'readiness','events/journal':'events','events/statistics':'statistics','events/traffic':'traffic','settings/main':'settings','settings/setup':'settings','help/topics':'help','help/training':'learn','help/about':'help'};
      if(typeof key==='string'&&key.indexOf('help/topic/')===0)return 'help';
      return Object.prototype.hasOwnProperty.call(aliases,key)?aliases[key]:key;
    }
    function placeHybridControls(page){
      if(appRoot)appRoot.setAttribute('data-hv-design',page==='home'?'b':currentDesign());
      if(!hybridControls)return;
      ['power','action'].forEach(function(key){
        var item=hybridControls[key];if(!item||!item.node)return;
        var target=page==='home'?item.home:item.parent;
        if(target&&item.node.parentNode!==target){
          if(page!=='home'&&item.next&&item.next.parentNode===target)target.insertBefore(item.node,item.next);
          else target.appendChild(item.node);
        }
      });
    }
""")
    replace("if(setup||validTab(requestedTab)&&['overview','home'].indexOf(requestedTab)<0)homeMenuRequested=true;", "if(setup||validTab(requestedTab)&&requestedTab!=='home')homeMenuRequested=true;")
    replace('    var requestedTab=window.location.hash.slice(1);','    var requestedTab=hybridPage(window.location.hash.slice(1));')
    replace('    function showPage(key){','    function showPage(key){\n      key=hybridPage(key);placeHybridControls(key);')
    replace("put('home',renderSimpleHome(status,inventory,homeModel,homeControl,openHomeMenu));", """var power=homeControl&&homeControl.querySelector('.hv-auto-power'),action=homeControl&&homeControl.querySelector('.hv-auto-action');
        var powerParent=power&&power.parentNode,powerNext=power&&document.createComment('Auto power position'),actionParent=action&&action.parentNode,actionNext=action&&document.createComment('Auto action position');
        if(powerParent)powerParent.insertBefore(powerNext,power);if(actionParent)actionParent.insertBefore(actionNext,action);
        var homeView=renderSimpleHome(status,inventory,homeModel,homeControl,openHomeMenu);
        put('home',homeView);
        hybridControls={power:{node:power,parent:powerParent,next:powerNext,home:homeView.querySelector('.hv-simple-power')},action:{node:action,parent:actionParent,next:actionNext,home:homeView.querySelector('.hv-simple-power-unit')}};
        hybridRenderedState=JSON.stringify([homeModel.state,homeModel.title,homeModel.summary,homeModel.selectedRole,homeModel.targetHealth.state]);""")
    replace("if(activeTab==='home'&&!simpleHomeModel(homeLatest,inventory,statusNow(homeLatest)).showCard)showPage(startLanding(homeLatest,inventory));", "var key=uiStateSignature(homeLatest,inventory,statusNow(homeLatest));if(key!==hybridUiState)draw(homeLatest);")
    replace('      var homeFreshTimer=window.setInterval(function(){', "      UI_OPERATION_REFRESH=function(){if(homeLatest&&appRoot&&appRoot.isConnected)draw(homeLatest);};\n      var homeFreshTimer=window.setInterval(function(){")
    replace("'class':'hv-app hv-workspace','data-hv-design':currentDesign()", "'class':'hv-app hv-workspace hv-hybrid-release','data-hv-design':currentDesign()")
    replace("E('nav',{'tabindex':'0','aria-label':bi('VPN sections','Разделы VPN')},links)","E('nav',{'id':'hv-expanded-nav','aria-label':bi('VPN sections','Разделы VPN')},links)")
    replace("var statusCall=rpc.declare({object:'homensai-vpn',reject:true,method:'status',expect:{}});", "var statusRpc=rpc.declare({object:'homensai-vpn',reject:true,method:'status',expect:{}});\nvar statusCall=function(){return uiStatusRequest(statusRpc);};")
    # A page error is not "the router does not answer": render failures get their own code, and during a real
    # outage the page clock keeps running, so old measurements turn grey instead of looking fresh.
    # A hidden browser tab does not ask the router for status every 10 seconds; it refreshes at once when shown again.
    replace("poll.add(function(){return statusCall().then(draw).catch(function(){draw(Object.assign({},lastGoodStatus,{rpc_error:'RPC-UNAVAILABLE'}));});},10);",
            """var hvStatusInFlight=null,hvStatusEpoch=0;
    var hvStatusTick=function(){if(typeof document!=='undefined'&&document.hidden)return Promise.resolve();
      if(hvStatusInFlight)return hvStatusInFlight;
      var epoch=++hvStatusEpoch,resolveDone,timer,request,requestOrder,done=new Promise(function(resolve){resolveDone=resolve;});hvStatusInFlight=done;
      function finish(fresh,failed){
        if(epoch!==hvStatusEpoch)return;
        hvStatusEpoch++;if(timer)clearTimeout(timer);hvStatusInFlight=null;
        try{draw(failed?uiStatusFailure(lastGoodStatus,requestOrder):fresh);}catch(error){uiRenderFailed(error);}
        resolveDone();
      }
      timer=setTimeout(function(){finish(null,true);},30000);
      try{request=statusCall();requestOrder=uiStatusOrder(request);Promise.resolve(request).then(function(fresh){finish(fresh,false);},function(){finish(null,true);});}catch(error){finish(null,true);}
      return done;
    };UI_STATUS_REFRESH=hvStatusTick;poll.add(hvStatusTick,10);if(typeof document!=='undefined'&&typeof document.addEventListener==='function')document.addEventListener('visibilitychange',function(){if(!document.hidden)hvStatusTick();});""")
    # Keyboard focus survives the refresh on links and summaries too (PAGE_FOCUS_SELECTOR in viewport_state).
    replace("document.activeElement.matches('button,input[type=checkbox],input[type=range],select')","document.activeElement.matches(PAGE_FOCUS_SELECTOR)")
    # The owner asked for the channel failure test on the Tests page again (27 Oct 2026).
    # "Go back" at the bottom of every page returns to the previous page and its scroll position.
    replace("      key=hybridPage(key);placeHybridControls(key);","      key=hybridPage(key);placeHybridControls(key);\n      if(activeTab&&key!==activeTab)pageBackRemember(activeTab,window.pageYOffset||0);")
    replace("      if(appRoot)updateSidebarLayout(appRoot,oldTab!==key);","      if(appRoot)updateSidebarLayout(appRoot,oldTab!==key);\n      pageBackPlace(appRoot||panel,key);attachStatsResets(appRoot||panel);\n      if(key==='overview'&&oldTab!=='overview'&&!PAGE_BACK_GOING)setTimeout(overviewToAuto,80);")
    # Keep the established shipped-size budget without changing JavaScript semantics.
    # These reviewed, whole developer comments remain in the source modules; legal and owner attribution stay shipped.
    for module in ['fool_guard', 'setup_guides', 'monitor_panel', 'country_panel', 'vendor_diagnostics', 'onboarding_panel', 'identity_panel', 'design_panel', 'design_views', 'latency_chart', 'speed_table', 'traffic_chart', 'live_log', 'simple_home_policy']:
        header=(Path(__file__).parent/(module+'.inc.js')).read_text(encoding='utf8')
        assert header.startswith('/*'),'HYBRID-COMMENT-HEADER '+module
        header=header[:header.index('*/')+2]
        assert not any(word in header.lower() for word in ('copyright','license','©')),'HYBRID-COMMENT-LEGAL '+module
        replace(header,'')
    for comment in ['// Text limits that match the backend (names and channel groups 1-64 characters; chat id; bot token).', '// Check one raw value of a number field. Returns {ok, value, message}; message is plain words (bilingual), never a code.', '// Disable or enable a Save/Next button from a list of checks (every check also paints its own red message).', '// A readiness check is expensive on a router. Share one pending request and reuse its result for ten seconds.', '// Every reason why the failure test cannot start, in plain words, each with the place to fix it (mirrors the router-side checks).', '// Router time as the browser sees it; a PC clock a few seconds off must not turn fresh data into "waiting".', '// The latest router check of a channel in words. A failed check is a result too: it shows what failed and when.', '// What each note on a server means, in plain words. These are descriptions, not errors; real error codes are shown as links.', '// Top of the System readiness page: what it is, that nothing needs to be pressed, how to read the colours.', '// Settings > Automatic switching: why the LAN helper exists, how to get it, where the full guide and the AI prompt are.', '// The forecast panel lists checks that this router has not been certified for yet. Each code gets a plain explanation.', '// Failure codes of the controller that prove a planning check has FAILED (not only that it is still unproven).', '// verified = the code is no longer listed as unproven; failed = a related failure code is reported; otherwise still empty.', '// Jump to the row of a code in the error table on the Events page, open its "how to fix" and highlight it.', '// Page and router program differ (old cached page or unfinished upgrade): a quiet link to the Help topic that explains it.', '// Checks per server: recent samples first, replaced by the hourly aggregates when the router kept them (same rule as the ranking table).', '// Keys of design C: 1..9 open the sections, "/" focuses the search box. Ignored while typing and with modifier keys.', '// The recommendation is computed from the loss statistics of the saved pair and of the measured profiles.']:
        replace(comment+'\n','')
    return source
