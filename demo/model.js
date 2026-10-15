(function (root) {
  'use strict';
  const CODES = {
    'WAN-001':'Внешний интернет через WAN недоступен',
    'DNS-001':'DNS не отвечает при доступном HTTPS',
    'VPN-001':'VPN-сервер не подключён',
    'VPN-003':'Туннель подключён, проверочный трафик не проходит',
    'CHECK-001':'Путь проверки не подтверждён',
    'SWITCH-001':'Нет готового резервного кандидата',
    'SWITCH-002':'После переключения интернет не восстановился',
    'SWITCH-OK':'Переключение успешно подтверждено',
    'CONFIG-001':'Автоматическое переключение выключено',
    'RECOVERY':'Основной выход устойчиво восстановился',
    'MANUAL':'Ручной выбор выхода в демонстрации'
  };
  const MONTH_FORMAT=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Berlin',year:'numeric',month:'2-digit'});
  const HOUR_FORMAT=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Berlin',hour:'2-digit',hourCycle:'h23'});
  const MONTH_CACHE=new Map();
  function monthStart(time){
    const parts=Object.fromEntries(MONTH_FORMAT.formatToParts(time).filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));
    const key=parts.year+'-'+parts.month;if(MONTH_CACHE.has(key))return MONTH_CACHE.get(key);
    const midnight=Date.UTC(Number(parts.year),Number(parts.month)-1,1),hour=Number(HOUR_FORMAT.format(midnight)),result=midnight-hour*3600000;
    MONTH_CACHE.set(key,result);if(MONTH_CACHE.size>60)MONTH_CACHE.delete(MONTH_CACHE.keys().next().value);return result;
  }
  const profileIndex=s=>[...s.id].reduce((a,ch)=>(a*31+ch.charCodeAt(0))%997,0)%9;
  const id = () => 'id_' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);
  class Model {
    constructor(saved,options={}) {
      this.time = Date.now(); this.auto=true; this.priority=true; this.wanFallback=false;
      this.autoReturn=true; this.wan=true; this.channels=[]; this.events=[]; this.history=[];
      this.monthLedger=null; this.switchLedger=null; this.outageSince=null; this.episode=null; this.failureStreak=0; this.retryDelay=30000; this.probes={}; this.retentionDays=7; this.rankGeneration=0; this.active=null; this.usingWan=false; this.failNextSwitch=false; this.lastSwitch=-Infinity; this.goodSince={}; this.bad=0; this.currentCode=null;
      if (saved && saved.version===1 && Array.isArray(saved.channels) && saved.channels.length<=20) {
        this.channels=saved.channels.map((c,i)=>({id:String(c.id),name:String(c.name).slice(0,64),description:String(c.description||'').slice(0,160),priority:Number.isInteger(c.priority)&&c.priority>0&&c.priority<=20?c.priority:i+1,color:i%5,archived:!!c.archived,servers:(c.servers||[]).slice(0,20).map(s=>({id:String(s.id),name:String(s.name).slice(0,64),protocol:s.protocol==='WireGuard'?'WireGuard':'OpenVPN',online:true,dns:true,path:true,connected:true,archived:!!s.archived}))}));
        const ids=this.channels.flatMap(c=>[c.id,...c.servers.map(s=>s.id)]);
        if (ids.some(x=>!/^id_[a-z0-9]+$/.test(x)) || new Set(ids).size!==ids.length) throw Error('Invalid saved IDs');
      } else {
        this.addChannel('Основной','Обычный трафик',false);
        this.addServer(this.channels[0].id,'Украина · сервер 1','OpenVPN',false);
        this.addServer(this.channels[0].id,'Украина · сервер 2','OpenVPN',false);
        this.addChannel('Резервный','Резерв общего трафика',false);
        this.addServer(this.channels[1].id,'Германия · сервер 1','WireGuard',false);
        this.addServer(this.channels[1].id,'Германия · сервер 2','WireGuard',false);
      }
      if(saved?.settings){for(const key of ['auto','priority','wanFallback','autoReturn'])if(typeof saved.settings[key]==='boolean')this[key]=saved.settings[key];}
      this.active=this.candidates()[0]?.s.id||null;
      if(options.seedHistory!==false){this.seed();this.seedProbes();}this.measureServers();
    }
    exportConfig(){ return {version:1,channels:this.channels,settings:{auto:this.auto,priority:this.priority,wanFallback:this.wanFallback,autoReturn:this.autoReturn}}; }
    candidates(){return this.channels.filter(c=>!c.archived).sort((a,b)=>a.priority-b.priority).flatMap(c=>c.servers.filter(s=>!s.archived).map(s=>({c,s})));}
    find(server){for(const c of this.channels){const s=c.servers.find(s=>s.id===server);if(s)return {c,s};}return null;}
    health(s){return !s.path?'CHECK-001':!s.connected?'VPN-001':!s.online?'VPN-003':!s.dns?'DNS-001':null;}
    addChannel(name,description='',record=true){if(this.channels.length>=20)throw Error('Не более 20 каналов');const c={id:id(),name:name.trim().slice(0,64)||'Новый канал',description:description.slice(0,160),priority:this.channels.length+1,color:this.channels.length%5,servers:[],archived:false};this.channels.push(c);return c;}
    addServer(channel,name,protocol,record=true){const c=this.channels.find(c=>c.id===channel&&!c.archived);if(!c)throw Error('Канал не найден');if(c.servers.length>=20)throw Error('Не более 20 серверов в канале');const s={id:id(),name:name.trim().slice(0,64)||'Новый сервер',protocol:protocol==='WireGuard'?'WireGuard':'OpenVPN',online:true,dns:true,path:true,connected:true,archived:false};c.servers.push(s);return s;}
    event(code,detail,extra={}){this.ensureSwitchLedger();const a=this.find(this.active);const e={id:id(),time:this.time,code,title:CODES[code]||code,detail,channel:a?.c.id||null,server:a?.s.id||null,channelName:a?.c.name||'Нет канала',serverName:a?.s.name||'Нет сервера',protocol:a?.s.protocol||'—',...extra};this.recordSwitch(e);this.events.unshift(e);this.events=this.events.slice(0,1000);return e;}
    switchTo(server,reason='MANUAL',duration=5){
      const from=this.find(this.active),to=this.find(server);
      if(!to||to.s.archived||to.c.archived)throw Error('Выход недоступен');
      if(this.health(to.s)||!this.wan)throw Error('Кандидат не готов');
      if(server===this.active)return null;
      const success=!this.failNextSwitch;this.failNextSwitch=false;
      const recovery=success&&this.outageSince!==null?(this.time-this.outageSince)/1000:null;
      const event=this.event(success?'SWITCH-OK':'SWITCH-002',success?(CODES[reason]||reason):'Модельная проверка после применения неуспешна; выполнен откат.',{
        kind:'switch',reason,
        from:from?{channel:from.c.id,server:from.s.id,channelName:from.c.name,serverName:from.s.name,protocol:from.s.protocol}:null,
        to:{channel:to.c.id,server:to.s.id,channelName:to.c.name,serverName:to.s.name,protocol:to.s.protocol},
        success,recovery,episode:this.episode||id()
      });
      if(success){this.active=server;this.usingWan=false;this.outageSince=null;this.episode=null;this.failureStreak=0;this.retryDelay=30000;}
      else {this.failureStreak++;this.retryDelay=Math.min(300000,30000*2**Math.min(4,this.failureStreak-1));}
      this.lastSwitch=this.time;this.bad=0;this.currentCode=null;return event;
    }
    seed(){const start=Math.min(monthStart(this.time),this.time-7*86400000);const candidates=this.candidates();if(!candidates.length)return;for(let i=0;i<Math.ceil((this.time-start)/900000);i++){let active=candidates[(i%96>=40&&i%96<45&&candidates.length>2)?2:0];const ok=i%137!==0;this.history.push({start:start+i*900000,end:Math.min(this.time,start+(i+1)*900000),channel:active.c.id,server:active.s.id,protocol:active.s.protocol,ok,known:true,latency:ok?Math.round(35+active.c.color*32+18*Math.sin(i*.7)):null,rx:ok?10000000+(i%13)*1700000:0,tx:ok?1000000+(i%7)*300000:0});if(i>0&&(i%96===40||i%96===45)&&candidates.length>2){const returning=i%96===45,from=candidates[returning?2:0],to=candidates[returning?0:2];this.events.unshift({id:id(),time:start+i*900000,code:'SWITCH-OK',title:CODES['SWITCH-OK'],detail:'Искусственный исторический пример',kind:'switch',reason:'VPN-003',channel:to.c.id,server:to.s.id,channelName:to.c.name,serverName:to.s.name,protocol:to.s.protocol,from:{channel:from.c.id,server:from.s.id,channelName:from.c.name,serverName:from.s.name,protocol:from.s.protocol},to:{channel:to.c.id,server:to.s.id,channelName:to.c.name,serverName:to.s.name,protocol:to.s.protocol},success:true,recovery:8,episode:id()});}}
    }
    scenario(kind){const a=this.find(this.active);if(kind==='restore'){this.wan=true;for(const {s} of this.candidates()){s.online=s.dns=s.path=s.connected=true;}this.event('RECOVERY','В демонстрации все проверки снова успешны');return;}
      if(kind==='apply'){this.failNextSwitch=true;return;}
      if(kind==='wan'){this.wan=false;return;}
      if(kind==='all'){for(const {s} of this.candidates())s.online=false;return;}
      if(!a)throw Error('Добавьте канал и сервер');
      if(kind==='channel'){for(const s of a.c.servers)s.online=false;}
      else if(kind==='dns')a.s.dns=false;
      else if(kind==='unknown')a.s.path=false;
      else a.s.online=false;
    }
    get wanFallback(){return this._wanFallback;}
    set wanFallback(value){
      if(typeof value!=='boolean')throw Error('WAN fallback must be boolean');
      this._wanFallback=value;
      if(!value&&this.usingWan){this.usingWan=false;this.active=null;this.bad=0;}
    }
    tick(){
      const start=this.time;this.time+=5000;
      if(!this.lastProbe||this.time-this.lastProbe>=30000)this.measureServers();
      for(const {s} of this.candidates()){
        if(this.wan&&!this.health(s)){if(this.goodSince[s.id]===undefined)this.goodSince[s.id]=this.time;}
        else delete this.goodSince[s.id];
      }
      const a=this.find(this.active);
      const code=!this.wan?'WAN-001':a?this.health(a.s):this.usingWan?null:'SWITCH-001';
      if(code&&code!=='CHECK-001'&&this.outageSince===null){this.outageSince=start;this.episode=id();}
      if(code==='CHECK-001'){this.outageSince=null;this.episode=null;}
      if(code!==this.currentCode){this.currentCode=code;if(code)this.event(code,'Результат модельных проверок. Причина за пределами модели не установлена.',{episode:this.episode});}
      const known=code!=='CHECK-001',ok=!code;
      const interval={start,end:this.time,channel:a?.c.id||null,server:a?.s.id||null,protocol:a?.s.protocol||'—',known,ok,
        latency:ok?Math.round(40+(a?.c.color||0)*30+Math.sin(this.time/5000)*10):null,
        rx:ok?Math.round((2+Math.abs(Math.sin(this.time/25000))*6)*1e6):0,tx:ok?900000:0};
      this.ensureMonthLedger();this.accountInterval(interval);this.history.push(interval);this.history=this.history.slice(-5000);
      if(!this.wan||code==='CHECK-001'){this.bad=0;return;}
      const enabled=this.auto&&this.priority;
      const ready=()=>this.candidates().find(({s})=>s.id!==this.active&&!this.health(s)&&this.time-(this.goodSince[s.id]??this.time)>=5000);
      if(this.usingWan&&enabled&&this.time-this.lastSwitch>=this.retryDelay){const candidate=ready();if(candidate){this.switchTo(candidate.s.id,'RECOVERY');return;}}
      if(code){
        this.bad++;
        if(this.bad>=3&&enabled&&this.time-this.lastSwitch>=this.retryDelay){
          const candidate=ready();
          if(candidate)this.switchTo(candidate.s.id,code);
          else if(this.wanFallback){this.event('SWITCH-001','Прямой WAN разрешён только в модели; защищённые назначения здесь не моделируются');this.active=null;this.usingWan=true;this.lastSwitch=this.time;this.currentCode=null;this.outageSince=null;this.episode=null;}
          else if(!this.events.slice(0,2).some(e=>e.code==='SWITCH-001'))this.event('SWITCH-001','Все VPN недоступны. Прямой WAN выключен.',{episode:this.episode});
        }
      } else {
        this.bad=0;
        if(this.outageSince!==null){this.event('RECOVERY','Интернет восстановился без смены выхода',{episode:this.episode,recovery:(this.time-this.outageSince)/1000});this.outageSince=null;this.episode=null;this.failureStreak=0;this.retryDelay=30000;}
        const primary=this.candidates()[0];
        if(enabled&&this.autoReturn&&primary&&primary.s.id!==this.active&&this.time-this.lastSwitch>=300000&&this.time-(this.goodSince[primary.s.id]??this.time)>=120000)this.switchTo(primary.s.id,'RECOVERY');
      }
    }
    seedProbes(){for(const {s}of this.candidates()){const index=profileIndex(s),rows=[];for(let i=0;i<672;i++){const time=this.time-7*86400000+i*900000;const passed=(i+index*11)%113!==0;const rtt=Math.round(28+index*14+12*Math.sin(i*.3+index));const down=70+index*18+15*Math.sin(i*.2+index);rows.push({bucket:Math.floor(time/900000),time,n:1,success:passed?1:0,rtt:passed?rtt:0,down:passed?down:0,up:passed?down*.22:0,unknown:0});}this.probes[s.id]={rows,last:null};}}
    measureServers(){this.lastProbe=this.time;this.rankGeneration++;for(const {s} of this.candidates()){const index=profileIndex(s),code=this.wan?this.health(s):'WAN-001',known=code!=='CHECK-001'&&code!=='WAN-001',passed=!code;const rtt=passed?Math.max(8,Math.round(28+index*14+12*Math.sin(this.time/900000+index))):null,down=passed?Math.round(70+index*18+15*Math.sin(this.time/600000+index)):null;const p=this.probes[s.id]||(this.probes[s.id]={rows:[],last:null});p.last={time:this.time,known,passed,code,rtt,down,up:down===null?null:Math.round(down*.22)};const bucket=Math.floor(this.time/900000);let row=p.rows.find(r=>r.bucket===bucket);if(!row){row={bucket,time:this.time,n:0,success:0,rtt:0,down:0,up:0,unknown:0};p.rows.push(row);}row.time=this.time;if(known){row.n++;if(passed){row.success++;row.rtt+=rtt;row.down+=down;row.up+=p.last.up;}}else row.unknown++;p.rows=p.rows.filter(r=>r.time>=this.time-this.retentionDays*86400000).slice(-3000);}}
    ranking(windowMs,current=false){return this.candidates().map(({c,s})=>{const p=this.probes[s.id],rows=(p?.rows||[]).filter(r=>r.time>=this.time-windowMs);const n=rows.reduce((a,r)=>a+r.n,0),success=rows.reduce((a,r)=>a+r.success,0);const last=p?.last;const usable=this.wan&&!this.health(s)&&!!last?.known&&last.passed&&this.time-last.time<=60000&&this.time>=last.time;const eligible=current?usable:usable&&n>0&&success>0;return {c,s,last,n,success,availability:n?100*success/n:null,errors:n-success,unknown:rows.reduce((a,r)=>a+r.unknown,0),rtt:current?last?.rtt:success?rows.reduce((a,r)=>a+r.rtt,0)/success:null,down:current?last?.down:success?rows.reduce((a,r)=>a+r.down,0)/success:null,eligible};}).sort((a,b)=>Number(b.eligible)-Number(a.eligible)||(current?0:(b.availability??-1)-(a.availability??-1))||(b.down??-1)-(a.down??-1)||(a.rtt??Infinity)-(b.rtt??Infinity));}
    applyRanking(ids,windowMs,current=false,orderChannels=false){if(!Array.isArray(ids)||new Set(ids).size!==ids.length)throw Error('Некорректный выбор');const ranking=this.ranking(windowMs,current);const selected=ranking.filter(r=>ids.includes(r.s.id));if(selected.length!==ids.length||selected.some(r=>!r.eligible))throw Error('Выберите только проверенные доступные серверы');for(const c of this.channels){const sorted=selected.filter(r=>r.c.id===c.id).map(r=>r.s);const rest=c.servers.filter(s=>!sorted.includes(s));c.servers=[...sorted,...rest];}if(orderChannels){const ids=[...new Set(selected.map(r=>r.c.id))];const rest=this.channels.filter(c=>!c.archived&&!ids.includes(c.id)).sort((a,b)=>a.priority-b.priority);[...ids.map(id=>this.channels.find(c=>c.id===id)),...rest].forEach((c,i)=>c.priority=i+1);}return selected.length;}
    ensureSwitchLedger(){
      if(this.switchLedger!==null)return;
      this.switchLedger=new Map();for(const event of this.events)this.recordSwitch(event);
    }
    recordSwitch(event){
      if(event.kind!=='switch')return;
      const row=this.switchLedger.get(event.time)||{time:event.time,total:0,success:0,intra:0,cross:0,protocol:0,recoveryN:0,recoverySum:0,recoveryMax:0};
      row.total++;if(event.success)row.success++;
      if(event.from){if(event.from.channel===event.to.channel)row.intra++;else row.cross++;if(event.from.protocol!==event.to.protocol)row.protocol++;}
      if(event.success&&Number.isFinite(event.recovery)){row.recoveryN++;row.recoverySum+=event.recovery;row.recoveryMax=Math.max(row.recoveryMax,event.recovery);}
      this.switchLedger.set(event.time,row);
      for(const time of this.switchLedger.keys())if(time<this.time-8*86400000)this.switchLedger.delete(time);
    }
    ensureMonthLedger(){
      if(this.monthLedger!==null)return;
      this.monthLedger={};for(const interval of this.history)this.accountInterval(interval);
    }
    accountInterval(interval){
      if(!Number.isFinite(interval.start)||!Number.isFinite(interval.end)||interval.end<=interval.start)return;
      let cursor=interval.start;
      while(cursor<interval.end){
        if(!this.monthBounds||cursor<this.monthBounds.start||cursor>=this.monthBounds.end){const start=monthStart(cursor);this.monthBounds={start,end:monthStart(start+40*86400000)};}
        const key=this.monthBounds.start,end=Math.min(interval.end,this.monthBounds.end);
        const record=this.monthLedger[key]||(this.monthLedger[key]={rx:0,tx:0,coverage:0});
        const ms=end-cursor,ratio=ms/(interval.end-interval.start);
        if(interval.known){record.coverage+=ms;if(interval.channel){record.rx+=interval.rx*ratio;record.tx+=interval.tx*ratio;}}
        cursor=end;
      }
      const keys=Object.keys(this.monthLedger).sort((a,b)=>Number(a)-Number(b));
      while(keys.length>18)delete this.monthLedger[keys.shift()];
    }
    monthly(){
      this.ensureMonthLedger();const start=monthStart(this.time),record=this.monthLedger[start]||{rx:0,tx:0,coverage:0};
      return {start,rx:record.rx,tx:record.tx,coverage:record.coverage,expected:this.time-start,complete:record.coverage>=this.time-start};
    }
    metrics(windowMs){const cutoff=this.time-windowMs;const rows=this.history.filter(h=>h.end>cutoff);let known=0,good=0,unknown=0,down=0;const channels={};for(const h of rows){const ms=h.end-Math.max(h.start,cutoff);if(h.known){known+=ms;if(h.ok)good+=ms;else down+=ms;}else unknown+=ms;if(h.channel){const c=channels[h.channel]||(channels[h.channel]={ms:0,rx:0,tx:0});c.ms+=ms;const ratio=ms/(h.end-h.start);c.rx+=h.rx*ratio;c.tx+=h.tx*ratio;}}
      this.ensureSwitchLedger();let total=0,success=0,intra=0,cross=0,protocol=0,recoveryN=0,recoverySum=0,recoveryMax=0;
      for(const item of this.switchLedger.values())if(item.time>=cutoff){total+=item.total;success+=item.success;intra+=item.intra;cross+=item.cross;protocol+=item.protocol;recoveryN+=item.recoveryN;recoverySum+=item.recoverySum;recoveryMax=Math.max(recoveryMax,item.recoveryMax);}
      return {rows,known,good,unknown,down,channels,coverage:known+unknown,availability:known?100*good/known:null,switches:total,intra,cross,protocol,efficiency:total?100*success/total:null,average:recoveryN?recoverySum/recoveryN:null,max:recoveryN?recoveryMax:null};}

  }
  const api={Model,CODES,monthStart};if(typeof module!=='undefined'&&module.exports)module.exports=api;root.Alta=api;
})(typeof window==='undefined'?globalThis:window);
