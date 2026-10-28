const fs=require('fs'),vm=require('vm'),assert=require('assert');
let y=700,page='events',reset=0,timers=[];
const keys=['start','readiness','overview','channels','settings','help','learn','tests','statistics','traffic','services','events'],links=keys.map(key=>({getAttribute:()=>key})),outside={getAttribute:()=> 'events'};
const nav={contains:node=>links.includes(node)},root={querySelector:selector=>selector==='.hv-sidebar nav'?nav:null};
const context={PAGE_BACK_GOING:false,LAZY_HELP:{pendingCode:'DNS-001',pendingTopic:'dns'},document:{scrollingElement:{scrollTop:0}},pageKeyNow:()=>page,setTimeout(fn){timers.push(fn);},window:{scrollTo(x,value){y=value;}},resetPageViewport(host,key){assert.strictEqual(host,root);assert.equal(key,page);reset++;y=0;}};
vm.createContext(context);vm.runInContext(fs.readFileSync('router/sidebar_layout.inc.js','utf8'),context);
const event=(link,isTrusted=true)=>({isTrusted,target:{closest:()=>link}}),flush=()=>{const old=timers;timers=[];old.forEach(fn=>fn());};
for(const link of links){page=link.getAttribute();for(let i=0;i<2;i++){y=650;context.sidebarMenuViewport(event(link),root);assert.equal(y,0,'every menu click/reclick starts at zero: '+page);y=80;flush();assert.equal(y,0,'late factory/focus/old overview callback cannot leave menu below zero: '+page);}}
assert.equal(context.LAZY_HELP.pendingCode,null);assert.equal(context.LAZY_HELP.pendingTopic,null);
y=320;context.sidebarMenuViewport(event(outside),root);assert.equal(y,320,'non-menu error link retains its anchor');
page='events';context.sidebarMenuViewport(event(links.at(-1)),root);context.PAGE_BACK_GOING=true;context.sidebarMenuViewport(event(links[1],false),root);context.PAGE_BACK_GOING=false;y=510;flush();assert.equal(y,510,'Go back cancels a pending top callback and retains its saved position');
context.sidebarMenuViewport(event(links.at(-1)),root);context.sidebarMenuViewport(event(links.at(-1),false),root);y=460;flush();assert.equal(y,460,'programmatic code deep link cancels pending menu reset');
context.sidebarMenuViewport(event(links.at(-1)),root);page='help';y=250;flush();assert.equal(y,250,'stale callback cannot scroll another page');
delete context.resetPageViewport;page='events';y=200;context.sidebarMenuViewport(event(links.at(-1)),root);assert.equal(y,0,'direct fallback reaches actual window top');
console.log('PASS: all12 sidebar clicks/reclicks reach actual top after delayed factory work; Back/code/topic anchors and stale async navigation remain protected');
