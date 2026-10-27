/* Pure presentation routes. No browser mutation, RPC or readiness authority. */
var MINIMUM_MAIN_PAGES=['channels','diagnostics','events','settings','help'];
function minimumRoute(raw){
  var input=typeof raw==='string'?raw:'',key=input.replace(/^#/,'');
  var defaults={home:'summary',channels:'pair',diagnostics:'checks',events:'journal',settings:'main',help:'topics'};
  var views={home:['summary'],channels:['pair'],diagnostics:['checks','speed','readiness','technical','recovery'],events:['journal','statistics','traffic'],settings:['main','setup'],help:['topics','training','about','topic']};
  var aliases={overview:'home',start:'settings/setup',tests:'diagnostics',readiness:'diagnostics/readiness',services:'diagnostics/technical',ranking:'diagnostics/speed',statistics:'events/statistics',traffic:'events/traffic',learn:'help/training'};
  var candidate=Object.prototype.hasOwnProperty.call(aliases,key)?aliases[key]:key;
  // Decode individual path segments only. Encoded slashes never create routes.
  var segments;
  try{segments=candidate.split('/').map(function(part){return decodeURIComponent(part);});}catch(error){segments=[];}
  var page=segments[0],subview=segments[1]||defaults[page],topic=null;
  var known=Object.prototype.hasOwnProperty.call(defaults,page)&&views[page].indexOf(subview)>=0;
  if(known&&page==='help'&&subview==='topic'){
    topic=segments[2];known=segments.length===3&&typeof topic==='string'&&/^[A-Za-z0-9][A-Za-z0-9._:-]{0,95}$/.test(topic);
  }else known=known&&segments.length<=2;
  // An explicit empty trailing segment is not a valid deep link.
  if(candidate.indexOf('/')>=0&&segments.some(function(part){return !part;}))known=false;
  if(!known){page='home';subview='summary';topic=null;}
  var hash=page+(subview!==defaults[page]?'/'+subview:'')+(topic?'/'+encodeURIComponent(topic):'');
  return {page:page,subview:subview,topic:topic,hash:hash,recognized:!!known,legacy:!!known&&key!==hash};
}
function minimumRouteFromUrl(href){
  try{
    var url=new URL(href),route=minimumRoute(url.hash),setup=url.searchParams.getAll('setup');
    if((!url.hash||url.hash==='#settings')&&setup.length===1&&['telegram','system'].indexOf(setup[0])>=0)return minimumRoute('settings/setup');
    return route;
  }catch(error){return minimumRoute('');}
}
function minimumNavigationState(input,lastExpanded){
  var route=minimumRoute(input),saved=minimumRoute(typeof lastExpanded==='string'?lastExpanded:'channels');
  if(saved.page==='home')saved=minimumRoute('channels');
  return {route:route,lastExpanded:route.page==='home'?saved.hash:route.hash};
}
function minimumNavigationTransition(state,input){
  return minimumNavigationState(input,state&&state.lastExpanded);
}
function minimumAdvancedRoute(state){
  var route=minimumRoute(state&&state.lastExpanded);
  return route.page==='home'?minimumRoute('channels'):route;
}
