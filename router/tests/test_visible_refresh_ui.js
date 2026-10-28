const fs=require('fs'),vm=require('vm'),assert=require('assert');
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const selected=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
const source=fs.readFileSync(process.env.HV_VISIBLE_SOURCE||('router/files/www/luci-static/resources/view/homensai-vpn/'+selected+'.js'),'utf8');
assert(source.includes('function ensureVisiblePage(key)'), 'selected module uses actual page factories');

class Node {
  constructor(tag,attrs={},children=[]){this.tagName=String(tag).toUpperCase();this.attrs=attrs||{};this.children=[];this.parentNode=null;this.hidden=false;this.dataset={};this.nodeType=1;this.isConnected=true;this.classList={contains:name=>String(this.attrs.class||'').split(' ').includes(name)};Object.keys(this.attrs).forEach(key=>{if(key.startsWith('data-'))this.dataset[key.slice(5).replace(/-([a-z])/g,(_,c)=>c.toUpperCase())]=this.attrs[key];});[].concat(children==null?[]:children).forEach(child=>this.appendChild(child));}
  get firstChild(){return this.children[0]||null;}get nextSibling(){if(!this.parentNode)return null;return this.parentNode.children[this.parentNode.children.indexOf(this)+1]||null;}
  appendChild(node){if(node&&node.parentNode)node.parentNode.removeChild(node);this.children.push(node);if(node&&typeof node==='object')node.parentNode=this;return node;}
  removeChild(node){const i=this.children.indexOf(node);assert(i>=0);this.children.splice(i,1);if(node&&typeof node==='object')node.parentNode=null;return node;}
  insertBefore(node,before){if(!before)return this.appendChild(node);if(node.parentNode)node.parentNode.removeChild(node);const i=this.children.indexOf(before);assert(i>=0);this.children.splice(i,0,node);node.parentNode=this;return node;}
  replaceChild(node,old){this.insertBefore(node,old);this.removeChild(old);return old;}
  setAttribute(key,value){this.attrs[key]=value;}getAttribute(key){return this.attrs[key]??null;}hasAttribute(key){return Object.hasOwn(this.attrs,key);}
  contains(node){return this===node||this.children.some(child=>child instanceof Node&&child.contains(node));}
  matches(selector){if(selector[0]==='.')return this.classList.contains(selector.slice(1));if(selector[0]==='#')return this.attrs.id===selector.slice(1);const attribute=/^\[([^=\]]+)(?:="([^"]*)")?\]$/.exec(selector);if(attribute)return this.hasAttribute(attribute[1])&&(attribute[2]===undefined||this.getAttribute(attribute[1])===attribute[2]);return this.tagName===selector.toUpperCase();}
  querySelectorAll(selector){if(selector==='table')return [];return this.children.flatMap(child=>child instanceof Node?[(child.matches(selector)?child:null),...child.querySelectorAll(selector)].filter(Boolean):[]);}
  querySelector(selector){return this.querySelectorAll(selector)[0]||null;}addEventListener(){}focus(){}setSelectionRange(){}
}
const calls={},pageCalls=[],lastStatus={};
const c={console,Date,Intl,Number,JSON,Object,Array,Promise,Math,URL,Blob,Node,
  E:(...args)=>new Node(...args),bi:en=>en,tr:text=>text,text:value=>String(value??''),bytes:String,
  data:[{settings:{}},{serial:0,profiles:[]}],inventory:{settings:{}},setup:false,locale:'en',
  window:{location:{hash:'#channels',href:'http://router/admin/services/homensai-vpn'},pageYOffset:0,history:{replaceState(){}},setInterval(){},clearInterval(){},addEventListener(){}},
  document:{activeElement:new Node('outside'),body:new Node('body'),createComment:()=>new Node('comment')},
  L:{resource:path=>path,url:path=>path},PAGE_FOCUS_SELECTOR:'button,a[href],summary',PAGE_SUBTITLES:{},ADVANCED_KEYS:[],PAGE_BACK_GOING:false,
  helpNode:null,learnNode:null,errorTable:null,speedCardNode:null,monitorBlockHost:null,
  statusNow:()=>100,resolveRouterVpnUrl:()=>null,languageViewContext:()=>null,
  simpleHomeModel:s=>({showCard:!!s.__home,state:'running',title:'Auto',summary:'OK',selectedRole:'primary',targetHealth:{state:'healthy'}}),
  startLanding:()=> 'start',rememberPageViewport:()=>null,restorePageViewport(){},revisitPageViewport(){},pageBackRemember(){},pageBackPlace(){},attachStatsResets(){},restorePageControlFocus(){},updateConnectivityCheck(){},updateSidebarLayout(){},overviewToAuto(){},rememberDisclosure(){},
  recordPage:key=>pageCalls.push(key),setTimeout(){},clearTimeout(){},
  websiteSamples:()=>[],websiteQuality:()=>({}),renderChannelPing:()=>new Node('small'),websiteMs:v=>v.toFixed(1),
  refreshAttribution(){},currentCheckRole:()=>0,currentCheckRoleCell:()=>new Node('td'),
  channelCardHosts:()=>({get:()=>new Node('div'),finish(){}}),roleOrderedRows:()=>[],currentCheckOrderedRows:()=>[],
  rankEnough:()=>false,rankConfidence:String,limitTableRows:node=>node,
  lazyHelpRoute(){},ensureLazyPage:()=>Promise.resolve(),lazyHelpDeepLink(){},
  hideErrorBack(){calls.hideErrorBack=(calls.hideErrorBack||0)+1;},
};
function spy(name){c[name]=function(status){calls[name]=(calls[name]||0)+1;lastStatus[name]=status;return new Node('section',{'data-spy':name});};}
for(const name of ['renderServerSummary','renderVendorChannels','renderLatencyPanel','chart','histogram','renderCascadePath','renderSummary','renderIdentityNotice','renderDesignOverview','fillSideStatus','fillMonitorBlock','renderStartPage','readinessIntro','renderReadiness','renderEventHistory','renderTransitionAnalytics','renderVendorEvents','renderLiveLog','speedPanel','faultPanel','trafficHistoryPanel','renderMonitorInfo','renderErrorTable','renderHelp','renderLearn','lanHelperExplain','metricInfo','metric','badge'])spy(name);
c.currentDesign=()=> 'c';
c.renderAutoControl=function(status){calls.renderAutoControl=(calls.renderAutoControl||0)+1;lastStatus.renderAutoControl=status;return new Node('section',{'class':'hv-auto-control'},[new Node('button',{'class':'hv-auto-power'}),new Node('strong',{'class':'hv-auto-action'})]);};
c.renderSimpleHome=function(status,inventory,model,control){calls.renderSimpleHome=(calls.renderSimpleHome||0)+1;const power=control.querySelector('.hv-auto-power'),action=control.querySelector('.hv-auto-action');return new Node('section',{},[new Node('div',{'class':'hv-simple-power'},power),new Node('div',{'class':'hv-simple-power-unit'},action)]);};
vm.createContext(c);
const begin=source.indexOf('    var panel=E('),end=source.indexOf('\n    draw(data[1]);',begin);
assert(begin>0&&end>begin);
vm.runInContext(source.slice(begin,end).replace('visibleRenderers[key]();','recordPage(key);visibleRenderers[key]();'),c);
const draw=serial=>c.draw({serial,profiles:[]});
draw(1);draw(2);
assert.deepEqual(pageCalls,['channels','channels'],'one actual page factory per poll');
assert.equal(calls.renderServerSummary,2);assert.equal(calls.renderAutoControl,2);
for(const name of ['renderReadiness','renderLiveLog','renderEventHistory','speedPanel','renderHelp','renderLearn','chart','histogram','renderSimpleHome'])assert.equal(calls[name]||0,0,'hidden renderer is not called: '+name);
c.showPage('services');assert.equal(calls.renderLiveLog,1);assert.equal(lastStatus.renderLiveLog.serial,2,'stale page renders most recent status on opening');
c.showPage('services');assert.equal(calls.renderLiveLog,1,'already fresh page is kept');
draw(3);assert.equal(calls.renderLiveLog,2);assert.equal(calls.renderServerSummary,2,'other page remains untouched');
c.showPage('channels');assert.equal(calls.renderServerSummary,3);assert.equal(lastStatus.renderServerSummary.serial,3);
const generation=c.pageGeneration,autos=calls.renderAutoControl;c.pointerHeld=true;draw(4);
assert.equal(c.pageGeneration,generation);assert.equal(calls.renderAutoControl,autos);assert.equal(c.deferredStatus.serial,4);
c.pointerHeld=false;c.draw(c.deferredStatus);c.deferredStatus=null;assert.equal(lastStatus.renderServerSummary.serial,4);
c.showPage('tests');assert.equal(calls.speedPanel,1);assert.equal(calls.faultPanel,1);assert.equal(c.pages.ranking,undefined,'ranking is built directly inside Tests');
c.showPage('events');c.showPage('help');c.showPage('learn');c.showPage('statistics');c.showPage('traffic');c.showPage('settings');c.showPage('readiness');c.showPage('start');
assert.equal(calls.hideErrorBack,1,'leaving Events clears its previous return location immediately');
assert.equal(calls.renderReadiness,1);assert.equal(calls.chart,1);assert.equal(calls.renderHelp,1);assert.equal(calls.renderLearn,1);
c.draw({serial:5,profiles:[],__home:true});c.showPage('home');
assert.equal(calls.renderSimpleHome,1);assert(c.pages.home.contains(c.hybridControls.power.node));
c.draw({serial:6,profiles:[],__home:true});
assert.equal(calls.renderSimpleHome,2);assert(c.pages.home.contains(c.hybridControls.power.node));
c.showPage('channels');assert(c.visibleAutoCard.contains(c.hybridControls.power.node),'same actual control returns to current card');
assert.equal(c.panel.querySelectorAll('.hv-auto-power').filter(node=>node.tagName==='BUTTON').length,1,'only one actual Auto button survives page changes');
console.log('PASS: actual visible factories only, stale navigation, current data, pointer deferral, merged ranking and one shared Minimum/Overview Auto control');
