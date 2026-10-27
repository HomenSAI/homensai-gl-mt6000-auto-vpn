"""Owner-selected legacy expanded shell with the current always-available Minimum."""
from pathlib import Path


def apply(source):
    def replace(old,new):
        nonlocal source
        assert source.count(old)==1,'HYBRID-ANCHOR '+old[:90]
        source=source.replace(old,new,1)
    gate="    if(!inventory.error&&!onboardingComplete(inventory)&&!simpleHomeAutoEnabled(data[1],statusNow(data[1]))&&languageViewContext(window.location.href)!=='full'&&!onboardingEntryDeferred())return renderOnboardingGate(inventory,data[1]);"
    replace(gate,'    // Minimum remains accessible; terms and backend Start checks still apply.')
    replace('    var homeShortcut=null;',"""    var homeShortcut=null,hybridControls=null,hybridRenderedState='';
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
    replace("if(activeTab==='home'&&!simpleHomeModel(homeLatest,inventory,statusNow(homeLatest)).showCard)showPage(startLanding(homeLatest,inventory));", "if(activeTab==='home'){var timed=simpleHomeModel(homeLatest,inventory,statusNow(homeLatest));var key=JSON.stringify([timed.state,timed.title,timed.summary,timed.selectedRole,timed.targetHealth.state]);if(key!==hybridRenderedState)draw(homeLatest);}")
    replace("'class':'hv-app hv-workspace','data-hv-design':currentDesign()", "'class':'hv-app hv-workspace hv-hybrid-release','data-hv-design':currentDesign()")
    replace("E('nav',{'tabindex':'0','aria-label':bi('VPN sections','Разделы VPN')},links)","E('nav',{'id':'hv-expanded-nav','aria-label':bi('VPN sections','Разделы VPN')},links)")
    # The owner asked for the channel failure test on the Tests page again (27 Oct 2026).
    # "Go back" at the bottom of every page returns to the previous page and its scroll position.
    replace("      key=hybridPage(key);placeHybridControls(key);","      key=hybridPage(key);placeHybridControls(key);\n      if(activeTab&&key!==activeTab)pageBackRemember(activeTab,window.pageYOffset||0);")
    replace("      if(appRoot)updateSidebarLayout(appRoot,oldTab!==key);","      if(appRoot)updateSidebarLayout(appRoot,oldTab!==key);\n      pageBackPlace(appRoot||panel,key);attachStatsResets(appRoot||panel);")
    return source
