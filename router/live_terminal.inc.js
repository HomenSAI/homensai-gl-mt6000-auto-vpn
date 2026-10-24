/* One-second pinned clock; scrollback contains real event runs, never timer spam. */
var LIVE_TERMINAL={root:null,pinned:null,body:null,clock:null,followButton:null,frame:null,inventory:null,entries:[],seen:new Set(),following:true,scrollTop:0,anchor:null,restorePending:false,timer:null,language:null};
function terminalLimit(){var n=((LIVE_TERMINAL.inventory||{}).settings||{}).live_log_limit;return Number.isInteger(n)&&n>=1&&n<=2000?n:2000;}
function terminalTime(stamp){return new Date(stamp*1000).toLocaleString(locale==='ru'?'ru-RU':'en-GB',{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'});}
function terminalLine(entry,status){
  var node=E('div',{'class':'hv-terminal-line hv-terminal-'+(entry.level||'info'),'data-log-key':entry.key},[E('time'),E('span')]);
  terminalUpdateLine(node,entry,status);return node;
}
function terminalUpdateLine(node,entry,status){
  var first=Number.isFinite(entry.firstTime)?entry.firstTime:entry.time,count=entry.count||1;
  node.children[0].setAttribute('datetime',new Date(first*1000).toISOString());
  node.children[0].textContent=terminalTime(first)+(first===entry.time?'':' — '+terminalTime(entry.time));
  var content=node.children[1];content.textContent='';
  var badge=renderJournalChannelBadge(entry);if(badge)content.appendChild(badge);
  content.appendChild(E('span',{},journalMessage(entry,status)+(count>1?' · '+bi('repeated ','повторено ')+count+' '+bi('times','раз'):'')));
  node.setAttribute('data-repeat-count',String(count));
}
function terminalSignature(entry){
  return JSON.stringify([entry.origin||'',entry.profile||'',entry.role||'',entry.state||'',entry.kind||'',entry.code||'',entry.level||'',entry.source||'',entry.target||'',entry.original_restored===true,entry.return_primary===true,entry.action_source||'']);
}
function terminalGroups(entries){
  var groups=[];
  entries.forEach(function(entry){
    if(entry.heartbeat)return;
    var signature=terminalSignature(entry),last=groups[groups.length-1];
    if(last&&last.signature===signature){last.firstTime=entry.time;last.count++;last.key=entry.key;}
    else groups.push(Object.assign({},entry,{firstTime:entry.time,count:1,signature:signature}));
  });return groups;
}
function terminalRenderRuns(){
  var state=LIVE_TERMINAL,body=state.body,groups=terminalGroups(state.entries),existing=new Map(),keep=new Set();
  Array.from(body.children).forEach(function(node){existing.set(node.getAttribute('data-log-key'),node);});
  groups.forEach(function(entry,index){
    var node=existing.get(entry.key);
    if(node)terminalUpdateLine(node,entry,state.frame);else node=terminalLine(entry,state.frame);
    keep.add(node);if(body.children[index]!==node)body.insertBefore(node,body.children[index]||null);
  });
  Array.from(body.children).forEach(function(node){if(!keep.has(node))body.removeChild(node);});
}
function terminalLaidOut(body){return body&&body.isConnected!==false&&body.clientHeight>0;}
function terminalAnchor(body){
  var top=body.scrollTop||0,measured=typeof body.getBoundingClientRect==='function',bodyTop=measured?body.getBoundingClientRect().top:0,y=0,result=null;
  Array.from(body.children).some(function(node){
    var height=node.offsetHeight||0,start=measured?node.getBoundingClientRect().top-bodyTop+top:y;y+=height;
    if(start+height>top){result={key:node.getAttribute('data-log-key'),offset:top-start};return true;}return false;
  });return result;
}
function terminalRestoreView(){
  var state=LIVE_TERMINAL,body=state.body;if(!terminalLaidOut(body))return;
  var node=state.anchor&&Array.from(body.children).find(function(n){return n.getAttribute('data-log-key')===state.anchor.key;}),top=state.scrollTop;
  if(state.following)top=0;
  else if(node){
    var start=0;if(typeof body.getBoundingClientRect==='function')start=node.getBoundingClientRect().top-body.getBoundingClientRect().top+body.scrollTop;
    else Array.from(body.children).some(function(n){if(n===node)return true;start+=n.offsetHeight||0;return false;});
    top=start+state.anchor.offset;
  }
  body.scrollTop=Math.max(0,top);state.scrollTop=body.scrollTop;state.restorePending=false;
  state.anchor=state.following?null:terminalAnchor(body);
}
function terminalAppend(entry,deferRender){
  var state=LIVE_TERMINAL,body=state.body;if(!body||entry.heartbeat)return;
  if(!deferRender){
    if(state.restorePending)terminalRestoreView();
    if(!state.following&&terminalLaidOut(body)){state.anchor=terminalAnchor(body);state.scrollTop=body.scrollTop;}
  }
  // Merge by observation time; late history stays below fresher observations.
  var index=0;while(index<state.entries.length&&state.entries[index].time>entry.time)index++;
  if(index>=terminalLimit())return;
  state.entries.splice(index,0,entry);
  while(state.entries.length>terminalLimit())state.entries.pop();
  // Retain bounded raw observations so a late intervening event can split a run
  // accurately. Reuse keyed nodes and the existing reading anchor after grouping.
  if(deferRender)return true;
  terminalRenderRuns();
  // Polling temporarily detaches the whole panel. Preserve the keyed reading
  // anchor until layout returns instead of reading a detached scrollTop of 0.
  state.restorePending=true;terminalRestoreView();return true;
}
function terminalPinned(now){
  var state=LIVE_TERMINAL,status=state.frame||{},inventory=state.inventory||{},rows=status.profiles||[],fresh=!status.rpc_error&&!status.error&&Number.isFinite(status.time)&&now-status.time>=-5&&now-status.time<=90;
  while(state.pinned.firstChild)state.pinned.removeChild(state.pinned.firstChild);
  state.clock.textContent=terminalTime(now);
  function line(kind,name,text){return E('div',{'class':'hv-terminal-status'},[E('span',{'class':'hv-check-lamp hv-check-'+kind,'aria-hidden':'true'}),E('strong',{},name),E('span',{},text)]);}
  state.pinned.appendChild(line(fresh?'green':'red','HomenS.AI monitor',fresh?'OK · '+bi('last router observation ','последнее наблюдение роутера ')+terminalTime(status.time):bi('No fresh verified data','Нет свежих проверенных данных')));
  var light=autoLightModel(status,inventory,now),running=autoWorking(light),autoKind=running?(light.key==='switching'?'yellow':'green'):light.key==='off'?'grey':'red';
  state.pinned.appendChild(line(autoKind,'Auto VPN',(running?'OK · '+bi('ON','ВКЛ'):bi('OFF or unconfirmed','ВЫКЛ или не подтверждено'))+' · '+light.title+(running?' · '+bi('Activation: ','Активация: ')+journalSourceLabel((status.auto_control||{}).activation_source):'')));
  rolePairIds(status,inventory,now).map(function(id,index){
    var p=rows.find(function(p){return p.id===id;}),use=p?channelDisplayUse(p,status,inventory):null;
    var rank=use&&use.kind==='green'?0:use&&use.kind==='yellow'?1:use&&use.kind==='red'?3:2;
    return {p:p,use:use,index:index,rank:rank};
  }).sort(function(a,b){return a.rank-b.rank||a.index-b.index;}).forEach(function(row){
    var p=row.p,use=row.use,index=row.index;
    var sample=journalCurrentLatency(p,status,now),delay=sample?sample.rtt_ms.toFixed(1)+' '+bi('ms HTTPS','мс HTTPS'):bi('No fresh delay measurement','Нет свежего замера задержки');
    state.pinned.appendChild(line(use?use.kind:'grey',index===0?bi('Primary channel','Основной канал'):bi('Reserve channel','Резервный канал'),p?use.label+' · '+endpointText(p,now)+' · '+delay:bi('Profile not confirmed','Профиль не подтверждён')));
  });
  state.followButton.textContent=state.following?bi('Newest records on top','Новые записи сверху'):bi('Return to live ↑','К текущим событиям ↑');state.followButton.setAttribute('aria-pressed',state.following?'true':'false');
}
function terminalTick(){
  var state=LIVE_TERMINAL;
  if(!state.root||!document.body.contains(state.root)){if(state.timer){clearInterval(state.timer);state.timer=null;}return;}
  var section=typeof state.root.closest==='function'?state.root.closest('[data-hv-page]'):null;if(section&&section.hidden)return;
  if(state.restorePending)terminalRestoreView();
  var now=typeof statusNow==='function'?statusNow(state.frame):Date.now()/1000;terminalPinned(now);
}
function renderLiveTerminal(status,inventory){
  var state=LIVE_TERMINAL,now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
  if(state.restorePending)terminalRestoreView();
  if(!state.following&&terminalLaidOut(state.body)){state.anchor=terminalAnchor(state.body);state.scrollTop=state.body.scrollTop;}
  state.frame=status;state.inventory=inventory||{};
  var oldCount=state.entries.length;
  state.entries=state.entries.filter(function(e){return e.time>=now-journalHistoryDays(status)*86400;}).slice(0,terminalLimit());
  if(!state.root||state.language!==locale){
    state.language=locale;state.pinned=E('div',{'class':'hv-terminal-pinned','data-terminal-pinned':'1'});state.clock=E('time');
    state.body=E('div',{'class':'hv-terminal-scrollback','role':'log','aria-label':bi('Live observations, repeated states grouped, newest first','Живые наблюдения, повторы объединены, новые сверху'),'tabindex':'0','scroll':function(){if(state.restorePending||!terminalLaidOut(state.body))return;state.following=state.body.scrollTop<28;state.scrollTop=state.body.scrollTop;state.anchor=state.following?null:terminalAnchor(state.body);}});
    state.followButton=E('button',{'type':'button','class':'cbi-button','click':function(){state.following=true;state.anchor=null;state.restorePending=true;terminalRestoreView();terminalPinned(typeof statusNow==='function'?statusNow(state.frame):Date.now()/1000);}});
    state.root=E('div',{'class':'hv-live','data-live-terminal':'1'},[
      E('div',{'class':'hv-live-head'},[state.clock,state.followButton]),
      E('div',{'class':'hv-linux-terminal'},[state.pinned,state.body]),
      E('small',{},[bi('Clock: 1 second; no timer messages. Consecutive identical events share a time range and repeat count. The buffer size is set in Monitoring and history retention (1–2000 observations). Network checks retain their configured cadence; recorded events are in ','Часы: 1 секунда, без сообщений таймера. Подряд повторяющиеся события объединены: диапазон времени и число повторов. Размер буфера задаётся в «Мониторинг и хранение истории» (1–2000 наблюдений). Интервал сетевых проверок не меняется; сохранённые события — в '),E('a',{'href':'#events'},bi('Events and errors','Событиях и ошибках'))])]);
    terminalRenderRuns();
  }
  var changed=oldCount!==state.entries.length;
  journalRows(status,null,now).forEach(function(entry){if(!state.seen.has(entry.key)){state.seen.add(entry.key);if(terminalAppend(entry,true))changed=true;}});
  if(changed)terminalRenderRuns();
  if(state.seen.size>terminalLimit()*2)state.seen=new Set(state.entries.filter(function(e){return !e.heartbeat;}).map(function(e){return e.key;}));
  terminalPinned(now);
  if(!state.timer)state.timer=setInterval(terminalTick,1000);
  state.restorePending=true;setTimeout(function(){if(document.body.contains(state.root))terminalRestoreView();},0);
  return state.root;
}
