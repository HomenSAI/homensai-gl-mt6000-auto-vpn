-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- history.lua: native_history.History for the Lua supervisor (2.0.0-lua-alpha2).
--
-- Same file (/etc/homensai-vpn/native-history.json + native-history.backup.json), same envelope
-- {"data":...,"schema":1,"sha256":sha256(encoded(data))}, same item fields, attempt/episode correlation,
-- METRICS counters (counter_version 2), pruning and the 2 MB retention budget. Python's resident writer copy
-- (diagnostic statistics mode only) is not kept: the owner runs the Work mode, where the history is read,
-- used and released per event. public()/read_public stay with the monitor (it serves the page).
-- Dates: env.localdate(format, seconds) (default os.date; the daemon runs with TZ set like Python's CET rule).
local canon=require('canon')
local ctl=require('auto_control')

local M={}
local NULL=canon.null
local isnone,num,finite=ctl.isnone,ctl.num,ctl.finite

M.METRICS={'attempts','committed','manual_attempts','manual_committed','trials_passed','rollbacks','returns','blocked_episodes',
  'automatic_attempts','automatic_committed','server_switches','channel_switches','protocol_switches','rate_limited_episodes'}
local METRIC_SET={} for _,m in ipairs(M.METRICS) do METRIC_SET[m]=true end
M.RETENTION_BYTES=2*1024*1024

local HistoryError={}
HistoryError.__index=HistoryError
HistoryError.__tostring=function(e) return e.code end
M.HistoryError=HistoryError
local function fail(code) error(setmetatable({code=code},HistoryError),0) end

local function is_code(v) return type(v)=='string' and #v>=1 and #v<=96 and string.find(v,'^[A-Z0-9_-]+$')~=nil end
local function is_profile(v)
  return type(v)=='string' and (string.find(v,'^openvpn:[0-9]+_[0-9]+$')~=nil or string.find(v,'^wireguard:peer_[0-9]+$')~=nil)
end
M.is_profile=is_profile
local function is_int(v) return type(v)=='number' and v%1==0 end
local function is_bool(v) return type(v)=='boolean' end
local function has(t,k) return t[k]~=nil end
local function count_keys(t) local n=0;for _ in pairs(t) do n=n+1 end;return n end
local function encoded(v) return canon.encode(v) end
M.encoded=encoded
local function clone(v) return canon.decode(canon.encode(v)) end
local function getd(t,k,d) local v=t[k];if isnone(v) then return d end;return v end
local function contains(list,x) for _,v in ipairs(list) do if v==x then return true end end;return false end
local function sorted_keys(t) local keys={};for k in pairs(t) do keys[#keys+1]=k end;table.sort(keys);return keys end

-- transition_destination(value) -> role, identifier (both may be nil)
function M.transition_destination(value)
  if value.route_changed==false or value.activation_reapply==true then return nil,nil end
  if value.transition_metadata_present==true and not has(value,'destination_role') then return nil,nil end
  if has(value,'destination_role') or has(value,'destination_profile_id') then
    local role,identifier=value.destination_role,value.destination_profile_id
    if (role=='source' or role=='target') and identifier==value[role] and is_profile(identifier) then return role,identifier end
    return nil,nil
  end
  local state=value.state
  local role
  if state=='RESTORING' or state=='ROLLED-BACK' or (state=='STOPPED' and value.reason=='OPERATOR-RETURN') then role='source'
  elseif state=='APPLYING' or state=='WAIT-CLIENT' or state=='COMMITTED' or state=='STOPPED-ON-RESERVE' then role='target' end
  local identifier=role and value[role] or nil
  if is_profile(identifier) then return role,identifier end
  return role,nil
end

function M.clean_transition_latency(raw,value,now)
  local _,identifier=M.transition_destination(value)
  if not identifier or not canon.is_object(raw) or raw.profile~=identifier or raw.metric~='https-rtt-ms' then return nil end
  local stamp,delay=num(raw.time),num(raw.rtt_ms)
  local interface,generation=raw.interface,raw.generation
  if not stamp or not (now-90<=stamp and stamp<=now+5) or not delay or not (0<=delay and delay<=600000)
     or type(interface)~='string' or not (string.find(interface,'^wgclient[0-9]+$') or string.find(interface,'^ovpnclient[0-9]+$')) or #interface>14
     or ((string.sub(identifier,1,10)=='wireguard:')~=(string.sub(interface,1,8)=='wgclient')) or not ctl.hex(generation,32) then return nil end
  return canon.object({profile=identifier,metric='https-rtt-ms',time=raw.time,rtt_ms=raw.rtt_ms,interface=interface,generation=generation})
end

-- native_history.capture_transition_latency (plan item 6): the destination channel's own HTTPS RTT from the
-- monitor's status.json at the event, bound to the journal's vendor binding; never today's ping.
function M.capture_transition_latency(value,status,binding,now)
  local role,identifier=M.transition_destination(value)
  if not identifier or not canon.is_object(status) or not canon.is_object(binding) or binding.id~=identifier then return nil end
  local stamp=num(status.time)
  local py=require('py')
  if py.truthy(status.error) or py.truthy(status.rpc_error) or type(status.time)=='boolean' or not stamp or not (now-90<=stamp and stamp<=now+5) then return nil end
  local rows=status.profiles
  if rows==nil then rows=canon.array({}) end
  if not canon.is_array(rows) then return nil end
  local matched={}
  for _,p in ipairs(rows) do if canon.is_object(p) and p.id==identifier then matched[#matched+1]=p end end
  if #matched~=1 then return nil end
  local p=matched[1]
  if not isnone(p.code) or p.dns_ok~=true or not is_int(p.https_success) or p.https_success<2 or p.vendor_state~='SETTLED'
     or (p.protocol~='wireguard' and p.protocol~='openvpn') or p.vendor_tunnel_id~=p.protocol..':'..py.str(getd(p,'interface',NULL)) then return nil end
  for _,k in ipairs({'id','protocol','interface','vendor_tunnel_id','vendor_generation'}) do
    if not py.eq(getd(p,k,NULL),getd(binding,k,NULL)) then return nil end
  end
  return M.clean_transition_latency(canon.object({profile=identifier,metric='https-rtt-ms',time=getd(p,'time',NULL),rtt_ms=getd(p,'rtt_ms',NULL),
    interface=getd(p,'interface',NULL),generation=getd(p,'vendor_generation',NULL)}),value,now)
end

------------------------------------------------------------------------------------------------------
-- History
------------------------------------------------------------------------------------------------------
local History={}
History.__index=History

function M.new(env,directory,limit,detail_days)
  if detail_days==nil then
    detail_days=env.backend and env.backend.history_days and env.backend.history_days() or 7
  end
  if not is_int(detail_days) or detail_days<1 or detail_days>30 then fail('HISTORY-RETENTION') end  -- retention.MAX_DAYS
  limit=limit or 10000
  if not is_int(limit) or limit<1 or limit>10000 then fail('HISTORY-LIMIT') end
  return setmetatable({env=env,detail_days=detail_days,limit=limit,path=directory..'/native-history.json',
    backup=directory..'/native-history.backup.json',lock=directory..'/native-history.lock',restored=false},History)
end

function History:localdate(fmt,t)
  local f=self.env.localdate or os.date
  return f(fmt,math.floor(num(t)))
end

-- Resident copy (plan item 1, CPU): decoding and re-hashing the whole history costs about a second per publish
-- on the MT3000 in Lua, and the supervisor publishes on every pass. The decoded data is kept while both files
-- read back with the same (inode, size, mtime, ctime) as when this process last loaded or wrote them; every
-- write renames a new file into place, so any change by anyone changes the key. A failed record drops it.
-- Without fs.key (tests, a router without nixio) nothing is kept: the full load runs as before.
local resident=nil
function M.forget_resident() resident=nil end
function History:files_key()
  local key=self.env.run.fs.key
  if not key then return nil end
  local a,b=key(self.path),key(self.backup)
  if a==nil or b==nil then return nil end
  return a..'|'..b
end
function History:load()
  local key=self:files_key()
  if key and resident and resident.key==key and resident.path==self.path and resident.detail_days==self.detail_days then
    self.restored=resident.restored
    return resident.data
  end
  resident=nil
  local data=self:load_files()
  if key then resident={key=key,path=self.path,detail_days=self.detail_days,restored=self.restored,data=data} end
  return data
end

function History:load_files()
  local found=false
  local run=self.env.run
  for index,path in ipairs({self.path,self.backup}) do
    local ok,data=pcall(function()
      if run.fs.unsafe and run.fs.unsafe(path) then fail('HISTORY-PATH') end
      local text=run.fs.read(path)
      if text==nil then return nil end
      found=true
      if #text>2300*1024 then fail('HISTORY-SIZE') end
      local envelope=canon.decode(text)
      if not canon.is_object(envelope) then fail('HISTORY-SCHEMA') end
      local data=envelope.data
      if envelope.schema~=1 or not canon.is_object(data) or canon.sha256(encoded(data))~=envelope.sha256 then fail('HISTORY-CHECKSUM') end
      if not canon.is_array(data.events) or not canon.is_object(data.months) or not is_int(data.sequence) or data.sequence<0 or data.sequence>=2^53 then fail('HISTORY-SCHEMA') end
      for _,spec in ipairs({{'active_attempt',{id=true,episode=true,source=true,target=true,terminal=true}},{'retry_episode',{id=true,source=true,trial=true,closed=true}}}) do
        local name,fields=spec[1],spec[2]
        local metadata=getd(data,name,canon.object({}))
        if canon.is_object(metadata) and next(metadata)==nil then
        else
          if not canon.is_object(metadata) then fail('HISTORY-METADATA') end
          for k in pairs(metadata) do if not fields[k] then fail('HISTORY-METADATA') end end
          for k in pairs(fields) do if metadata[k]==nil then fail('HISTORY-METADATA') end end
          for _,key in ipairs({'id','episode'}) do
            if fields[key] and (not is_int(metadata[key]) or metadata[key]<1 or metadata[key]>data.sequence) then fail('HISTORY-METADATA') end
          end
          for _,key in ipairs({'source','target'}) do
            local identifier=metadata[key]
            if not isnone(identifier) and not is_profile(identifier) then fail('HISTORY-METADATA') end
          end
          for _,key in ipairs({'terminal','trial','closed'}) do
            if fields[key] and not is_bool(metadata[key]) then fail('HISTORY-METADATA') end
          end
        end
      end
      local days=getd(data,'days',canon.object({}))
      if #data.events>10000 or count_keys(data.months)>1200 or not canon.is_object(days) or count_keys(days)>400 then fail('HISTORY-BOUNDS') end
      if data.counter_version==2 then
        for _,name in ipairs({'totals','counted'}) do
          local values=data[name]
          if not canon.is_object(values) then fail('HISTORY-COUNTERS') end
          for key,value in pairs(values) do
            if not METRIC_SET[key] or not is_int(value) or value<0 or value>=2^53 then fail('HISTORY-COUNTERS') end
          end
        end
        for _,row in ipairs(data.events) do
          if has(row,'counted_metrics') then
            local cm=row.counted_metrics
            if not canon.is_array(cm) or #cm>#M.METRICS then fail('HISTORY-COUNTERS') end
            for _,key in ipairs(cm) do if not METRIC_SET[key] then fail('HISTORY-COUNTERS') end end
          end
        end
      end
      self.restored=index==2
      return data
    end)
    if ok and data~=nil then return data end
  end
  if found then fail('HISTORY-CORRUPT') end
  return canon.object({sequence=0,events=canon.array({}),months=canon.object({}),last_key=NULL,last_time=NULL,timezone='Europe/Berlin'})
end

function History:envelope(data)
  return canon.object({schema=1,data=data,sha256=canon.sha256(encoded(data))})
end
function M.envelope_bytes(raw) return '{"data":'..raw..',"schema":1,"sha256":"'..canon.sha256(raw)..'"}' end

local function matches_active(item,active)
  for _,k in ipairs({'source','target'}) do
    if not isnone(item[k]) and item[k]~=active[k] then return false end
  end
  return true
end

function History:correlate(data,item)
  local active=canon.object({});for k,v in pairs(getd(data,'active_attempt',canon.object({}))) do active[k]=v end
  local episode=canon.object({});for k,v in pairs(getd(data,'retry_episode',canon.object({}))) do episode[k]=v end
  local has_active=next(active)~=nil
  if item.route_changed==false or item.activation_reapply==true then
    if item.transition_completed==true and item.transition_outcome=='refused' and has_active and matches_active(item,active) then
      item.attempt_id=active.id;item.retry_episode_id=active.episode;active.terminal=true
    end
    return active,episode
  end
  local codes=item.codes
  local trial_passed=contains(codes,'TRIAL-PASSED')
  local prepare=item.state=='ARMED' and not trial_passed
  local restoring=item.state=='RESTORING' and item.transition_metadata_present==true and item.route_changed==true
  local starting=prepare or item.state=='APPLYING' or (restoring and (not has_active or active.terminal==true))
  local prior=#data.events>0 and data.events[#data.events].state or nil
  if starting and (not has_active or active.terminal==true or (prior~='ARMED' and prior~='APPLYING')
                   or active.source~=item.source or active.target~=item.target) then
    local sequence=data.sequence+1
    local origin=getd(item,'from_profile_id',item.source)
    if next(episode)==nil or episode.closed==true or episode.source~=origin or episode.trial~=item.trial then
      episode=canon.object({id=sequence,source=origin==nil and NULL or origin,trial=item.trial,closed=false})
    end
    active=canon.object({id=sequence,episode=episode.id,source=item.source==nil and NULL or item.source,target=item.target==nil and NULL or item.target,terminal=false})
    has_active=true
  end
  if has_active and matches_active(item,active) then
    item.attempt_id=active.id;item.retry_episode_id=active.episode
    local s=item.state
    if item.transition_completed==true or s=='COMMITTED' or s=='ROLLED-BACK' or s=='BLOCKED' or s=='STOPPED' or s=='EXPIRED' or s=='STOPPED-ON-RESERVE' or trial_passed then
      active.terminal=true
    end
    if item.transition_outcome=='committed' or item.transition_outcome=='restored' or s=='COMMITTED' or trial_passed then episode.closed=true end
  end
  return active,episode
end

function History:counters(data,item)
  local state=item.state
  local identity=getd(item,'attempt_id',item.sequence)
  local recorded={}
  if isnone(data.counted) then data.counted=canon.object({}) end
  local seen=data.counted
  local month=self:localdate('%Y-%m',item.time)
  local day=self:localdate('%Y-%m-%d',item.time)
  if isnone(data.totals) then data.totals=canon.object({}) end
  if isnone(data.days) then data.days=canon.object({}) end
  if isnone(data.months[month]) then data.months[month]=canon.object({}) end
  if isnone(data.days[day]) then data.days[day]=canon.object({}) end
  local function add(metric,unique)
    if unique~=nil then
      if unique<=(num(seen[metric]) or 0) then return end
      seen[metric]=unique
    end
    for _,total in ipairs({data.totals,data.months[month],data.days[day]}) do total[metric]=(num(total[metric]) or 0)+1 end
    recorded[#recorded+1]=metric
  end
  local codes=item.codes
  local actual=item.route_changed~=false and item.activation_reapply~=true and item.transition_outcome~='refused'
  if state=='APPLYING' and actual then
    add('attempts',identity)
    if item.manual==true then add('manual_attempts',identity) elseif not item.trial then add('automatic_attempts',identity) end
  end
  local committed=(item.transition_completed==true and item.transition_outcome=='committed') or (state=='COMMITTED' and not has(item,'transition_outcome'))
  if committed and actual then
    local new=identity>(num(seen.committed) or 0)
    add('committed',identity)
    if new and not item.trial then
      add(item.manual==true and 'manual_committed' or 'automatic_committed',identity)
      local kind=item.transition_kind
      if kind=='server' or kind=='channel' or kind=='protocol' then add(kind..'_switches',identity) end
    end
  end
  if actual and item.transition_completed==true and (item.transition_outcome=='committed' or item.transition_outcome=='restored')
     and item.from_role=='target' and item.destination_role=='source' and not item.trial then add('returns',identity) end
  if state=='ARMED' and contains(codes,'TRIAL-PASSED') then add('trials_passed',identity) end
  if (state=='ROLLED-BACK' or (item.transition_completed==true and item.transition_outcome=='restored')) and actual then
    add('rollbacks',identity)
    if item.original_restored==true and (contains(codes,'PRIMARY-STABLY-RECOVERED') or item.manual==true) then add('returns',identity) end
  end
  local prior=data.counted_state
  if state=='BLOCKED' and prior~='BLOCKED' then add('blocked_episodes') end
  local rate=contains(codes,'PAIR-RATE-LIMIT')
  if rate and data.counted_reason~='PAIR-RATE-LIMIT' then add('rate_limited_episodes') end
  data.counted_state=state
  data.counted_reason=rate and 'PAIR-RATE-LIMIT' or NULL
  return canon.array(recorded)
end

function History:migrate(data)
  if data.counter_version==2 then return end
  local events=data.events
  local complete=data.sequence==0 or (#events>0 and #events==data.sequence)
  if complete and data.sequence~=0 then
    for i,row in ipairs(events) do if row.sequence~=i then complete=false end end
  end
  data.legacy_months=clone(data.months)
  data.counter_version=2;data.counted=canon.object({});data.totals=canon.object({})
  data.returns_since=canon.float(self.env.run.wall())
  data.counter_accuracy=complete and 'complete retained event replay' or 'legacy partial counters; deduplicated from upgrade'
  if complete then
    data.months=canon.object({});data.days=canon.object({})
    for _,item in ipairs(events) do item.counted_metrics=self:counters(data,item) end
  else
    for _,totals in pairs(data.months) do
      for key,value in pairs(totals) do
        if METRIC_SET[key] and is_int(value) and value>=0 then data.totals[key]=(num(data.totals[key]) or 0)+value end
      end
    end
    local replay=canon.object({months=canon.object({}),days=canon.object({})})
    for _,item in ipairs(events) do self:counters(replay,item) end
    for _,key in ipairs({'counted','counted_state','counted_reason'}) do if replay[key]~=nil then data[key]=replay[key] end end
  end
end

function History:prune(data,now)
  local kept={}
  local horizon=now-self.detail_days*86400
  for _,row in ipairs(data.events) do
    local t=num(row.time)
    if t and horizon<=t and t<=now then kept[#kept+1]=row end
  end
  data.events=canon.array(kept)
  local months=sorted_keys(data.months)
  for i=1,#months-1200 do data.months[months[i]]=nil end
  local cutoff=self:localdate('%Y-%m-%d',math.max(0,horizon))
  local days=getd(data,'days',canon.object({}))
  for _,day in ipairs(sorted_keys(days)) do if day<cutoff then days[day]=nil end end
end

function History:atomic(path,value) self.env.run.fs.write_atomic(path,encoded(value)) end

function History:record(value,now)
  local lock=self.env.history_lock or function(_,fn) return fn() end
  local ok,result=pcall(lock,self.lock,function() return self:_record(value,now) end)
  if not ok then resident=nil;error(result,0) end
  return result
end

function History:_record(value,now)
  now=now or self.env.run.wall()
  if type(now)~='number' or not finite(now) or now<0 then fail('HISTORY-CLOCK') end
  local run=self.env.run
  local data=self:load()
  local exists
  if run.fs.key then exists=run.fs.key(self.path)~='absent' else exists=run.fs.read(self.path)~=nil end
  local from_main=not self.restored and exists
  local legacy=data.counter_version~=2
  if legacy then from_main=false end
  self:migrate(data)
  if not isnone(data.last_time) and now<num(data.last_time) then now=num(data.last_time) end
  local state=getd(value,'state','UNKNOWN')
  if not is_code(state) then fail('HISTORY-STATE') end
  local codes={}
  local blockers=getd(value,'blockers',canon.array({}))
  for i=1,math.min(16,#blockers) do codes[#codes+1]=blockers[i] end
  if not isnone(value.reason) and value.reason~='' and value.reason~=false then codes[#codes+1]=value.reason end
  local set={}
  for _,c in ipairs(codes) do if is_code(c) then set[c]=true end end
  codes={};for c in pairs(set) do codes[#codes+1]=c end;table.sort(codes)
  local item=canon.object({state=state,codes=canon.array(codes),trial=value.trial==true})
  local ts=value.transition_source
  if ts=='manual' or ts=='automatic' or ts=='test' or ts=='programmatic' or ts=='unknown' then item.transition_source=ts end
  local control_time=num(value.control_time)
  if (value.control_action=='start' or value.control_action=='stop')
     and (value.control_source=='manual' or value.control_source=='test' or value.control_source=='programmatic' or value.control_source=='unknown')
     and control_time and 0<control_time and control_time<=now and finite(control_time) then
    item.control_action=value.control_action;item.control_source=value.control_source;item.control_time=value.control_time
  end
  if value.manual==true or set['OPERATOR-MANUAL'] then item.manual=true end
  if is_bool(value.original_restored) then item.original_restored=value.original_restored end
  local scope=getd(value,'proof_scope','external-lan')
  if scope~='external-lan' and scope~='router-hosted-ipv4' and scope~='router-probed-ipv4' then fail('HISTORY-SCOPE') end
  if has(value,'proof_scope') then item.proof_scope=scope end
  for _,key in ipairs({'source','target'}) do if is_profile(value[key]) then item[key]=value[key] end end
  for _,key in ipairs({'from_role','destination_role','before_policy_role'}) do
    if value[key]=='source' or value[key]=='target' then item[key]=value[key] end
  end
  for _,pair in ipairs({{'from_role','from_profile_id'},{'destination_role','destination_profile_id'}}) do
    local role,key=pair[1],pair[2]
    local identifier=value[key]
    if (value[role]=='source' or value[role]=='target') and identifier==value[value[role]] and is_profile(identifier) then item[key]=identifier end
  end
  for _,key in ipairs({'route_changed','transition_completed','activation_reapply','transition_metadata_present'}) do
    if is_bool(value[key]) then item[key]=value[key] end
  end
  local outcome=value.transition_outcome
  if outcome=='committed' or outcome=='restored' or outcome=='refused' or outcome=='policy-verified' then item.transition_outcome=outcome end
  for _,key in ipairs({'before_order','after_order','session_order','restored_order'}) do
    local order=value[key]
    if canon.is_array(order) and #order>=2 and #order<=400 then
      local ok,seen=true,{}
      for _,x in ipairs(order) do
        if type(x)~='string' or #x>64 or not string.find(x,'^[A-Za-z0-9_]+$') or seen[x] then ok=false;break end
        seen[x]=true
      end
      if ok then local copy={};for i,x in ipairs(order) do copy[i]=x end;item[key]=canon.array(copy) end
    end
  end
  local latency=M.clean_transition_latency(value.latency,value,now)
  if latency~=nil then item.latency=latency end
  if self.env.deps and self.env.deps.clean_website_response then
    local website=self.env.deps.clean_website_response(value.website_response,value,now)
    if website~=nil then item.website_response=website end
  end
  local kind=value.transition_kind
  if kind=='server' or kind=='channel' or kind=='protocol' then item.transition_kind=kind end
  local raw=value.probe_evidence
  if canon.is_object(raw) then
    local evidence=canon.object({})
    local any=false
    for _,name in ipairs({'source_streak_met','reserve_streak_met'}) do if is_bool(raw[name]) then evidence[name]=raw[name];any=true end end
    for _,spec in ipairs({{'required_failures',3},{'required_successes',2}}) do
      local v=raw[spec[1]]
      if is_int(v) and spec[2]<=v and v<=10 then evidence[spec[1]]=v;any=true end
    end
    if any then item.probe_evidence=evidence end
  end
  local phases=value.phase_evidence
  if canon.is_array(phases) then
    local clean={}
    for i=math.max(1,#phases-31),#phases do
      local row=phases[i]
      if canon.is_object(row) then
        local phase,stamp=row.phase,num(row.time)
        if is_code(phase) and stamp and finite(stamp) and 0<=stamp and stamp<=now and (#clean==0 or stamp>=num(clean[#clean].time)) then
          clean[#clean+1]=canon.object({phase=phase,time=row.time})
        end
      end
    end
    if #clean>0 then item.phase_evidence=canon.array(clean) end
  end
  local active,episode=self:correlate(data,item)
  local keyed=canon.object({})
  for k,v in pairs(item) do if k~='latency' and k~='website_response' then keyed[k]=v end end
  local key=canon.sha256(encoded(keyed))
  if key==data.last_key then
    local original_events,original_days=#data.events,count_keys(getd(data,'days',canon.object({})))
    self:prune(data,now)
    if legacy or #data.events~=original_events or count_keys(getd(data,'days',canon.object({})))~=original_days then
      self:atomic(self.backup,self:envelope(clone(data)));self:atomic(self.path,self:envelope(data));resident=nil
    end
    if isnone(data.daily_since) then
      local old=self:envelope(clone(data));data.daily_since=canon.float(now);data.days=canon.object({})
      self:atomic(self.backup,old);self:atomic(self.path,self:envelope(data));resident=nil
    end
    return false
  end
  local legacy_old=nil
  if not from_main then legacy_old=self:envelope(clone(data)) end
  if data.sequence>=2^53-1 then fail('HISTORY-SEQUENCE-LIMIT') end
  data.active_attempt=active;data.retry_episode=episode
  item.time=canon.float(now);item.sequence=data.sequence+1
  data.sequence=data.sequence+1;data.last_key=key;data.last_time=canon.float(now)
  local retained={}
  for _,row in ipairs(data.events) do retained[#retained+1]=row end
  retained[#retained+1]=item
  local dropped=num(getd(data,'detail_budget_dropped',0)) or 0
  local excess=#retained-self.limit
  for i=1,math.max(0,excess) do if num(retained[i].time)>=now-self.detail_days*86400 then dropped=dropped+1 end end
  data.detail_budget_dropped=dropped
  local events={}
  for i=math.max(1,excess+1),#retained do events[#events+1]=retained[i] end
  data.events=canon.array(events)
  local month=self:localdate('%Y-%m',now);local day=self:localdate('%Y-%m-%d',now)
  if isnone(data.daily_since) then data.daily_since=canon.float(now) end
  if isnone(data.days) then data.days=canon.object({}) end
  item.counted_metrics=self:counters(data,item)
  if isnone(data.months[month]) then data.months[month]=canon.object({}) end
  if isnone(data.days[day]) then data.days[day]=canon.object({}) end
  for _,totals in ipairs({data.totals,data.months[month],data.days[day]}) do
    for _,metric in ipairs(M.METRICS) do if totals[metric]==nil then totals[metric]=0 end end
  end
  self:prune(data,now)
  local raw=encoded(data)
  while #data.events>1 and #raw>M.RETENTION_BYTES do
    table.remove(data.events,1)
    data.detail_budget_dropped=(num(getd(data,'detail_budget_dropped',0)) or 0)+1
    raw=encoded(data)
  end
  if #raw>M.RETENTION_BYTES then fail('HISTORY-SIZE') end
  -- main := new data, backup := the previous main (renamed), one full flash write per event
  if from_main and run.fs.read(self.path)~=nil and run.fs.rename then
    run.fs.rename(self.path,self.backup)
  else
    self:atomic(self.backup,legacy_old or self:envelope(clone(data)))
  end
  run.fs.write_atomic(self.path,M.envelope_bytes(raw))
  local key=self:files_key()
  resident=key and {key=key,path=self.path,detail_days=self.detail_days,restored=false,data=data} or nil
  return true
end

return M
