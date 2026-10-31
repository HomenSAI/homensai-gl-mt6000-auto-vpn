-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- platform.lua: the platform guards of the Python Auto for the Lua supervisor (2.0.0-lua line).
-- Ports: native_platform (PINS, assess, wait_quiet); mt3000_manual_platform (_read, _zones, _held_firewall_locks,
-- _workers); native_switch Linux.acceleration (+ fresh_hook_state, appended_hook_state) and slot_contract_verified;
-- preparation_control.auto_blocker (records, boot_id); rollback_recovery vendor_lock_pid / rtp_lock_busy;
-- rtp_boot (assess, ready, prepare). Every function takes the sys table (sys.lua or a test fake).
-- A file hash is cached by its (inode, size, mtime, ctime): the vendor pins are re-hashed only when the file
-- changed, never on every tick (the Python Auto re-hashed ten files every two seconds).
local canon=require('canon')
local py=require('py')
local identity=require('identity')

local M={}
local NULL=canon.null
local function value_error(code) identity.value_error(code) end

M.PINS={
  ['/etc/init.d/firewall']='dbc6e31653ba3d7e57534386cf1a83523318ed9dbb0d793f7947520e33b0e776',
  ['/etc/rc.common']='ebeeedc132a75942ce876465e4636a75f745e468c573fdf9ad058e57e58a0341',
  ['/etc/init.d/dnsmasq']='63cb5858ced4dee214f2cceb8a0de986e344607440fff5bf4eae21af381c9936',
  ['/usr/bin/gl_block_wan_access_exit']='a02a43b46c6722b012745fd5f960f35414b34e011379181cc5c52d98135926ce',
}
M.RTP_LOCK='/tmp/run/rtp2.lock'
M.FIREWALL_LOCKS={'/tmp/run/fw3.lock','/tmp/lock/procd_firewall.lock'}
M.ALLOWED_STALE_LOCK=nil  -- set only while a vendor-rebuild proof reads diagnostics (rollback_recovery)

------------------------------------------------------------------------------------------------------
-- files
------------------------------------------------------------------------------------------------------
-- _read(): a regular file (not a symlink) of at most maximum bytes
function M.read_limited(sys,path,maximum)
  maximum=maximum or 131072
  local st=sys.lstat(path)
  if not st or st.type~='reg' then value_error('UNVERIFIED-FILE') end
  local text=sys.read(path,maximum)
  if text==nil then value_error('UNVERIFIED-FILE') end
  return text
end

local hashes={}  -- path -> {key=, sha=}
function M.sha_file(sys,path,maximum)
  local key=sys.key(path)
  local row=hashes[path]
  if row and row.key==key and key~='absent' then return row.sha end
  local text=maximum and M.read_limited(sys,path,maximum) or sys.read(path)
  if text==nil then value_error('UNVERIFIED-FILE') end
  local sha=canon.sha256(text)
  hashes[path]={key=key,sha=sha}
  return sha
end
function M.forget_hashes() hashes={} end

------------------------------------------------------------------------------------------------------
-- _zones(): the fw3 runtime state (shlex.split with comments, POSIX)
------------------------------------------------------------------------------------------------------
local WHITE={[' ']=true,['\t']=true,['\r']=true,['\n']=true}
function M.shlex_comments(line)
  local tokens,buf,state,have={},{},' ',false
  local i,n=1,#line
  while i<=n do
    local c=string.sub(line,i,i)
    if state==' ' then
      if WHITE[c] then
        if have then tokens[#tokens+1]=table.concat(buf);buf={};have=false end
      elseif c=='#' then break
      elseif c=='\\' then
        if i==n then return nil end
        buf[#buf+1]=string.sub(line,i+1,i+1);have=true;i=i+1
      elseif c=="'" then state="'";have=true
      elseif c=='"' then state='"';have=true
      else buf[#buf+1]=c;have=true end
    elseif state=="'" then
      if c=="'" then state=' ' else buf[#buf+1]=c end
    else
      if c=='"' then state=' '
      elseif c=='\\' then
        if i==n then return nil end
        local d=string.sub(line,i+1,i+1)
        if d=='"' or d=='\\' or d=='$' or d=='`' or d=='\n' then buf[#buf+1]=d else buf[#buf+1]='\\'..d end
        i=i+1
      else buf[#buf+1]=c end
    end
    i=i+1
  end
  if state~=' ' then return nil end
  if have then tokens[#tokens+1]=table.concat(buf) end
  return tokens
end

function M.zones(text)
  if type(text)~='string' or #text==0 or #text>65536 then value_error('STATE-SIZE') end
  local zones,defaults,section,options,named,package,count={},0,nil,{},{},false,0
  local seen={}
  local function finish()
    if section=='zone' then
      local name=options.name
      if type(name)~='string' or #name<1 or #name>64 or not string.find(name,'^[A-Za-z0-9_.-]+$') then value_error('STATE-ZONE-NAME') end
      zones[#zones+1]=name
    end
  end
  for _,line in ipairs(require('fast_policy').splitlines(text)) do
    local words=M.shlex_comments(line)
    if words==nil then value_error('STATE-SYNTAX') end
    if #words>0 then
      if words[1]=='package' then
        if not (#words==2 and words[2]=='fw3_state') or package or section~=nil then value_error('STATE-PACKAGE') end
        package=true
      elseif words[1]=='config' then
        finish()
        count=count+1
        if not package or #words<2 or #words>3 or not (words[2]=='defaults' or words[2]=='zone' or words[2]=='ipset') or count>1024 then value_error('STATE-SECTION') end
        if #words==3 then
          if named[words[3]] then value_error('STATE-DUPLICATE-SECTION') end
          named[words[3]]=true
        end
        section,options=words[2],{}
        if section=='defaults' then defaults=defaults+1 end
      else
        if section==nil or #words~=3 or not (words[1]=='option' or words[1]=='list') then value_error('STATE-OPTION') end
        if words[1]=='option' then
          if options[words[2]]~=nil then value_error('STATE-DUPLICATE') end
          options[words[2]]=words[3]
        else
          if options[words[2]]~=nil and type(options[words[2]])~='table' then value_error('STATE-MIXED-OPTION') end
          options[words[2]]=options[words[2]] or {}
          table.insert(options[words[2]],words[3])
        end
      end
    end
  end
  finish()
  local set={}
  for _,z in ipairs(zones) do if set[z] then value_error('STATE-ZONES') end;set[z]=true end
  if defaults~=1 or not set.lan or not set.wan then value_error('STATE-ZONES') end
  return set
end

------------------------------------------------------------------------------------------------------
-- workers: held firewall locks and vendor processes (two sampled reads per process)
------------------------------------------------------------------------------------------------------
local function band(a,b) return require('attest').band(a,b) end
local function device_numbers(dev)
  local major=(math.floor(dev/256)%4096)+(math.floor(dev/2^32)-math.floor(dev/2^32)%4096)
  local high=math.floor(dev/4096)
  local minor=(dev%256)+(high-high%256)
  return major,minor
end
M.device_numbers=device_numbers

function M.held_firewall_locks(sys)
  local targets={}
  for _,path in ipairs(M.FIREWALL_LOCKS) do
    local link=sys.lstat(path)
    if link and link.type=='lnk' then value_error('UNVERIFIED-LOCK-PATH') end
    local st=sys.stat(path)
    if st then
      if st.type~='reg' then value_error('UNVERIFIED-LOCK-FILE') end
      local major,minor=device_numbers(st.dev)
      targets[string.format('%d:%d:%d',major,minor,st.ino)]=true
    end
  end
  local held=0
  local text=M.read_limited(sys,'/proc/locks',131072)
  if string.find(text,'[\128-\255]') then value_error('UNVERIFIED-LOCK-RECORD') end
  for _,line in ipairs(require('fast_policy').splitlines(text)) do
    local words={}
    for w in string.gmatch(line,'%S+') do words[#words+1]=w end
    local offset=(#words>1 and words[2]=='->') and 2 or 1
    local kind=words[offset+1]
    if #words~=offset+7 or not (kind=='FLOCK' or kind=='POSIX' or kind=='OFDLCK' or kind=='LEASE') then value_error('UNVERIFIED-LOCK-RECORD') end
    local a,b,c=string.match(words[offset+5],'^([^:]*):([^:]*):([^:]*)$')
    local x,y,z=py.int_auto('0x'..(a or '')),py.int_auto('0x'..(b or '')),py.int(c or '')
    if not (a and string.find(a,'^%x+$') and string.find(b,'^%x+$') and string.find(c,'^%d+$')) or not x or not y or not z then value_error('UNVERIFIED-LOCK-IDENTITY') end
    if targets[string.format('%d:%d:%d',x,y,z)] then held=held+1 end
  end
  return held
end

local function basename(arg)
  local s=string.gsub(arg,'/+$','')
  return string.match(s,'([^/]*)$') or ''
end
local WORKERS={fw3=true,['rtp2.sh']=true,gl_block_wan_access_exit=true,['tunnel-switch.sh']=true,['vpn-failover-trigger.sh']=true,
  ['vpn-failover-watcher.sh']=true,['wgclient.sh']=true,['hotplug-call']=true,['ovpnclient.sh']=true}
local INIT={['/etc/init.d/firewall']=true,['/etc/init.d/dnsmasq']=true,['/etc/init.d/network']=true}

local function tunnel_switch_locks(sys)
  for _,name in ipairs(sys.dir('/var/run') or {}) do
    if string.sub(name,1,13)=='tunnel-switch' and string.sub(name,-5)=='.lock' then return true end
  end
  return false
end
M.tunnel_switch_locks=tunnel_switch_locks

local function stat_tail(raw)
  local last=nil
  local start=1
  while true do local i=string.find(raw,') ',start,true);if not i then break end;last=i;start=i+1 end
  if not last then value_error('PROCESS-IDENTITY') end
  local tail={}
  for w in string.gmatch(string.sub(raw,last+2),'%S+') do tail[#tail+1]=w end
  return tail
end

-- _workers(deadline): {time, busy, verified=true}; raises when a live process could not be read
function M.workers(sys,deadline)
  if deadline and sys.clock()>=deadline then value_error('MT3000-COLLECTION-DEADLINE') end
  local busy=M.held_firewall_locks(sys)
  local entries=sys.dir('/proc')
  if not entries then value_error('PROCESS-LIST') end
  if #entries>4096 then value_error('PROCESS-LIMIT') end
  for _,name in ipairs(entries) do
    if deadline and sys.clock()>=deadline then value_error('MT3000-COLLECTION-DEADLINE') end
    if string.find(name,'^%d+$') then
      local base='/proc/'..name
      local ok,counted=pcall(function()
        local raw=sys.read(base..'/stat',8192)
        if not raw then value_error('PROCESS-READ') end
        local tail=stat_tail(raw)
        if string.match(raw,'^(%S*)')~=name or #tail<20 then value_error('PROCESS-IDENTITY') end
        local flags=tonumber(tail[7])
        if not flags then value_error('PROCESS-IDENTITY') end
        if tail[1]=='Z' or tail[1]=='X' or band(flags,0x00200000)~=0 then return 0 end
        local command=sys.read(base..'/cmdline',8192)
        if not command or command=='' or string.sub(command,-1)~='\0' then value_error('PROCESS-COMMAND') end
        local args={}
        for a in string.gmatch(string.sub(command,1,-2)..'\0','([^%z]*)%z') do args[#args+1]=require('kernel').decode(a) end
        local wchan=sys.read(base..'/wchan',256)
        if wchan==nil then value_error('PROCESS-READ') end
        wchan=string.match(wchan,'^%s*(.-)%s*$')
        local after=sys.read(base..'/stat',8192)
        if not after then value_error('PROCESS-READ') end
        local after_tail=stat_tail(after)
        if #after_tail<20 or after_tail[20]~=tail[20] or after_tail[2]~=tail[2] then value_error('PROCESS-IDENTITY-CHANGED') end
        local hit=false
        for _,a in ipairs(args) do if WORKERS[basename(a)] or INIT[a] then hit=true end end
        if hit or wchan=='locks_lock_inode_wait' then return 1 end
        return 0
      end)
      if ok then busy=busy+counted
      elseif sys.exists(base) then value_error('PROCESS-READ-UNVERIFIED') end
    end
  end
  local lock=sys.lstat(M.RTP_LOCK)
  if tunnel_switch_locks(sys) or (lock and lock.type=='lnk') or (lock and M.mt3000_rtp_lock_busy(sys)) then busy=busy+1 end
  return {time=sys.wall(),busy=busy,verified=true}
end

------------------------------------------------------------------------------------------------------
-- rollback_recovery: the vendor RTP lock
------------------------------------------------------------------------------------------------------
function M.vendor_lock_pid(sys)
  if tunnel_switch_locks(sys) then value_error('VENDOR-WORKER-BUSY') end
  local st=sys.lstat(M.RTP_LOCK)
  if st and st.type=='lnk' then value_error('VENDOR-WORKER-BUSY') end
  if not st then return nil end
  local raw=sys.read(M.RTP_LOCK)
  if raw==nil then return nil end
  local text=#raw<=32 and string.match(raw,'^%s*(.-)%s*$') or ''
  if not string.find(text,'^[1-9]%d*$') or #text>10 then value_error('VENDOR-WORKER-BUSY') end
  local command=sys.read('/proc/'..text..'/cmdline')
  if command==nil then return tonumber(text) end  -- dead pid: its EXIT trap never ran
  if string.find(command,'rtp2',1,true) then value_error('VENDOR-WORKER-BUSY') end
  return tonumber(text)
end
-- Any vendor lock is busy, except the one stale lock a rebuild proof has just proved.
function M.rtp_lock_busy(sys)
  if not sys.lstat(M.RTP_LOCK) then return false end
  local allowed=M.ALLOWED_STALE_LOCK
  if allowed==nil then return true end
  local ok,pid=pcall(M.vendor_lock_pid,sys)
  if not ok then return true end
  return pid~=allowed
end
-- mt3000_manual_platform._rtp_lock_busy
function M.mt3000_rtp_lock_busy(sys)
  if M.ALLOWED_STALE_LOCK==nil then return true end
  return M.rtp_lock_busy(sys)
end

local function queues_busy(sys)
  for _,name in ipairs({'gl_reload_service','gl_restart_service'}) do
    local path='/var/run/'..name
    local link=sys.lstat(path)
    if link then
      if link.type=='lnk' then return true end
      local entries=sys.dir(path)
      if link.type~='dir' or entries==nil or #entries>0 then return true end
    end
  end
  return false
end
M.queues_busy=queues_busy

------------------------------------------------------------------------------------------------------
-- native_platform.assess(board, data)
------------------------------------------------------------------------------------------------------
function M.assess(sys,board,data)
  local name=canon.is_object(board) and board.board_name or nil
  if name=='glinet,gl-mt6000' then return {} end
  if name~='glinet,mt3000-snand' then return {'UNSUPPORTED-BOARD'} end
  local errors={}
  local release=board.release
  if not canon.is_object(release) then release=canon.object({}) end
  if board.model~='GL.iNet GL-MT3000' or board.kernel~='5.4.211' or release.target~='mediatek/mt7981' or sys.machine()~='aarch64' then
    errors[#errors+1]='MT3000-FIRMWARE-UNVERIFIED'
  end
  local include=data.firewall_include
  if include==nil then include=canon.object({}) end
  if not canon.is_object(include) or include.path~='/usr/bin/rtp2.sh' or include.type~='script' or include.reload~='0'
     or not (include.enabled==nil or include.enabled==NULL or include.enabled=='1') then
    errors[#errors+1]='FW3-INCLUDE-CONTRACT-UNVERIFIED'
  end
  local ok=pcall(function()
    if sys.exists('/sbin/fw4') or sys.exists('/usr/sbin/fw4') then errors[#errors+1]='MT3000-FIREWALL-UNVERIFIED' end
    local text=M.read_limited(sys,'/var/run/fw3.state',65536)
    if not canon.valid_utf8(text) then value_error('STATE-UTF8') end
    local zones=M.zones(text)
    local settings=data.settings;if settings==nil then settings=canon.object({}) end
    local roles=identity.roles(settings)
    for _,zone in pairs(roles) do if not zones[zone] then errors[#errors+1]='FW3-SELECTED-ZONE-UNVERIFIED';break end end
  end)
  if not ok then errors[#errors+1]='FW3-RUNTIME-STATE-UNVERIFIED' end
  local pinned=pcall(function()
    for _,path in ipairs({'/etc/init.d/firewall','/etc/rc.common','/etc/init.d/dnsmasq','/usr/bin/gl_block_wan_access_exit'}) do
      if M.sha_file(sys,path,262144)~=M.PINS[path] then errors[#errors+1]='VENDOR-CODE-CHANGED' end
    end
  end)
  if not pinned then errors[#errors+1]='VENDOR-CODE-UNVERIFIED' end
  local quiet=pcall(function()
    if M.workers(sys,sys.clock()+2).busy>0 then errors[#errors+1]='VENDOR-WORKER-BUSY' end
    if queues_busy(sys) then errors[#errors+1]='VENDOR-WORKER-BUSY' end
  end)
  if not quiet then errors[#errors+1]='VENDOR-WORKER-QUIET-UNVERIFIED' end
  return py.unique(errors)
end

-- wait_quiet(): RTP backgrounds DNS restart and firewall reload; command exit is not done.
function M.wait_quiet(sys,seconds,sample,stopped)
  seconds=seconds or 20
  sample=sample or function(end_) return M.workers(sys,end_) end
  local clock=sys.clock
  local end_=clock()+seconds
  local quiet,count,unverified=nil,0,false
  while clock()<end_ do
    local ok,row=pcall(sample,end_)
    local busy,queues
    if ok then
      ok=type(row)=='table' and row.verified==true and type(row.busy)=='number' and row.busy%1==0 and row.busy>=0 and row.busy<=16
      if ok then busy=row.busy;queues=queues_busy(sys) end
    end
    if not ok then
      if type(row)=='table' and type(row.code)=='string' and not row.value_error then error(row,0) end  -- Stop/revision: not a busy worker
      quiet=nil;count=0;unverified=true
      sys.sleep(math.min(0.75,math.max(0,end_-clock())))
    else
      if clock()>=end_ then break end
      if busy>0 or queues then quiet=nil;count=0
      else
        quiet=quiet or clock();count=count+1
        if clock()-quiet>=3 and count>=4 then return end
      end
      sys.sleep(math.min(0.75,math.max(0,end_-clock())))
    end
  end
  value_error(unverified and 'VENDOR-WORKER-QUIET-UNVERIFIED' or 'VENDOR-WORKER-BUSY')
end

------------------------------------------------------------------------------------------------------
-- acceleration (Linux.acceleration: one read per 60 s per process, like Python's ACCELERATION_CACHE)
------------------------------------------------------------------------------------------------------
local function lower(s) return string.lower(s) end
local function hook_message(message)  -- fullmatch (?:hnat[ _]*)?hook(?:_toggle)?\s*(?:(?:is|state|status|currently|:|=)\s*)*(enabled|disabled)[ !.]*
  local s=message
  if string.sub(s,1,4)=='hnat' then s=(string.gsub(string.sub(s,5),'^[ _]*','')) end
  if string.sub(s,1,4)~='hook' then return nil end
  s=string.sub(s,5)
  if string.sub(s,1,7)=='_toggle' then s=string.sub(s,8) end
  s=string.match(s,'^%s*(.*)$')
  while true do
    local moved=false
    for _,w in ipairs({'currently','status','state','is',':','='}) do
      if string.sub(s,1,#w)==w then s=string.match(string.sub(s,#w+1),'^%s*(.*)$');moved=true;break end
    end
    if not moved then break end
  end
  return string.match(s,'^(enabled)[ !%.]*$') or string.match(s,'^(disabled)[ !%.]*$')
end
M.hook_message=hook_message

function M.fresh_hook_state(lines,after)
  local list=require('fast_policy').splitlines(lines)
  for index=#list,1,-1 do
    local line=list[index]
    local stamp,message=string.match(line,'^%[%s*([%d%.]+)%]%s*(.*)$')
    local valid=stamp and (string.find(stamp,'^%d+$') or string.find(stamp,'^%d+%.%d+$'))
    if valid and tonumber(stamp)>=after then
      message=lower(message)
      if not string.find(message,'going to',1,true) then
        local v,state=string.match(message,'^value=([01]), hook is (%a+) now!$')
        if v and state==(v=='0' and 'disabled' or 'enabled') then return state end
        local m=hook_message(message)
        if m then return m end
      end
    end
  end
  return 'unknown'
end
function M.appended_hook_state(before,after)
  if not before or before=='' then return 'unknown' end
  local fp=require('fast_policy')
  local blines=fp.splitlines(before)
  local marker=blines[#blines]
  local lines=fp.splitlines(after)
  local index,count=nil,0
  for i,l in ipairs(lines) do if l==marker then count=count+1;index=index or i end end
  if count~=1 then return 'unknown' end
  local rest={}
  for i=index+1,#lines do rest[#rest+1]=lines[i] end
  return M.fresh_hook_state(table.concat(rest,'\n'),0)
end

local function is_mount(sys,path)
  local text=sys.read('/proc/self/mounts')
  if not text then return false end
  for line in string.gmatch(text,'[^\n]+') do
    local _,point=string.match(line,'^(%S+)%s+(%S+)')
    if point==path then return true end
  end
  return false
end

M.ACCELERATION_TTL=60
local accel_cache=nil
function M.acceleration(sys)
  if accel_cache and sys.clock()-accel_cache.time>=0 and sys.clock()-accel_cache.time<M.ACCELERATION_TTL then return py.copy(accel_cache.value) end
  local loaded={}
  for _,m in ipairs({'mtkhnat','mtk_hnat','shortcut_fe','fast_classifier'}) do if sys.exists('/sys/module/'..m) then loaded[#loaded+1]=m end end
  local rc,before=sys.exec({'dmesg'})
  if rc~=0 then before=nil else before=require('kernel').decode(before) end
  local runtime=sys.read('/sys/kernel/debug/hnat/hook_toggle',257)
  if runtime==nil then runtime='unknown' else runtime=string.match(runtime,'^%s*(.-)%s*$') end
  local hook_log={}
  if runtime=='' then
    local rc2,kernel_text=sys.exec({'dmesg'})
    if rc2==0 then
      kernel_text=require('kernel').decode(kernel_text)
      runtime=M.appended_hook_state(before,kernel_text)
      local lines={}
      for _,line in ipairs(require('fast_policy').splitlines(kernel_text)) do
        local l=lower(line)
        if string.find(l,'hook',1,true) and (string.find(l,'hnat',1,true) or string.find(l,'toggle',1,true)) then
          lines[#lines+1]=#line>200 and string.sub(line,-200) or line
        end
      end
      for i=math.max(1,#lines-2),#lines do hook_log[#hook_log+1]=lines[i] end
    end
  end
  local value=canon.object({loaded=canon.array(loaded),hnat_runtime=(runtime=='enabled' or runtime=='disabled') and runtime or 'unknown',
    hnat_state_text=py.prefix(runtime,256),hook_log=canon.array(hook_log),debugfs_mounted=is_mount(sys,'/sys/kernel/debug'),
    hook_exists=sys.exists('/sys/kernel/debug/hnat/hook_toggle')})
  accel_cache={value=py.copy(value),time=sys.clock()}
  return value
end
function M.forget_acceleration() accel_cache=nil end

------------------------------------------------------------------------------------------------------
-- preparation_control.auto_blocker
------------------------------------------------------------------------------------------------------
local BOOT='^%x%x%x%x%x%x%x%x%-%x%x%x%x%-%x%x%x%x%-%x%x%x%x%-%x%x%x%x%x%x%x%x%x%x%x%x$'
local function lower_hex(s) return not string.find(s,'[A-F]') end
local ACTIONS={['wg-autostart']=true,['ovpn-autostart']=true,['source-autostart']=true,['target-autostart']=true,['vpn-boot']=true,
  ['sfe-boot']=true,hnat=true,['flow-offload']=true,['sfe-autoload']=true}
function M.preparation_records(sys,persist)
  local directory=persist..'/preparation-changes'
  local st=sys.lstat(directory)
  if st and st.type=='lnk' then value_error('PREPARATION-BACKUP-UNVERIFIED') end
  if not st then return {} end
  if st.type~='dir' then value_error('PREPARATION-BACKUP-UNVERIFIED') end
  local names=sys.dir(directory) or {}
  if #names>64 then value_error('PREPARATION-HISTORY-LIMIT') end
  local rows={}
  for _,name in ipairs(names) do
    local path=directory..'/'..name
    local fst=sys.lstat(path)
    if not string.find(name,'^%x+%.json$') or #name~=37 or not lower_hex(name) or not fst or fst.type~='reg' or fst.size>65536 then
      value_error('PREPARATION-BACKUP-UNVERIFIED')
    end
    local text=sys.read(path,4*1024*1024)
    local ok,envelope=pcall(canon.decode,text or '')
    if not ok then value_error('PREPARATION-RECOVERY-REQUIRED') end
    local data=canon.is_object(envelope) and envelope.data or nil
    local function stamp(v) local x=canon.number(v);return x~=nil and type(v)~='boolean' and x>0 and x<1e12 end
    if not canon.is_object(data) or envelope.sha256~=canon.digest(data) or type(data.action)~='string' or not ACTIONS[data.action]
       or data.state~='VERIFIED' or type(data.restart_required)~='boolean' or type(data.boot_id)~='string'
       or not string.find(data.boot_id,BOOT) or not lower_hex(data.boot_id) or not stamp(data.time) or not stamp(data.verified_at)
       or not canon.is_object(data.before) or not (data.board=='mt3000' or data.board=='mt6000')
       or type(data.revision)~='string' or #data.revision~=64 or not string.find(data.revision,'^[a-f0-9]+$') then
      value_error('PREPARATION-RECOVERY-REQUIRED')
    end
    rows[#rows+1]=data
  end
  return rows
end
function M.boot_id(sys)
  local text=M.read_limited(sys,'/proc/sys/kernel/random/boot_id',128)
  local value=string.match(text,'^%s*(.-)%s*$')
  if not string.find(value,BOOT) or not lower_hex(value) then value_error('PREPARATION-PLATFORM-UNVERIFIED') end
  return value
end
function M.auto_blocker(sys,persist)
  local ok,result=pcall(function()
    local rows=M.preparation_records(sys,persist)
    if #rows>0 then
      local boot=nil
      for _,row in ipairs(rows) do
        if row.restart_required then
          boot=boot or M.boot_id(sys)
          if row.boot_id==boot then return 'PREPARATION-RESTART-REQUIRED' end
        end
      end
    end
    return nil
  end)
  if not ok then return 'PREPARATION-RECOVERY-REQUIRED' end
  return result
end

-- preparation_status.snapshot(settings): the persistent MT3000 preparation checks
M.AUTOLOAD_SHA='8aad0842bbf4de46c61719fba3237d3127cee632f4312807ff3b591d388b2f49'
function M.preparation_snapshot(sys,settings)
  local checks={}
  local function add(code,state) checks[#checks+1]={code=code,state=state} end
  local function flag(name,expected)
    local rc,out=sys.exec({'uci','-q','get',name},{timeout=2})
    if rc==1 then return 'fail' end
    if rc~=0 or #out>128 or string.find(out,'[\128-\255]') then return 'unknown' end
    return string.match(out,'^%s*(.-)%s*$')==expected and 'pass' or 'fail'
  end
  local board=nil
  local st=sys.lstat('/tmp/sysinfo/board_name')
  if st and st.type~='lnk' and st.size<=128 then
    local text=sys.read('/tmp/sysinfo/board_name',128)
    if text and not string.find(text,'[\128-\255]') then board=string.match(text,'^%s*(.-)%s*$') end
  end
  if board~='glinet,mt3000-snand' then
    return {scope='persistent-mt3000-preparation',state=(board and board~='') and 'unsupported' or 'unknown',checks={},native_permission=false,external_lan_verified=false}
  end
  add('PREP-HNAT-CONFIG',flag('mtkhnat.global.enable','0'))
  local ok,selected=pcall(identity.roles,settings or canon.object({}))
  if not ok then selected={} end
  for _,role in ipairs({'source','target'}) do
    local name=selected[role]
    add('PREP-'..string.upper(role)..'-AUTOSTART',name and flag('network.'..name..'.auto','0') or 'unknown')
  end
  for _,pair_ in ipairs({{'vpn-client','PREP-STOCK-VPN-BOOT'},{'shortcut-fe','PREP-SFE-BOOT'}}) do
    local links=sys.dir('/etc/rc.d')
    if not links then add(pair_[2],'unknown')
    else
      local active=false
      for _,name in ipairs(links) do
        if string.sub(name,1,1)=='S' and string.find(string.sub(name,2,3),'^%d%d$') and string.sub(name,4)==pair_[1] then active=true end
      end
      add(pair_[2],active and 'fail' or 'pass')
    end
  end
  local autoload='/etc/modules.d/09-shortcut-fe'
  local saved='/etc/homensai-vpn/disabled-module-autoload/09-shortcut-fe'
  local state
  if sys.lstat(autoload) then state='fail'
  else
    local s=sys.lstat(saved)
    if not s or s.type~='reg' or s.size>4096 then state='unknown'
    else
      local text=sys.read(saved,4096)
      state=(text and canon.sha256(text)==M.AUTOLOAD_SHA) and 'pass' or 'unknown'
    end
  end
  add('PREP-SFE-AUTOLOAD',state)
  local mok,modules=pcall(function()
    local s=sys.lstat('/proc/modules')
    if not s or s.type=='lnk' or s.size>262144 then value_error('MODULES') end
    local text=sys.read('/proc/modules',262144)
    if not text or string.find(text,'[\128-\255]') then value_error('MODULES') end
    local set={}
    for line in string.gmatch(text,'[^\n]+') do local first=string.match(line,'^%s*(%S+)');if first then set[first]=true end end
    return set
  end)
  if not mok then add('PREP-SFE-RUNTIME','unknown')
  else add('PREP-SFE-RUNTIME',(modules.shortcut_fe or modules.shortcut_fe_ipv6 or modules.fast_classifier) and 'fail' or 'pass') end
  local all=true
  for _,c in ipairs(checks) do if c.state~='pass' then all=false end end
  return {scope='persistent-mt3000-preparation',state=all and 'pass' or 'incomplete',checks=checks,native_permission=false,external_lan_verified=false}
end

------------------------------------------------------------------------------------------------------
-- the pinned stock programs
------------------------------------------------------------------------------------------------------
function M.audit_pins(sys,lib)
  local text=sys.read((lib or '/usr/lib/homensai-vpn')..'/native-audit-hashes.json')
  if not text then value_error('VENDOR-CODE-UNVERIFIED') end
  local value=canon.decode(text)
  if not canon.is_object(value) then value_error('VENDOR-CODE-UNVERIFIED') end
  return value
end
function M.slot_contract_verified(sys,lib)
  local ok,result=pcall(function()
    local pins=M.audit_pins(sys,lib)
    for _,name in ipairs({'/usr/bin/rtp2.sh','/usr/bin/setup_instance'}) do
      if pins[name]==nil or M.sha_file(sys,name)~=pins[name] then return false end
    end
    return true
  end)
  return ok and result==true
end

------------------------------------------------------------------------------------------------------
-- rtp_boot: the exact pinned stock boot prefix (empty runtime directories and the zero-byte RTP gate)
------------------------------------------------------------------------------------------------------
M.RTP_BOOT_PINS={['/etc/init.d/vpn-client']='3b751f0691202bc930b8113d7b55d0a38003369c015c672d0797723f1aa79e9a',
  ['/usr/bin/rtp2.sh']='d6863630241e0bc68f56cc1eb8ccca45006083c1166e742e8500b28b5e2a544e'}
local RTP_CODE='RTP-BOOT-PRECONDITION-UNVERIFIED'
local function rtp_refuse() value_error(RTP_CODE) end

local euid=nil
function M.rtp_checked(sys,path,opts)
  opts=opts or {}
  local info=sys.lstat_exact(path)
  if not info then if opts.optional then return nil end;rtp_refuse() end
  euid=euid or sys.euid()
  local kind_ok=(opts.directory and info.type=='dir') or ((not opts.directory) and info.type=='reg')
  local writable=math.floor(info.mode/2)%2==1 or math.floor(info.mode/16)%2==1  -- st_mode & 0o022
  if info.type=='lnk' or info.uid~=euid or not kind_ok or (writable and not opts.temporary_root)
     or ((not opts.directory) and info.size~=0) then rtp_refuse() end
  if opts.temporary_root and info.mode%4096~=1023 then rtp_refuse() end  -- S_IMODE == 0o1777
  return info
end
function M.rtp_contract(sys)
  for name,sha in pairs(M.RTP_BOOT_PINS) do
    local st=sys.lstat(name)
    if not st or st.type~='reg' or st.size>262144 or M.sha_file(sys,name)~=sha then rtp_refuse() end
  end
  for _,pair_ in ipairs({{'/tmp/sysinfo/board_name','glinet,mt3000-snand'},{'/etc/glversion','4.11.0'}}) do
    local st=sys.lstat(pair_[1])
    local text=st and st.type=='reg' and st.size<=128 and sys.read(pair_[1],128) or nil
    if not text or string.match(text,'^%s*(.-)%s*$')~=pair_[2] then rtp_refuse() end
  end
  M.rtp_checked(sys,'/tmp',{directory=true,temporary_root=true})
  M.rtp_checked(sys,'/tmp/run',{directory=true})
end
function M.rtp_ready(sys)
  M.rtp_contract(sys)
  for _,name in ipairs({'/tmp/resolv.conf.d','/tmp/hosts.vpn'}) do M.rtp_checked(sys,name,{directory=true}) end
  M.rtp_checked(sys,'/tmp/run/vpn-client-booted')
  return true
end
function M.rtp_assess(sys)
  M.rtp_contract(sys)
  local ready=true
  for _,name in ipairs({'/tmp/resolv.conf.d','/tmp/hosts.vpn'}) do if M.rtp_checked(sys,name,{directory=true,optional=true})==nil then ready=false end end
  if M.rtp_checked(sys,'/tmp/run/vpn-client-booted',{optional=true})==nil then ready=false end
  return {safe=true,ready=ready,kernel_verified=false}
end
-- rtp_boot.prepare(revision): under the control lock, only for the running pair session of this revision
function M.rtp_prepare(env,sys,revision)
  local ctl=require('auto_control')
  local T=require('transaction')
  local pair=require('pair')
  local ok,result=pcall(function()
    return env.run.lock(function()
      T.require_control_revision(env,revision)
      local requested=pair.intent(env);local state=pair.read_state(env)
      if requested.mode~='on' or requested.revision~=revision or not py.eq(requested.id,state.id) or state.revision~=revision
         or not (state.phase=='STARTING' or state.phase=='RUNNING' or state.phase=='HELD') then ctl.refuse('CLIENT-STOP') end
      M.rtp_assess(sys)
      local dirs={'/tmp/resolv.conf.d','/tmp/hosts.vpn'}
      local marker='/tmp/run/vpn-client-booted'
      local before_dirs={}
      for i,path in ipairs(dirs) do before_dirs[i]=M.rtp_checked(sys,path,{directory=true,optional=true})~=nil end
      local before_marker=M.rtp_checked(sys,marker,{optional=true})~=nil
      if before_dirs[1] and before_dirs[2] and before_marker then M.rtp_ready(sys);return {prepared=true,changed=false,kernel_verified=false} end
      local record=canon.object({revision=revision,state='PREPARED',before=canon.object({directories=canon.array(before_dirs),marker=before_marker})})
      ctl.write_json(env.run,env.runtime..'/rtp-boot-preparation.json',record)
      for _,path in ipairs(dirs) do
        T.require_control_revision(env,revision)
        if M.rtp_checked(sys,path,{directory=true,optional=true})==nil then sys.mkdir(path,493) end
        M.rtp_checked(sys,path,{directory=true})
      end
      T.require_control_revision(env,revision)
      if M.rtp_checked(sys,marker,{optional=true})==nil then sys.create_exclusive(marker,'') end
      M.rtp_ready(sys)
      T.require_control_revision(env,revision)
      record.state='VERIFIED';ctl.write_json(env.run,env.runtime..'/rtp-boot-preparation.json',record)
      return {prepared=true,changed=true,kernel_verified=false}
    end,env.runtime)
  end)
  if ok then return result end
  if type(result)=='table' and result.code=='CLIENT-STOP' then error(result,0) end
  if type(result)=='table' and result.code and not result.value_error and result.code~=RTP_CODE then error(result,0) end
  ctl.refuse(RTP_CODE)
end

return M
