/* Preserve reading position across synchronous redraws and page round trips. */
var pageViewportStates=Object.create(null);
function capturePageViewport(root,page){
  if(!root||!root.isConnected)return null;
  var section=root.querySelector('[data-hv-page="'+page+'"]')||root;
  var saved={page:page,x:window.scrollX||0,y:window.scrollY||window.pageYOffset||0,anchor:null,details:[]};
  var candidates=section.querySelectorAll('#hv-auto-live-chart,#hv-auto-day-chart,[data-error-code]');
  for(var i=0;i<candidates.length;i++){
    var node=candidates[i],rect=node.getBoundingClientRect();
    if(rect.bottom>0&&rect.top<(window.innerHeight||800)){
      saved.anchor={id:node.id||null,code:node.getAttribute('data-error-code'),top:rect.top};break;
    }
  }
  section.querySelectorAll('details').forEach(function(node,index){saved.details.push({index:index,key:typeof node.getAttribute==='function'?node.getAttribute('data-auto-disclosure'):null,open:node.open});});
  return saved;
}
function restorePageViewport(root,saved){
  if(!root||!root.isConnected||!saved||!Number.isFinite(saved.y))return;
  var section=root.querySelector('[data-hv-page="'+saved.page+'"]')||root;
  var details=section.querySelectorAll('details');
  (Array.isArray(saved.details)?saved.details.slice(0,1000):[]).forEach(function(item){
    if(!item)return;var node=null;
    if(typeof item.key==='string'&&/^[a-z][a-z0-9-]{0,63}$/.test(item.key))node=section.querySelector('details[data-auto-disclosure="'+item.key+'"]');
    else if(Number.isSafeInteger(item.index)&&item.index>=0)node=details[item.index];
    if(node)node.open=item.open===true;
  });
  var top=saved.y,anchor=saved.anchor,node=null;
  if(anchor&&Number.isFinite(anchor.top)){
    if(anchor.id==='hv-auto-live-chart'||anchor.id==='hv-auto-day-chart')node=section.querySelector('#'+anchor.id);
    else if(typeof anchor.code==='string'&&/^[A-Z0-9*-]{1,96}$/.test(anchor.code))node=section.querySelector('[data-error-code="'+anchor.code+'"]');
    if(node)top=(window.scrollY||window.pageYOffset||0)+node.getBoundingClientRect().top-anchor.top;
  }
  window.scrollTo({left:Number.isFinite(saved.x)?saved.x:0,top:Math.max(0,top),behavior:'instant'});
}
function rememberPageViewport(root,page){var saved=capturePageViewport(root,page);if(saved)pageViewportStates[page]=saved;return saved;}
function revisitPageViewport(root,page){restorePageViewport(root,pageViewportStates[page]||{page:page,x:0,y:0,details:[]});}
function installViewportPersistence(root,getPage){
  window.addEventListener('pagehide',function(){
    try{rememberPageViewport(root,getPage());sessionStorage.setItem('homensai-vpn-viewports',JSON.stringify({path:window.location.pathname,time:Date.now(),pages:pageViewportStates}));}catch(error){}
  });
  try{
    var navigation=performance.getEntriesByType('navigation')[0];
    if(!navigation||['reload','back_forward'].indexOf(navigation.type)<0)return;
    var old=JSON.parse(sessionStorage.getItem('homensai-vpn-viewports')||'null');
    if(!old||old.path!==window.location.pathname||Date.now()-old.time>86400000)return;
    Object.keys(old.pages||{}).slice(0,20).forEach(function(key){
      var value=old.pages[key];
      if(/^[a-z]+$/.test(key)&&value&&value.page===key&&Number.isFinite(value.y)&&value.y>=0&&value.y<10000000)pageViewportStates[key]=value;
    });
    requestAnimationFrame(function(){revisitPageViewport(root,getPage());});
  }catch(error){}
}

// An explicit shortcut entry starts at the card top; polling preserves reading position.
function resetPageViewport(root,page){
  pageViewportStates[page]={page:page,x:0,y:0,details:[]};
  revisitPageViewport(root,page);
}
