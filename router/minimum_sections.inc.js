/* Presentation composition only. Existing command nodes and retained data are moved,
 * never copied into a second controller. No RPC is invoked by page composition. */
var minimumNavigate=null;
var MINIMUM_JOURNAL_FILTER={period:'day',type:'all'};
function filteredJournalRows(rows,status,query,sort,desc){
  var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
  var seconds={hour:3600,day:86400,week:604800,all:Infinity}[MINIMUM_JOURNAL_FILTER.period]||86400;
  return retainedFilteredJournalRows(rows,status,query,sort,desc).filter(function(row){
    if(row.time<now-seconds)return false;
    if(MINIMUM_JOURNAL_FILTER.type==='errors')return row.level==='error';
    if(MINIMUM_JOURNAL_FILTER.type==='switches')return row.origin==='controller'||row.kind==='CONTROL';
    return true;
  });
}
function minimumEnhanceJournal(host){
  if(!host||host.getAttribute('data-minimum-journal'))return;
  host.setAttribute('data-minimum-journal','1');
  var oldControls=host.querySelector('.hv-native-actions');
  if(oldControls&&oldControls.parentNode===host)host.insertBefore(minimumDisclosure(bi('Search and sorting','Поиск и сортировка'),'journal-search',oldControls),host.firstChild);
  var controls=E('div',{'class':'hv-minimum-journal-filters'});
  [['period',bi('Period','Период'),[['hour','Hour','Час'],['day','Day','Сутки'],['week','Week','Неделя'],['all','All retained','Весь срок хранения']]],['type',bi('Type','Тип'),[['all','All events','Все события'],['switches','Switching','Переключения'],['errors','Errors','Ошибки']]]].forEach(function(field){
    var select=E('select',{'aria-label':field[1],'change':function(ev){MINIMUM_JOURNAL_FILTER[field[0]]=ev.target.value;EVENT_VIEW.page=0;EVENT_VIEW.draw();}},field[2].map(function(row){return E('option',{'value':row[0]},bi(row[1],row[2]));}));
    select.value=MINIMUM_JOURNAL_FILTER[field[0]];controls.appendChild(E('label',{},[field[1],select]));
  });
  host.insertBefore(controls,host.firstChild);
}
function renderMinimumFooter(status){return E('footer',{'class':'hv-minimum-footer'},[
  E('a',{'href':'https://homensai.com','target':'_blank','rel':'noopener noreferrer'},'HomenS.AI'),
  E('span',{},'© 2026 Serhii Khomenko'),E('a',{'href':'#help/about'},bi('About and licenses','О программе и лицензиях'))
]);}
function minimumDisclosure(label,key,nodes){
  var box=E('details',{'class':'hv-chart-card hv-minimum-details','data-minimum-disclosure':key},[E('summary',{},label)].concat((Array.isArray(nodes)?nodes:[nodes]).filter(Boolean)));
  if(typeof rememberDisclosure==='function')rememberDisclosure(box,'minimum-'+key);
  return box;
}
function minimumSubview(page,key,nodes){return E('section',{'class':'hv-minimum-section','data-minimum-subview':page+'/'+key},(Array.isArray(nodes)?nodes:[nodes]).filter(Boolean));}
function minimumSubviewLinks(page,items){return E('nav',{'class':'hv-minimum-subnav','aria-label':bi('Section views','Подразделы')},items.map(function(item){return E('a',{'href':'#'+page+'/'+item[0],'data-minimum-subtab':page+'/'+item[0]},bi(item[1],item[2]));}));}
function minimumDetachPage(pages,key){
  var node=pages[key];if(!node)return null;
  node.removeAttribute('data-hv-page');node.setAttribute('data-minimum-legacy',key);return node;
}
function minimumComposePages(legacy,panel,status,inventory,controlCard,commandHost,routerUrl){
  var result={},home=legacy.home,model=simpleHomeModel(status,inventory,statusNow(status));
  function page(key,children){var node=E('section',{'class':'hv-page','data-hv-page':key},children.filter(Boolean));result[key]=node;panel.appendChild(node);return node;}
  function detach(key){return minimumDetachPage(legacy,key);}
  var oldOverview=detach('overview'),oldChannels=detach('channels'),oldTests=detach('tests'),oldReadiness=detach('readiness'),oldSettings=detach('settings'),oldServices=detach('services'),oldEvents=detach('events'),oldStatistics=detach('statistics'),oldTraffic=detach('traffic'),oldHelp=detach('help'),oldLearn=detach('learn');
  detach('start');detach('ranking');
  /* Detach legacy page roots first: they must never compete with canonical pages. */
  Object.keys(legacy).forEach(function(key){var node=legacy[key];if(node&&node.parentNode===panel)panel.removeChild(node);});
  if(home){result.home=home;panel.appendChild(home);}

  var power=home&&home.querySelector('.hv-auto-power')||controlCard&&controlCard.querySelector('.hv-auto-power');
  var originalAction=home&&home.querySelector('.hv-auto-action')||controlCard&&controlCard.querySelector('.hv-auto-action');
  var homeAction=originalAction&&originalAction.parentNode;
  while(commandHost.firstChild)commandHost.removeChild(commandHost.firstChild);
  var fullPower=E('div',{'class':'hv-minimum-command-power'});
  commandHost.appendChild(E('div',{'class':'hv-minimum-command-state','role':'status'},[E('strong',{},model.title),E('span',{},model.summary)]));
  commandHost.appendChild(fullPower);
  /* The action label is updated by the authoritative Auto handler immediately. */
  if(originalAction)commandHost.appendChild(originalAction);
  var control={power:power,homePower:home&&home.querySelector('.hv-simple-power'),fullPower:fullPower,action:originalAction,homeAction:homeAction,fullAction:commandHost};
  // The monitor summary intentionally shares .hv-connectivity-control. Select
  // the actual check action, not the first look-alike status panel.
  var checkButton=controlCard&&controlCard.querySelector('.hv-connectivity-action');
  var connectivity=checkButton&&checkButton.parentNode;
  if(connectivity){
    var checkTitle=connectivity.querySelector('.hv-check-text>strong');
    if(checkTitle)checkTitle.textContent=bi('Check connection','Проверить соединение');
    checkButton.setAttribute('aria-label',bi('Check connection','Проверить соединение'));
    checkButton.setAttribute('title',bi('Check connection','Проверить соединение'));
    var verbose=connectivity.querySelector('.hv-check-text>small');if(verbose)verbose.remove();
    var nextStep=connectivity.querySelector('.hv-check-next');if(nextStep)nextStep.remove();
    var repeatedBar=connectivity.querySelector('.hv-check-bar');if(repeatedBar)repeatedBar.remove();
  }
  var manual=controlCard&&controlCard.querySelector('.hv-manual-switch');
  var statistics=controlCard&&controlCard.querySelector('.hv-auto-statistics');
  var hold=controlCard&&controlCard.querySelector('.hv-auto-hold');
  var scope=controlCard&&controlCard.querySelector('.hv-auto-scope');

  page('channels',[renderMinimumChannels(status,inventory,routerUrl),manual?minimumDisclosure(bi('Manual channel selection','Ручной выбор канала'),'manual-selection',manual):null]);

  var blockers=autoReadiness(status,inventory,statusNow(status));
  var environment=readinessModel(status,statusNow(status));
  var checks=environment.environmentFresh?environment.checks:[];
  var passed=checks.filter(function(row){return row.state==='pass';}).length;
  var failures=checks.filter(function(row){return row.state!=='pass';});
  var checkSummary=E('div',{'class':'hv-chart-card hv-minimum-checks'},[
    E('h2',{},bi('Connection check','Проверка соединения')),
    E('p',{'role':'status'},model.dataUnavailable?bi('No fresh router data.','Нет свежих данных роутера.'):bi('Check VPN availability without changing the active channel.','Проверить доступность VPN без смены рабочего канала.')),connectivity,
    E('small',{},bi('The router does the check itself.','Проверку делает сам роутер.'))
  ].filter(Boolean));
  if(!model.dataUnavailable&&passed)checkSummary.appendChild(minimumDisclosure(bi('Passed checks: ','Пройдено проверок: ')+passed,'passed-checks',E('ul',{},checks.filter(function(row){return row.state==='pass';}).map(function(row){var label=READINESS_CHECKS[row.code];return E('li',{},label?bi(label[0],label[1]):row.code);})))) ;
  if(!model.dataUnavailable&&failures.length)checkSummary.appendChild(E('ul',{},failures.map(function(row){return E('li',{},autoCodeNotice(row.code));})));
  var blockerCodes=(Array.isArray((status.native_failover||{}).blockers)?status.native_failover.blockers:[]).slice(0,32);
  if(blockerCodes.length)checkSummary.appendChild(E('div',{'class':'hv-minimum-blockers'},blockerCodes.slice(0,3).map(function(code){return autoCodeNotice(code);})));
  var technical=[oldServices,oldChannels?minimumDisclosure(bi('All profile observations','Проверки всех профилей'),'profile-observations',oldChannels):null,oldOverview?minimumDisclosure(bi('What Auto sees','Что видит Auto'),'controller-observations',oldOverview):null];
  page('diagnostics',[
    minimumSubviewLinks('diagnostics',[['checks','Checks','Проверки'],['speed','Speed','Скорость'],['recovery','Recovery','Восстановление'],['technical','Technical details','Технические сведения']]),
    minimumSubview('diagnostics','checks',[checkSummary,minimumDisclosure(bi('Startup conditions','Условия запуска'),'readiness',oldReadiness)]),
    minimumSubview('diagnostics','readiness',[]),
    minimumSubview('diagnostics','speed',[oldTests&&oldTests.querySelector('.hv-speed-panel'),minimumDisclosure(bi('Test settings and retained rankings','Настройки теста и сохранённые рейтинги'),'speed-settings',oldTests)]),
    minimumSubview('diagnostics','recovery',[
      E('h2',{},bi('Recovery','Восстановление')),
      E('p',{},bi('Use Stop above to stop Auto. Check the actual result before changing router settings.','Для остановки Auto используйте кнопку выше. Перед изменением настроек роутера проверьте фактический результат.')),
      E('a',{'href':'#help/topic/no-internet'},bi('No internet: recovery steps','Нет интернета: порядок восстановления')),
      hold,scope,minimumDisclosure(bi('Controller conditions and actions','Условия и действия контроллера'),'recovery-controls',controlCard)
    ].filter(Boolean)),
    minimumSubview('diagnostics','technical',technical)
  ]);
  /* A legacy readiness node belongs to one DOM parent only. Keep the checks
   * disclosure self-contained and use a fresh read-only rendering for deep links. */
  var readinessView=result.diagnostics.querySelector('[data-minimum-subview="diagnostics/readiness"]');
  if(readinessView)readinessView.appendChild(renderReadiness(status,inventory));
  var oldErrors=oldEvents&&oldEvents.querySelector('.hv-errtable');
  if(oldErrors&&oldErrors.parentNode)oldErrors.parentNode.removeChild(oldErrors);
  if(oldEvents){
    var journal=oldEvents.querySelector('[data-event-history]');minimumEnhanceJournal(journal);
    var extra=Array.from(oldEvents.children).filter(function(node){return node!==journal&&node.tagName!=='BUTTON';});
    if(extra.length)oldEvents.appendChild(minimumDisclosure(bi('Detailed event analytics','Подробная аналитика событий'),'event-analytics',extra));
  }
  page('events',[
    minimumSubviewLinks('events',[['journal','Journal','Журнал'],['statistics','History','История'],['traffic','Traffic','Трафик']]),
    minimumSubview('events','journal',[oldEvents]),
    minimumSubview('events','statistics',[statistics,minimumDisclosure(bi('Latency and availability','Задержка и доступность'),'statistics',oldStatistics)]),
    minimumSubview('events','traffic',[oldTraffic])
  ]);
  page('settings',[oldSettings?minimumDisclosure(bi('Controller configuration details','Сведения о настройке контроллера'),'controller-settings',oldSettings):null]);
  page('help',[
    minimumSubviewLinks('help',[['topics','Help topics','Инструкции'],['training','Training','Обучение'],['about','About','О программе']]),
    minimumSubview('help','topics',[renderMinimumHelp(oldHelp,inventory),oldErrors?minimumDisclosure(bi('Diagnostic codes','Диагностические коды'),'error-codes',oldErrors):null]),
    minimumSubview('help','training',[oldLearn]),
    minimumSubview('help','about',[
      E('h2',{},'Auto VPN'),E('p',{},'HomenS.AI · Serhii Khomenko'),
      E('p',{},bi('Version: ','Версия: ')+(status.version||'unknown')),
      typeof renderAttribution==='function'?renderAttribution(status):null,
      E('p',{},bi('Tested on GL-MT3000 with firmware 4.11.0.','Проверено на GL-MT3000 с прошивкой 4.11.0.')),
      E('a',{'href':'https://github.com/HomenSAI/homensai-gl-mt6000-auto-vpn/blob/main/LICENSE','target':'_blank','rel':'noopener noreferrer'},bi('MIT license and project source','Лицензия MIT и исходники проекта'))
    ])
  ]);
  return {pages:result,control:control};
}
function minimumApplyRoute(root,route,control){
  if(!root)return;
  root.querySelectorAll('[data-minimum-subview]').forEach(function(node){
    var key=node.getAttribute('data-minimum-subview');
    node.hidden=key!==route.page+'/'+(route.page==='help'&&route.subview==='topic'?'topics':route.subview);
  });
  root.querySelectorAll('[data-minimum-subtab]').forEach(function(node){node.setAttribute('aria-current',node.getAttribute('data-minimum-subtab')===route.page+'/'+route.subview?'page':'false');});
  if(control&&control.power){var target=route.page==='home'?control.homePower:control.fullPower;if(target&&control.power.parentNode!==target)target.appendChild(control.power);}
  if(control&&control.action){var labelTarget=route.page==='home'?control.homeAction:control.fullAction;if(labelTarget&&control.action.parentNode!==labelTarget)labelTarget.appendChild(control.action);}
}
function minimumOpenAncestors(node){for(var parent=node&&node.parentElement;parent;parent=parent.parentElement)if(parent.tagName==='DETAILS')parent.open=true;}
function minimumRevealTopic(id){
  var topic=document.getElementById('help-'+id);if(!topic)return;
  minimumOpenAncestors(topic);topic.open=true;topic.scrollIntoView({block:'start'});
}
/* Route-aware replacements of legacy helpers. They never click a write control. */
function openHelpTopic(id){
  if(typeof id!=='string'||!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$/.test(id))return;
  var route='help/topic/'+encodeURIComponent(id);
  if(minimumNavigate)minimumNavigate(route);else window.location.hash=route;
}
function goToSection(tab,id){
  if(minimumNavigate&&!minimumNavigate(minimumRoute(tab).hash))return;
  setTimeout(function(){var node=id&&document.getElementById(id);if(node){minimumOpenAncestors(node);node.scrollIntoView({block:'start'});}},0);
}
function showErrorBack(){
  if(!errorReturn||!document.querySelector('.hv-app'))return;
  if(!errorBackButton||!errorBackButton.isConnected){
    errorBackButton=E('button',{'type':'button','class':'hv-errback-button','click':function(){var previous=errorReturn;if(!previous)return;if(minimumNavigate&&!minimumNavigate(previous.tab))return;hideErrorBack();setTimeout(function(){window.scrollTo(0,previous.y||0);},0);}},bi('← Back to where you were','← Вернуться назад'));
    document.body.appendChild(errorBackButton);
  }
  errorBackButton.removeAttribute('hidden');
}
function showErrorCode(code){
  var key=Object.prototype.hasOwnProperty.call(ERROR_GROUP_OF,code)?code:((typeof errorFamilyOf==='function'&&errorFamilyOf(code))?errorFamilyOf(code)[0]+'*':code);
  if(!/^[A-Z][A-Z0-9*-]{1,95}$/.test(key))return;
  var previous={tab:minimumRoute(window.location.hash).hash,y:window.pageYOffset||0};
  if(minimumNavigate&&!minimumNavigate('help'))return;
  if(!errorReturn)errorReturn=previous;
  if(typeof ERROR_TABLE_STATE!=='undefined'){ERROR_TABLE_STATE.selected=key;persistErrorTableState();}
  if(errorTable){minimumOpenAncestors(errorTable);var search=errorTable.querySelector('input[type="search"]');if(search){search.value=key;search.dispatchEvent(new Event('input',{bubbles:true}));}}
  setTimeout(function(){var row=document.querySelector('[data-error-code="'+key+'"]');if(!row)return;minimumOpenAncestors(row);var fix=row.nextElementSibling;if(fix&&fix.classList.contains('hv-errfix')&&fix.hidden){var button=row.querySelector('button');if(button)button.click();}row.scrollIntoView({block:'center'});showErrorBack();},0);
}
