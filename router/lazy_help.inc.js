/* Versioned optional pages. Hosts are synchronous; module acquisition starts only on navigation. */
var LAZY_HELP_NAME='__LAZY_HELP_MODULE__';
var LAZY_HELP={api:null,promise:null,failed:false,attempt:0,hosts:Object.create(null),inventory:null,pendingTopic:null,pendingCode:null};
var helpNode=null,learnNode=null,errorTable=null,ERROR_GROUP_OF={},ERROR_GROUPS=[],ERROR_TABLE_STATE={query:'',open:Object.create(null),selected:null};
var ERROR_FAMILIES=ERROR_ROWS.filter(function(row){return row[0].endsWith('*');}).map(function(row){return [row[0].slice(0,-1)].concat(row.slice(1));});
ERROR_ROWS.forEach(function(row){ERROR_GROUP_OF[row[0]]=row[1];if(!ERROR_GROUPS.some(function(g){return g[0]===row[1];}))ERROR_GROUPS.push([row[1],[row[1],row[1]]]);});
function errorFamilyOf(code){if(typeof code!=='string')return null;var row=ERROR_ROWS.find(function(r){return r[0].endsWith('*')&&code.indexOf(r[0].slice(0,-1))===0;});return row?[row[0].slice(0,-1)].concat(row.slice(1)):null;}
function persistErrorTableState(){try{sessionStorage.setItem('homensai-vpn-error-table',JSON.stringify(ERROR_TABLE_STATE));}catch(error){}}
function lazyHelpRoute(route){
  if(typeof route!=='string')return;
  if(route.indexOf('help/topic/')===0&&/^[a-zA-Z0-9_-]{1,96}$/.test(route.slice(11)))LAZY_HELP.pendingTopic=route.slice(11);
}
function lazyHelpDeepLink(key){
  if(!LAZY_HELP.api||typeof document==='undefined')return;
  if(typeof pageKeyNow==='function'&&pageKeyNow()!==key)return;
  if(key==='help'&&LAZY_HELP.pendingTopic){var topic=document.getElementById('help-'+LAZY_HELP.pendingTopic);if(topic){LAZY_HELP.pendingTopic=null;topic.open=true;try{topic.scrollIntoView({block:'start'});}catch(error){}}}
  if(key==='events'&&LAZY_HELP.pendingCode){var code=LAZY_HELP.pendingCode;LAZY_HELP.pendingCode=null;showErrorCode(code);}
}
function lazyHelpStatus(host,failed){
  while(host.firstChild)host.removeChild(host.firstChild);
  host.appendChild(E('p',{'role':failed?'alert':'status'},failed?['UI-HELP-LOAD-FAILED: ',bi('Help could not be loaded. Try again.','Не удалось загрузить справку. Повторите попытку.')]:bi('Loading…','Загрузка…')));
  if(failed)host.appendChild(E('button',{'type':'button','class':'cbi-button','click':function(){return loadLazyHelp(true).then(function(){lazyHelpDeepLink(typeof pageKeyNow==='function'?pageKeyNow():'');});}},bi('Retry','Повторить')));
}
function renderLazyPage(key,inventory){
  if(inventory)LAZY_HELP.inventory=inventory;
  if(!LAZY_HELP.hosts[key]){var host=E('div',{'data-hv-lazy-page':key});LAZY_HELP.hosts[key]={node:host,ready:false,requested:false};lazyHelpStatus(host,LAZY_HELP.failed);}
  return LAZY_HELP.hosts[key].node;
}
function renderHelp(inventory){return renderLazyPage('help',inventory);}
function renderLearn(){return renderLazyPage('learn');}
function renderErrorTable(){return renderLazyPage('events');}
function mountLazyHelp(){
  if(!LAZY_HELP.api)return;
  Object.keys(LAZY_HELP.hosts).forEach(function(key){var item=LAZY_HELP.hosts[key];if(item.ready||!item.requested)return;
    var node=key==='switches'?LAZY_HELP.api.renderSwitchPage(switchStatsModel(LAZY_HELP.switchStatus)):key==='collection'?LAZY_HELP.api.renderCollectionPage(collectionModel(LAZY_HELP.collectionStatus)):LAZY_HELP.api[{help:'renderHelp',learn:'renderLearn',events:'renderErrorTable'}[key]](LAZY_HELP.inventory);
    while(item.node.firstChild)item.node.removeChild(item.node.firstChild);item.node.appendChild(node);item.ready=true;
  });
}
function lazyHelpContext(){return {E:E,hvCss:hvCss,bi:bi,locale:locale,richText:richText,helpCommand:helpCommand,
  READINESS_GUIDES:READINESS_GUIDES,READINESS_CHECKS:READINESS_CHECKS,renderReadinessHelp:renderReadinessHelp,
  renderAutoRemedy:renderAutoRemedy,AUTO_BLOCKERS:AUTO_BLOCKERS,AUTO_REMEDIES:AUTO_REMEDIES,autoRemedyKey:autoRemedyKey,
  PLAN_BLOCKERS:PLAN_BLOCKERS,errorCodeLink:errorCodeLink,spanText:spanText,ensureJournalDictionary:ensureJournalDictionary,extraHelpTopics:HELP_TOPICS,
  // The catalogue restored its validated session state. Eager defaults must not overwrite it;
  // an explicit code clicked while loading is applied afterwards by lazyHelpDeepLink.
  installCatalogue:function(value){ERROR_ROWS=value.rows;ERROR_GROUPS=value.groups;ERROR_GROUP_OF=value.groupOf;ERROR_TABLE_STATE=value.state;persistErrorTableState=value.persist;}
};}
// Retry without eval (CSP, F-77): LuCI 23.05 caches a rejected L.require per name (luci.js classes[name]), so a retry asks
// LuCI for the same pinned file under a fresh name: '/' for '.', then percent-encoded letters the web server decodes.
function lazyHelpRetryName(attempt){
  var at=LAZY_HELP_NAME.lastIndexOf('.'),file=LAZY_HELP_NAME.slice(at+1),bits=(attempt-2)%(1<<file.length);
  return LAZY_HELP_NAME.slice(0,at)+'/'+file.replace(/./g,function(ch,i){return bits>>i&1?'%'+ch.charCodeAt(0).toString(16):ch;});
}
function lazyHelpRequire(retry){return L.require(retry?lazyHelpRetryName(LAZY_HELP.attempt):LAZY_HELP_NAME);}
function loadLazyHelp(retry){
  if(LAZY_HELP.api){mountLazyHelp();return Promise.resolve(LAZY_HELP.api);}
  if(LAZY_HELP.promise)return LAZY_HELP.promise;
  if(LAZY_HELP.failed&&!retry)return Promise.resolve(null);
  LAZY_HELP.failed=false;LAZY_HELP.attempt++;
  Object.keys(LAZY_HELP.hosts).forEach(function(key){lazyHelpStatus(LAZY_HELP.hosts[key].node,false);});
  LAZY_HELP.promise=Promise.resolve().then(function(){return lazyHelpRequire(retry);}).then(function(module){
    if(!module||typeof module.create!=='function')throw new Error('UI-HELP-LOAD-FAILED');
    LAZY_HELP.api=module.create(lazyHelpContext());mountLazyHelp();return LAZY_HELP.api;
  }).catch(function(){LAZY_HELP.api=null;LAZY_HELP.failed=true;Object.keys(LAZY_HELP.hosts).forEach(function(key){LAZY_HELP.hosts[key].ready=false;lazyHelpStatus(LAZY_HELP.hosts[key].node,true);});return null;
  }).then(function(value){LAZY_HELP.promise=null;return value;});return LAZY_HELP.promise;
}
function ensureLazyPage(key,inventory){
  if(['help','learn','events','switches','collection'].indexOf(key)<0)return Promise.resolve(null);
  renderLazyPage(key,inventory);LAZY_HELP.hosts[key].requested=true;return loadLazyHelp(false);
}
