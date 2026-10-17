/* Installed identity and part-mismatch diagnosis. The router program and this page are shipped together; they can differ after
   an interrupted upgrade or a cached page. Build values are written by the page generator. */
var UI_BUILD='__UI_BUILD__',UI_AGENT='__UI_AGENT__';
function identityModel(status){
  var agent=typeof status.version==='string'&&/^[0-9A-Za-z.+~_-]{1,48}$/.test(status.version)?status.version:null;
  var pkg=typeof status.package==='string'&&/^[0-9A-Za-z.+~_-]{1,48}$/.test(status.package)?status.package:null;
  var known=!status.rpc_error&&!!agent;
  return {agent:agent,pkg:pkg,ui:UI_BUILD,uiAgent:UI_AGENT,
    pageOld:known&&agent!==UI_AGENT,
    // The package version starts with the agent version; anything else means a mixed or partial upgrade.
    packageMismatch:known&&!!pkg&&pkg.indexOf(agent)!==0};
}
function renderIdentityNotice(status){
  var model=identityModel(status);
  if(!model.pageOld&&!model.packageMismatch)return null;
  var text=model.packageMismatch
    ?bi('The installed package ('+model.pkg+') and the running program ('+model.agent+') differ. The upgrade may be unfinished: restart the monitor (Settings → Monitor service) or see Help → “The page is old, empty or says the monitor is not running”.','Установленный пакет ('+model.pkg+') и работающая программа ('+model.agent+') различаются. Возможно, обновление не завершено: перезапустите мониторинг («Настройки» → «Служба мониторинга») или откройте «Помощь» → «Страница старая, пустая или пишет, что мониторинг не работает».')
    :bi('This page belongs to version '+model.uiAgent+' but the router runs '+model.agent+'. Press Ctrl+F5 to reload the page. If it stays, sign out of LuCI and in again; then see Help.','Эта страница относится к версии '+model.uiAgent+', а на роутере работает '+model.agent+'. Нажмите Ctrl+F5, чтобы обновить страницу. Если не помогло, выйдите из LuCI и войдите снова; затем см. «Помощь».');
  return E('p',{'class':'alert-message warning','role':'status'},text);
}
function identityLine(status){
  var model=identityModel(status);
  return bi('Package ','Пакет ')+(model.pkg||'?')+' · '+bi('page ','страница ')+model.ui;
}
