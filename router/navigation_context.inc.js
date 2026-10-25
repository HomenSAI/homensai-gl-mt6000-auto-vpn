/* One-reload UI context only. No settings, Auto command or cross-tab storage. */
function languageViewContext(href){
  try{var values=new URL(href).searchParams.getAll('hv_view');return values.length===1&&['full','home'].indexOf(values[0])>=0?values[0]:null;}catch(error){return null;}
}
function clearLanguageViewUrl(href){var url=new URL(href);url.searchParams.delete('hv_view');return url.toString();}
function languageNavigationUrl(href,language,page){
  var url=new URL(href),key=typeof page==='string'&&/^[a-z][a-z-]{0,39}$/.test(page)?page:'overview';
  url.searchParams.set('lang',language==='ru'?'ru':'en');
  url.searchParams.set('hv_view',key==='home'?'home':'full');
  url.hash=key;
  // A stale settings-entry shortcut must not override the page being translated.
  if(key!=='settings')url.searchParams.delete('setup');
  return url.toString();
}
