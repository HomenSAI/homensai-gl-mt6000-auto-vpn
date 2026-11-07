/* Views: «Простой» (mockup A), «Пульт» (mockup D) and the first-run wizard (mockup C). Header and footer carry the
   owner attributes on every view; the view switch sits next to the language button. */

/* ---------------- Shared chrome ---------------- */
function viewName(){return HV.view==='console'?t('Пульт','Console'):t('Простой','Simple');}
/* Header Internet/Auto lamps (not controls; the label is in the lamp name). */
function headLampsHTML(){return '<div class="hlamps" role="group" aria-label="'+t('Состояние','Status')+'">'+[['ov',t('Интернет','Internet')],['auto','Auto']].map(function(x){return '<span class="hlamp"><i class="lamp" data-lamp="'+x[0]+'" data-hl="'+esc(x[1])+'"></i><span class="hll" aria-hidden="true">'+esc(x[1])+'</span></span>';}).join('')+'</div>';}
function brandHTML(){var v=VER();return '<div class="hb"><a class="brand" href="https://homensai.com" target="_blank" rel="noopener noreferrer" title="homensai.com"><span class="logo">HS</span><span class="col gap0"><b>HomenS<span class="ai">.AI</span> Auto VPN</b><span class="devline" data-b="model">'+esc(v.model)+'</span></span></a></div><div class="bv"><span class="badge-ver hv-version" title="'+t('Версия программы','Program version')+'" data-b="badge">v'+esc(v.app)+'</span></div>';}
function toolsHTML(){
  var vs='<span class="viewsw" role="group" aria-label="'+t('Вид','View')+'"><span class="vlabel">'+t('Вид','View')+'</span>'+[['simple','☰',t('Вид: Простой','View: Simple')],['console','▦',t('Вид: Пульт','View: Console')]].map(function(x){return '<button class="iconbtn" data-act="view" data-v="'+x[0]+'" aria-pressed="'+(HV.view===x[0])+'" title="'+x[2]+'" aria-label="'+x[2]+'">'+x[1]+'</button>';}).join('')+'</span>';
  return vs+'<button class="iconbtn" data-act="lang" title="'+t('Язык','Language')+'" aria-label="'+t('Переключить язык','Switch language')+'">'+(locale==='ru'?'EN':'RU')+'</button><button class="iconbtn" data-act="theme" title="'+t('Тема','Theme')+'" aria-label="'+t('Переключить тему','Switch theme')+'">'+({system:'◐',light:'☀',dark:'☾'}[HV.theme])+'</button>';
}
function footerHTML(){var v=VER();return '<footer class="attr hv-attribution" data-attribution="1"><div class="wrap"><strong>HomenS<span class="ai">.AI</span> Auto VPN</strong><span>'+esc(v.model)+' <span class="tiny">('+(v.detected?t('обнаружено роутером','detected by the router'):t('модель не определена роутером','model not detected by the router'))+')</span></span><a href="https://homensai.com" target="_blank" rel="noopener noreferrer">'+t('Разработчик · Serhii Khomenko','Developer · Serhii Khomenko')+'</a><span data-b="buildline">'+buildLine()+'</span><span>'+esc(v.style)+'</span><span class="copy">© 2026 Serhii Khomenko · HomenS.AI · <a href="https://homensai.com" target="_blank" rel="noopener noreferrer">homensai.com</a></span></div></footer>';}
function buildLine(){var v=VER();return esc(t('Программа','Program')+' '+v.app);}
function noticesHTML(){
  var v=VER(),out='';
  if(v.mismatch)out+='<p class="note warn warnbar">'+t('Версии страницы и роутера различаются: нажмите Ctrl+F5.','The page and router versions differ: press Ctrl+F5.')+' ('+esc(HV_AGENT)+' / '+esc(v.app)+')</p>';
  if(HV.inv.error)out+='<p class="note bad warnbar">'+t('Настройки роутера не прочитаны. Обновите страницу.','Router settings were not read. Reload the page.')+' <a class="code" href="#" data-act="code" data-code="RPC-INVENTORY-UNAVAILABLE">RPC-INVENTORY-UNAVAILABLE</a></p>';
  return out;
}
/* Install reasons (owner 07.11.2026), red, with the catalogue name: status.upgrade_result (rolled back / refused update), status.integrity no-auto|stopped. */
function integrityBanner(){
  var st=V.st||{},u=st.upgrade_result,g=st.integrity,out=[],ok=function(v){return typeof v==='string'&&/^[0-9A-Za-z.+~_-]{1,48}$/.test(v);};
  if(u&&/^UPGRADE-ROLL(ED-BACK|BACK-UNAVAILABLE|BACK-FAILED)$/.test(u.code))out.push([u.code,ok(u.from)&&ok(u.to)?' ('+u.from+' → '+u.to+')':'']);
  /* plan item 54: a package operation runs (Auto and the switching buttons wait) or one was interrupted (power cut) */
  var m=st.maintenance;
  if(m&&m.state==='active'&&m.code==='MAINTENANCE-IN-PROGRESS')out.push([m.code,'']);
  else if(m&&m.state==='stale'&&m.code==='MAINTENANCE-INTERRUPTED'||u&&u.code==='MAINTENANCE-INTERRUPTED')out.push(['MAINTENANCE-INTERRUPTED','']);
  if(g&&(g.mode==='no-auto'||g.mode==='stopped')&&codeOk(g.code))out.push([g.code,'']);
  return out.map(function(x){var r=(typeof ERROR_ROWS!=='undefined'?ERROR_ROWS:[]).filter(function(r){return r[0]===x[0];})[0];
    return '<p class="note bad warnbar" data-install-reason="'+x[0]+'">'+esc((r?t(r[3],r[2]):x[0])+x[1])+' <a class="code" href="#" data-act="code" data-code="'+x[0]+'">'+x[0]+'</a></p>';}).join('');
}
function readinessBanner(){
  var m=readinessModel(V.st,V.now),bad=(m.checks||[]).filter(function(c){return c.state==='fail';});
  return bad.length?'<p class="note bad warnbar">'+t('Готовность роутера: есть проблемы — ','Router readiness: problems — ')+bad.map(function(c){return '<a class="code" href="#" data-act="code" data-code="'+esc(c.code)+'">'+esc(c.code)+'</a>';}).join(' ')+' · <a href="#" data-act="goready">'+t('подробнее','details')+'</a></p>':'';
}
function chCard(role,opt){opt=opt||{};var k=role==='primary'?'p':'r';
  return '<div class="ch" data-ch="'+role+'" data-b-class="'+k+'.active"><div class="top"><i class="lamp l" data-lamp="'+role+'"></i><div class="fx1m0"><div class="role" data-b="'+k+'.role"></div><div class="nm" data-b="'+k+'.name"></div></div><span data-b="'+k+'.tag"></span></div>'+
  '<div class="row mt6sb"><div class="ms" data-b="'+k+'.ms"></div><div class="small tar"><div data-b="'+k+'.text"></div><div class="mute tiny" data-b="'+k+'.age"></div></div></div>'+
  (opt.meta===false?'':'<div class="tiny mute" data-b="'+k+'.meta"></div>')+
  '<div class="foot"><span class="tiny mute" data-b="'+k+'.pick"></span><span data-b="'+k+'.sw"></span></div></div>';}
function autoSwitchHTML(sub){return '<button class="aswitch" role="switch" data-act="auto" data-auto-switch aria-label="Auto"><span class="trk"></span>'+(sub===false?'<b data-b="auto.text"></b>':'<span><b data-b="auto.text"></b><br><span class="small mute" data-b="auto.sub"></span></span>')+'</button>';}
function helpSecHTML(sub,extra){return '<details class="sec" data-open="sec-help"'+(HV.open['sec-help']?' open':'')+' data-help-sec><summary><span class="t"><b>'+sub[0]+'</b><span data-help-count data-sub="'+esc(sub[1])+'">'+(helpCount()?helpCount()+' '+t('тем','topics')+' · ':'')+sub[1]+'</span></span></summary><div class="body hlp">'+(extra||'')+'<h3>'+t('Темы помощи','Help topics')+'</h3>'+helpListHTML()+'</div></details>';}

/* ---------------- Live bindings: every view reads the same snapshot ---------------- */
var LAMP={ov:function(){return overall().lamp;},auto:function(){return autoIndicator().lamp;},last:function(){var e=lastSwitch();return e?evKind(e).lamp:'n';},primary:function(){return reading('primary').lamp;},reserve:function(){return reading('reserve').lamp;},mon:monLamp};
var B={
  'ov.title':function(){var o=overall();return (o.icon?'<span class="ovi" aria-hidden="true">'+esc(o.icon)+'</span> ':'')+esc(o.title);},'ov.sub':function(){return esc(overall().sub);},
  'auto.text':function(){var a=autoIndicator();return (a.icon?'<span class="ovi" aria-hidden="true">'+esc(a.icon)+'</span> ':'')+esc(a.text);},'auto.sub':function(){return esc(autoDetail());},
  'last.short':function(){var e=lastSwitch();return e?esc(fmtTime(e.time)+' · '+evText(e)):t('переходов в сохранённой истории нет','no switches in the retained history');},
  'last.why':function(){var e=lastSwitch();return e?esc(evWhy(e)):'';},
  'last.time':function(){var e=lastSwitch();return e?esc(fmtTime(e.time)):'—';},'last.what':function(){var e=lastSwitch();return e?esc(evText(e)):t('переходов в сохранённой истории нет','no switches in the retained history');},
  'speed':function(){return speedHTML();},'fault':function(){return faultHTML();},'mon.text':function(){return esc(monText());},
  'manual':function(){return manualFeedback();},'check':function(){return checkBtnHTML();},'check.l':function(){return checkBtnHTML().replace('class="btn sm"','class="btn"');},
  'events':function(){return eventsHTML(HV.all?20:5,HV.filters.a,{openFirst:true});},'events20':function(){return eventsHTML(20,HV.filters.d,{openSwitch:true});},
  'tiles':function(){return statsTiles();},'live':function(){return liveLogHTML();},'monrestore':function(){return V.monitor.maintenance?'':V.monitor.key==='problem'?'<button class="btn sm" data-act="monrestore">'+t('Восстановить мониторинг','Restore monitoring')+'</button>':V.monitor.serviceOff?'<span class="small">'+esc(monitorServiceOffText())+'</span> <button class="btn sm" data-act="monrestore">'+t('Включить службу Auto','Switch the Auto service on')+'</button>':V.monitor.key!=='ok'?'<button class="btn sm" data-act="monrestore">'+t('Восстановить мониторинг','Restore monitoring')+'</button>':'';},'ready':function(){return readinessHTML();},'banner':function(){return noticesHTML()+integrityBanner()+readinessBanner()+sensorBanner();},'adv.card':function(){return advCardHTML();},'sensors':function(){return sensorsHTML();},
  'badge':function(){return 'v'+esc(VER().app);},'model':function(){return esc(VER().model);},'buildline':function(){return buildLine();},
  'autochip':function(){return esc(presetName())+' · '+t('уровень','level')+' '+D().level;},
  'autoplain':function(){var d=draftFromInventory(),iv=Number(((V.st.probe_policy||{}).effective_interval))||d.interval;return t('Сейчас Auto проверяет каналы каждые '+iv+' с. Переключит '+detectorPhrase(true)+', если резерв прошёл '+d.resOk+' проверок. Не больше '+d.attempts+' переключений за '+d.window+' мин.','Auto checks both channels every '+iv+' s. It switches '+detectorPhrase(false)+' if the reserve passed '+d.resOk+' checks. No more than '+d.attempts+' switches per '+d.window+' min.');}
};
['primary','reserve'].forEach(function(r){var k=r==='primary'?'p':'r';
  B[k+'.name']=function(){return esc(chName(r));};B[k+'.role']=function(){return esc(roleName(r));};
  B[k+'.meta']=function(){var p=roleProfile(r);if(!p)return '';var ep='';try{ep=endpointText(p,V.now)||'';}catch(e){}var c='';try{c=countryName(p)||'';}catch(e){}
    return esc([p.protocol==='wireguard'?'WireGuard':p.protocol==='openvpn'?'OpenVPN':t('протокол: нет данных','protocol: no data'),ep?ep.replace(/^(Server|Сервер): /,''):t('сервер: нет данных','server: no data'),c||t('страна: нет данных','country: no data')].join(' · '));};
  B[k+'.ms']=function(){var x=reading(r);return x.ms==null?'—':x.ms+' <small>'+t('мс','ms')+'</small>';};
  B[k+'.text']=function(){var x=reading(r);return '<span title="'+esc(x.why||'')+'">'+esc(x.text)+'</span>';};B[k+'.age']=function(){return esc(reading(r).ageText);};
  B[k+'.tag']=function(){var s=selectedRole();if(V.d.dataUnavailable||!roleProfile(r))return '';return s===r?'<span class="chip ok">'+t('Трафик здесь','Traffic here')+'</span>':s?'<span class="chip">'+t('Ждёт в резерве','Standing by')+'</span>':'<span class="chip warn">'+t('уточняется','being confirmed')+'</span>';};
  B[k+'.pick']=function(){return V.s.server_pick===true?t('Подбор лучшего сервера: вкл.','Best server pick: on'):'';};
  B[k+'.sw']=function(){var s=selectedRole();if(s===r||!roleProfile(r))return '';var ok=switchAllowed(r)&&!MANUAL_SWITCH_PENDING,sp=speedPauseNow();return '<button class="btn sm" data-act="switch" data-role="'+r+'"'+(ok?'':' aria-disabled="true"')+(sp?' title="'+esc(t('Идёт тест скорости: переключение после его окончания','A speed test is running: switching after it ends'))+'"':'')+'>'+t('Переключить сюда','Switch here')+'</button>';};
  B[k+'.active']=function(){return selectedRole()===r&&!V.d.dataUnavailable?'ch active':'ch';};
  B[k+'.srv']=function(){return selectedRole()===r&&!V.d.dataUnavailable?'card srv active':'card srv';};
});
function paintLive(){
  if(!HV.root)return;V=snap();
  $$('[data-b]',HV.root).forEach(function(el){var f=B[el.dataset.b];if(f){var v;try{v=f();}catch(e){v=esc(NODATA());}if(el.innerHTML!==v)el.innerHTML=v;}});
  $$('[data-b-class]',HV.root).forEach(function(el){var f=B[el.dataset.bClass];if(f){var v=f();if(el.className!==v)el.className=v;}});
  $$('[data-lamp]',HV.root).forEach(function(el){var f=LAMP[el.dataset.lamp];if(!f)return;var c;try{c=f();}catch(e){c='n';}['g','y','r','n'].forEach(function(k){el.classList.toggle(k,k===c);});el.setAttribute('role','img');var word={g:t('зелёный','green'),y:t('жёлтый','yellow'),r:t('красный','red'),n:t('серый','grey')}[c];var tip='';if(el.dataset.lamp==='ov'){try{var o=overall();word+=' — '+o.title;tip=o.title+(o.sub?' · '+o.sub:'');}catch(e){}}if(el.dataset.lamp==='auto'){try{var ai=autoIndicator(),dt=autoDetail();word+=' — '+ai.text;tip=ai.text+(dt?' · '+dt:'');}catch(e){}}if(el.dataset.hl){word=el.dataset.hl+': '+word;if(tip)el.setAttribute('title',tip);}el.setAttribute('aria-label',word);});
  var on=autoEnabled(V.light),busy=V.op==='starting'||V.op==='stopping'||V.op==='unconfirmed'||V.control.paused;
  var sig;try{sig=autoIndicator().lamp;}catch(e){sig='n';}  // owner rule 07.11.2026 (two indicators): the Auto track is the AUTO INDICATOR, not the internet light
  $$('[data-auto-switch]',HV.root).forEach(function(el){el.setAttribute('aria-checked',String(!!on));el.setAttribute('data-sig',sig);el.classList.toggle('busy',!!busy);el.setAttribute('aria-busy',busy?'true':'false');});
  var spBusy=!!(HV.speedRun||HV.busy.speed||speedPauseNow());
  $$('[data-act="speed"]',HV.root).forEach(function(el){if(spBusy){el.setAttribute('aria-disabled','true');el.setAttribute('title',t('Тест скорости уже идёт','A speed test is already running'));}else{el.removeAttribute('aria-disabled');el.removeAttribute('title');}});
  $$('.prog i[data-pct]',HV.root).forEach(function(i){if(i.style)i.style.width=Math.max(0,Math.min(100,Number(i.getAttribute('data-pct'))||0))+'%';});  // width through the CSSOM: an inline style attribute would need 'unsafe-inline'
  var probs=eventRows().filter(function(e){return evKind(e).problem&&V.now-e.time<86400;}).length;$$('[data-cnt]',HV.root).forEach(function(n){n.textContent=probs?String(probs):'';n.hidden=!probs;});
  scanFollow();
}

/* ---------------- View «Простой» (mockup A) ---------------- */
function navA(){return '<nav class="topnav" aria-label="'+t('Меню','Menu')+'">'+[['home',t('Главная','Home')],['settings',t('Настройки','Settings')]].map(function(p){return '<button data-act="go" data-p="'+p[0]+'"'+(HV.page===p[0]?' aria-current="page"':'')+'>'+p[1]+'</button>';}).join('')+'<button data-act="helpall" aria-label="'+t('Помощь','Help')+'">?<span class="hl"> '+t('Помощь','Help')+'</span></button></nav>';}
/* F1 golden grid: columns 38.2/61.8 %; status card is a golden rectangle; the traffic channel gets 61.8 %. */
function homeA(){return '<div data-b="banner"></div>'+
 '<div class="gold"><div class="gcol gl"><section class="card hero" data-g="status" aria-live="polite"><div class="hero-top"><i class="lamp xl" data-lamp="ov"></i><div class="hero-t"><h1 data-b="ov.title" tabindex="-1"></h1><p class="mute" data-b="ov.sub"></p></div></div>'+
  '<div class="hero-act">'+autoSwitchHTML()+'<span data-b="check.l"></span></div></section>'+
  '<section class="card stcard" data-g="stats"><h2>'+t('За 24 часа','Last 24 hours')+'</h2><div data-b="tiles"></div>'+
   '<details class="more" data-open="aLat"'+(HV.open.aLat?' open':'')+'><summary>'+t('График отклика за 6 часов','Response chart, 6 hours')+'</summary><div data-lazy="lat">'+(HV.open.aLat?latencyChart():'')+'</div></details>'+
   '<details class="more" data-open="aSw"'+(HV.open.aSw?' open':'')+'><summary>'+t('Время каждого переключения','Timing of each switch')+'</summary><div data-lazy="sw">'+(HV.open.aSw?switchTimesTable():'')+'</div></details>'+
   '<details class="more" data-open="aTr"'+(HV.open.aTr?' open':'')+'><summary>'+t('Трафик за месяц','Monthly traffic')+'</summary><div data-lazy="tr">'+(HV.open.aTr?trafficChart():'')+'</div></details>'+
   '<details class="more" data-open="aRec"'+(HV.open.aRec?' open':'')+'><summary>'+t('Время восстановления: медиана, P95, максимум','Recovery time: median, P95, maximum')+'</summary><div data-lazy="rec">'+(HV.open.aRec?recStatsHTML():'')+'</div></details></section>'+
  '<section class="card advcard" data-g="advisor" data-b="adv.card"></section></div>'+
 '<div class="gcol gr"><div class="chpair" data-g="channels">'+chCard('primary')+chCard('reserve')+'</div><div data-b="manual"></div>'+
  '<section class="card evcard" data-g="events"><div class="head2"><h2>'+t('События и причины','Events and reasons')+'</h2><span class="tiny mute">'+t('нажмите строку — «почему»','tap a row for "why"')+'</span></div>'+filtersHTML(HV.filters.a,'a')+'<div id="evbox" data-b="events"></div><button class="btn sm ghost" data-act="all">'+(HV.all?t('Свернуть до 5','Collapse to 5'):t('Показать 20 последних','Show last 20'))+'</button></section></div></div>'+
 '<div class="tests"><section class="card"><h3>'+t('Тест скорости','Speed test')+'</h3><div data-b="speed" class="tbox"></div><button class="btn sm" data-act="speed">'+t('Измерить скорость текущего канала','Measure current channel speed')+'</button></section>'+
 '<section class="card"><h3>'+t('Тест сбоя','Failure test')+'</h3><div data-b="fault" class="tbox"></div><button class="btn sm" data-act="fault">'+t('Запустить тест сбоя','Run failure test')+'</button></section></div>';}
function settingsA(){return '<h1 class="pg-h" tabindex="-1">'+t('Настройки','Settings')+'</h1><p class="mute small">'+t('Всё, что нужно редко. Изменения применяются только после «Сохранить». Сохранение никогда не включает Auto.','Everything you need rarely. Changes apply only after "Save". Saving never turns Auto on.')+'</p>'+
 '<h2 class="grp">'+t('Основное','Main')+'</h2>'+['pair','rules','load','tg','ui'].map(function(id){return secHTML(id);}).join('')+
 '<h2 class="grp">'+t('Для эксперта','Expert')+'</h2>'+['adv','xdet','speed','history','system'].map(function(id){return secHTML(id);}).join('')+
 '<h2 class="grp">'+t('Справка','Reference')+'</h2>'+secHTML('about')+helpSecHTML([t('Помощь, коды и обучение','Help, codes and training'),t('промпты для ИИ · коды · обучение 5 минут','AI prompts · codes · 5-minute training')],codesPanelHTML()+'<button class="btn sm" data-act="learn">🎓 '+t('Пройти обучение (5 минут)','Take the training (5 minutes)')+'</button> <button class="btn sm" data-act="advtour" data-i="0">🎓 '+t('Как работает автоподстройка (5 шагов)','How auto-adaptation works (5 steps)')+'</button>');}

/* ---------------- View «Пульт» (mockup D in F1) ---------------- */
var TABS=[['ch','⇄',function(){return t('Каналы','Channels');}],['auto','A',function(){return 'Auto';}],['srv','◎',function(){return t('Серверы','Servers');}],['log','≡',function(){return t('Журнал','Log');}],['sys','⚙',function(){return t('Система','System');}]];
function more(id,title,html){return '<details class="more" data-open="'+id+'"'+(HV.open[id]?' open':'')+'><summary>'+title+'</summary>'+html+'</details>';}
/* Golden grid of a tab: left 38.2 % and right 61.8 % columns; data-o gives the phone order (one column, by importance). */
function goldCols(l,r){return '<div class="gold"><div class="gcol gl">'+l+'</div><div class="gcol gr">'+r+'</div></div>';}
function ordered(n,h){return h.replace(/^<(\w+)/,'<$1 data-o="'+n+'"');}
function tabCh(){
  var last='<section class="card hero" data-o="2" data-g="last"><div class="hline"><i class="lamp l n" data-lamp="last"></i><h2>'+t('Последний переход','Last switch')+'</h2></div><div><div class="big" data-b="last.time"></div><div class="what" data-b="last.what"></div></div><p class="small mute" data-b="last.why"></p></section>';
  var pair=ordered(1,'<div class="chpair" data-g="channels">'+chCard('primary')+chCard('reserve')+'</div>')+'<div data-b="manual" data-o="1"></div>';
  var mo='<section class="card" data-o="3">'+more('dLat','<b>'+t('График отклика за 6 часов','Response chart, 6 hours')+'</b>','<div data-lazy="lat">'+(HV.open.dLat?latencyChart():'')+'</div>')+more('dPair','<b>'+t('Изменить пару каналов','Change the channel pair')+'</b>','<div data-secid="pair">'+secBody('pair')+'</div>')+'</section>';
  return '<div data-b="banner"></div><div class="panel-h"><h1 tabindex="-1">'+t('Каналы','Channels')+'</h1><span data-b="check"></span></div>'+goldCols(last,pair+mo);}
function tabAuto(){
  var hero='<section class="card hero" data-o="1" data-g="auto"><div class="row sb">'+autoSwitchHTML()+'</div><div><span class="chip acc" data-b="autochip"></span></div><p data-b="autoplain"></p></section>';
  var fault='<section class="card" data-o="4"><h2>'+t('Тест сбоя','Failure test')+'</h2><p class="small mute">'+t('Короткий управляемый сбой канала, который везёт трафик: проверяет, что Auto уйдёт на другой канал и вернётся.','A short controlled failure of the channel carrying traffic: checks that Auto moves to the other channel and back.')+'</p><div data-b="fault" class="tbox"></div><button class="btn sm" data-act="fault">'+t('Запустить тест сбоя','Run failure test')+'</button></section>';
  var stats='<section class="card stcard" data-o="5"><h2>'+t('Как Auto справлялся','How Auto performed')+'</h2><div data-b="tiles"></div>'+more('dSw',t('Время каждого переключения','Timing of each switch'),'<div data-lazy="sw">'+(HV.open.dSw?switchTimesTable():'')+'</div>')+more('dRec',t('Время восстановления: медиана, P95, максимум','Recovery time: median, P95, maximum'),'<div data-lazy="rec">'+(HV.open.dRec?recStatsHTML():'')+'</div>')+'</section>';
  return '<div class="panel-h"><h1 tabindex="-1">Auto</h1></div>'+goldCols(hero+fault,ordered(2,secHTML('adv',{tag:false}))+ordered(3,secHTML('rules',{tag:false}))+ordered(3,secHTML('load',{tag:false}))+ordered(3,secHTML('xdet',{tag:false}))+stats);}
function srvCard(r){var k=r==='primary'?'p':'r';return '<section class="card srv" data-b-class="'+k+'.srv" data-ch="'+r+'"><h2>'+esc(roleName(r))+' · '+esc(chName(r))+'</h2><div class="f"><label for="pk-'+r+'">'+t('Подбирать лучший сервер','Pick the best server')+'</label><input class="tg" type="checkbox" id="pk-'+r+'" data-set="pick"'+(D().pick?' checked':'')+'><div class="h">'+t('Меняет сервер только когда канал простаивает. Один выключатель на оба канала.','Changes the server only while the channel is idle. One switch for both channels.')+'</div></div>'+serversHTML(r)+'</section>';}
function tabSrv(){return '<div class="panel-h"><h1 tabindex="-1">'+t('Серверы','Servers')+'</h1></div><div class="srvpair">'+srvCard('primary')+srvCard('reserve')+'</div>'+
 '<section class="card spd"><div><h2>'+t('Тест скорости','Speed test')+'</h2><div data-b="speed" class="tbox"></div><div class="row"><button class="btn sm" data-act="speed" data-role="primary">'+t('Основной','Primary')+'</button><button class="btn sm" data-act="speed" data-role="reserve">'+t('Резерв','Reserve')+'</button></div></div><div>'+more('dSp',t('Параметры теста скорости','Speed test parameters'),'<div data-secid="speed">'+secBody('speed')+'</div>')+'</div></section>'+
 '<p class="small srvnote"><a href="'+esc(glVpnUrl()||'#')+'" target="_blank" rel="noopener noreferrer" data-act="glvpn">'+t('Добавить или удалить серверы — в панели GL.iNet → VPN ↗','Add or remove servers in the GL.iNet panel → VPN ↗')+'</a></p>';}
function tabLog(){
  var ev='<section class="card evcard" data-o="1">'+filtersHTML(HV.filters.d,'d')+'<div id="evbox" data-b="events20"></div></section>';
  var rail='<section class="card" data-o="2">'+more('dTr','<b>'+t('Трафик за месяц','Monthly traffic')+'</b>','<div data-lazy="tr">'+(HV.open.dTr?trafficChart():'')+'</div>')+more('dLive','<b>'+t('Живой журнал (эксперт)','Live log (expert)')+'</b>','<div data-b="live"></div>')+more('dDec','<b>'+t('Журнал решений: уровни и ускорение','Decision log: levels and boost')+'</b>','<p class="small"><a href="#" data-act="decisions">'+t('Открыть','Open')+'</a></p>')+'</section>';
  return '<div class="panel-h"><h1 tabindex="-1">'+t('Журнал','Log')+'</h1><button class="btn sm" data-act="incident">'+t('Отчёт для печати','Printable report')+'</button></div>'+goldCols(rail,ev);}
function tabSys(){
  var ready='<section class="card" id="ready" data-o="1"><h2>'+t('Готовность роутера','Router readiness')+'</h2><div class="rd" data-b="ready"></div><p class="row small"><i class="lamp" data-lamp="mon"></i><span data-b="mon.text"></span></p><h3 id="sensors">'+t('Датчики: WAN и ключи серверов','Sensors: WAN and server keys')+'</h3><div data-b="sensors"></div>'+monitorExtra()+'</section>';
  var help=ordered(5,helpSecHTML([t('Помощь, коды, обучение','Help, codes, training'),t('коды · промпты для ИИ','codes · AI prompts')],codesPanelHTML()+'<div class="row mt8">'+lanHelperHTML()+'<button class="btn sm" data-act="prompt" data-h="">'+t('Промпт диагностики для ИИ','AI diagnostics prompt')+'</button><button class="btn sm" data-act="learn">🎓 '+t('Обучение','Training')+'</button><button class="btn sm" data-act="advtour" data-i="0">🎓 '+t('Автоподстройка (5 шагов)','Auto-adaptation (5 steps)')+'</button></div>'));
  return '<div class="panel-h"><h1 tabindex="-1">'+t('Система','System')+'</h1></div>'+goldCols(ready,ordered(2,secHTML('tg',{tag:false}))+ordered(3,secHTML('history',{tag:false}))+ordered(4,secHTML('ui',{tag:false}))+help+ordered(6,secHTML('about',{tag:false})));}

/* ---------------- First-run wizard (mockup C, wizard only) ---------------- */
function wizard(){
  var names=[t('Роутер','Router'),t('Каналы','Channels'),t('Поведение','Behaviour'),t('Условия и запуск','Terms and start')],body='',d=D(),step=HV.step,running=step===4&&needsStop();
  if(step===1)body='<h2>'+t('1. Проверяем роутер','1. Checking the router')+'</h2><p class="mute">'+t('Модель и нужные части определяются автоматически. Выбрать модель вручную нельзя — проверки готовности обязательны.','The model and required parts are detected automatically. A model cannot be chosen by hand — readiness checks are mandatory.')+'</p><div data-b="ready"></div>';
  if(step===2){var rows=pairChoices();body='<h2>'+t('2. Выберите два канала','2. Choose two channels')+'</h2><p class="mute">'+t('Найдены VPN-клиенты, настроенные в панели GL.iNet. Основной используется всегда, резерв — при сбое.','VPN clients configured in the GL.iNet panel were found. Primary is used always, reserve on a failure.')+'</p><div class="prof">'+(rows.length?rows.map(function(p){var jp=joinedProfile(p),x=readingOf(jp,pairKeyOf(p));return '<div><i class="lamp '+x.lamp+'"></i><b class="fx1">'+esc(profileName(jp))+'</b><span class="small mute">'+(p.protocol==='wireguard'?'WireGuard':'OpenVPN')+' · '+esc(x.text)+(x.ms!=null?' · '+x.ms+' '+t('мс','ms'):'')+'</span></div>';}).join(''):'<div><i class="lamp n"></i><b class="fx1">'+t('Подходящих VPN-клиентов нет','No suitable VPN clients')+'</b></div>')+'</div><div class="mt10">'+fSel('pairP',t('Основной','Primary'),pairOptions())+fSel('pairR',t('Резерв','Reserve'),pairOptions())+'</div><p class="small"><a href="'+esc(glVpnUrl()||'#')+'" target="_blank" rel="noopener noreferrer" data-act="glvpn">'+t('Нет нужного? Добавьте профиль в GL.iNet → VPN ↗','Missing one? Add a profile in GL.iNet → VPN ↗')+'</a></p>';}
  if(step===3)body='<h2>'+t('3. Как переключать','3. How to switch')+'</h2><p class="mute">'+t('Можно оставить как есть — значения по умолчанию проверены на роутере.','You can keep the defaults — they were verified on a router.')+'</p>'+noSave(secBody('rules'))+'<hr class="sep"><h3>'+t('Нагрузка на роутер','Router load')+'</h3>'+noSave(secBody('load'))+'<hr class="sep"><h3>'+t('Telegram (необязательно)','Telegram (optional)')+'</h3>'+fTog('tg',t('Присылать отчёты о переходах','Send switch reports'))+(d.tg?fTxt('tgToken',t('Токен бота','Bot token'),(HV.inv.settings||{}).telegram_configured?'••••••••':'123456:ABC…','','password'):'')+fTxt('tgChat',t('Получатель','Recipient'),t('@channel или Chat ID','@channel or Chat ID'));
  if(step===4)body='<h2>'+t('4. Условия и запуск','4. Terms and start')+'</h2><dl class="kv mb10"><dt>'+t('Основной','Primary')+'</dt><dd>'+esc(nameOf(d.pairP))+'</dd><dt>'+t('Резерв','Reserve')+'</dt><dd>'+esc(nameOf(d.pairR))+'</dd><dt>'+t('Переключение','Switching')+'</dt><dd>'+esc(presetName())+'</dd><dt>'+t('Нагрузка','Load')+'</dt><dd>'+esc(levelText())+'</dd><dt>Telegram</dt><dd>'+(d.tg?t('вкл.','on'):t('выкл.','off'))+'</dd></dl>'+
    (running?'<p class="note warn" data-wiz-running>'+t('Auto работает — настройки меняются после Stop. Откройте интерфейс; остановить Auto можно там.','Auto is running — settings change after Stop. Open the interface; you can stop Auto there.')+'</p>':(V.terms?'<p class="note">'+t('Условия уже приняты вами (версия '+TERMS_VERSION+').','Terms already accepted by you (version '+TERMS_VERSION+').')+'</p>':'<div class="terms-box">'+termsText()+'</div>'+termsChecks('w'))+
    '<p class="tiny mute">'+t('Auto включится только по кнопке ниже. «Сохранить без запуска» оставит Auto выключенным.','Auto turns on only with the button below. "Save without starting" leaves Auto off.')+'</p>');
  var nav='<div class="nav">'+(step>1?'<button class="btn" data-act="wprev">‹ '+t('Назад','Back')+'</button>':'<span></span>')+(step<4?'<button class="btn pri" data-act="wnext">'+t('Далее','Next')+' ›</button>':running?'<span></span>':'<span class="row"><button class="btn" data-act="wsave">'+t('Сохранить без запуска','Save without starting')+'</button><button class="btn ok" data-act="wstart" id="wstart"'+(V.terms?'':' disabled')+'>'+(V.terms?t('Включить Auto','Turn Auto on'):t('Принять условия и включить Auto','Accept terms and turn Auto on'))+'</button></span>')+'</div>';
  var exit='<div class="wz-exit"><button class="btn" data-act="wskip">'+t('Пропустить — открыть интерфейс','Skip — open the interface')+'</button><p class="tiny mute">'+(onboardingComplete(HV.inv)?t('Мастер закроется без изменений.','The wizard closes without changes.'):t('Настройки останутся текущими или по умолчанию. Auto не включится, условия не будут приняты за вас.','The current or default settings stay. Auto is not started and the terms are not accepted for you.'))+'</p></div>';
  return '<div class="wiz" data-g="wizard"><div class="wz-side"><p class="wz-lead mute">'+t('Первая настройка · около 2 минут','First setup · about 2 minutes')+'</p><ol class="steps">'+names.map(function(n,i){return '<li class="'+(i+1<step?'done':i+1===step?'cur':'')+'"'+(i+1===step?' aria-current="step"':'')+'>'+(i+1)+' <span>'+n+'</span>'+(i+1<step?'<i class="vh"> — '+t('выполнен','done')+'</i>':'')+'</li>';}).join('')+'</ol>'+(onboardingComplete(HV.inv)?'<p class="small"><a href="#" data-act="wclose">'+t('Закрыть мастер без изменений','Close the wizard without changes')+'</a></p>':'')+'</div><section class="card wz-main">'+body+nav+exit+'</section></div>';
}
function noSave(h){return h.replace(/<div class="savebar">[\s\S]*?<\/div>/g,'');}
function nameOf(id){var p=((HV.inv||{}).profiles||[]).filter(function(x){return x.id===id;})[0];return p?profileName(p):'—';}
function onboardingDraft(){
  var d=D(),s=HV.inv.settings||{},n=function(v,x){return Number.isFinite(Number(v))&&v!==''&&v!=null?Number(v):x;};
  return {system:{defer_pair:false,source:d.pairP,target:d.pairR,duration:n(s.native_duration,10),session_loss:d.allowDrop===true,servers:serversRows()},
    monitor:{interval:Number(d.interval),checkpoint:n(s.checkpoint,900),probe_limit:Math.min(32,n(s.probe_limit,16)),planning_enabled:s.plan_enabled===true,live_log_limit:n(s.live_log_limit,2000),history_days:n(s.history_days,7)},
    recovery:{failures:Number(d.fails),successes:Number(d.resOk),cooldown:Number(d.cooldown),min_dwell:Number(d.dwell),primary_successes:Number(d.retOk),primary_stable:Number(d.stab),attempt_limit:Number(d.attempts),attempt_window:Number(d.window),rescue_stable:Number(d.rescue),return_policy:d.returnPolicy},
    speed:{enabled:s.speed_enabled===true,auto_new:s.speed_auto_new===true,budget_mib:n(s.speed_budget_mib,8),duration:n(s.speed_duration,5),streams:n(s.speed_streams,2),daily_mib:n(s.speed_daily_mib,128),busy_mbps:n(s.speed_busy_mbps,2)},
    telegram:d.tg||String(d.tgToken||'').trim()?{configure:true,token:String(d.tgToken||'').trim(),chat:tgChatClean(d.tgChat),enabled:d.tg===true,interval:n(s.telegram_interval,60),schedule:s.telegram_schedule==='daily'?'daily':'interval',hour:n(s.telegram_hour,7),weekly:s.telegram_weekly!==false,monthly:s.telegram_monthly!==false,items:s.telegram_items||TG_PRESETS.maximum.join(',')}:{configure:false},
    appearance:{language:locale==='en'?'en':'ru',theme:HV.theme,design:'b',router_model:'auto'}};
}
/* The exit of the wizard (owner 04.11.2026): always there, with Auto running or stopped. It only marks the first run as
   done (rpc setup_onboarding_skip); it never starts Auto or accepts the terms. A refused mark never keeps the person in. */
function wizardSkip(){
  if(HV.busy.wiz)return Promise.resolve(false);
  var leave=function(msg){go(function(){HV.wiz=false;});setHash();if(msg)toast(msg);return true;};
  if(onboardingComplete(HV.inv))return Promise.resolve(leave());
  HV.busy.wiz=true;
  return rpcCall('setup_onboarding_skip')().then(function(r){if(!(r&&r.saved===true))throw {code:r&&r.code};return reloadInventory();})
    .then(function(){snapshotDraft();return leave(t('Интерфейс открыт. Настройки остались как были; Auto не менялся.','The interface is open. Settings stayed as they were; Auto was not changed.'));})
    .catch(function(e){var c=e&&codeOk(e.code)?e.code:'SETUP-SAVE-UNCONFIRMED';return leave(t('Интерфейс открыт, но отметка не сохранилась ('+c+'): мастер может появиться снова.','The interface is open, but the mark was not saved ('+c+'): the wizard may appear again.'));})
    .finally(function(){HV.busy.wiz=false;});
}
/* The wizard opens by itself only on a really unconfigured router: never over a running Auto or an existing pair. */
function wizardNeeded(){
  if(HV.inv.error||onboardingComplete(HV.inv))return false;
  V=snap();var s=HV.inv.settings||{};
  return !(autoOn()||V.d.enabled||(s.plan_source&&s.plan_target)||(s.plan_source_tunnel&&s.plan_target_tunnel));
}
function wizardSave(start){
  if(HV.busy.wiz)return Promise.resolve(false);var d=D();
  if(!d.pairP||!d.pairR||d.pairP===d.pairR){HV.step=2;render();modal({title:t('Нужны два разных канала','Two different channels needed'),body:'<p>'+t('Основной и резерв должны быть разными VPN-клиентами.','Primary and reserve must be different VPN clients.')+'</p>'});return Promise.resolve(false);}
  HV.busy.wiz=true;var p=onboardingDraft();
  return rpcCall('setup_onboarding',['system','monitor','recovery','speed','telegram','appearance'])(p.system,p.monitor,p.recovery,p.speed,p.telegram,p.appearance).then(function(r){
    if(!(r&&r.saved===true&&r.onboarding_complete===true&&r.onboarding_version===1))throw {code:(r&&r.code)||'ONBOARDING-SAVE-FAILED'};
    var s=HV.inv.settings||{};
    if(Number(d.level)!==Number(((HV.st||{}).probe_policy||{}).level)||(d.boost===true)!==(((HV.st||{}).probe_policy||{}).boost_enabled!==false))return rpcCall('setup_probe',['level','boost'])(Number(d.level),d.level<=2?true:d.boost===true).then(function(x){if(!(x&&x.saved===true))throw {code:(x&&x.code)||'PROBE-SETTINGS-FAILED'};});
  }).then(function(){return reloadInventory();}).then(function(){snapshotDraft();return true;})
    .catch(function(e){failModal(t('Настройки не сохранены','Settings not saved'),e&&codeOk(e.code)?e.code:'ONBOARDING-SAVE-UNCONFIRMED');return false;}).finally(function(){HV.busy.wiz=false;});
}

/* ---------------- Render ---------------- */
function render(){
  if(!HV.root)return;V=snap();
  var y=window.pageYOffset||0,focus=document.activeElement&&HV.root.contains(document.activeElement)?document.activeElement.id:null;
  HV.root.className='hvx v-'+(HV.wiz?'wizard':HV.view);
  if(HV.theme==='system')HV.root.removeAttribute('data-theme');else HV.root.setAttribute('data-theme',HV.theme);
  HV.root.setAttribute('lang',locale);
  var hdr='<header class="hdr"><div class="wrap hdr-in">'+brandHTML()+headLampsHTML()+(!HV.wiz&&HV.view==='simple'?navA():'')+'<div class="hdr-tools">'+toolsHTML()+'</div></div></header>',main;
  if(HV.wiz)main='<main><div class="wrap">'+wizard()+'</div></main>';
  else if(HV.view==='console'){var probs='<span class="cnt" data-cnt hidden></span>';
    main='<div class="strip" aria-live="polite"><div class="wrap"><div class="st"><i class="lamp l" data-lamp="ov"></i><div><div class="st-t" data-b="ov.title"></div><div class="st-s" data-b="ov.sub"></div></div></div><div class="st-r">'+autoSwitchHTML()+'</div></div></div>'+
    '<div class="tabbar"><div class="wrap"><nav role="tablist" aria-label="'+t('Разделы','Sections')+'">'+TABS.map(function(x){return '<button role="tab" data-act="tab" data-t="'+x[0]+'" aria-selected="'+(HV.tab===x[0])+'"><span class="ic" aria-hidden="true">'+x[1]+'</span>'+x[2]()+(x[0]==='log'?' '+probs:'')+'</button>';}).join('')+'</nav></div></div>'+
    '<main><div class="wrap" role="tabpanel">'+({ch:tabCh,auto:tabAuto,srv:tabSrv,log:tabLog,sys:tabSys}[HV.tab])()+'</div></main>';}
  else main='<main><div class="wrap">'+(HV.page==='settings'?settingsA():homeA())+'</div></main>';
  HV.root.innerHTML=hdr+main+footerHTML()+topHTML();
  var cs=$$('.wacc',HV.root),b=$('#wstart',HV.root);if(cs.length&&b)cs.forEach(function(c){c.onchange=function(){b.disabled=!cs.every(function(x){return x.checked;});};});
  paintLive();
  if($('[data-help-list]',HV.root)&&HV.open['sec-help'])fillHelpLists();
  if(focus){var f=document.getElementById(focus);if(f)f.focus();}
  window.scrollTo(0,y);topUpdate();
}
/* Top button («Наверх»): one in every view, repainted with the page; shown after more than one screen of scrolling by the single scroll listener of boot(). */
function topHTML(){var l=t('Наверх','Back to top');return '<button type="button" class="totop" data-act="top" aria-label="'+l+'" title="'+l+'" hidden><span aria-hidden="true">↑</span></button>';}
function topUpdate(){var b=HV.root&&$('.totop',HV.root);if(b)b.hidden=!((window.pageYOffset||0)>(window.innerHeight||600))||!!$('.modal-bg',HV.root);}
function toTop(){var m=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)');window.scrollTo({top:0,behavior:m&&m.matches?'auto':'smooth'});var h=$('h1',HV.root);if(h&&h.focus)try{h.focus({preventScroll:true});}catch(e){}}
function go(fn){$$('.modal-bg',HV.root).forEach(function(m){m.remove();});fn();render();window.scrollTo(0,0);var h=$('h1',HV.root);if(h&&h.focus)try{h.focus({preventScroll:true});}catch(e){}}
function setHash(){try{history.replaceState(null,'',window.location.pathname+window.location.search+'#'+(HV.view==='console'?HV.tab:HV.page));}catch(e){}}

/* ---------------- Events ---------------- */
function onClick(e){var a=e.target.closest('[data-act]');if(!a||!HV.root.contains(a))return;var act=a.dataset.act;
  if(/^adv/.test(act)){e.preventDefault();if(a.disabled||a.getAttribute('aria-disabled')==='true')return;advClick(act,a);return;}
  if(act==='keyaccept'){keyAccept(a);return;}
  if(act==='recper'){ADV.per=a.dataset.p;$$('[data-lazy="rec"]',HV.root).forEach(function(z){if(z.innerHTML)z.innerHTML=recStatsHTML();});return;}
  if(act==='gokeys'){e.preventDefault();go(function(){if(HV.view==='console')HV.tab='sys';else{HV.page='settings';HV.open['sec-system']=true;}});setHash();return;}
  var H={
    lang:function(){locale=locale==='ru'?'en':'ru';store.set(LANG_KEY,locale);render();},
    theme:function(){HV.theme={system:'light',light:'dark',dark:'system'}[HV.theme];store.set(THEME_KEY,HV.theme);D().theme=HV.theme;render();},
    view:function(){HV.view=a.dataset.v==='console'?'console':'simple';store.set(VIEW_KEY,HV.view);go(function(){});setHash();},
    go:function(){go(function(){HV.page=a.dataset.p;});setHash();},tab:function(){go(function(){HV.tab=a.dataset.t;});setHash();},
    top:toTop,helpall:helpModal,gohelp:function(){go(function(){HV.view='simple';HV.page='settings';HV.open['sec-help']=true;});},
    goready:function(){go(function(){if(HV.view==='console')HV.tab='sys';else{HV.page='settings';HV.open['sec-system']=true;}});},
    auto:toggleAuto,switch:function(){switchTo(a.dataset.role);},check:function(){checkNow(a);},speed:function(){speedTest(a.dataset.role);},speedcancel:speedCancel,
    fault:faultTest,stopfault:stopFault,reset:resetStats,all:function(){HV.all=!HV.all;render();},
    evx:function(){var w=a.parentNode.querySelector('.ev-why');w.hidden=!w.hidden;a.setAttribute('aria-expanded',String(!w.hidden));HV.evOpen[a.dataset.k]=!w.hidden;},
    code:function(){e.stopPropagation();showCode(a.dataset.code);},codepage:function(){if(a.tagName!=='SELECT')moveCodes(a.dataset.page,a);},codeclear:function(){HV.codeQ='';HV.codePage=0;refreshCodePanels();var f=$('[data-act=codeq]',HV.root);if(f)f.focus();},filter:function(){if(a.dataset.id==='a')HV.filters.a=a.dataset.f;else HV.filters.d=a.dataset.f;render();},
    save:function(){saveSection(a.dataset.sec);},discard:function(){discardSection(a.dataset.sec);},
    defaults:function(){Object.assign(D(),{interval:10,fails:3,resOk:2,cooldown:60,dwell:60,attempts:3,window:15,retOk:2,stab:120,rescue:10,returnPolicy:'healthy_primary',preset:'balanced'});HV.dirty.rules=true;render();},
    terms:function(){modal({title:t('Условия использования','Terms of use'),body:'<div class="terms-box">'+termsText()+'</div><p class="small mute">'+(V.terms?t('Вы приняли эти условия. Версия '+TERMS_VERSION+'.','You accepted these terms. Version '+TERMS_VERSION+'.'):t('Условия ещё не приняты. Их предложат при включении Auto.','Terms are not accepted yet. They are offered when Auto is turned on.'))+'</p>'});},
    help:function(){openTopic(a.dataset.h);},prompt:function(){copyPrompt(a.dataset.h);},learn:openLearn,helpretry:function(){fillHelpLists(1);},
    tgtest:tgTest,tgshow:tgShow,manualretry:manualRetry,tgforget:tgForget,glvpn:function(){if(!glVpnUrl()){e.preventDefault();toast(t('Откройте штатную панель GL.iNet → VPN','Open the GL.iNet panel → VPN'));}},
    incident:incidentReport,decisions:decisionsModal,monrestore:restoreMonitor,
    rewiz:function(){go(function(){HV.wiz=true;HV.step=1;snapshotDraft();});},wclose:function(){go(function(){HV.wiz=false;});},
    wnext:function(){if(HV.step===2){var d=D();if(!d.pairP||!d.pairR||d.pairP===d.pairR){modal({title:t('Нужны два разных канала','Two different channels needed'),body:'<p>'+t('Основной и резерв должны быть разными VPN-клиентами.','Primary and reserve must be different VPN clients.')+'</p>'});return;}}HV.step++;render();window.scrollTo(0,0);},
    wprev:function(){HV.step--;render();},
    wskip:function(){wizardSkip();},
    wsave:function(){wizardSave(false).then(function(ok){if(ok){go(function(){HV.wiz=false;});toast(t('Настройки сохранены. Auto выключен.','Settings saved. Auto is off.'));}});},
    wstart:function(){var accepted=V.terms;if(!accepted){var cs=$$('.wacc',HV.root);if(!cs.length||!cs.every(function(c){return c.checked;}))return;}
      wizardSave(true).then(function(ok){if(!ok)return;return (accepted?Promise.resolve():acceptTerms()).then(function(){go(function(){HV.wiz=false;});return refreshNow();}).then(function(){toggleAuto();}).catch(function(){});});}
  };
  if(H[act]){if(a.tagName==='A'&&act!=='glvpn')e.preventDefault();if(a.getAttribute('aria-disabled')==='true'&&act!=='switch')return;H[act]();}
}
function onInput(e){var el=e.target;if(!HV.root.contains(el))return;
  if(advInput(el)||xdInput(el,e))return;
  if(el.matches('[data-act="codeq"]')){HV.codeQ=el.value;HV.codePage=0;refreshCodePanels();return;}
  if(el.matches('select[data-act="codepage"]')){moveCodes(el.value,el);return;}
  if(!el.dataset||!el.dataset.set)return;var k=el.dataset.set,d=D(),v=el.type==='checkbox'?el.checked:el.value;if(el.type==='number'||el.type==='range'||['level','pingInt','tgHour','diagHours'].indexOf(k)>=0)v=Number(v);
  if(k==='pick'||k==='fast'){d[k]=v;if(e.type==='change')saveImmediate(k,v);return;}
  if(k==='preset'){d.preset=v;var pv=presetValues(v);Object.keys(REC_MAP).forEach(function(x){d[x]=pv[REC_MAP[x]];});d.returnPolicy=pv.return_policy;}
  else{d[k]=v;if(REC_KEYS.indexOf(k)>=0&&k!=='interval')d.preset=presetOf(d);}
  if(k==='theme'){HV.theme=v;store.set(THEME_KEY,v);render();return;}
  if(k==='level'){$$('[data-lvl]',HV.root).forEach(function(l){l.textContent=levelText();});var bx=$('#s-boost',HV.root);if(bx){bx.disabled=v<=2;if(v<=2)bx.checked=true;}}
  var sec=secOf(el)||(el.closest('[data-secid]')||{}).dataset;if(typeof sec==='object')sec=sec&&sec.secid;
  if(!sec&&el.closest('#ready,.more'))sec=el.closest('details.more[data-open="monMore"]')?'monitor':null;
  if(el.closest('details.more[data-open="monMore"]'))sec='monitor';
  if(sec){HV.dirty[sec]=true;$$('[data-dirty="'+sec+'"]',HV.root).forEach(function(x){x.hidden=false;});var sm=$('#sec-'+sec+' summary .t>span',HV.root);if(sm&&SECTIONS[sec])sm.textContent=secSum(sec);}
  if(k==='preset'){$$('input[type=number][data-set]',HV.root).forEach(function(i){if(d[i.dataset.set]!==undefined)i.value=d[i.dataset.set];});$$('select[data-set="returnPolicy"]',HV.root).forEach(function(i){i.value=d.returnPolicy;});}
  if(k==='tgSchedule'||k==='mode'||(k==='tg'&&HV.wiz))render();
}
function onToggle(e){var d=e.target;if(!d.dataset||!d.dataset.open)return;HV.open[d.dataset.open]=d.open;
  if(d.open&&/^sec-(xdet|adv)$/.test(d.dataset.open))xdLoad();
  if(d.open){var z=$('[data-lazy]',d);if(z&&!z.innerHTML)z.innerHTML={lat:latencyChart,sw:switchTimesTable,tr:trafficChart,rec:recStatsHTML}[z.dataset.lazy]();if(d.hasAttribute('data-help-sec'))fillHelpLists();}}
function onKey(e){if((e.key==='Enter'||e.key===' ')&&e.target.matches&&e.target.matches('.ev-h,.codes-tbl tr')){e.preventDefault();e.target.click();}}

/* ---------------- Data: load, poll, refresh ---------------- */
/* Inventory replies can overtake each other: only the newest request writes the page state. */
var INV_GEN=0;
function reloadInventory(){var gen=++INV_GEN;return loadInventory(0).then(function(inv){if(gen!==INV_GEN)return HV.inv;if(inv&&!inv.error)HV.inv=inv;else HV.inv=Object.assign({},HV.inv,{error:inv&&inv.error||'RPC-INVENTORY-UNAVAILABLE'});return HV.inv;});}
/* One status request at a time. A request made while one is in flight (an action has just finished) cannot be answered by that older
   reply: it waits for it and then asks once more (one trailing refresh, shared by all such callers). */
var STATUS_BUSY=null,STATUS_TRAIL=null;
/* BH2-03: any object reply without a transport error is a router answer; 'error' (SERVICE-STOPPED, SYSTEM-001) is the monitor's state. */
function uiRouterAnswered(st){return !!st&&typeof st==='object'&&!Array.isArray(st)&&!st.rpc_error;}
function refreshNow(){
  if(STATUS_BUSY){if(!STATUS_TRAIL)STATUS_TRAIL=STATUS_BUSY.then(function(){STATUS_TRAIL=null;return refreshNow();});return STATUS_TRAIL;}
  var current=HV.st;
  STATUS_BUSY=statusCall().then(function(st){HV.st=uiNewestStatus(HV.st,st);if(uiRouterAnswered(st))HV.answerAt=Date.now()/1000;},function(){HV.st=uiStatusFailure(current,0);}).then(function(){STATUS_BUSY=null;paintLive();});
  return STATUS_BUSY;
}
/* RU is the default; an explicit ?lang=, then this browser's choice, then the router's saved appearance win. */
function pickLocale(s){var q=null;try{q=new URLSearchParams(window.location.search).get('lang');}catch(e){}var saved=store.get(LANG_KEY,null);return q==='en'||q==='ru'?q:saved==='en'||saved==='ru'?saved:s.appearance_language==='en'?'en':'ru';}
function boot(root,data){
  HV.root=root;HV.inv=data[0]||{};HV.st=data[1]||{rpc_error:'RPC-UNAVAILABLE'};HV.shownAt=Date.now()/1000;if(uiRouterAnswered(data[1]))HV.answerAt=HV.shownAt;
  locale=pickLocale(HV.inv.settings||{});
  var th=store.get(THEME_KEY,null);HV.theme=['system','light','dark'].indexOf(th)>=0?th:['light','dark'].indexOf((HV.inv.settings||{}).appearance_theme)>=0?(HV.inv.settings||{}).appearance_theme:'system';
  HV.view=store.get(VIEW_KEY,'simple')==='console'?'console':'simple';
  var h=(window.location.hash||'').slice(1);if(['ch','auto','srv','log','sys'].indexOf(h)>=0){HV.view='console';HV.tab=h;}else if(h==='settings'||h==='home'){HV.view='simple';HV.page=h;}
  var wq=null;try{wq=new URLSearchParams(window.location.search).get('wizard');}catch(e){}
  HV.wiz=wizardNeeded()||(!HV.inv.error&&wq==='1');
  HV.refresh=refreshNow;UI_STATUS_REFRESH=function(){refreshNow();};
  root.addEventListener('click',onClick);root.addEventListener('input',onInput);root.addEventListener('change',onInput);root.addEventListener('toggle',onToggle,true);root.addEventListener('keydown',onKey);
  window.addEventListener('scroll',topUpdate,{passive:true});
  snapshotDraft();render();
  poll.add(function(){if(typeof document!=='undefined'&&document.hidden)return Promise.resolve();return refreshNow();},10);
  setInterval(function(){if(!document.hidden)paintLive();},1000);
  document.addEventListener('visibilitychange',function(){if(!document.hidden){HV.shownAt=Date.now()/1000;refreshNow();}});
}
