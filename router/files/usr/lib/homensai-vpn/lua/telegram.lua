-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- telegram.lua: Telegram reports on Lua (port of telegram_report.py, report_calendar.py, telegram_items.py and
-- telegram_state.py, owner plan item 7). Same message text, same schedule keys, same state file
-- (PERSIST/telegram-state.json + backup, checksummed envelope), same codes. Credentials never appear in a
-- reply, a status field, a log line or a command line: the bot URL goes to curl in a 0600 config file (-K).
--   format_report/format_period/delta_lines/prepare/limited_text  the text and the calendar (pure functions)
--   deliver(d, status, saved, now)  one delivery round (the monitor runs it in a child: `telegram.lua deliver`)
--   send_test / retry_unknown        rpc telegram_test / telegram_retry
-- Local time is the process TZ (monitor_io.TZ, CET-1CEST,M3.5.0,M10.5.0/3, set like agent.py does), so os.date
-- and os.time (mktime with isdst=-1) give Python's datetime.fromtimestamp/time.mktime values.
-- d (deps): runtime, persist, read/write/remove/size/is_link (speed_pause deps), wall(), sleep(s), config()->table,
-- lock(fn, directory) (blocking control lock of a directory), send(config, text) (raises a delivery error),
-- sha256(text), uuid(), allow(key, interval, now).
if arg and arg[0] and string.find(arg[0],'telegram%.lua$') then package.path='/usr/lib/homensai-vpn/lua/?.lua;'..package.path end
local canon=require('canon')

local M={}
M.ITEMS={'servers','events','traffic','delta','controller','controller_events','controller_totals','gaps'}
M.CURL='/usr/bin/curl'
M.TEST_TEXT='HomenSAI Auto VPN: delivery test. This is not router measurement data.'
local NULL=canon.null

local function is_dict(v) return canon.is_object(v) end
local function is_list(v) return canon.is_array(v) or (type(v)=='table' and v~=NULL and not canon.is_float(v) and not canon.is_object(v)) end
local function num(v) return canon.number(v) end
local function finite(v) local n=num(v);return n~=nil and n==n and n~=math.huge and n~=-math.huge end
local function truthy(v)
  if v==nil or v==NULL or v==false or v=='' or v==0 then return false end
  if canon.is_float(v) then return v.value~=0 end
  if type(v)=='table' then return next(v)~=nil end
  return true
end
local function get(t,k,default) if type(t)=='table' and t~=NULL and t[k]~=nil then return t[k] end;return default end
local function dict(v) if is_dict(v) or (type(v)=='table' and v~=NULL and not canon.is_array(v) and not canon.is_float(v)) then return v end;return canon.object() end
local function count(t) local n=0;for _ in pairs(t) do n=n+1 end;return n end
local function codeword(v) return type(v)=='string' and #v>=1 and #v<=96 and string.find(v,'^[A-Z0-9_-]+$')~=nil end

local Delivery={}
Delivery.__tostring=function(e) return e.code end
M.Delivery=Delivery
local function delivery_error(code,uncertain,retry_after) return setmetatable({code=code,uncertain=uncertain and true or false,retry_after=retry_after or 300},Delivery) end
M.delivery_error=delivery_error
function M.is_delivery_error(e) return type(e)=='table' and getmetatable(e)==Delivery end
function M.rejection(code,retry_after)
  local known={[400]='TELEGRAM-REQUEST-REJECTED',[401]='TELEGRAM-TOKEN-REJECTED',[403]='TELEGRAM-PERMISSION',[429]='TELEGRAM-RATE-LIMIT'}
  return delivery_error(known[code] or 'TELEGRAM-DELIVERY-UNKNOWN',known[code]==nil,math.max(300,math.min(3600,retry_after or 300)))
end

------------------------------------------------------------------------------------------------------
-- Python text semantics
------------------------------------------------------------------------------------------------------
-- str(v) of a JSON value as Python prints it ('None', 'True', ints without a point, floats as repr)
local function pystr(v)
  if v==NULL then return 'None' end
  if v==true then return 'True' elseif v==false then return 'False' end
  if canon.is_float(v) then return canon.repr_float(v.value) end
  if type(v)=='number' then
    if v%1==0 and math.abs(v)<2^53 then return string.format('%d',v) end
    return canon.repr_float(v)
  end
  if type(v)=='string' then return v end
  return canon.encode(v)
end
M.pystr=pystr
local function fnum(v) local n=num(v);if n==nil then error('not a number',0) end;return n end
local function f3(x) return string.format('%.3f',x) end
local function trunc(x) return x>=0 and math.floor(x) or -math.floor(-x) end
local function pyd(x) return string.format('%d',trunc(fnum(x))) end

-- UTF-8 code points of a string (lone surrogates of canon's WTF-8 are single code points too)
local function codepoints(s)
  local out={}
  local i,n=1,#s
  while i<=n do
    local c=string.byte(s,i)
    local len=c<0x80 and 1 or (c<0xE0 and 2 or (c<0xF0 and 3 or 4))
    local cp
    if len==1 then cp=c
    elseif len==2 then cp=(c%0x20)*64+(string.byte(s,i+1) or 0)%64
    elseif len==3 then cp=((c%0x10)*64+(string.byte(s,i+1) or 0)%64)*64+(string.byte(s,i+2) or 0)%64
    else cp=(((c%0x08)*64+(string.byte(s,i+1) or 0)%64)*64+(string.byte(s,i+2) or 0)%64)*64+(string.byte(s,i+3) or 0)%64 end
    out[#out+1]={string.sub(s,i,i+len-1),cp}
    i=i+len
  end
  return out
end
-- text[:n] in code points
function M.head(text,n)
  local points=codepoints(text)
  if #points<=n then return text end
  local parts={};for i=1,n do parts[i]=points[i][1] end
  return table.concat(parts)
end
-- report_calendar.limited_text: Telegram counts UTF-16 units; keep headroom without splitting a pair.
function M.limited_text(text,units)
  units=units or 4000
  local points=codepoints(text)
  local total=0
  for _,p in ipairs(points) do total=total+(p[2]>0xFFFF and 2 or 1) end
  if total<=units then return text end
  local parts,used={},0
  for _,p in ipairs(points) do
    local size=p[2]>0xFFFF and 2 or 1
    if used+size>units-1 then break end
    parts[#parts+1]=p[1];used=used+size
  end
  return table.concat(parts)..'\226\128\166'
end

------------------------------------------------------------------------------------------------------
-- local calendar (process TZ): datetime.fromtimestamp / date arithmetic / time.mktime
------------------------------------------------------------------------------------------------------
local function seconds(t)  -- datetime.fromtimestamp rounds to microseconds first
  t=fnum(t)
  local s=math.floor(t);local us=math.floor((t-s)*1e6+0.5)
  if us>=1000000 then s=s+1 end
  return s
end
function M.strftime(fmt,t) return os.date(fmt,seconds(t)) end
local function days_from_civil(y,m,d)
  y=m<=2 and y-1 or y
  local era=math.floor(y/400);local yoe=y-era*400
  local doy=math.floor((153*(m+(m>2 and -3 or 9))+2)/5)+d-1
  local doe=yoe*365+math.floor(yoe/4)-math.floor(yoe/100)+doy
  return era*146097+doe-719468
end
local function civil_from_days(z)
  z=z+719468
  local era=math.floor(z/146097);local doe=z-era*146097
  local yoe=math.floor((doe-math.floor(doe/1460)+math.floor(doe/36524)-math.floor(doe/146096))/365)
  local y=yoe+era*400;local doy=doe-(365*yoe+math.floor(yoe/4)-math.floor(yoe/100))
  local mp=math.floor((5*doy+2)/153);local d=doy-math.floor((153*mp+2)/5)+1
  local m=mp+(mp<10 and 3 or -9)
  return {year=m<=2 and y+1 or y,month=m,day=d}
end
local function date_of(t) local x=os.date('*t',seconds(t));return {year=x.year,month=x.month,day=x.day} end
local function day_number(date) return days_from_civil(date.year,date.month,date.day) end
local function add_days(date,n) return civil_from_days(day_number(date)+n) end
local function weekday(date) return (day_number(date)+3)%7 end  -- Monday=0 (1970-01-01 was a Thursday)
local function iso(date) return string.format('%04d-%02d-%02d',date.year,date.month,date.day) end
local function at_hour(date,hour) return os.time({year=date.year,month=date.month,day=date.day,hour=hour,min=0,sec=0}) end
M.date_of,M.add_days,M.iso,M.at_hour=date_of,add_days,iso,at_hour

------------------------------------------------------------------------------------------------------
-- telegram_items
------------------------------------------------------------------------------------------------------
function M.parse_items(value)
  local all={};for _,k in ipairs(M.ITEMS) do all[k]=true end
  if value==nil or value=='' or value==NULL then return all end
  if value=='none' then return {} end
  if type(value)~='string' then return all end
  local chosen={}
  for part in string.gmatch(value..',','([^,]*),') do if all[part] then chosen[part]=true end end
  return chosen
end

------------------------------------------------------------------------------------------------------
-- telegram_report.format_report
------------------------------------------------------------------------------------------------------
local function role_name(role) return role=='source' and 'Primary channel' or (role=='target' and 'Reserve channel' or nil) end

function M.format_report(status,minutes,now,items)
  items=items or M.parse_items(nil)
  status=dict(status)
  local lines={'HomenSAI Auto VPN · monitoring',M.strftime('%d.%m.%Y %H:%M Europe/Berlin',now),'Report interval: '..pystr(minutes)..' min'}
  if items.servers then
    lines[#lines+1]='Currently connected servers:'
    local active={}
    for _,p in ipairs(get(status,'profiles',{})) do if truthy(get(p,'interface')) then active[#active+1]=p end end
    for _,p in ipairs(active) do
      local role=role_name(p.role) or 'Profile outside the confirmed pair'
      local code=truthy(p.code) and p.code or 'OK'
      local rtt=p.rtt_ms;if rtt==nil then rtt='—' end
      if p.name==nil or p.protocol==nil then error('profile fields',0) end
      lines[#lines+1]=role..' · '..pystr(p.name)..' · '..pystr(p.protocol)..' · '..pystr(code)..' · HTTPS '..pystr(rtt)..' ms'
    end
    if #active==0 then lines[#lines+1]='No connected profiles found.' end
  end
  local cutoff=now-minutes*60
  if items.events then
    local events={}
    for _,e in ipairs(get(status,'events',{})) do if fnum(get(e,'time',0))>=cutoff then events[#events+1]=e end end
    lines[#lines+1]='State changes during the interval: '..#events
    for i=math.max(1,#events-19),#events do
      local event=events[i]
      local role=role_name(event.role) or (truthy(event.profile) and 'Channel not saved in event' or 'Service')
      lines[#lines+1]=M.strftime('%H:%M:%S',event.time)..' · '..role..' · '..pystr(get(event,'profile','service'))..' · '..pystr(get(event,'code','OK'))
    end
  end
  local accounting=dict(get(status,'accounting',canon.object()))
  local month=M.strftime('%Y-%m',now)
  if items.traffic then
    local traffic=get(dict(get(accounting,'months',canon.object())),month)
    if truthy(traffic) then
      lines[#lines+1]='VPN traffic '..month..': '..f3((fnum(get(traffic,'rx',0))+fnum(get(traffic,'tx',0)))/1e9)..' GB (since monitoring started)'
    else lines[#lines+1]='Traffic: no accumulated measurements yet.' end
  end
  local native=dict(get(status,'native_failover',canon.object()))
  if items.controller then
    local state=get(native,'state','UNKNOWN')
    if not codeword(state) then state='UNKNOWN' end
    lines[#lines+1]='Native controller: '..state..' (not proof of LAN availability).'
  end
  -- An alarm is never optional: it says that automatic switching has stopped.
  local alarm=native.alarm
  if codeword(alarm) then lines[#lines+1]='ALARM: '..alarm..'. Automatic switching is stopped; see the Events page and Help.' end
  local history=dict(get(status,'native_history',canon.object()))
  if items.controller_events then
    if truthy(history.error) then lines[#lines+1]='Controller history unavailable: HISTORY-001.' end
    local native_events={}
    for _,e in ipairs(get(history,'events',{})) do if finite(get(e,'time')) and num(e.time)>=cutoff then native_events[#native_events+1]=e end end
    lines[#lines+1]='Controller events during the interval: '..#native_events
    for i=math.max(1,#native_events-9),#native_events do
      local event=native_events[i]
      local event_state=get(event,'state','UNKNOWN')
      if not codeword(event_state) then event_state='UNKNOWN' end
      local codes={}
      for _,c in ipairs(get(event,'codes',{})) do if codeword(c) then codes[#codes+1]=c end end
      lines[#lines+1]=M.strftime('%H:%M:%S',event.time)..' · '..event_state..(truthy(event.trial) and ' · trial' or '')..' · '..table.concat(codes,', ')
    end
  end
  local totals=get(dict(get(history,'months',canon.object())),month)
  if truthy(totals) and items.controller_totals then
    lines[#lines+1]='Controller '..month..', accumulated: attempts '..pystr(get(totals,'attempts',0))..'; trials passed '..pystr(get(totals,'trials_passed',0))..
      '; automatic commits '..pystr(get(totals,'committed',0))..'; rollbacks '..pystr(get(totals,'rollbacks',0))..'. This is a partial month.'
  end
  if items.gaps then
    lines[#lines+1]='Observation gaps: '..pystr(get(accounting,'gaps',0))
    lines[#lines+1]='Router-originated IPv4 checks. A failure cause is stated only when supported by evidence.'
  end
  return M.head(table.concat(lines,'\n'),4000)
end

------------------------------------------------------------------------------------------------------
-- report_calendar
------------------------------------------------------------------------------------------------------
local function enabled(value,default)
  if value==nil or value=='' or value==NULL then return default end
  return value=='1' or value==true
end
local function pyint(text)
  if type(text)=='number' then return trunc(text) end
  local n=type(text)=='string' and string.match(text,'^%s*([+-]?%d+)%s*$')
  if not n then error('invalid literal for int()',0) end
  return tonumber(n)
end
local function orv(v,default) if truthy(v) then return v end;return default end

-- prepare(options, saved, now) -> jobs, state, public
function M.prepare(options,saved,now)
  local mode=orv(options.telegram_schedule,'interval')
  if mode~='interval' and mode~='daily' then error('TELEGRAM-SCHEDULE',0) end
  local minutes=math.max(5,math.min(10080,pyint(orv(options.telegram_interval,'60'))))
  local hour=pyint(orv(options.telegram_hour,'7'))
  if not (0<=hour and hour<=23) then error('TELEGRAM-SCHEDULE',0) end
  local today=date_of(now)
  local jobs={}
  local state=canon.object();for k,v in pairs(saved) do state[k]=v end
  local starts=canon.object();for k,v in pairs(dict(get(saved,'calendar_started',canon.object()))) do starts[k]=v end
  local confirmed=dict(get(saved,'period_keys',canon.object()))
  local unknown=dict(get(saved,'uncertain',canon.object()))
  if mode=='interval' and now-fnum(get(saved,'sent',0))>=minutes*60 then
    local key='interval:'..string.format('%d',math.floor(now/(minutes*60)))
    if unknown[key]==nil then jobs[#jobs+1]={kind='interval',key=key,minutes=minutes,start=now-minutes*60,['end']=now} end
  end
  for _,row in ipairs({{'daily',mode=='daily'},{'weekly',enabled(options.telegram_weekly,true)},{'monthly',enabled(options.telegram_monthly,true)}}) do
    local kind,wanted=row[1],row[2]
    if wanted then
      if starts[kind]==nil then starts[kind]=canon.float(now) end
      local end_,due,start
      if kind=='daily' then
        end_=today;due=at_hour(end_,hour)
        if now<due then end_=add_days(end_,-1);due=at_hour(end_,hour) end
        start=add_days(end_,-1)
      elseif kind=='weekly' then
        end_=add_days(today,-weekday(today));due=at_hour(end_,hour)
        if now<due then end_=add_days(end_,-7);due=at_hour(end_,hour) end
        start=add_days(end_,-7)
      else
        end_={year=today.year,month=today.month,day=1};due=at_hour(end_,hour)
        if now<due then local prev=add_days(end_,-1);end_={year=prev.year,month=prev.month,day=1};due=at_hour(end_,hour) end
        local prev=add_days(end_,-1);start={year=prev.year,month=prev.month,day=1}
      end
      local key=kind..':'..iso(start)
      -- New schedules start at their next slot. Restarts retain starts/keys and catch up once.
      if due>=fnum(starts[kind]) and confirmed[kind]~=key and unknown[key]==nil then
        jobs[#jobs+1]={kind=kind,key=key,start=at_hour(start,0),['end']=at_hour(end_,0)}
      end
    end
  end
  state.calendar_started=starts
  return jobs,state,canon.object({schedule=mode,hour=hour,interval_minutes=minutes,
    weekly=enabled(options.telegram_weekly,true),monthly=enabled(options.telegram_monthly,true)})
end

function M.traffic_lines(accounting,start,end_,monthly)
  accounting=dict(accounting)
  local first=M.strftime('%Y-%m-%d',start)
  local last=M.strftime('%Y-%m-%d',end_-1)
  if monthly then
    local item=get(dict(get(accounting,'months',canon.object())),string.sub(first,1,7))
    if not truthy(item) then return {'No measured monthly traffic.'} end
    return {f3((fnum(get(item,'rx',0))+fnum(get(item,'tx',0)))/1e9)..' GB; partial collection, interface overhead included.'}
  end
  local amount,observed,gaps=0,0,0
  for day,value in pairs(dict(get(accounting,'days',canon.object()))) do
    if first<=day and day<=last and truthy(get(value,'observed')) then
      observed=observed+1;amount=amount+fnum(get(value,'rx',0))+fnum(get(value,'tx',0));gaps=gaps+fnum(get(value,'gaps',0))
    end
  end
  if observed==0 then return {'No daily traffic samples for this period.'} end
  local expected=day_number(date_of(end_-1))-day_number(date_of(start))+1
  return {f3(amount/1e9)..' GB; observed days '..observed..'/'..string.format('%d',expected)..'; sampling discontinuities '..pyd(gaps)..
    '. Missing data is not reconstructed.'}
end

function M.format_period(status,job,now,items)
  items=items or M.parse_items(nil)
  status=dict(status)
  local start,end_=job.start,job['end']
  local first=M.strftime('%Y-%m-%d',start);local last=M.strftime('%Y-%m-%d',end_-1)
  local accounting=dict(get(status,'accounting',canon.object()));local history=dict(get(status,'native_history',canon.object()))
  local lines={'HomenSAI Auto VPN · '..string.upper(string.sub(job.kind,1,1))..string.sub(job.kind,2)..' summary','Report id: '..job.key,
    'Period: '..first..' to '..last..' · Europe/Berlin','Generated: '..M.strftime('%Y-%m-%d %H:%M',now),
    'Scope: router-originated measurements; LAN uptime is not verified.'}
  local function extend(list) for _,line in ipairs(list) do lines[#lines+1]=line end end
  if items.traffic then
    lines[#lines+1]='WAN traffic through this router:';extend(M.traffic_lines(truthy(accounting.wan) and accounting.wan or canon.object(),start,end_,job.kind=='monthly'))
    lines[#lines+1]='VPN interface traffic:';extend(M.traffic_lines(accounting,start,end_,job.kind=='monthly'))
  end
  if items.servers then
    local profiles={}
    for identifier,profile in pairs(dict(get(accounting,'activity',canon.object()))) do
      local total={up=0,down=0,unknown=0,connections=0,failures=0}
      local dates=0
      for day,bucket in pairs(dict(get(profile,'days',canon.object()))) do
        if first<=day and day<=last then
          dates=dates+1
          for key in pairs(total) do total[key]=total[key]+fnum(get(bucket,key,0)) end
        end
      end
      if dates>0 then profiles[#profiles+1]={identifier,profile,total} end
    end
    if #profiles>0 then
      -- Python: the activity dict's order, stable under the sort; that order is the sorted ids of a loaded file
      table.sort(profiles,function(a,b) if a[3].down~=b[3].down then return a[3].down>b[3].down end;return a[1]<b[1] end)
      local sums={up=0,down=0,unknown=0}
      local ordered={};for _,row in ipairs(profiles) do ordered[#ordered+1]=row end
      table.sort(ordered,function(a,b) return a[1]<b[1] end)
      for _,row in ipairs(ordered) do for key in pairs(sums) do sums[key]=sums[key]+row[3][key] end end
      lines[#lines+1]=string.format('Monitored server-hours (sum across servers): healthy %.2f; failed %.2f; unknown %.2f.',sums.up/3600,sums.down/3600,sums.unknown/3600)
      lines[#lines+1]='Server observations · up/down/unknown hours · connections · failure episodes:'
      for i=1,math.min(10,#profiles) do
        local profile,total=profiles[i][2],profiles[i][3]
        lines[#lines+1]=pystr(get(profile,'name','server'))..' · '..string.format('%.2f/%.2f/%.2f',total.up/3600,total.down/3600,total.unknown/3600)..
          ' h · '..pyd(total.connections)..' · '..pyd(total.failures)
      end
      if #profiles>10 then lines[#lines+1]='Showing 10 of '..#profiles..' observed servers; detailed history is available in the dashboard.' end
    else lines[#lines+1]='No server activity observations for this period.' end
  end
  if items.controller_events then
    local keys={'attempts','committed','trials_passed','rollbacks','blocked_episodes','automatic_attempts','automatic_committed','server_switches','channel_switches','protocol_switches'}
    local totals={};for _,k in ipairs(keys) do totals[k]=0 end
    for day,value in pairs(dict(get(history,'days',canon.object()))) do
      if first<=day and day<=last then for _,k in ipairs(keys) do totals[k]=totals[k]+fnum(get(value,k,0)) end end
    end
    local since=history.daily_since
    if since==nil or since==NULL then lines[#lines+1]='Daily controller counters: unavailable before the accounting upgrade.'
    else
      lines[#lines+1]='Recorded controller activity: attempts '..pyd(totals.attempts)..'; commits '..pyd(totals.committed)..'; passed trials '..pyd(totals.trials_passed)..
        '; restorations/rollbacks '..pyd(totals.rollbacks)..'; blocked episodes '..pyd(totals.blocked_episodes)..'.'
      lines[#lines+1]='Automatic transitions: successful '..pyd(totals.automatic_committed)..'/'..pyd(totals.automatic_attempts)..'; server/channel/protocol kinds '..
        pyd(totals.server_switches)..'/'..pyd(totals.channel_switches)..'/'..pyd(totals.protocol_switches)..'. Kind categories are not summed with the total.'
      if fnum(since)>start then lines[#lines+1]='Controller daily/kind counters are partial: collected since '..M.strftime('%Y-%m-%d %H:%M',since)..'.' end
    end
  end
  local months=dict(get(history,'months',canon.object()))
  if items.controller_totals and job.kind=='monthly' and months[string.sub(first,1,7)]~=nil then
    local value=months[string.sub(first,1,7)]
    lines[#lines+1]='Retained monthly controller totals: attempts '..pystr(get(value,'attempts',0))..'; commits '..pystr(get(value,'committed',0))..
      '; trials '..pystr(get(value,'trials_passed',0))..'; rollbacks '..pystr(get(value,'rollbacks',0))..'.'
  end
  local events=0
  for _,event in ipairs(get(status,'events',{})) do
    if finite(get(event,'time')) and start<=num(event.time) and num(event.time)<end_ then events=events+1 end
  end
  if items.events and events>0 then lines[#lines+1]='Retained measurement state changes in period: '..events..' (bounded event history).' end
  if items.gaps then
    lines[#lines+1]='Sampling discontinuities, cumulative: '..pystr(get(accounting,'gaps',0))..'. Unknown causes and unobserved intervals remain unknown.'
    if truthy(accounting.retention) then lines[#lines+1]='History retention limits were applied; some historical observations are unavailable.' end
  end
  return M.limited_text(table.concat(lines,'\n'))
end

------------------------------------------------------------------------------------------------------
-- traffic delta since the last confirmed report
------------------------------------------------------------------------------------------------------
function M.traffic_snapshot(status,now)
  status=dict(status)
  local accounting=dict(get(status,'accounting',canon.object()))
  local function totals(data)
    local out=canon.object()
    for key,row in pairs(dict(get(dict(data),'months',canon.object()))) do out[key]=fnum(get(row,'rx',0))+fnum(get(row,'tx',0)) end
    return out
  end
  local stamp=get(status,'time',now)
  return canon.object({time=canon.is_float(stamp) and stamp or (type(stamp)=='number' and stamp%1~=0 and canon.float(stamp) or stamp),
    vpn=totals(accounting),wan=totals(truthy(accounting.wan) and accounting.wan or canon.object())})
end

function M.delta_lines(status,saved,now)
  local old=saved.snapshot
  local current=M.traffic_snapshot(status,now)
  if not is_dict(old) then return {'Traffic delta: unavailable until the first confirmed report snapshot.'} end
  local stamp=get(old,'time',now)
  local lines={'Traffic delta since last confirmed report ('..M.strftime('%Y-%m-%d %H:%M',stamp)..'):'}
  for _,row in ipairs({{'wan','WAN'},{'vpn','VPN interfaces'}}) do
    local key,label=row[1],row[2]
    local d0=date_of(stamp);local prev=add_days({year=d0.year,month=d0.month,day=1},-1)
    local threshold=string.format('%04d-%02d',prev.year,prev.month)
    local before,any={},false
    for month,value in pairs(dict(get(old,key,canon.object()))) do if month>=threshold then before[month]=fnum(value);any=true end end
    if not any or next(current[key])==nil then lines[#lines+1]=label..': no comparable counters.'
    else
      local broken=false
      for month,value in pairs(before) do if current[key][month]==nil or current[key][month]<value then broken=true end end
      if broken then lines[#lines+1]=label..': counter discontinuity; delta is unknown.'
      else
        local lowest;for month in pairs(before) do if lowest==nil or month<lowest then lowest=month end end
        local delta=0
        for month,value in pairs(current[key]) do if month>=lowest then delta=delta+value-(before[month] or 0) end end
        lines[#lines+1]=label..': '..f3(delta/1e9)..' GB (available interface counters).'
      end
    end
  end
  return lines
end

------------------------------------------------------------------------------------------------------
-- telegram_state: checksummed sender ledger with legacy migration and previous-good recovery
------------------------------------------------------------------------------------------------------
local ALLOWED={sent=true,attempt=true,calendar_started=true,period_keys=true,uncertain=true,config_fingerprint=true,last_code=true,
  snapshot=true,retry_handled=true,retry_nonce=true,retry_after=true,confirmed_at=true,confirmed_reports=true,known_failures=true,unknown_deliveries=true}
local function nonneg(v) return finite(v) and num(v)>=0 end
function M.valid(data)
  if not is_dict(data) then return false end
  for k in pairs(data) do if not ALLOWED[k] then return false end end
  for _,key in ipairs({'sent','attempt','retry_handled','retry_after','confirmed_at','confirmed_reports','known_failures','unknown_deliveries'}) do
    local v=data[key];if v==nil then v=0 end
    if not nonneg(v) then return false end
  end
  for _,key in ipairs({'calendar_started','period_keys','uncertain'}) do
    local v=data[key]
    if v~=nil and (not is_dict(v) or count(v)>32) then return false end
  end
  for key,value in pairs(dict(data.period_keys)) do
    if key~='interval' and key~='daily' and key~='weekly' and key~='monthly' then return false end
    if type(value)~='string' or #value>128 or string.sub(value,1,#key+1)~=key..':' then return false end
  end
  for key in pairs(dict(data.calendar_started)) do if key~='daily' and key~='weekly' and key~='monthly' then return false end end
  for key in pairs(dict(data.uncertain)) do
    local kind,rest=string.match(key,'^(%a+):([0-9-]+)$')
    if #key>128 or not (kind=='interval' or kind=='daily' or kind=='weekly' or kind=='monthly') or not rest then return false end
  end
  for _,key in ipairs({'calendar_started','uncertain'}) do for _,v in pairs(dict(data[key])) do if not nonneg(v) then return false end end end
  for _,key in ipairs({'config_fingerprint','retry_nonce'}) do
    local v=data[key]
    if v~=nil and not (type(v)=='string' and #v>=32 and #v<=64 and string.find(v,'^[a-f0-9]+$')) then return false end
  end
  if data.last_code~=nil and not (type(data.last_code)=='string' and string.find(data.last_code,'^TELEGRAM%-[A-Z0-9_-]+$')) then return false end
  local snapshot=data.snapshot
  if snapshot~=nil and snapshot~=NULL then
    if not is_dict(snapshot) then return false end
    for k in pairs(snapshot) do if k~='time' and k~='wan' and k~='vpn' then return false end end
    local stamp=snapshot.time;if stamp==nil then stamp=0 end
    if not nonneg(stamp) then return false end
    for _,key in ipairs({'wan','vpn'}) do
      local rows=snapshot[key];if rows==nil then rows=canon.object() end
      if not is_dict(rows) or count(rows)>18 then return false end
      for month,value in pairs(rows) do
        if type(month)~='string' or not string.find(month,'^%d%d%d%d%-%d%d$') or not nonneg(value) then return false end
      end
    end
  end
  return true
end

function M.unwrap(raw)
  if is_dict(raw) and num(raw.schema)==1 then
    local data=raw.data
    if data==nil then data=NULL end
    if raw.sha256~=canon.digest(data) or not M.valid(data) then error('TELEGRAM-STATE-CORRUPT',0) end
    return data
  end
  if M.valid(raw) then return raw end
  error('TELEGRAM-STATE-CORRUPT',0)
end

local function read_json(d,path,default)
  if d.is_link(path) then error('symlink storage refused',0) end
  local text=d.read(path)
  if text==nil then return default end
  return canon.decode(text)
end

function M.load_state(d)
  local found=false
  for index,name in ipairs({'telegram-state.json','telegram-state.backup.json'}) do
    local ok,data=pcall(function()
      local raw=read_json(d,d.persist..'/'..name,nil)
      if raw==nil then return nil end
      found=true
      return M.unwrap(raw)
    end)
    if ok and data~=nil then return data,index>1 and 'TELEGRAM-STATE-RECOVERED' or nil end
    if not ok then found=true end
  end
  if found then return canon.object(),'TELEGRAM-STATE-CORRUPT' end
  return canon.object(),nil
end

function M.save_state(d,data)
  if not M.valid(data) then error('TELEGRAM-STATE-CORRUPT',0) end
  local path=d.persist..'/telegram-state.json'
  pcall(function()
    local old=read_json(d,path,nil)
    if old~=nil then M.unwrap(old);d.write(d.persist..'/telegram-state.backup.json',canon.encode(old)) end
  end)
  d.write(path,canon.encode(canon.object({schema=1,data=data,sha256=canon.digest(data)})))
end

------------------------------------------------------------------------------------------------------
-- deliver(status, saved, now) -> public, state, sent
------------------------------------------------------------------------------------------------------
local TOKEN='^[0-9]+:[A-Za-z0-9_-]+$'
local function chat_ok(chat)
  if type(chat)~='string' then return false end
  if string.find(chat,'^%-?%d+$') then local digits=#string.gsub(chat,'^%-','');return digits>=1 and digits<=20 end
  return #chat>=6 and #chat<=33 and string.find(chat,'^@[A-Za-z][A-Za-z0-9_]+$')~=nil
end
M.chat_ok=chat_ok
local function token_ok(token) return type(token)=='string' and string.find(token,TOKEN)~=nil end
M.token_ok=token_ok
local function copy(t) local out=canon.object();for k,v in pairs(t) do out[k]=v end;return out end
local function with(t,extra) local out=copy(t);for k,v in pairs(extra) do out[k]=v end;return out end

local function sort_uncertain(uncertain)
  local rows={}
  for k,v in pairs(uncertain) do rows[#rows+1]={k,v} end
  table.sort(rows,function(a,b) if fnum(a[2])~=fnum(b[2]) then return fnum(a[2])<fnum(b[2]) end;return a[1]<b[1] end)
  local out=canon.object()
  for i=math.max(1,#rows-15),#rows do out[rows[i][1]]=rows[i][2] end
  return out
end

function M.deliver(d,status,saved,now)
  if not M.valid(saved) then return canon.object({enabled=true,code='TELEGRAM-STATE-CORRUPT'}),saved,false end
  local okc,config=pcall(d.config)
  if not okc or type(config)~='table' then return canon.object({enabled=true,code='TELEGRAM-CONFIG'}),saved,false end
  if config.telegram_enabled~='1' then return canon.object({enabled=false}),saved,false end
  if not chat_ok(config.telegram_chat) or not token_ok(config.telegram_token) then return canon.object({enabled=true,code='TELEGRAM-CONFIG'}),saved,false end
  local fingerprint=d.sha256(config.telegram_chat)
  local state=copy(saved)
  if state.config_fingerprint~=nil and state.config_fingerprint~=fingerprint then state=canon.object() end
  state.config_fingerprint=fingerprint
  local okr,request=pcall(read_json,d,d.runtime..'/telegram-retry.json',canon.object())
  if not okr then error(request,0) end
  if is_dict(request) and truthy(request.id) and request.id~=state.retry_nonce then
    state.uncertain=canon.object();state.retry_nonce=request.id;state.retry_handled=canon.float(now)
  end
  local okp,jobs,prepared,public=pcall(M.prepare,config,state,now)
  if not okp then return canon.object({enabled=true,code='TELEGRAM-CONFIG'}),state,false end
  state=prepared
  public.enabled=true;public.last_sent=get(state,'confirmed_at',get(state,'sent',0));public.uncertain_reports=count(dict(get(state,'uncertain',canon.object())))
  if fnum(get(state,'sent',0))>now+5 then return with(public,{code='TELEGRAM-CLOCK-BACKWARD'}),state,false end
  local remaining=fnum(get(state,'retry_after',300))-(now-fnum(get(state,'attempt',0)))
  if remaining>0 and truthy(get(state,'attempt',0)) then
    return with(public,{code=get(state,'last_code','TELEGRAM-RETRY'),retry_in=math.ceil(remaining)}),state,false
  end
  if #jobs==0 then
    if truthy(state.uncertain) then public.code='TELEGRAM-DELIVERY-UNKNOWN' end
    return public,state,false
  end
  local sent=false
  local items=M.parse_items(config.telegram_items)
  local result
  d.lock(function()
    for index,job in ipairs(jobs) do
      if index>1 then d.sleep(1.05) end
      state=with(state,{attempt=canon.float(now)})
      local okf,text=pcall(function()
        local body
        if job.kind=='interval' then
          body=M.format_report(status,job.minutes,now,items)
          if items.delta then body=body..'\n'..table.concat(M.delta_lines(status,state,now),'\n') end
          body='Report id: '..job.key..'\n'..body
        else body=M.format_period(status,job,now,items) end
        return body
      end)
      if not okf then
        state.last_code='TELEGRAM-FORMAT-FAILED'
        result={with(public,{code='TELEGRAM-FORMAT-FAILED'}),state,sent};return
      end
      local oks,err=pcall(d.send,config,M.limited_text(text))
      if not oks then
        if not M.is_delivery_error(err) then err=delivery_error('TELEGRAM-DELIVERY-UNKNOWN',true) end
        state.last_code=err.code;state.retry_after=err.retry_after
        local counter=err.uncertain and 'unknown_deliveries' or 'known_failures'
        state[counter]=fnum(get(state,counter,0))+1
        if err.uncertain then
          local uncertain=copy(dict(get(state,'uncertain',canon.object())));uncertain[job.key]=canon.float(now)
          state.uncertain=sort_uncertain(uncertain)
        end
        result={with(public,{code=err.code,last_sent=get(state,'sent',0),uncertain_reports=count(dict(get(state,'uncertain',canon.object())))}),state,sent};return
      end
      local keys=copy(dict(get(state,'period_keys',canon.object())));keys[job.kind]=job.key;state.period_keys=keys
      local confirmed=canon.float(d.wall())
      state.sent=confirmed;state.confirmed_at=confirmed;state.last_code='TELEGRAM-DELIVERED';state.retry_after=300
      state.snapshot=M.traffic_snapshot(status,now)
      state.confirmed_reports=fnum(get(state,'confirmed_reports',0))+1;sent=true
    end
  end,d.runtime..'/telegram-control')
  if result then return result[1],result[2],result[3] end
  return with(public,{last_sent=get(state,'confirmed_at',now),uncertain_reports=count(dict(get(state,'uncertain',canon.object())))}),state,sent
end

------------------------------------------------------------------------------------------------------
-- rpc telegram_retry / telegram_test
------------------------------------------------------------------------------------------------------
-- retry_unknown(d) -> reply, or nil when the (non-blocking) control lock was busy
function M.retry_unknown(d)
  if not d.allow('telegram_retry',10,d.wall()) then return canon.object({queued=false,code='RPC-RATE-LIMIT'}) end
  local locked=d.lock(function()
    d.write(d.runtime..'/telegram-retry.json',canon.encode(canon.object({id=d.uuid(),time=canon.float(d.wall())})))
  end,d.runtime)
  if not locked then return nil end
  return canon.object({queued=true,may_duplicate_uncertain_delivery=true})
end

function M.send_test(d)
  local _,reply=d.lock(function()
    local now=d.wall();local path=d.runtime..'/telegram-test.json'
    local old=read_json(d,path,canon.object())
    if now-fnum(get(dict(old),'attempt',0))<60 then return canon.object({delivered=false,code='TELEGRAM-TEST-RATE-LIMIT'}) end
    local okc,config=pcall(d.config)
    if not okc or type(config)~='table' then return canon.object({delivered=false,code='TELEGRAM-CONFIG'}) end
    d.write(path,canon.encode(canon.object({attempt=canon.float(now)})))
    local oks,err=pcall(d.send,config,M.TEST_TEXT)
    if not oks then
      if not M.is_delivery_error(err) then err=delivery_error('TELEGRAM-DELIVERY-UNKNOWN',true) end
      return canon.object({delivered=false,code=err.code,uncertain=err.uncertain})
    end
    d.write(path,canon.encode(canon.object({attempt=canon.float(now),confirmed=canon.float(d.wall())})))
    return canon.object({delivered=true,code='TELEGRAM-TEST-DELIVERED'})
  end,d.runtime..'/telegram-control')
  return reply
end

------------------------------------------------------------------------------------------------------
-- the sender: curl with the bot URL in a 0600 config file (never on a command line), JSON body from a file
------------------------------------------------------------------------------------------------------
-- curl exit codes of a certificate that cannot be verified (Python: SSLCertVerificationError -> TELEGRAM-TLS)
M.CURL_CERT={[51]=true,[60]=true}
M.CURL_DNS={[6]=true}
function M.classify(exit,http,body)
  if M.CURL_CERT[exit] then error(delivery_error('TELEGRAM-TLS'),0) end
  if M.CURL_DNS[exit] then error(delivery_error('TELEGRAM-DNS'),0) end
  if exit~=0 or not http then error(delivery_error('TELEGRAM-DELIVERY-UNKNOWN',true),0) end
  if http<200 or http>=300 then error(M.rejection(http),0) end
  if body==nil or #body>65536 then error(delivery_error('TELEGRAM-DELIVERY-UNKNOWN',true),0) end
  local ok,result=pcall(canon.decode,body)
  if not ok or not is_dict(result) then error(delivery_error('TELEGRAM-DELIVERY-UNKNOWN',true),0) end
  if result.ok~=true then
    local parameters=result.parameters
    local delay=is_dict(parameters) and parameters.retry_after or 300
    if delay==nil then delay=300 end
    local code=result.error_code
    error(M.rejection(type(code)=='number' and code or -1,(type(delay)=='number' and delay%1==0) and delay or 300),0)
  end
  return true
end

function M.send_message(d,config,text)
  local token,chat=config.telegram_token,config.telegram_chat
  if not token_ok(token) or not chat_ok(chat) then error(delivery_error('TELEGRAM-CONFIG'),0) end
  local base=d.runtime..'/.telegram-'..canon.unique()
  local cfg,payload,body,code=base..'.cfg',base..'.json',base..'.body',base..'.code'
  local ok,err=pcall(function()
    d.write_private(cfg,'url = "https://api.telegram.org/bot'..token..'/sendMessage"\n')
    d.write_private(payload,canon.encode(canon.object({chat_id=chat,text=M.limited_text(text)})))
    local exit=d.exec_curl({d.curl or M.CURL,'-q','-s','--proto','=https','--max-redirs','0','--connect-timeout','10','-m','15',
      '--max-filesize','65536','-K',cfg,'-H','Content-Type: application/json','--data-binary','@'..payload,'-o',body,'-w','%{http_code}'},code)
    local http=tonumber(string.match(d.read(code) or '','^(%d%d%d)'))
    if http==0 then http=nil end
    return M.classify(exit,http,d.read(body))
  end)
  for _,path in ipairs({cfg,payload,body,code}) do d.remove(path) end
  if not ok then error(err,0) end
end

------------------------------------------------------------------------------------------------------
-- router deps and the command line
------------------------------------------------------------------------------------------------------
M.CONFIG_KEYS={'telegram_enabled','telegram_token','telegram_chat','telegram_interval','telegram_schedule','telegram_hour',
  'telegram_weekly','telegram_monthly','telegram_items'}
local function quote(arg)
  if type(arg)~='string' or string.find(arg,"[%z\n']") then error('telegram: unsafe command argument',0) end
  return "'"..arg.."'"
end
function M.router(options)
  options=options or {}
  local pause=require('speed_pause')
  local mio=options.io or require('monitor_io')
  local d=pause.router({runtime=options.runtime,persist=options.persist,io=mio})
  -- the control lock of a directory (RUNTIME or RUNTIME/telegram-control), blocking like Python's control_lock
  d.lock=options.lock or function(fn,directory)
    os.execute('mkdir -p '..directory..' && chmod 700 '..directory)
    local results={require('control').lock(fn,directory)};return true,unpack(results)
  end
  -- telegram_private.lua in this process: the credentials stay in memory, never in a reply
  d.config=options.config or function()
    local c=require('uci').cursor()
    local s=c:get_all('homensai_vpn','main') or {}
    local out={}
    for _,key in ipairs(M.CONFIG_KEYS) do local v=s[key];out[key]=type(v)=='string' and v or '' end
    return out
  end
  -- created 0600 before anything is written into it (umask in the creating shell)
  function d.write_private(path,text)
    os.execute('umask 077 && : >'..path)
    local f=assert(io.open(path,'wb'))
    assert(f:write(text));f:close()
  end
  function d.exec_curl(argv,output)
    local parts={};for i,a in ipairs(argv) do parts[i]=quote(a) end
    local status=output..'.st'
    os.execute(table.concat(parts,' ')..' >'..output..' 2>/dev/null </dev/null'..require('speed').closing(mio)..'; echo $? >'..status)
    local text=d.read(status);os.remove(status)
    return tonumber(string.match(text or '','^(%d+)')) or 255
  end
  d.send=options.send or function(config,text) return M.send_message(d,config,text) end
  function d.uuid() return require('auto_control').uuid_hex() end
  function d.allow(key,interval,now)
    return require('setup').allow({runner=mio,runtime=d.runtime},key,interval,now)
  end
  for key,value in pairs(options.overrides or {}) do d[key]=value end
  return d
end

-- `lua telegram.lua deliver <input.json> <output.json>`: one delivery round of the monitor, in a child process.
-- `lua telegram.lua call telegram_test|telegram_retry`: the rpcd dispatcher's Lua path (prints one JSON line).
-- One round on the monitor's job files: the child saves a changed sender state itself (agent.py's telegram_collect
-- did it in the monitor), so a monitor restart during a send never loses a confirmed delivery.
-- stored: true (saved), false (TELEGRAM-STATE-WRITE-FAILED), null (unchanged).
function M.deliver_files(d,input_path,output_path)
  local job='^'..string.gsub(d.runtime,'[%-%.]','%%%0')..'/telegram%-job%-[0-9a-f-]+%.'
  if not string.find(input_path,job..'in%.json$') or not string.find(output_path,job..'out%.json$') then return false end
  local input=canon.decode(d.read(input_path) or 'null')
  local public,saved,sent=M.deliver(d,input.status,input.saved,num(input.now))
  local stored=NULL
  if not require('speed_pause').equal(saved,input.saved) then stored=pcall(M.save_state,d,saved) end
  d.write(output_path,canon.encode(canon.object({public=public,saved=saved,sent=sent and true or false,stored=stored})))
  return true
end

function M.main(argv)
  local okn,nixio=pcall(require,'nixio')
  if okn and type(nixio)=='table' and nixio.setenv then nixio.setenv('TZ',require('monitor_io').TZ) end
  local d=M.router({})
  if argv[1]=='deliver' and argv[2] and argv[3] then return M.deliver_files(d,argv[2],argv[3]) and 0 or 2 end
  if argv[1]=='call' and (argv[2]=='telegram_test' or argv[2]=='telegram_retry') then
    local text=io.read('*a') or ''
    local ok,arguments=pcall(require('rpc').decode_request,text)
    local reply
    if not ok then reply=canon.object({error=require('rpc').code_of(arguments)})
    elseif next(arguments)~=nil then reply=canon.object({error='RPC-UNEXPECTED-ARGS'})
    elseif argv[2]=='telegram_test' then reply=M.send_test(d)
    else reply=M.retry_unknown(d) end
    io.write(canon.encode(reply),'\n')
    return 0
  end
  return 2
end

if arg and arg[0] and string.find(arg[0],'telegram%.lua$') and arg[1] then os.exit(M.main(arg)) end

return M
