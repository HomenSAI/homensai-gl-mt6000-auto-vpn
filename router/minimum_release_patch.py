"""Final, fail-closed adapter from preserved legacy renderers to Minimum UI."""
from pathlib import Path
import re


def apply(source):
    base=Path(__file__).parent
    def replace(old,new):
        nonlocal source
        assert source.count(old)==1, 'MINIMUM-ANCHOR '+old[:100]
        source=source.replace(old,new,1)
    def between(start,end,new):
        nonlocal source
        assert source.count(start)==1 and source.count(end)==1, 'MINIMUM-RANGE '+start[:70]
        a=source.index(start);b=source.index(end,a)
        source=source[:a]+new+source[b:]
    replace('return view.extend({','\n'.join((base/name).read_text(encoding='utf8') for name in ('minimum_navigation.inc.js','minimum_channels.inc.js','minimum_settings.inc.js','minimum_help.inc.js','minimum_sections.inc.js'))+'\nreturn view.extend({')
    # Human terms remain authoritative. Initial setup becomes an explicit action,
    # rather than a navigation gate that hides the home/Stop/recovery surface.
    gate="    if(!inventory.error&&!onboardingComplete(inventory)&&!simpleHomeAutoEnabled(data[1],statusNow(data[1]))&&languageViewContext(window.location.href)!=='full'&&!onboardingEntryDeferred())return renderOnboardingGate(inventory,data[1]);"
    replace(gate,'    // Minimum is accessible before setup; backend Start still verifies all conditions.')
    source,n=re.subn(r"    var tabs=\[.*?\];", "    var tabs=[['channels','⇄',bi('Channels','Каналы')],['diagnostics','✓',bi('Diagnostics','Диагностика')],['events','≡',bi('Events','События')],['settings','⚙',bi('Settings','Настройки')],['help','?',bi('Help','Помощь')]];",source,count=1)
    assert n==1,'MINIMUM-TABS'
    between('    var homeLatest=data[1],homeMenuRequested=false;','    function showPage(key){',"""    var homeLatest=data[1],homeMenuRequested=false,homeShortcut=null;
    var minimumCurrentRoute=minimumRouteFromUrl(window.location.href);
    var minimumNav=minimumNavigationState(minimumCurrentRoute.hash),minimumControlNodes=null,minimumRenderedState='';
    var minimumCommandHost=E('section',{'class':'hv-minimum-command','aria-label':bi('Auto control','Управление Auto')});
    tabs.push(['home','',bi('Minimum','Минимум')]);
    var activeTab=minimumCurrentRoute.page;
    minimumNavigate=function(key){var route=minimumRoute(key);if(showPage(route.hash)!==true)return false;if(window.location.hash!=='#'+route.hash)window.location.hash=route.hash;return true;};
    function openHomeMenu(){minimumNavigate(minimumAdvancedRoute(minimumNav).hash);}
    function goSimpleHome(){if(!minimumNavigate('home'))return false;resetPageViewport(appRoot||panel,'home');var entry=appRoot&&appRoot.querySelector('.hv-simple-open-menu');if(entry)entry.focus({preventScroll:true});return true;}

""")
    between('    function showPage(key){','    function put(key,node){',"""    function showPage(key){
      var route=minimumRoute(key),oldTab=activeTab,oldRoute=minimumCurrentRoute;
      if(route.hash!==oldRoute.hash&&minimumSettingsDirty()&&!minimumSettingsCanLeave()){
        try{var retainedUrl=new URL(window.location.href);retainedUrl.hash=oldRoute.hash;window.history.replaceState(null,'',retainedUrl.toString());}catch(error){}
        return minimumSettingsRequestLeave(function(){minimumNavigate(route.hash);});
      }
      if(oldRoute.hash!==route.hash)rememberPageViewport(appRoot||panel,oldTab);
      minimumCurrentRoute=route;minimumNav=minimumNavigationTransition(minimumNav,route.hash);activeTab=route.page;
      var scope=appRoot||panel;
      if(appRoot){appRoot.setAttribute('data-hv-active',activeTab);appRoot.setAttribute('data-minimum-route',route.hash);}
      scope.querySelectorAll('[data-hv-page]').forEach(function(node){node.hidden=node.getAttribute('data-hv-page')!==activeTab;});
      if(appRoot)appRoot.querySelectorAll('[data-hv-tab]').forEach(function(node){node.setAttribute('aria-current',node.getAttribute('data-hv-tab')===activeTab?'page':'false');});
      minimumApplyRoute(scope,route,minimumControlNodes);
      if(heading)heading.textContent=(tabs.filter(function(tab){return tab[0]===activeTab;})[0]||tabs[5])[2];
      if(subtitle)subtitle.hidden=true;
      if(appRoot){updateSidebarLayout(appRoot,oldTab!==activeTab);appRoot.setAttribute('data-minimum-menu-open','false');var menuButton=appRoot.querySelector('.hv-minimum-mobile-menu');if(menuButton)menuButton.setAttribute('aria-expanded','false');}
      if(oldRoute.hash!==route.hash){revisitPageViewport(scope,activeTab);if(activeTab!=='home'&&heading&&document.body.contains(heading))heading.focus({preventScroll:true});}
      if(route.page==='help'&&route.topic)minimumRevealTopic(route.topic);
      return true;
    }
""")
    # No experimental fault panel in the operator UI. The test helper stays intact.
    replace("      put('tests',faultPanel(status,inventory,function(){return statusCall().then(draw);}));",'      // Controlled fault injection belongs to the dedicated test kit.')
    # Remove overview design-specific duplicate renderers; preserve the data pages
    # and original controller for bounded disclosures/recovery.
    start='var identityNotice=renderIdentityNotice(status);try{pages.overview.insertBefore(renderDesignOverview('
    a=source.index(start);b=source.index('\n',a)
    source=source[:a]+'var identityNotice=renderIdentityNotice(status);'+source[b:]
    between('      var homeModel=simpleHomeModel(status,inventory,statusNow(status));','      installErrorLinks(appRoot);sortableTables();showPage(activeTab);',"""      var homeModel=simpleHomeModel(status,inventory,statusNow(status));
      minimumRenderedState=JSON.stringify([homeModel.state,homeModel.title,homeModel.summary,homeModel.selectedRole,homeModel.targetHealth.state]);
      if(homeShortcut)homeShortcut.update(homeModel);
      var homeControl=pages.overview&&pages.overview.querySelector('.hv-auto-control');
      put('home',renderSimpleHome(status,inventory,homeModel,homeControl,openHomeMenu));
      var composed=minimumComposePages(pages,panel,status,inventory,controlCard,minimumCommandHost,routerVpnUrl());
      pages=composed.pages;minimumControlNodes=composed.control;
""")
    # Polling must retain a subsection, not fall back to the default tab.
    source=source.replace('sortableTables();showPage(activeTab);','sortableTables();showPage(minimumCurrentRoute.hash);')
    replace("languageNavigationUrl(window.location.href,chosen,activeTab)","languageNavigationUrl(window.location.href,chosen,minimumCurrentRoute.hash)")
    between("      settingsHost=E('section',{'class':'hv-settings'",'      function tabLink(key){',"""      settingsHost=renderMinimumSettings(inventory,homeLatest,function(){return {inventory:inventory,status:homeLatest};});
""")
    between('      var advancedOpen=false;','      appRoot=E(',"""      var links=['channels','diagnostics','events','settings','help'].map(tabLink);
""")
    replace("'class':'hv-app hv-workspace','data-hv-design':currentDesign()", "'class':'hv-app hv-workspace hv-minimum-release','data-hv-design':'b'")
    # Exactly five main links. Mobile uses an explicit disclosure rather than a
    # fixed bottom strip; desktop keeps the existing sidebar footprint.
    replace("E('nav',{'tabindex':'0','aria-label':bi('VPN sections','Разделы VPN')},links)","E('button',{'type':'button','class':'hv-minimum-mobile-menu','aria-controls':'hv-minimum-nav','aria-expanded':'false','click':function(ev){var open=appRoot.getAttribute('data-minimum-menu-open')!=='true';appRoot.setAttribute('data-minimum-menu-open',open?'true':'false');ev.currentTarget.setAttribute('aria-expanded',open?'true':'false');}},bi('Sections','Разделы')),E('nav',{'id':'hv-minimum-nav','aria-label':bi('VPN sections','Разделы VPN')},links)")
    replace("panel,settingsHost,renderAttribution(data[1]),footer", "minimumCommandHost,panel,settingsHost,renderAttribution(data[1]),footer")
    # Settings is a persistent form; it is never rebuilt by status polling.
    between("      settingsHost.appendChild(E('section',{'class':'hv-chart-card hv-card-monitor'}", "      panel.addEventListener('pointerdown'",'')
    source=source.replace("if(activeTab==='home'&&!simpleHomeModel(homeLatest,inventory,statusNow(homeLatest)).showCard)showPage(startLanding(homeLatest,inventory));", "// Stale data updates the Minimum state; it never ejects the user to setup.")
    replace("showPage(activeTab);window.addEventListener('hashchange',function(){showPage(window.location.hash.slice(1));});", "showPage(minimumCurrentRoute.hash);window.addEventListener('hashchange',function(){showPage(window.location.hash.slice(1));});")
    replace("installSpeedLive(appRoot,function(){return activeTab;});", "installSpeedLive(appRoot,function(){return minimumCurrentRoute.page==='diagnostics'&&minimumCurrentRoute.subview==='speed'?'tests':'inactive';});")
    # A single accepted design; ignore only legacy layout preference, preserving
    # language/theme and all router options. No configuration reset or RPC.
    source,n=re.subn(r"function currentDesign\(\)\{[^\n]*\}","function currentDesign(){return 'b';}",source,count=1)
    assert n==1,'MINIMUM-DESIGN'
    source=source.replace("'click':function(){showPage(tab[0]);}","'click':function(ev){ev.preventDefault();minimumNavigate(tab[0]);}")
    source=source.replace("// Stale data updates the Minimum state; it never ejects the user to setup.","var timed=simpleHomeModel(homeLatest,inventory,statusNow(homeLatest));var timedKey=JSON.stringify([timed.state,timed.title,timed.summary,timed.selectedRole,timed.targetHealth.state]);if(timedKey!==minimumRenderedState)draw(homeLatest);")
    source=source.replace("installViewportPersistence(appRoot,function(){return activeTab;});", "installViewportPersistence(appRoot,function(){return activeTab;});installMinimumSettingsGuard(appRoot);")
    oldLanguage="var chosen=language.value==='ru'?'ru':'en';try{localStorage.setItem('homensai-vpn-language',chosen);}catch(e){}window.location.assign(languageNavigationUrl(window.location.href,chosen,minimumCurrentRoute.hash));"
    newLanguage="var chosen=language.value==='ru'?'ru':'en';language.value=locale;minimumSettingsRequestLeave(function(){try{localStorage.setItem('homensai-vpn-language',chosen);}catch(e){}window.location.assign(languageNavigationUrl(window.location.href,chosen,minimumCurrentRoute.hash));});"
    replace(oldLanguage,newLanguage)
    assert source.count('function filteredJournalRows(rows,status,query,sort,desc){')==2,'MINIMUM-JOURNAL-FILTER'
    source=source.replace('function filteredJournalRows(rows,status,query,sort,desc){','function retainedFilteredJournalRows(rows,status,query,sort,desc){',1)
    replace('renderAttribution(data[1]),footer','renderMinimumFooter(data[1])')
    source,count=re.subn(r"E\('div',\{'class':'hv-side-footer'\},\[sideState,.*?identityLine\(data\[1\]\)\)\]\)","E('div',{'class':'hv-side-footer'},[])",source,count=1)
    assert count==1,'MINIMUM-SIDEBAR-STATUS'
    replace('minimumCommandHost,panel,settingsHost,renderMinimumFooter(data[1])','minimumCommandHost,settingsHost,panel,renderMinimumFooter(data[1])')
    replace("E('div',{'class':'hv-page-actions'},[versionBadge,language,renderThemeSelect()])","E('div',{'class':'hv-page-actions'},[])")
    replace("      panel.addEventListener('pointerdown'", """      settingsHost.appendChild(minimumDisclosure(bi('Interface in this browser','Интерфейс в этом браузере'),'browser-interface',E('div',{'class':'hv-minimum-browser-controls'},[language,renderThemeSelect()])));
      panel.addEventListener('pointerdown'""")
    return source
