/* Measured switch timing from saved events: first failed check, switch start/end, return start/end. Missing pieces stay null. */
function spanText(s){
  if(!Number.isFinite(s)||s<0)return '—';s=Math.round(s);
  var h=Math.floor(s/3600),m=Math.floor(s%3600/60),r=s%60,u=function(n,en,ru){return n+bi(' '+en,' '+ru);};
  return h?u(h,'h','ч')+(m?' '+u(m,'min','мин'):''):m?u(m,'min','мин')+(r?' '+u(r,'s','с'):''):u(r,'s','с');
}
function switchKind(r){
  if(r.action_source==='manual'||/^OPERATOR-(MANUAL|RETURN)$/.test(r.code||''))return 'manual';
  return r.action_source==='test'?'test':r.action_source==='automatic'||/^(SOURCE-FAILED|PRIMARY-STABLY-RECOVERED|RESERVE-FAILED)/.test(r.code||'')?'auto':'unknown';
}
function switchTimeline(records){
  var list=(records||[]).slice().sort(function(a,b){var o={failures:0,monitor:1,controller:2};function n(r){var m=/:(\d+)$/.exec(r.key||'');return m?+m[1]:0;}
    return a.time-b.time||(o[a.origin]||0)-(o[b.origin]||0)||n(a)-n(b);});
  var episodes=[],cur=null,fails={},ups={},WEEK=7*86400;
  list.forEach(function(r){delete r.timing;});
  function d(a,b){var v=b-a;return Number.isFinite(v)&&v>=0&&v<=WEEK?v:null;}
  function note(r,text){if(text)r.timing=r.timing?r.timing+' · '+text:text;}
  function open(r,props){cur=Object.assign({key:r.key,source:r.source,target:r.target,kind:switchKind(r),failure:null,start:null,reserve:null,returnStart:null,back:null,rolledBack:null,recovery:null,down:null,returnKind:null},props);episodes.push(cur);return cur;}
  list.forEach(function(r){
    var failed=r.state==='FAILURE'||r.kind==='FAILURE',up=r.state==='RECOVERY'||r.kind==='RECOVERY';
    if(failed&&r.profile){if(!fails[r.profile])fails[r.profile]=r;return;}
    if(up&&r.profile){
      var down=Number.isFinite(r.outage_seconds)&&r.outage_seconds>=0?r.outage_seconds:null;delete fails[r.profile];ups[r.profile]=r;
      if(down!==null)note(r,(r.role==='source'?bi('primary channel was down ','основной канал не работал '):r.role==='target'?bi('reserve channel was down ','резервный канал не работал '):bi('channel was down ','канал не работал '))+spanText(down));
      if(cur&&cur.source===r.profile&&cur.reserve!==null&&cur.back===null&&cur.recovery===null){cur.recovery=r.time;cur.down=down;}
      return;
    }
    var t=savedTransition(r),s=r.state,dir=null,done=false;
    if(t.present){if(t.changed&&!t.reapply&&!t.unchanged&&t.outcome!=='refused'&&!t.invalid){dir=t.to;done=t.completed&&(t.outcome==='committed'||t.outcome==='restored');}}
    else{dir=['APPLYING','WAIT-CLIENT','COMMITTED','STOPPED-ON-RESERVE'].indexOf(s)>=0?'target':['RESTORING','ROLLED-BACK'].indexOf(s)>=0||r.return_primary?'source':null;done=s==='COMMITTED'||s==='ROLLED-BACK'||r.return_primary;}
    if(!dir)return;
    var starting=!done&&(s==='APPLYING'||s==='RESTORING');
    if(dir==='target'&&starting){
      if(cur&&cur.start!==null&&cur.reserve===null&&cur.rolledBack===null)return;
      var f=r.source&&fails[r.source];if(f&&d(f.time,r.time)===null)f=null;
      open(r,{start:r.time,failure:f?f.time:null});
      if(f)note(r,bi('failure confirmed ','сбой подтверждён за ')+spanText(r.time-f.time)+bi(' after the first failed check',' после первой неудачной проверки'));
    }else if(dir==='target'&&done){
      if(cur&&cur.reserve===null&&cur.rolledBack===null&&cur.returnStart===null&&cur.back===null){cur.reserve=r.time;
        if(cur.start!==null)note(r,bi('switch took ','переключение ')+spanText(r.time-cur.start)+bi(' (from switch start)',' (с начала перехода)'));
        if(cur.failure!==null)note(r,bi('from the first failed check ','от первой неудачной проверки ')+spanText(r.time-cur.failure));
      }else if(!cur||cur.back!==null||cur.rolledBack!==null)open(r,{reserve:r.time});
    }else if(dir==='source'&&starting){
      if(cur&&cur.reserve!==null&&cur.returnStart===null&&cur.back===null){cur.returnStart=r.time;cur.returnKind=switchKind(r);
        note(r,bi('on the reserve for ','на резерве ')+spanText(r.time-cur.reserve));
        var u=cur.source&&ups[cur.source];if(u&&u.time>=cur.reserve&&u.time<=r.time)note(r,bi('primary working again for ','основной снова работает ')+spanText(r.time-u.time));
      }else if(!cur||cur.back!==null||cur.rolledBack!==null)open(r,{returnStart:r.time,returnKind:switchKind(r)});
    }else if(dir==='source'&&done){
      if(cur&&cur.start!==null&&cur.reserve===null&&cur.rolledBack===null){cur.rolledBack=r.time;note(r,bi('attempt ended without a switch after ','попытка завершилась без переключения через ')+spanText(r.time-cur.start));}
      else if(cur&&(cur.reserve!==null||cur.returnStart!==null)&&cur.back===null){cur.back=r.time;if(!cur.returnKind)cur.returnKind=switchKind(r);
        if(cur.returnStart!==null)note(r,bi('return took ','возврат ')+spanText(r.time-cur.returnStart)+bi(' (from return start)',' (с начала возврата)'));
        if(cur.reserve!==null)note(r,bi('reserve used for ','на резерве ')+spanText(r.time-cur.reserve));
        if(cur.failure!==null)note(r,bi('whole episode ','весь эпизод ')+spanText(r.time-cur.failure)+bi(' from the first failed check',' от первой неудачной проверки'));
      }else if(!cur||cur.back!==null||cur.rolledBack!==null)open(r,{back:r.time,returnKind:switchKind(r)});
    }
  });
  episodes.forEach(function(e){
    e.detect=d(e.failure,e.start);e.switching=d(e.start,e.reserve);e.total=d(e.failure,e.reserve);e.onReserve=d(e.reserve,e.returnStart);e.returning=d(e.returnStart,e.back);
    e.time=[e.failure,e.start,e.reserve,e.returnStart,e.back].find(Number.isFinite);
  });
  return episodes;
}
function switchStatsModel(status){
  status=status||{};var now=typeof statusNow==='function'?statusNow(status):Date.now()/1000;
  return {now:now,episodes:switchTimeline(journalRows(status,null,now)),timing:status.switch_timing&&typeof status.switch_timing==='object'?status.switch_timing:null,history:!!(status.native_history&&Array.isArray(status.native_history.events))};
}
function renderSwitchStats(status){
  LAZY_HELP.switchStatus=status;var host=renderLazyPage('switches'),item=LAZY_HELP.hosts.switches;
  if(LAZY_HELP.api&&item.requested){while(host.firstChild)host.removeChild(host.firstChild);host.appendChild(LAZY_HELP.api.renderSwitchPage(switchStatsModel(status)));item.ready=true;}
  return host;
}
