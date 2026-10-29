"""Build per-page factories from the reviewed hybrid draw; hidden factories never run."""
import re


def replace_fragment(fragment,old,new,expected=1):
    count=fragment.count(old)
    if count!=expected:raise ValueError('VISIBLE-FRAGMENT-COUNT: expected %s, got %s: %s'%(expected,count,old[:100]))
    return fragment.replace(old,new)


def apply(source):
    def replace(old,new):
        nonlocal source
        assert source.count(old)==1,'VISIBLE-ANCHOR '+old[:100]
        source=source.replace(old,new,1)

    assert source.count('    function draw(status){')==1,'VISIBLE-DRAW-COUNT'
    assert source.count('\n    draw(data[1]);')==1,'VISIBLE-INITIAL-DRAW-COUNT'
    begin=source.index('    function draw(status){')
    end=source.index('\n    draw(data[1]);',begin)
    original=source[begin:end]

    def section(start,stop):
        assert original.count(start)==1,'VISIBLE-START '+start
        assert original.count(stop)==1,'VISIBLE-END '+stop
        a=original.index(start);b=original.index(stop,a)
        return original[a:b]

    def puts(fragment):
        """Take balanced put(...) calls; their arguments remain inside the page factory."""
        found=[]
        for match in re.finditer(r"put\('([a-z]+)',",fragment):
            index=match.start();cursor=fragment.index('(',index);depth=0;quote=None;escaped=False
            while cursor<len(fragment):
                char=fragment[cursor]
                if quote:
                    if escaped:escaped=False
                    elif char=='\\':escaped=True
                    elif char==quote:quote=None
                elif char in "'\"`":quote=char
                elif char=='(':depth+=1
                elif char==')':
                    depth-=1
                    if depth==0:
                        assert fragment[cursor+1]==';','VISIBLE-PUT-TERMINATOR'
                        found.append((match.group(1),fragment[index:cursor+2]));break
                cursor+=1
            else:raise AssertionError('VISIBLE-PUT-BALANCE')
        return found

    overview=section("if(status.rpc_error)put('overview'",'      var rows=status.profiles')
    common=section('      var rows=status.profiles',"      put('overview',E('div',{'class':'hv-metrics'}")
    overview+=section("      put('overview',E('div',{'class':'hv-metrics'}","      put('channels',vpnSetupCard())")
    channels=section("      put('channels',vpnSetupCard())","      put('statistics',E('section'")
    statistics=section("      put('statistics',E('section'",'      var fp=status.failover_plan')
    common+=section('      var ns=status.native_failover','      var controlCard=renderAutoControl')
    # This line previously mixed six pages. Extracting each complete call keeps the
    # lazy Help/Training API independent from this refresh optimization.
    control=section('      var controlCard=renderAutoControl','      var stateNames=')
    mixed=puts(control)
    other={}
    for key,call in mixed:
        other.setdefault(key,[]).append(call)
        control=replace_fragment(control,call,'')
    assert control.count('pages.overview.insertBefore')==5,'VISIBLE-OVERVIEW-PLACEMENT-COUNT'
    placement=control.index('pages.overview.insertBefore')
    auto=control[:placement]
    overview+='\n'+''.join(other.pop('overview'))+'\n'+control[placement:]
    common+=section('      var stateNames=','      var stale=')
    shared=section('      if(versionBadge)','      var descriptions=')
    settings=section('      var nativePanel=','      var nh=status.native_history')
    history=section('      var nh=status.native_history','      var table=E(')
    events='\n'.join(call for key,call in puts(history) if key=='events')
    channels+=section('      var table=E(','      var samples=')
    ranking=section('      var samples=','      var accounting=status.accounting')
    # Ranking has no menu destination in the hybrid page; render it directly on Tests.
    ranking=replace_fragment(ranking,"'ranking'","'tests'",expected=4)
    traffic=section('      var accounting=status.accounting',"      put('services',E('h3'")
    services=section("      put('services',E('h3'","      put('events',E('button'")
    events+=section("      put('events',E('button'","      put('ranking',speedPanel")
    speed=section("      put('ranking',speedPanel","      put('traffic',trafficHistoryPanel")
    speed=replace_fragment(speed,"put('ranking',","put('tests',")
    traffic+=section("      put('traffic',trafficHistoryPanel","      put('tests',faultPanel")
    tests=section("      put('tests',faultPanel",'      restorePageControlFocus')
    move="if(pages.ranking){while(pages.ranking.firstChild)pages.tests.appendChild(pages.ranking.firstChild);}"
    tests=replace_fragment(tests,move,ranking+'\n'+speed)
    warning=section('      if(inventory.error)',"      put('statistics',renderMonitorInfo")
    overview+=warning
    tail=section("      put('statistics',renderMonitorInfo",'      var homeModel=simpleHomeModel')
    for key,call in puts(tail):
        if key=='statistics':statistics+=call+'\n'
        elif key=='events':events+=call+'\n'
        else:raise AssertionError('VISIBLE-TAIL-PAGE '+key)
    home=section('      if(homeModel.showCard){','      installErrorLinks(appRoot);')
    return_button=next(line for line in home.splitlines() if "pages.overview.insertBefore(E('button'" in line)
    home=replace_fragment(home,return_button,'')
    overview+='\nif(homeModel.showCard){'+return_button+'}\n'
    reroute="        if(!setup&&!homeMenuRequested&&['start','overview','home'].indexOf(activeTab)>=0)activeTab='home';"
    home=replace_fragment(home,reroute,'')
    assert home.endswith("      }else if(activeTab==='home')activeTab=startLanding(status,inventory);\n")
    home=home[:-len("else if(activeTab==='home')activeTab=startLanding(status,inventory);\n")]
    renderers={'overview':overview,'channels':channels,'statistics':statistics,'tests':''.join(other.pop('tests'))+'\n'+tests,
               'traffic':traffic,'services':services,'events':events,'settings':settings,'home':home}
    for key,calls in other.items():renderers[key]='\n'.join(calls)
    assert set(renderers)=={'overview','channels','statistics','tests','traffic','services','events','settings','home','readiness','help','learn','start'}
    factories=',\n'.join("        '%s':function(){\n%s\n        }"%(key,body) for key,body in renderers.items())
    body="""    function draw(status){
      var refreshViewport=rememberPageViewport(appRoot||panel,activeTab);
      try {
      if(typeof uiNewestStatus==='function')status=uiNewestStatus(deferredStatus||homeLatest,status);
      if(pointerHeld){deferredStatus=status;updateConnectivityCheck(status);return;}
      homeLatest=status;
      var controlFocus=panel.contains(document.activeElement)&&document.activeElement.matches(PAGE_FOCUS_SELECTOR)?{node:document.activeElement,page:(document.activeElement.closest('[data-hv-page]')||{dataset:{hvPage:activeTab}}).dataset.hvPage,label:document.activeElement.getAttribute('aria-label'),text:document.activeElement.textContent,tag:document.activeElement.tagName}:null;
      var focused=panel.contains(document.activeElement)&&document.activeElement.classList.contains('hv-search')?{key:document.activeElement.closest('[data-hv-page]').dataset.hvPage,start:document.activeElement.selectionStart,end:document.activeElement.selectionEnd}:null;
      updateConnectivityCheck(status);
      if(!status.rpc_error)lastGoodStatus=status;
COMMON
SHARED
      var homeModel=simpleHomeModel(status,inventory,statusNow(status));
      if(homeShortcut)homeShortcut.update(homeModel);
      if(homeModel.showCard){if(!setup&&!homeMenuRequested&&['start','overview','home'].indexOf(activeTab)>=0)activeTab='home';}
      else if(activeTab==='home')activeTab=startLanding(status,inventory);
      // Return the old shared buttons before replacing their card, including on Minimum.
      placeHybridControls('overview');hybridControls=null;
AUTO
      var oldAuto=visibleAutoCard;visibleAutoCard=controlCard;
      if(oldAuto&&oldAuto.parentNode)oldAuto.parentNode.replaceChild(controlCard,oldAuto);
      else put('overview',controlCard);
      var homeControl=controlCard;
      pageGeneration++;
      visibleRenderers={
FACTORIES
      };
      showPage(activeTab);
      if(typeof uiStateSignature==='function')hybridUiState=uiStateSignature(status,inventory,statusNow(status));
      restorePageControlFocus(pages,controlFocus);
      if(focused){var input=pages[focused.key]&&pages[focused.key].querySelector('.hv-search');if(input){input.focus();input.setSelectionRange(focused.start,focused.end);}}
      } finally {if(refreshViewport&&refreshViewport.page===activeTab)restorePageViewport(appRoot||panel,refreshViewport);}
    }""".replace('COMMON',common).replace('SHARED',shared).replace('AUTO',auto).replace('FACTORIES',factories)
    replace(original,body)
    helpers="""    var visibleRenderers=null,pageGeneration=0,pageFresh=Object.create(null),visibleAutoCard=null;
    function ensureVisiblePage(key){
      if(!visibleRenderers||!visibleRenderers[key]||pageFresh[key]===pageGeneration)return false;
      var page=pages[key];
      if(!page){page=pages[key]=E('section',{'class':'hv-page','data-hv-page':key});panel.appendChild(page);}
      while(page.firstChild)page.removeChild(page.firstChild);
      visibleRenderers[key]();
      sortableTables(page);attachStatsResets(page);
      pageFresh[key]=pageGeneration;
      return true;
    }
"""
    replace('    function showPage(key){',helpers+'    function showPage(key){')
    replace('key=hybridPage(key);placeHybridControls(key);','key=hybridPage(key);')
    replace("activeTab=key;if(appRoot)appRoot.setAttribute('data-hv-active',key);","activeTab=key;ensureVisiblePage(key);placeHybridControls(key);if(appRoot)appRoot.setAttribute('data-hv-active',key);")
    replace('    function sortableTables(){\n      panel.querySelectorAll',"    function sortableTables(scope){\n      (scope||panel).querySelectorAll")
    # Whole-line developer comments added after the hybrid pass (lazy core, preparation) stay in their modules.
    keep=re.compile(r'©|copyright|licen[cs]e|\bMIT\b|HomenS|Khomenko',re.I)
    source=re.sub(r'(?m)^[ \t]*(?://[^\n]*|/\*[\s\S]*?\*/[ \t]*)\n',lambda m:m.group(0) if keep.search(m.group(0)) else '',source)
    return source
