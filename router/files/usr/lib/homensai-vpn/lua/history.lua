-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- history.lua: native_history.History for the Lua supervisor (2.0.0-lua-alpha2).
--
-- Same files as Python (journal layout, schema 2: state native-history.json + backup, append-only archive
-- native-history.events.jsonl; a schema-1 file is migrated on the first write), same item fields, attempt/episode
-- correlation, METRICS counters (counter_version 2), pruning and the 2 MB detail budget, byte for byte.
-- public()/read_public stay with the monitor (it serves the page from the state only).
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
-- Journal layout (schema 2, docs/architecture/HISTORY-JOURNAL-2026-11-01.ru.md), byte for byte the files
-- native_history.py writes:
--   native-history.json          the STATE: the schema-1 data without 'events', plus 'tail' (last TAIL retained
--                                events, complete), 'index' ([sequence, time, counted_metrics|null, line bytes] per
--                                retained event) and 'archive_lines'/'archive_bytes'; envelope schema 2
--   native-history.backup.json   the previous state (rename)
--   native-history.events.jsonl  the append-only ARCHIVE: '<sha256 of the JSON text> <canonical JSON>\n' per event
--   native-history.v1.json       the schema-1 file a migration started from
-- Per event: state first (atomic), then one archive line (append + fsync). A writer whose archive size differs
-- from 'archive_bytes' rebuilds it from its verified lines plus the tail; events found nowhere leave the index and
-- are counted in 'archive_gap'. Compaction: more than 25 % stale lines or more than COMPACT_BYTES.
------------------------------------------------------------------------------------------------------
M.ARCHIVE='native-history.events.jsonl'
M.V1='native-history.v1.json'
M.TAIL=100
M.STATE_BYTES=3*1024*1024
M.READ_BYTES=4*1024*1024
M.ARCHIVE_READ_BYTES=8*1024*1024
M.COMPACT_BYTES=M.RETENTION_BYTES+M.RETENTION_BYTES/4
local LINE_OVERHEAD=66
local STATE_ONLY={tail=true,index=true,archive_lines=true,archive_bytes=true}

function M.envelope_bytes(raw,schema)
  return '{"data":'..raw..',"schema":'..tostring(schema or 1)..',"sha256":"'..canon.sha256(raw)..'"}'
end
local function state_bytes(state) return M.envelope_bytes(encoded(state),2) end
M.state_bytes=state_bytes

function M.archive_line(event)
  local text=encoded(event)
  return canon.sha256(text)..' '..text..'\n'
end

-- archive_entries(raw) -> {{sequence, line}, ...}: the verified complete lines in file order. The piece after the
-- last newline (a torn append) and any line whose checksum or shape fails are skipped.
function M.archive_entries(raw)
  local out={}
  local pos=1
  while true do
    local nl=string.find(raw,'\n',pos,true)
    if not nl then break end
    local piece=string.sub(raw,pos,nl-1)
    pos=nl+1
    if #piece>=LINE_OVERHEAD and string.sub(piece,65,65)==' ' then
      local body=string.sub(piece,66)
      if canon.sha256(body)==string.sub(piece,1,64) then
        local s=string.match(body,'"sequence":(%d+)[,}]')
        if s and #s<=16 then out[#out+1]={tonumber(s),piece..'\n'} end
      end
    end
  end
  return out
end

-- state_of(data) -> state, lines: schema-1 data (with events) as the state plus its archive lines
function M.state_of(data)
  local state=canon.object({})
  for k,v in pairs(data) do if k~='events' then state[k]=v end end
  local events=data.events
  local lines,index,total={},{},0
  for i,row in ipairs(events) do
    local line=M.archive_line(row)
    lines[i]=line;total=total+#line
    local cm=row.counted_metrics
    if cm==nil then cm=NULL end
    index[i]=canon.array({row.sequence,row.time,cm,#line})
  end
  local tail={}
  for i=math.max(1,#events-M.TAIL+1),#events do tail[#tail+1]=events[i] end
  state.tail=canon.array(tail);state.index=canon.array(index)
  state.archive_lines=#lines;state.archive_bytes=total
  return state,lines
end

function M.empty()
  return canon.object({sequence=0,events=canon.array({}),months=canon.object({}),last_key=NULL,last_time=NULL,timezone='Europe/Berlin'})
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
    backup=directory..'/native-history.backup.json',archive=directory..'/'..M.ARCHIVE,v1=directory..'/'..M.V1,
    lock=directory..'/native-history.lock',restored=false},History)
end

function History:localdate(fmt,t)
  local f=self.env.localdate or os.date
  return f(fmt,math.floor(num(t)))
end

-- file helpers over env.run.fs (size/append/rename are optional: fakes without them get the same bytes)
local function fs_size(fs,path)
  if fs.size then return fs.size(path) end
  local text=fs.read(path)
  return text and #text or nil
end
local function fs_append(fs,path,text)
  if fs.append then return fs.append(path,text) end
  return fs.write_atomic(path,(fs.read(path) or '')..text)
end

-- Resident copy (plan item 1, CPU): the decoded STATE is kept while both state files read back with the same
-- (inode, size, mtime, ctime) as when this process last loaded or wrote them; every write renames a new file into
-- place, so any change by anyone changes the key. A failed record drops it. In hv-core the monitor (page) and the
-- Auto supervisor share it (the parsed state does not depend on detail_days). Without fs.key nothing is kept.
local resident=nil
function M.forget_resident() resident=nil end
function History:files_key()
  local key=self.env.run.fs.key
  if not key then return nil end
  local a,b=key(self.path),key(self.backup)
  if a==nil or b==nil then return nil end
  return a..'|'..b
end

local function check_common(data,rows)
  if not canon.is_object(data.months) or not is_int(data.sequence) or data.sequence<0 or data.sequence>=2^53 then fail('HISTORY-SCHEMA') end
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
  if rows>10000 or count_keys(data.months)>1200 or not canon.is_object(days) or count_keys(days)>400 then fail('HISTORY-BOUNDS') end
  if data.counter_version==2 then
    for _,name in ipairs({'totals','counted'}) do
      local values=data[name]
      if not canon.is_object(values) then fail('HISTORY-COUNTERS') end
      for key,value in pairs(values) do
        if not METRIC_SET[key] or not is_int(value) or value<0 or value>=2^53 then fail('HISTORY-COUNTERS') end
      end
    end
  end
end
local function check_metrics(cm)
  if not canon.is_array(cm) or #cm>#M.METRICS then fail('HISTORY-COUNTERS') end
  for _,key in ipairs(cm) do if not METRIC_SET[key] then fail('HISTORY-COUNTERS') end end
end
local function check_state(state)
  local tail,index=state.tail,state.index
  if not canon.is_array(tail) or not canon.is_array(index) or #tail>M.TAIL or #tail>#index or state.events~=nil then fail('HISTORY-SCHEMA') end
  check_common(state,#index)
  if state.counter_version~=2 then fail('HISTORY-COUNTERS') end
  for _,name in ipairs({'archive_lines','archive_bytes'}) do
    local v=state[name]
    if not is_int(v) or v<0 or v>=2^53 then fail('HISTORY-SCHEMA') end
  end
  if state.archive_gap~=nil and (not is_int(state.archive_gap) or state.archive_gap<0 or state.archive_gap>=2^53) then fail('HISTORY-SCHEMA') end
  local previous=0
  for _,row in ipairs(index) do
    if not canon.is_array(row) or #row~=4 or not is_int(row[1]) or not (previous<row[1] and row[1]<=state.sequence)
       or not num(row[2]) or not finite(num(row[2])) or not is_int(row[4]) or not (LINE_OVERHEAD<row[4] and row[4]<2^53) then fail('HISTORY-SCHEMA') end
    if row[3]~=NULL then check_metrics(row[3]) end
    previous=row[1]
  end
  local offset=#index-#tail
  for i,row in ipairs(tail) do
    if not canon.is_object(row) or row.sequence~=index[offset+i][1] then fail('HISTORY-SCHEMA') end
    if has(row,'counted_metrics') then check_metrics(row.counted_metrics) end
  end
end

-- read() -> kind, value, text: 'v2' (state) | 'v1' (schema-1 data) | 'new' (empty schema-1 data); main, else backup
function History:read()
  local found=false
  local run=self.env.run
  for index,path in ipairs({self.path,self.backup}) do
    local ok,kind,data,text=pcall(function()
      if run.fs.unsafe and run.fs.unsafe(path,M.READ_BYTES) then
        -- an existing regular file over the limit is a damaged history (HISTORY-CORRUPT, never overwritten), as in
        -- Python; before alpha21 it read as absent and the next record started an empty history (MT3000, 31.10:
        -- the 1.27 MB file over the old 1 MB limit lost 1288 events)
        if not run.fs.unsafe(path,2^53) then found=true end
        fail('HISTORY-PATH')
      end
      local text=run.fs.read(path)
      if text==nil then return nil end
      found=true
      if #text>M.READ_BYTES then fail('HISTORY-SIZE') end
      local envelope=canon.decode(text)
      if not canon.is_object(envelope) then fail('HISTORY-SCHEMA') end
      local data=envelope.data
      if (envelope.schema~=1 and envelope.schema~=2) or not canon.is_object(data) or canon.sha256(encoded(data))~=envelope.sha256 then fail('HISTORY-CHECKSUM') end
      if envelope.schema==2 then
        check_state(data)
        return 'v2',data,text
      end
      if not canon.is_array(data.events) then fail('HISTORY-SCHEMA') end
      check_common(data,#data.events)
      if data.counter_version==2 then
        for _,row in ipairs(data.events) do if has(row,'counted_metrics') then check_metrics(row.counted_metrics) end end
      end
      return 'v1',data,text
    end)
    if ok and kind~=nil then self.restored=index==2;return kind,data,text end
  end
  if found then fail('HISTORY-CORRUPT') end
  return 'new',M.empty(),nil
end

local function read_archive(self)
  local fs=self.env.run.fs
  if fs.unsafe and fs.unsafe(self.archive,M.ARCHIVE_READ_BYTES) then return '' end
  local text=fs.read(self.archive)
  if text==nil or #text>M.ARCHIVE_READ_BYTES then return '' end
  return text
end

-- events_of(state): the retained events in index order (tail from the state, older ones from the archive)
function History:events_of(state)
  local tail={}
  for _,row in ipairs(state.tail) do tail[row.sequence]=row end
  local wanted,any={},false
  for _,row in ipairs(state.index) do if not tail[row[1]] then wanted[row[1]]=true;any=true end end
  local found={}
  if any then
    local ok,raw=pcall(read_archive,self)
    for _,entry in ipairs(M.archive_entries(ok and raw or '')) do
      if wanted[entry[1]] then found[entry[1]]=entry[2] end
    end
  end
  local events={}
  for _,row in ipairs(state.index) do
    local seq=row[1]
    if tail[seq] then events[#events+1]=tail[seq]
    elseif found[seq] then
      local okd,event=pcall(canon.decode,string.sub(found[seq],66,-2))
      if okd and canon.is_object(event) and event.sequence==seq then events[#events+1]=event end
    end
  end
  return canon.array(events)
end

-- load(): the schema-1 shaped data (with events, without the state-only fields): statistics reset/export
function History:load()
  local kind,value=self:read()
  if kind~='v2' then return value end
  local data=canon.object({})
  for k,v in pairs(value) do if not STATE_ONLY[k] then data[k]=v end end
  data.events=self:events_of(value)
  return data
end

-- state(): the state for the page (resident while both files are unchanged); a schema-1 file is converted in
-- memory only (the writer migrates it on flash)
function History:state()
  local key=self:files_key()
  if key and resident and resident.key==key and resident.path==self.path then
    self.restored=resident.restored
    return resident.data
  end
  local kind,value=self:read()
  if kind~='v2' then
    self:migrate(value);value=M.state_of(value)
  end
  if key then resident={key=key,path=self.path,kind=kind,restored=self.restored,data=value}
  else resident=nil end
  return value
end

function History:envelope(data)
  return canon.object({schema=1,data=data,sha256=canon.sha256(encoded(data))})
end
function History:atomic(path,value) self.env.run.fs.write_atomic(path,encoded(value)) end

-- store(data): replace the whole history by schema-1 shaped data whose events are a subset of the archive's (the
-- statistics reset): state (main, backup), then the archive
function History:store(data)
  local fs=self.env.run.fs
  local state,lines=M.state_of(data)
  local text=state_bytes(state)
  fs.write_atomic(self.path,text);fs.write_atomic(self.backup,text)
  fs.write_atomic(self.archive,table.concat(lines))
  resident=nil
end

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
  local rows=data.events or data.tail
  local prior=#rows>0 and rows[#rows].state or nil
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

-- prune(data, now): detail outside [now-detail_days, now] leaves (events, or index+tail; new arrays), aggregates
-- stay; month/day keys beyond the bounds are deleted from the given maps.
function History:prune(data,now)
  local horizon=now-self.detail_days*86400
  local function keep(rows,stamp)
    local kept={}
    for _,row in ipairs(rows) do
      local t=num(stamp(row))
      if t and horizon<=t and t<=now then kept[#kept+1]=row end
    end
    return canon.array(kept)
  end
  if data.events~=nil then data.events=keep(data.events,function(row) return row.time end) end
  if data.index~=nil then
    data.index=keep(data.index,function(row) return row[2] end)
    data.tail=keep(data.tail,function(row) return row.time end)
  end
  local months=sorted_keys(data.months)
  for i=1,#months-1200 do data.months[months[i]]=nil end
  local cutoff=self:localdate('%Y-%m-%d',math.max(0,horizon))
  local days=getd(data,'days',canon.object({}))
  for _,day in ipairs(sorted_keys(days)) do if day<cutoff then days[day]=nil end end
end

-- rebuild(state) -> archive text for the state's index (tail first, else the verified archive line); events found
-- nowhere leave the index ('archive_gap'); the archive accounting is set to the result.
function History:rebuild(state)
  local tail={}
  for _,row in ipairs(state.tail) do tail[row.sequence]=row end
  local wanted,any={},false
  for _,row in ipairs(state.index) do if not tail[row[1]] then wanted[row[1]]=true;any=true end end
  local found={}
  if any then
    for _,entry in ipairs(M.archive_entries(read_archive(self))) do
      if wanted[entry[1]] then found[entry[1]]=entry[2] end
    end
  end
  local kept,lines,total={},{},0
  for _,row in ipairs(state.index) do
    local line
    if tail[row[1]] then line=M.archive_line(tail[row[1]]) else line=found[row[1]] end
    if line then
      row[4]=#line;kept[#kept+1]=row;lines[#lines+1]=line;total=total+#line
    end
  end
  if #kept~=#state.index then
    state.archive_gap=(num(state.archive_gap) or 0)+#state.index-#kept
    state.index=canon.array(kept)
  end
  state.archive_lines=#lines;state.archive_bytes=total
  return table.concat(lines)
end

-- Schema 1 -> 2 on flash: archive, a copy of the old file (native-history.v1.json), then the state (backup, main).
-- The main file stays the schema-1 file until the last step: a power cut anywhere repeats the same migration.
function History:migrate_files(state,lines,text)
  local fs=self.env.run.fs
  fs.write_atomic(self.archive,table.concat(lines))
  fs.write_atomic(self.v1,text)
  local raw=state_bytes(state)
  fs.write_atomic(self.backup,raw);fs.write_atomic(self.path,raw)
end

-- writer_state() -> state, from_main, repaired: the resident state, else a read with the schema-1 migration;
-- then the archive check (size == archive_bytes, else rebuilt)
function History:writer_state()
  local fs=self.env.run.fs
  local key=self:files_key()
  local data,from_main
  if key and resident and resident.key==key and resident.path==self.path and resident.kind=='v2' then
    self.restored=resident.restored;data=resident.data
    from_main=not self.restored
  else
    resident=nil
    local kind,value,text=self:read()
    if kind~='v2' then
      self:migrate(value)
      local state,lines=M.state_of(value)
      if kind=='v1' then self:migrate_files(state,lines,text);self.restored=false end
      return state,kind=='v1',false
    end
    data=value
    local exists
    if fs.key then exists=fs.key(self.path)~='absent' else exists=fs.read(self.path)~=nil end
    from_main=not self.restored and exists
  end
  if (fs_size(fs,self.archive) or 0)~=data.archive_bytes then
    fs.write_atomic(self.archive,self:rebuild(data))
    return data,from_main,true
  end
  return data,from_main,false
end

function History:record(value,now)
  local lock=self.env.history_lock or function(_,fn) return fn() end
  local ok,result=pcall(lock,self.lock,function() return self:_record(value,now) end)
  if not ok then resident=nil;error(result,0) end
  return result
end

-- kept(data): main and backup now hold data; keep it resident (no decode on the next record)
function History:kept(data)
  local key=self:files_key()
  resident=key and {key=key,path=self.path,kind='v2',restored=false,data=data} or nil
end

function History:_record(value,now)
  now=now or self.env.run.wall()
  if type(now)~='number' or not finite(now) or now<0 then fail('HISTORY-CLOCK') end
  local run=self.env.run
  local data,from_main,repaired=self:writer_state()
  -- wall clock stepped back: keep the order, mark the event; its duration is unknown, never zero (review F-56)
  local stepped=not isnone(data.last_time) and now<num(data.last_time)
  if stepped then now=num(data.last_time) end
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
    for _,spec in ipairs({{'required_failures',2},{'required_successes',2}}) do
      local v=raw[spec[1]]
      if is_int(v) and spec[2]<=v and v<=10 then evidence[spec[1]]=v;any=true end
    end
    local rule=raw.failure_rule
    if rule=='model' or rule=='streak' or rule=='heartbeat' or rule=='unstable' then evidence.failure_rule=rule;any=true end
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
    local original_index,original_days=#data.index,count_keys(getd(data,'days',canon.object({})))
    self:prune(data,now)
    if repaired or #data.index~=original_index or count_keys(getd(data,'days',canon.object({})))~=original_days then
      local text=state_bytes(data)
      run.fs.write_atomic(self.backup,text);run.fs.write_atomic(self.path,text)
    end
    if isnone(data.daily_since) then
      local old=state_bytes(data);data.daily_since=canon.float(now);data.days=canon.object({})
      run.fs.write_atomic(self.backup,old);run.fs.write_atomic(self.path,state_bytes(data))
    end
    self:kept(data)
    return false
  end
  local legacy_old=nil
  if not from_main then legacy_old=state_bytes(data) end
  if data.sequence>=2^53-1 then fail('HISTORY-SEQUENCE-LIMIT') end
  data.active_attempt=active;data.retry_episode=episode
  item.time=canon.float(now);item.sequence=data.sequence+1
  if stepped then item.clock_stepped_back=true end
  data.sequence=data.sequence+1;data.last_key=key;data.last_time=canon.float(now)
  local index=data.index
  local excess=#index+1-self.limit
  local dropped=0
  for i=1,math.max(0,excess) do if num(index[i][2])>=now-self.detail_days*86400 then dropped=dropped+1 end end
  if excess>0 then
    local rest={};for i=excess+1,#index do rest[#rest+1]=index[i] end
    index=canon.array(rest);data.index=index
  end
  data.detail_budget_dropped=(num(getd(data,'detail_budget_dropped',0)) or 0)+dropped
  local month=self:localdate('%Y-%m',now);local day=self:localdate('%Y-%m-%d',now)
  if isnone(data.daily_since) then data.daily_since=canon.float(now) end
  if isnone(data.days) then data.days=canon.object({}) end
  item.counted_metrics=self:counters(data,item)
  local line=M.archive_line(item)
  index[#index+1]=canon.array({item.sequence,item.time,item.counted_metrics,#line})
  local tail={};for i,row in ipairs(data.tail) do tail[i]=row end;tail[#tail+1]=item
  data.tail=canon.array(tail)
  if isnone(data.months[month]) then data.months[month]=canon.object({}) end
  if isnone(data.days[day]) then data.days[day]=canon.object({}) end
  for _,totals in ipairs({data.totals,data.months[month],data.days[day]}) do
    for _,metric in ipairs(M.METRICS) do if totals[metric]==nil then totals[metric]=0 end end
  end
  self:prune(data,now)
  -- the detail budget is the archive's retained lines: the oldest events leave the index, counters stay
  index=data.index
  local size=0;for _,row in ipairs(index) do size=size+row[4] end
  local drop=0
  while #index-drop>1 and size>M.RETENTION_BYTES do drop=drop+1;size=size-index[drop][4] end
  if drop>0 then
    local rest={};for i=drop+1,#index do rest[#rest+1]=index[i] end
    index=canon.array(rest);data.index=index
    data.detail_budget_dropped=(num(getd(data,'detail_budget_dropped',0)) or 0)+drop
  end
  local keep={};for i=math.max(1,#index-M.TAIL+1),#index do keep[index[i][1]]=true end
  local trimmed={};for _,row in ipairs(data.tail) do if keep[row.sequence] then trimmed[#trimmed+1]=row end end
  local cut={};for i=math.max(1,#trimmed-M.TAIL+1),#trimmed do cut[#cut+1]=trimmed[i] end
  data.tail=canon.array(cut)
  data.archive_lines=data.archive_lines+1;data.archive_bytes=data.archive_bytes+#line
  local body=nil
  if (data.archive_lines-#index)*4>data.archive_lines or data.archive_bytes>M.COMPACT_BYTES then
    body=self:rebuild(data)  -- compaction: only the retained events (the new one comes from the tail)
  end
  local encoded_state=encoded(data)
  if #encoded_state>M.STATE_BYTES then fail('HISTORY-SIZE') end
  -- main := new state, backup := the previous main (renamed)
  if from_main and run.fs.read(self.path)~=nil and run.fs.rename then
    run.fs.rename(self.path,self.backup)
  else
    run.fs.write_atomic(self.backup,legacy_old or M.envelope_bytes(encoded_state,2))
  end
  run.fs.write_atomic(self.path,M.envelope_bytes(encoded_state,2))
  if body==nil then fs_append(run.fs,self.archive,line) else run.fs.write_atomic(self.archive,body) end
  self:kept(data)
  return true
end

return M
