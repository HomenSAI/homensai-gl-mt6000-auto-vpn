from pathlib import Path

def apply(source):
    base=Path(__file__).parent
    def replace(old,new):
        nonlocal source
        assert source.count(old)==1,old[:100]
        source=source.replace(old,new,1)
    replace('return view.extend({',(base/'simple_home_policy.inc.js').read_text(encoding='utf8')+'\n'+(base/'simple_home_panel.inc.js').read_text(encoding='utf8')+'\nreturn view.extend({')
    replace('First steps: terms, training, monitoring, your two VPNs and Auto. This page opens first until they are done.','Setup, training and checks. The simplified interface is available whenever Auto is on.')
    replace('Первые шаги: условия, обучение, мониторинг, два ваших VPN и Auto. Эта страница открывается первой, пока они не выполнены.','Настройка, обучение и проверки. При включённом Auto упрощённый интерфейс доступен всегда.')
    replace("if(!inventory.error&&!onboardingComplete(inventory)&&!onboardingEntryDeferred())return renderOnboardingGate(inventory,data[1]);","if(!inventory.error&&!onboardingComplete(inventory)&&!simpleHomeAutoEnabled(data[1],statusNow(data[1]))&&!onboardingEntryDeferred())return renderOnboardingGate(inventory,data[1]);")
    replace("heading,(subtitle=E('p',{},bi(","E('div',{'class':'hv-heading-row'},[heading,(homeShortcut=renderSimpleHomeShortcut(function(){return simpleHomeModel(homeLatest,inventory,statusNow(homeLatest));},goSimpleHome))]),(subtitle=E('p',{},bi(")
    replace("    var activeTab=setup?'settings':window.location.hash.slice(1);if(!validTab(activeTab))activeTab=startLanding(data[1],data[0]);", """    var homeLatest=data[1],homeMenuRequested=false;
    var homeShortcut=null;
    tabs.push(['home','',bi('Home','Главная')]);
    var requestedTab=window.location.hash.slice(1);
    if(setup||validTab(requestedTab)&&['overview','home'].indexOf(requestedTab)<0)homeMenuRequested=true;
    var activeTab=setup?'settings':requestedTab;
    if(!setup&&(!validTab(activeTab)||activeTab==='overview'||activeTab==='home'))activeTab=simpleHomeModel(data[1],inventory,statusNow(data[1])).showCard?'home':startLanding(data[1],inventory);
    function openHomeMenu(){homeMenuRequested=true;window.location.hash='overview';showPage('overview');}
    function goSimpleHome(){
      var model=simpleHomeModel(homeLatest,inventory,statusNow(homeLatest));
      if(homeShortcut)homeShortcut.update(model);
      if(!model.showCard)return false;
      homeMenuRequested=false;window.location.hash='home';showPage('home');return true;
    }
""")
    replace('    function showPage(key){', """    function showPage(key){
      if(key==='home'&&!simpleHomeModel(homeLatest,inventory,statusNow(homeLatest)).showCard)key=startLanding(homeLatest,inventory);
""")
    replace('    function draw(status){', '    function draw(status){\n      homeLatest=status;')
    replace('      showPage(activeTab);window.addEventListener',"""      var homeFreshTimer=window.setInterval(function(){
        if(!appRoot||!appRoot.isConnected){window.clearInterval(homeFreshTimer);return;}
        if(homeShortcut)homeShortcut.update();
        if(activeTab==='home'&&!simpleHomeModel(homeLatest,inventory,statusNow(homeLatest)).showCard)showPage(startLanding(homeLatest,inventory));
      },1000);
      if(homeShortcut)homeShortcut.update();
      showPage(activeTab);window.addEventListener""")
    anchor='      installErrorLinks(appRoot);sortableTables();showPage(activeTab);'
    replace(anchor,"""      var homeModel=simpleHomeModel(status,inventory,statusNow(status));
      if(homeShortcut)homeShortcut.update(homeModel);
      var homeControl=pages.overview&&pages.overview.querySelector('.hv-auto-control');
      if(homeModel.showCard){
        put('home',renderSimpleHome(status,inventory,homeModel,homeControl,openHomeMenu));
        if(pages.overview)pages.overview.insertBefore(E('button',{'type':'button','class':'cbi-button hv-simple-return','click':function(){homeMenuRequested=false;window.location.hash='home';showPage('home');}},bi('Return to home','На главный экран')),pages.overview.firstChild);
        if(!setup&&!homeMenuRequested&&['start','overview','home'].indexOf(activeTab)>=0)activeTab='home';
      }else if(activeTab==='home')activeTab=startLanding(status,inventory);
"""+anchor)
    return source
