-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- backend.lua: native_switch.Linux for the Lua Auto supervisor (2.0.0-lua line, plan item 1).
--
--   local backend=require('backend').new(sys)   -- sys.lua on the router, a fake table in tests
--   backend.bind(env)                           -- env.deps / env.net for transaction/pair/rollback/manual
--
-- Same results as Python for the same router state: policy(), order() (section_id/policy_order/policy_hash
-- digests), diagnostic() (board/firmware, accelerators, vendor pins, native_platform.assess, device profile,
-- choose(), resolve_pair freshness, live route bindings, vendor_identity), kernel_fingerprint(),
-- attest_policy(), reorder(), apply() (fast path, else rtp2.sh), guard()/unguard()/devices(), recovery_ready().
--
-- CPU: Python re-ran every read on every tick (43 % of a core while idle). Here every input is cached by a
-- cheap key and every computation by its exact inputs:
--   * UCI-derived JSON (native_policy.lua, inventory.lua, the pair network read) by inode/size/mtime of
--     /etc/config/<pkg> and of the uncommitted delta /tmp/.uci/<pkg>; every own write drops the caches;
--   * vendor file pins by the file's inode/size/mtime/ctime; status.json decoded once per monitor write;
--   * section digests memoised by their canonical text (sha256 may be a process on the router);
--   * kernel_fingerprint/attest by the iptables-save text without counters, the `ip rule` text, the policy text
--     and the selection; `ip route get` answers by the route and rule texts;
--   * the board and the nft binary once per process, acceleration once per 60 s (as Python).
-- Live facts are still read on every call: iptables-save and ip rule/route (small processes), the netifd
-- status (libubus, in process), vendor workers (/proc) and the clock. Nothing is skipped because it "probably
-- did not change": a cache answers only when its key read back equal.
--
-- Temporary bridge (documented, LUA-AUTO-ITEM1): probe()/trace() run the Python agent's probe through
-- lua_bridge.py until the Lua monitor (plan item 2) has its own DNS/HTTPS probes. Only health(), the WAIT-CLIENT
-- confirmation and a manual click use it; a negative health answer is reused for 10 s so a primary that the
-- monitor calls healthy but the bound probe does not cannot start a Python process every tick.
local canon=require('canon')
local ctl=require('auto_control')
local py=require('py')
local identity=require('identity')
local diagnosis=require('diagnosis')
local attest=require('attest')
local platform=require('platform')
local kernel=require('kernel')
local fp=require('fast_policy')

local M={}
local NULL=canon.null
local isnone,eq=py.isnone,py.eq
local refuse=ctl.refuse
local value_error=identity.value_error

M.VERSION=require('version')
M.HELPER='/usr/lib/homensai-vpn/native_policy.lua'
M.INVENTORY='/usr/lib/homensai-vpn/inventory.lua'
M.BRIDGE='/usr/lib/homensai-vpn/lua_bridge.py'
M.LIB='/usr/lib/homensai-vpn'
M.PERSIST='/etc/homensai-vpn'
M.TABLE='homensai_vpn_guard'
M.GUARD_RELEASE_SECONDS=90
M.RTP_TIMEOUT=45
M.TERMS_VERSION='1'
M.TARGETS={'1.1.1.1','8.8.8.8','9.9.9.9'}
M.HEALTH_NEGATIVE_SECONDS=10
-- health(id, reuse): a caller may accept a positive live probe up to `reuse` seconds old. Only the steady manual
-- hold (manual.held_reserve, every pass) does: until the supervisor probes natively each live probe is a Python
-- start through lua_bridge.py (~2 s CPU), measured on the MT3000 as ~30 % of a core while a hold lasted.
-- Transitions always probe live; a failing held channel is also seen by the monitor's own probes.
M.ALLOWED_DIAGNOSTIC={['RESERVE-NOT-CONNECTED']=true,['PROFILE-IDENTITY-CHANGED']=true,['VENDOR-SETTLING']=true,
  ['OBSERVATION-STALE']=true,['VENDOR-IDENTITY-UNKNOWN']=true}

local SAFE_SECTION='^[A-Za-z0-9_]+$'
local function safe_section(s) return type(s)=='string' and #s>=1 and #s<=64 and string.find(s,SAFE_SECTION)~=nil end
local function agent_safe(s) return type(s)=='string' and #s>=1 and #s<=96 and string.find(s,'^[A-Za-z0-9_.:-]+$')~=nil end
local function strip(s) return (string.match(s,'^%s*(.-)%s*$')) end
local function same_list(a,b)
  if type(a)~='table' or type(b)~='table' or #a~=#b then return false end
  for i=1,#a do if a[i]~=b[i] then return false end end
  return true
end
local function getd_none(v) if v==NULL then return nil end;return v end
local function code_of(err)
  if type(err)=='table' and type(err.code)=='string' and not err.value_error then return err.code end
  return nil
end

function M.new(sys)
  local B={process_bindings=nil,fast_path=nil}
  local env=nil
  local caches={}
  local memo_digest={}
  local memo_count=0

  -- digest(value) with a memo of the canonical text (bounded)
  local function digest(value)
    local text=canon.encode(value)
    local hit=memo_digest[text]
    if hit then return hit end
    if memo_count>=2048 then memo_digest={};memo_count=0 end
    hit=canon.sha256(text);memo_digest[text]=hit;memo_count=memo_count+1
    return hit
  end
  B.digest=digest
  identity.set_digest(digest)

  function B.invalidate() caches={} end

  local function uci_key(packages)
    local parts={}
    for _,p in ipairs(packages) do parts[#parts+1]=sys.key('/etc/config/'..p);parts[#parts+1]=sys.key('/tmp/.uci/'..p) end
    return table.concat(parts,'|')
  end
  -- cached(name, key, read): read() runs only when key changed; callers get a deep copy
  local function cached(name,key,read)
    local row=caches[name]
    if row and row.key==key then return row end
    local text,value=read()
    row={key=key,text=text,value=value}
    caches[name]=row
    return row
  end

  ------------------------------------------------------------------------------------------------------
  -- reads
  ------------------------------------------------------------------------------------------------------
  local POLICY_PACKAGES={'route_policy','firewall','homensai_vpn','mtkhnat','glipv6','network'}
  local function policy_row()
    return cached('policy',uci_key(POLICY_PACKAGES),function()
      -- a failed helper or reply is a coded refusal (Python: SubprocessError/ValueError -> NATIVE-SYSTEM-001 in the
      -- loop, POLICY-READ-FAILED inside diagnostic()), never a Lua error that would end the supervisor
      local ok,text=pcall(sys.script,M.HELPER)
      if not ok then value_error('NATIVE-SYSTEM-001') end
      local dok,value=pcall(canon.decode,text)
      if not dok or not canon.is_object(value) then value_error('NATIVE-SYSTEM-001') end
      return text,value
    end)
  end
  function B.policy() return py.copy(policy_row().value) end
  B.policy_text=function() return policy_row().text end

  local INVENTORY_PACKAGES={'network','ovpnclient','wireguard','homensai_vpn','route_policy','firewall'}
  function B.inventory()
    local row=cached('inventory',uci_key(INVENTORY_PACKAGES)..'|'..sys.key('/tmp/sysinfo/board_name'),function()
      local ok,text=pcall(sys.script,M.INVENTORY)
      if not ok then value_error('NATIVE-SYSTEM-001') end
      local dok,data=pcall(canon.decode,text)
      if not dok or not canon.is_object(data) then value_error('NATIVE-SYSTEM-001') end
      for _,key in ipairs({'profiles','servers','native_candidates','wan_interfaces'}) do
        local value=data[key]
        if value==nil then value=canon.array({}) end
        if canon.is_object(value) and next(value)==nil then value=canon.array({}) end
        if not canon.is_array(value) then value_error('POLICY-READ-FAILED') end
        data[key]=value
      end
      local profiles={}
      for _,p in ipairs(data.profiles) do
        if not canon.is_object(p) then value_error('POLICY-READ-FAILED') end
        local id,section=p.id,p.section
        if id==nil then id='' end;if section==nil then section='' end
        if agent_safe(id) and agent_safe(section) then profiles[#profiles+1]=p end
      end
      for _,p in ipairs(profiles) do
        local name=p.name;if name==nil then name=p.id end
        p.name=py.prefix(py.str(name),64)
        if py.truthy(p.interface) and not agent_safe(p.interface) then p.interface=NULL end
      end
      while #profiles>400 do table.remove(profiles) end
      data.profiles=canon.array(profiles)
      return text,data
    end)
    return py.copy(row.value)
  end

  -- status.json (agent.read_json rules), decoded once per monitor write
  function B.status()
    local path=sys.RUNTIME..'/status.json'
    local st=sys.lstat(path)
    if st and st.type=='lnk' then value_error('POLICY-READ-FAILED') end
    if not st then return canon.object({}) end
    if st.size>4*1024*1024 then value_error('POLICY-READ-FAILED') end
    local key=sys.key(path)
    local row=cached('status',key,function()
      local text=sys.read(path,4*1024*1024)
      if text==nil then return nil,canon.object({}) end
      local ok,value=pcall(ctl.decode_resident,path,text)
      if not ok then value_error('POLICY-READ-FAILED') end
      return nil,value
    end)
    return row.value
  end

  function B.use_process_bindings(bindings)
    local ok,value=pcall(identity.validate,bindings)
    if not ok then refuse('POLICY-IDENTITY-CHANGED') end
    B.process_bindings=value
  end

  local function order_of(sections,bindings)
    return identity.policy_order(sections,bindings),identity.policy_hash(sections,bindings)
  end
  function B.order()
    local row=policy_row()
    local key=row.key..'|'..(B.process_bindings and canon.encode(B.process_bindings) or '-')
    local memo=caches.order
    if not (memo and memo.key==key) then
      local o,h=order_of(row.value.sections,B.process_bindings)
      memo={key=key,order=o,hash=h};caches.order=memo
    end
    return py.copy(memo.order),memo.hash
  end

  function B.candidates()
    local data=B.policy()
    local profiles={}
    for _,p in ipairs(B.inventory().profiles) do if py.truthy(p.interface) then profiles[p.interface]=p end end
    local values={}
    for index,s in ipairs(data.sections) do
      local profile=type(s.via)=='string' and profiles[s.via] or nil
      if s['.type']=='rule' and s.enabled=='1' and s.killswitch=='1' and not identity.constrained(s) and profile then
        values[#values+1]=canon.object({id=profile.id,order=index-1,protocol=profile.protocol==nil and NULL or profile.protocol})
      end
    end
    return canon.array(values)
  end
  function B.acceleration() return platform.acceleration(sys) end
  function B.history_days()
    local ok,data=pcall(B.inventory)
    local days=ok and canon.is_object(data.settings) and data.settings.history_days or 7
    return (py.is_int(days) and days>=1 and days<=7) and days or 7
  end

  local board=nil
  local function board_info()
    if board then return board end
    local value=sys.ubus('system','board')
    if not canon.is_object(value) then value_error('FIRMWARE-UNKNOWN') end
    board=value
    return board
  end
  B.board_info=board_info
  local nft_ok=false
  local function nft_available()
    if nft_ok then return true end
    nft_ok=sys.exec({'nft','--version'},{timeout=5})==0
    return nft_ok
  end
  local function detect() return identity.detect(sys.read('/tmp/sysinfo/board_name',128)) end
  B.detect=detect

  ------------------------------------------------------------------------------------------------------
  -- route bindings (agent.route_binding), reads shared by both roles of one diagnostic
  ------------------------------------------------------------------------------------------------------
  local function ip_json(argv)
    local text=sys.command(argv,{timeout=5})
    local ok,value=pcall(canon.decode,text)
    if not ok then value_error('POLICY-READ-FAILED') end
    return text,value
  end
  local function route_reads()
    local routes_text,routes=ip_json({'ip','-4','-j','route','show','table','all'})
    local rules_text,rules=ip_json({'ip','-4','-j','rule','show'})
    local key=routes_text..'\0'..rules_text
    if not (caches.route_get and caches.route_get.key==key) then caches.route_get={key=key,answers={}} end
    return {routes=routes,rules=rules,answers=caches.route_get.answers}
  end
  function B.route_binding(logical,reads)
    local status=sys.ubus('network.interface.'..logical,'status')
    if status==nil then value_error('POLICY-READ-FAILED') end
    if not py.truthy(status.up) then return canon.object({code='VPN-001'}) end
    local device=status.l3_device
    if device==nil then device='' end
    if not agent_safe(device) or #device>15 then return canon.object({code='ROUTE-001'}) end
    reads=reads or route_reads()
    if not canon.is_array(reads.routes) or not canon.is_array(reads.rules) then value_error('POLICY-READ-FAILED') end
    local tables={}
    for _,r in ipairs(reads.routes) do
      if canon.is_object(r) and r.dev==device and r.dst=='default' then local t=r.table;if t==nil then t='main' end;tables[py.str(t)]=true end
    end
    local seen,candidates={},{}
    for _,rule in ipairs(reads.rules) do
      if canon.is_object(rule) and tables[py.str(rule.table)] and py.truthy(rule.fwmark) then
        local mark=py.int_auto(py.str(rule.fwmark))
        if mark==nil then value_error('POLICY-READ-FAILED') end
        if mark>0 then
          local key=string.format('%d\0%s',mark,py.str(rule.table))
          if not seen[key] then seen[key]=true;candidates[#candidates+1]={mark,py.str(rule.table)} end
        end
      end
    end
    if #candidates~=1 then return canon.object({code='CHECK-001',device=device}) end
    local mark,table_=candidates[1][1],candidates[1][2]
    for _,address in ipairs(M.TARGETS) do
      local key=address..'\0'..mark
      local answer=reads.answers[key]
      if answer==nil then
        local _,value=ip_json({'ip','-4','-j','route','get',address,'mark',string.format('%d',mark)})
        answer=value;reads.answers[key]=value
      end
      local t=canon.is_array(answer) and #answer==1 and canon.is_object(answer[1]) and answer[1].table or nil
      if t==nil then t='main' end
      if not canon.is_array(answer) or #answer~=1 or answer[1].dev~=device or py.str(t)~=table_ then
        return canon.object({code='ROUTE-001',device=device})
      end
    end
    local raw=sys.read('/sys/class/net/'..device..'/ifindex',64)
    local ifindex=raw and py.int(raw)
    if ifindex==nil then value_error('POLICY-READ-FAILED') end
    if ifindex<=0 then return canon.object({code='CHECK-001',device=device}) end
    return canon.object({code=NULL,device=device,mark=mark,table=table_,ifindex=ifindex})
  end

  ------------------------------------------------------------------------------------------------------
  -- diagnostic()
  ------------------------------------------------------------------------------------------------------
  local function audit_order()
    local text=sys.read(M.LIB..'/native-audit-hashes.json')
    if not text then value_error('VENDOR-CODE-UNVERIFIED') end
    local value=canon.decode(text)
    if not canon.is_object(value) then value_error('VENDOR-CODE-UNVERIFIED') end
    local names={}
    for name in string.gmatch(text,'"([^"]+)"%s*:') do if value[name]~=nil then names[#names+1]=name end end
    return value,names
  end

  function B.diagnostic()
    local blockers={}
    local function add(code) blockers[#blockers+1]=code end
    local reason=platform.auto_blocker(sys,M.PERSIST)
    if reason then add(reason) end
    local brd=canon.object({})
    local fok=pcall(function()
      brd=board_info()
      local name=brd.board_name
      if not (name=='glinet,gl-mt6000' or name=='glinet,mt3000-snand') then add('UNSUPPORTED-BOARD') end
      local version=sys.read('/etc/glversion')
      if version==nil then value_error('FIRMWARE-UNKNOWN') end
      if strip(version)~='4.11.0' then add('UNSUPPORTED-FIRMWARE') end
    end)
    if not fok then add('FIRMWARE-UNKNOWN') end
    local acceleration=B.acceleration()
    local loaded={}
    for _,m in ipairs(acceleration.loaded) do loaded[m]=true end
    if loaded.shortcut_fe or loaded.fast_classifier then add('SOFTWARE-ACCELERATOR-UNVERIFIED') end
    if not nft_available() then add('NFT-GUARD-UNAVAILABLE') end
    local aok=pcall(function()
      local pins,names=audit_order()
      for _,name in ipairs(names) do
        if platform.sha_file(sys,name)~=pins[name] then add('VENDOR-CODE-CHANGED') end
      end
    end)
    if not aok then add('VENDOR-CODE-UNVERIFIED') end
    local selection=nil
    local ok,err=pcall(function()
      local data=B.policy();local lan=data.lan
      local settings=data.settings;if settings==nil then settings=canon.object({}) end
      for _,code in ipairs(platform.assess(sys,brd,data)) do add(code) end
      local model=settings.router_model;if model==nil then model='auto' end
      local mok,merr=pcall(identity.validate_model,model,detect())
      if not mok then add(merr.code) end
      local mode=settings.monitor_only
      if not isnone(mode) and mode~='0' then add(mode=='1' and 'MONITOR-ONLY-DEPLOYMENT' or 'MONITOR-ONLY-INVALID') end
      if settings.terms_version~=M.TERMS_VERSION then add('TERMS-NOT-ACCEPTED') end
      if (loaded.mtkhnat or loaded.mtk_hnat) and (data.hnat_enable~='0' or acceleration.hnat_runtime~='disabled') then add('HARDWARE-ACCELERATOR-UNVERIFIED') end
      if lan~='br-lan' then add('LAN-LAYOUT-UNSUPPORTED') end
      local metadata=B.inventory()
      selection=identity.choose(data,metadata.profiles)
      if brd.board_name=='glinet,mt3000-snand' then
        if not pcall(identity.selection_interfaces,selection) then add('EXISTING-TUNNEL-BINDING-UNVERIFIED') end
      end
      B.use_process_bindings(getd_none(selection.process_bindings))
      local interval=settings.interval;if interval==nil then interval='10' end
      interval=py.int(interval)
      if interval==nil then refuse('OBSERVATION-STALE') end
      local observed=B.status()
      local pair=diagnosis.resolve_pair(observed,settings,canon.float(sys.wall()),math.max(30,math.min(900,interval*3)),math.max(30,math.min(600,interval*2)))
      if pair.coordination.state~='READY' then refuse(pair.coordination.code) end
      local reads=nil
      for _,role in ipairs({'source','target'}) do
        local current,measured=selection[role],pair[role]
        for _,key in ipairs({'id','protocol','interface','vendor_tunnel_id'}) do
          if not eq(current[key],measured[key]) then refuse('PROFILE-IDENTITY-CHANGED') end
        end
        local row=py.copy(current)
        for _,key in ipairs({'vendor_generation','vendor_state','vendor_changed_at'}) do local v=measured[key];row[key]=v==nil and NULL or v end
        selection[role]=row
        reads=reads or route_reads()
        local live=B.route_binding(current.interface,reads)
        if role=='target' and live.code=='VPN-001' and measured.code=='VPN-001' then refuse('RESERVE-NOT-CONNECTED') end
        local tolerated=role=='source' and live.code=='VPN-001' and measured.code=='VPN-001'
        local changed=false
        for _,key in ipairs({'device','mark','table','ifindex'}) do if not eq(live[key],measured[key]) then changed=true end end
        if (not isnone(live.code) and not tolerated) or changed then refuse('PROFILE-IDENTITY-CHANGED') end
        local binding=canon.object({})
        for _,key in ipairs({'code','device','mark','table','ifindex'}) do local v=live[key];binding[key]=v==nil and NULL or v end
        row.kernel_binding=binding
      end
      local proof=canon.object({})
      for _,role in ipairs({'source','target'}) do
        proof[role]=canon.object({profile=identity.profile_identity(selection[role]) or NULL,kernel=selection[role].kernel_binding})
      end
      selection.vendor_identity=digest(proof)
      selection.coordination=pair.coordination
      selection.settings_hash=identity.fingerprint(settings)
      local groups,disabled={},{}
      for _,s in ipairs(metadata.servers) do
        if canon.is_object(s) then
          local channel=s.channel;if channel==nil then channel='default' end
          if s.profile~=nil and s.profile~=NULL then groups[s.profile]=channel end
          if s.enabled==false and type(s.profile)=='string' then disabled[s.profile]=true end
        end
      end
      for _,role in ipairs({'source','target'}) do
        local profile=selection[role]
        local channel=groups[profile.id]
        if channel==nil then channel=profile.group_id;if channel==nil then channel='default' end end
        profile.channel=channel
      end
      if disabled[selection.source.id] or disabled[selection.target.id] then add('PROFILE-NOT-MONITORED') end
    end)
    if not ok then
      add(code_of(err) or 'POLICY-READ-FAILED');selection=nil
    end
    if platform.tunnel_switch_locks(sys) or platform.rtp_lock_busy(sys) then add('VENDOR-WORKER-BUSY') end
    return py.unique(blockers),selection
  end

  ------------------------------------------------------------------------------------------------------
  -- kernel reads: fingerprint and attestation
  ------------------------------------------------------------------------------------------------------
  local function strict_text(bytes)
    if not canon.valid_utf8(bytes) then value_error('KERNEL-POLICY-UNVERIFIED') end
    return bytes
  end
  local function mangle_text() return strict_text(sys.command({'iptables-save','-t','mangle'},{timeout=5})) end
  local function rules_read()
    local text=sys.command({'ip','-4','-j','rule','show'},{timeout=5})
    local ok,value=pcall(canon.decode,text)
    if not ok then value_error('KERNEL-POLICY-UNVERIFIED') end
    return text,value
  end
  -- the mangle text without comments and packet counters (parse_mangle ignores both)
  local function graph_key(text)
    text=string.gsub('\n'..text,'\n#[^\n]*','\n')
    return (string.gsub(text,'\n(:[^ \n]+ [^ \n]+) %[%d+:%d+%]','\n%1'))
  end
  local function parsed(text)
    local key=graph_key(text)
    local memo=caches.parsed
    if memo and memo.key==key then return memo.chains,memo.value end
    local chains=attest.parse(text)
    local value=attest.as_value(chains)
    caches.parsed={key=key,chains=chains,value=value,text=canon.encode(value)}
    return chains,value
  end
  local function parsed_text(text) parsed(text);return caches.parsed.text end

  function B.kernel_fingerprint()
    local ok,result=pcall(function()
      local before=mangle_text()
      local before_value=parsed_text(before)
      local rules_text,rules=rules_read()
      local after=mangle_text()
      local after_value=parsed_text(after)
      local rules_text2,rules2=rules_read()
      if before_value~=after_value or (rules_text~=rules_text2 and not eq(rules,rules2)) then return nil end
      local key=before_value..'\0'..rules_text
      local memo=caches.fingerprint
      if memo and memo.key==key then return memo.value end
      local value=digest(canon.object({mangle=select(2,parsed(before)),rules=rules}))
      caches.fingerprint={key=key,value=value}
      return value
    end)
    if ok then return result end
    return nil
  end

  function B.network_rows()
    local net=B.net or require('net').new(env,sys)
    return net.network()
  end

  function B.attest_policy(selection)
    local failed=canon.object({verified=false,repairable_missing=false,code='KERNEL-POLICY-UNVERIFIED',time=canon.float(sys.wall())})
    local ok,result=pcall(function()
      if selection==nil then
        local blockers,current=B.diagnostic()
        if #blockers>0 or not current then
          for _,b in ipairs(blockers) do if not M.ALLOWED_DIAGNOSTIC[b] then return failed end end
          current=identity.choose(B.policy(),B.inventory().profiles)
          for _,key in ipairs({'source','target'}) do current[key].kernel_binding=B.route_binding(current[key].interface) end
        end
        selection=current
      end
      if not platform.slot_contract_verified(sys,M.LIB) then return failed end
      local network_before=B.network_rows()
      selection=attest.static_bindings(selection,network_before)
      local expected_order,expected_hash=selection.order,selection.hash
      B.use_process_bindings(getd_none(selection.process_bindings))
      local row=policy_row()
      local policy=row.value
      local o,h=order_of(policy.sections,B.process_bindings)
      if not same_list(o,expected_order) or h~=expected_hash then return failed end
      local before=mangle_text()
      local rules_text,rules=rules_read()
      local after=mangle_text()
      local before_value=parsed_text(before)
      local after_value=parsed_text(after)
      local rules_text2,rules2=rules_read()
      local lo,lh=B.order()
      if before_value~=after_value or (rules_text~=rules_text2 and not eq(rules,rules2)) or not same_list(lo,expected_order) or lh~=expected_hash
         or canon.encode(B.network_rows())~=canon.encode(network_before) then return failed end
      local fkey=before_value..'\0'..rules_text
      local fingerprint
      if caches.fingerprint and caches.fingerprint.key==fkey then fingerprint=caches.fingerprint.value
      else
        local _,value=parsed(before)
        fingerprint=digest(canon.object({mangle=value,rules=rules}))
        caches.fingerprint={key=fkey,value=fingerprint}
      end
      failed.kernel_fingerprint=fingerprint
      -- attest/missing_only read only these selection fields (the coordination time changes on every call)
      local used=canon.object({order=selection.order,hash=selection.hash,process_bindings=selection.process_bindings==nil and NULL or selection.process_bindings})
      for _,key in ipairs({'source_rule','target_rule','direction','generic_rules'}) do local v=selection[key];used[key]=v==nil and NULL or v end
      for _,role in ipairs({'source','target'}) do
        local r=selection[role]
        used[role]=canon.object({id=r.id==nil and NULL or r.id,kernel_binding=r.kernel_binding==nil and NULL or r.kernel_binding})
      end
      local akey=fkey..'\0'..row.key..'\0'..canon.encode(used)
      local memo=caches.attest
      local verdict
      if memo and memo.key==akey then verdict=memo.verdict
      else
        local aok,value=pcall(attest.attest,policy,selection,before,rules)
        if aok then verdict={result=value}
        else
          local mok,missing=pcall(attest.missing_only,policy,selection,before,rules)
          verdict={missing=mok and missing==true}
        end
        caches.attest={key=akey,verdict=verdict}
      end
      if verdict.result==nil then
        failed.repairable_missing=verdict.missing
        return failed
      end
      local out=py.copy(verdict.result)
      out.time=canon.float(sys.wall());out.kernel_fingerprint=fingerprint
      return out
    end)
    if ok then return result end
    return failed
  end

  ------------------------------------------------------------------------------------------------------
  -- writes
  ------------------------------------------------------------------------------------------------------
  -- write_command(kind, fn, detail): kind 'uci' | 'kernel' | 'rtp'; fn may return a waiter (a function) for a
  -- command dispatched under the lock and awaited outside it (Python forward_dispatch).
  local function run_write(write_command,kind,fn,detail)
    local result
    if write_command then result=write_command(kind,fn,detail)
    else result=fn();if type(result)=='function' then result=result() end end
    B.invalidate()
    return result
  end
  B.run_write=run_write

  function B.forward_dispatch(argv,revision,timeout)
    local handle
    env.run.lock(function()
      require('transaction').require_control_revision(env,revision)
      handle=sys.spawn(argv,{timeout=timeout})
    end,env.runtime)
    if not handle then refuse('COMMAND-FAILED') end
    local rc=sys.wait(handle,(timeout or 5)+5)
    B.invalidate()
    if rc~=0 then refuse('COMMAND-FAILED') end
  end

  function B.reorder(order,before_write,write_command)
    local sections=policy_row().value.sections
    local current=identity.policy_order(sections,B.process_bindings)
    local want={};for _,x in ipairs(order) do want[x]=true end
    local have={};for _,x in ipairs(current) do have[x]=true end
    local same=#order==#current
    for k in pairs(want) do if not have[k] then same=false end end
    for k in pairs(have) do if not want[k] then same=false end end
    if not same then refuse('POLICY-IDENTITY-CHANGED') end
    local fingerprint=identity.policy_hash(sections,B.process_bindings)
    local expected={};for i,x in ipairs(current) do expected[i]=x end
    local moved=false
    for index,identifier in ipairs(order) do
      if expected[index]~=identifier then
        local live=policy_row().value.sections
        local lo,lh=order_of(live,B.process_bindings)
        if lh~=fingerprint or not same_list(lo,expected) then refuse('POLICY-IDENTITY-CHANGED') end
        local names={}
        for _,s in ipairs(live) do names[identity.section_id(s,B.process_bindings)]=s['.name'] end
        local section=names[identifier]
        if not safe_section(section) then refuse('UNSAFE-SECTION') end
        if before_write then before_write() end
        local position=string.format('%d',index-1)
        run_write(write_command,'uci',function() sys.command({'uci','reorder','route_policy.'..section..'='..position}) end,
          {op='reorder',section=section,index=index-1})
        for i=#expected,1,-1 do if expected[i]==identifier then table.remove(expected,i) end end
        table.insert(expected,index,identifier);moved=true
        local o,h=B.order()
        if not same_list(o,expected) or h~=fingerprint then refuse('POLICY-REORDER-UNVERIFIED') end
      end
    end
    if moved then
      local o,h=B.order()
      if not same_list(o,order) or h~=fingerprint then refuse('POLICY-IDENTITY-CHANGED') end
      if before_write then before_write() end
      run_write(write_command,'uci',function() sys.command({'uci','commit','route_policy'}) end,{op='commit'})
    end
    local o,h=B.order()
    if not same_list(o,order) or h~=fingerprint then refuse('POLICY-REORDER-UNVERIFIED') end
  end
  function B.uci_commit() sys.command({'uci','commit','route_policy'});B.invalidate() end

  -- process_policy.synchronization_script, run in this process: CAS of the two derived gl_process_vpn fields
  local function synchronize(system,first)
    local stage=sys.RUNTIME..'/homensai-process-'..sys.unique()
    if not sys.mkdir(stage,448) then refuse('COMMAND-FAILED') end
    local ok=pcall(function()
      local base=sys.uci_cursor()
      if not base then error('uci') end
      local pending=base:changes('route_policy');assert(not pending or next(pending)==nil,'pending')
      local c=sys.uci_cursor('/etc/config',stage)
      local s=c:get_all('route_policy','gl_process_vpn')
      assert(s and s['.type']=='rule_process' and s.enabled=='1' and s.from_type=='process_gid','identity')
      assert(s.via==system.via and s.mark==system.mark,'changed')
      local found=nil
      c:foreach('route_policy','rule',function(r) if not found and r.enabled=='1' and r.via~='novpn' then found=r end end)
      assert(found and found.via==first.via and found.mark==first.mark,'order')
      assert(c:set('route_policy','gl_process_vpn','via',found.via))
      assert(c:set('route_policy','gl_process_vpn','mark',found.mark))
      assert(c:save('route_policy'));assert(c:commit('route_policy'))
      local fresh=sys.uci_cursor('/etc/config',stage)
      assert(fresh:get('route_policy','gl_process_vpn','via')==found.via and fresh:get('route_policy','gl_process_vpn','mark')==found.mark,'readback')
    end)
    for _,name in ipairs(sys.dir(stage) or {}) do sys.remove(stage..'/'..name) end
    sys.rmdir(stage)
    if not ok then refuse('COMMAND-FAILED') end
  end

  function B.fast_switch_enabled()
    local text=sys.read('/etc/config/homensai_vpn')
    if not text then return false end
    for line in string.gmatch(text..'\n','([^\n]*)\n') do
      if string.find(line,"^%s*option%s+fast_switch%s+'?0'?%s*$") then return false end
    end
    return true
  end

  function B.apply_fast(write)
    local run=require('runner')
    local rules=require('instant_switch').read_rules(run)
    local before=kernel.snapshot(run.capture('iptables_save'))
    local plan=kernel.prepare(rules,before)
    if not plan.changed then return {used=true,changed=false} end
    local started=sys.clock()
    run_write(write,'kernel',function() run.restore(plan.payload) end,{op='kernel'})
    local swap_ms=math.floor((sys.clock()-started)*10000+0.5)/10
    local after=kernel.snapshot(run.capture('iptables_save'))
    kernel.verify(rules,after)
    pcall(run.conntrack_delete,plan.old_mark)
    return {used=true,changed=true,swap_ms=swap_ms}
  end

  function B.apply(write_command)
    local detected=detect()
    if detected=='mt3000' then
      if not pcall(platform.rtp_ready,sys) then refuse('RTP-BOOT-PRECONDITION-UNVERIFIED') end
    end
    local sections=policy_row().value.sections
    local bindings=B.process_bindings
    local need=false
    if bindings~=nil then
      local aok,applied=pcall(identity.applied,sections,bindings)
      if not aok then refuse('POLICY-IDENTITY-CHANGED') end
      if not applied then
        local system,first=identity.system_of(sections),identity.first_vpn_rule(sections)
        local mok,first_mark=pcall(identity.mark,first and first.mark)
        if not system or not identity.recognizes(system,bindings) or not first or type(first.via)~='string' or bindings[first.via]==nil
           or not mok or first_mark~=bindings[first.via] then refuse('POLICY-IDENTITY-CHANGED') end
        need={system={via=system.via,mark=system.mark},first={via=first.via,mark=first.mark}}
      end
    end
    if need then run_write(write_command,'uci',function() synchronize(need.system,need.first) end,{op='sync'}) end
    B.fast_path=nil
    if detected=='mt3000' and B.fast_switch_enabled() then
      local ok,result=pcall(B.apply_fast,write_command)
      if ok then B.fast_path=result
      elseif fp.is_unsupported(result) then B.fast_path={used=false,reason=result.code}
      else error(result,0) end
    end
    local used=B.fast_path and B.fast_path.used
    if not used then
      run_write(write_command,'rtp',function(timeout)
        timeout=timeout or M.RTP_TIMEOUT
        local handle=sys.spawn({'/usr/bin/rtp2.sh','not_reload_network'},{timeout=timeout})
        if not handle then refuse('COMMAND-FAILED') end
        return function()
          local rc=sys.wait(handle,timeout+5)
          if rc~=0 then refuse('COMMAND-FAILED') end
        end
      end,{op='rtp'})
    end
    if detected=='mt3000' and not used then
      local ok,err=pcall(platform.wait_quiet,sys)
      if not ok then
        local code=type(err)=='table' and err.code or nil
        refuse((code=='VENDOR-WORKER-BUSY' or code=='VENDOR-WORKER-QUIET-UNVERIFIED') and code or 'VENDOR-WORKER-QUIET-UNVERIFIED')
      end
    end
    local vok,verified=pcall(identity.applied,policy_row().value.sections,B.process_bindings)
    if not vok or not verified then refuse('POLICY-IDENTITY-CHANGED') end
  end

  ------------------------------------------------------------------------------------------------------
  -- guard
  ------------------------------------------------------------------------------------------------------
  function B.guard_exists()
    local rc,out=sys.exec({'nft','list','table','inet',M.TABLE},{timeout=5})
    if rc==0 then
      if not string.find(out,'homensai-owned-guard',1,true) then refuse('FOREIGN-GUARD-TABLE') end
      return true
    end
    if rc~=1 then refuse('GUARD-QUERY-FAILED') end
    return false
  end
  function B.guard(devices,control_revision)
    local exists=B.guard_exists()
    local rules,generation
    if devices~=nil then
      if #devices==0 then refuse('UNSAFE-GUARD-DEVICE') end
      local set,list={},{}
      for _,d in ipairs(devices) do
        if not safe_section(d) or #d>15 then refuse('UNSAFE-GUARD-DEVICE') end
        if not set[d] then set[d]=true;list[#list+1]=d end
      end
      table.sort(list)
      local quoted={};for i,d in ipairs(list) do quoted[i]='"'..d..'"' end
      rules={'iifname "br-lan" meta nfproto ipv6 drop comment "homensai-owned-guard"',
             'iifname "br-lan" oifname != { '..table.concat(quoted,', ')..' } drop comment "homensai-owned-guard"'}
    else
      generation=string.sub(string.gsub(sys.unique(),'[^0-9a-f]',''),1,8)
      if #generation~=8 then refuse('GUARD-CHECK-FAILED') end
      rules={'iifname @blocked_lan_'..generation..' drop comment "homensai-owned-guard-'..generation..'"'}
    end
    local lines={}
    if exists then lines[#lines+1]='delete table inet '..M.TABLE..';\n' end
    lines[#lines+1]='table inet '..M.TABLE..' {\n'
    if devices==nil then
      lines[#lines+1]=string.format('  set blocked_lan_%s { type ifname; flags timeout; timeout %ds; elements = { "br-lan" timeout %ds }; }\n',
        generation,M.GUARD_RELEASE_SECONDS,M.GUARD_RELEASE_SECONDS)
    end
    lines[#lines+1]='  chain forward {\n    type filter hook forward priority -310; policy accept;\n'
    for _,rule in ipairs(rules) do lines[#lines+1]='    '..rule..';\n' end
    lines[#lines+1]='  }\n}\n'
    local path=sys.RUNTIME..'/guard-'..sys.unique()..'.nft'
    sys.write_private(path,table.concat(lines))
    local ok,err=pcall(function()
      if sys.exec({'nft','-c','-f',path},{timeout=5})~=0 then refuse('GUARD-CHECK-FAILED') end
      if devices==nil and not sys.guard_release(generation,M.GUARD_RELEASE_SECONDS,M.TABLE) then refuse('GUARD-RELEASE-ARM-FAILED') end
      if control_revision==nil then
        if sys.exec({'nft','-f',path},{timeout=5})~=0 then refuse('GUARD-INSTALL-FAILED') end
      else
        B.forward_dispatch({'nft','-f',path},control_revision,5)
      end
    end)
    sys.remove(path)
    if not ok then error(err,0) end
    if not B.guard_exists() then refuse('GUARD-INSTALL-FAILED') end
  end
  function B.unguard()
    if B.guard_exists() then sys.exec({'nft','delete','table','inet',M.TABLE},{timeout=5}) end
    if B.guard_exists() then refuse('GUARD-RELEASE-UNCONFIRMED') end
  end
  function B.devices()
    local devices={}
    for _,p in ipairs(B.inventory().profiles) do
      if py.truthy(p.interface) and p.administrative_state~='disabled' then
        local s=sys.ubus('network.interface.'..p.interface,'status')
        if not canon.is_object(s) then refuse('GUARD-DEVICE-UNVERIFIED') end
        if py.truthy(s.up) and py.truthy(s.l3_device) then devices[#devices+1]=s.l3_device end
      end
    end
    return devices
  end

  ------------------------------------------------------------------------------------------------------
  -- own config: lease, native options
  ------------------------------------------------------------------------------------------------------
  function B.write_lease(scope,trial,until_text)
    local stage=sys.RUNTIME..'/pair-lease-'..sys.unique()
    if not sys.mkdir(stage,448) then refuse('COMMAND-FAILED') end
    local ok=pcall(function()
      local c=sys.uci_cursor('/etc/config',stage)
      assert(c:set('homensai_vpn','main','native_proof_scope',scope))
      assert(c:set('homensai_vpn','main','native_trial',trial))
      assert(c:set('homensai_vpn','main','native_until',until_text))
      assert(c:save('homensai_vpn'));assert(c:commit('homensai_vpn'))
    end)
    for _,name in ipairs(sys.dir(stage) or {}) do sys.remove(stage..'/'..name) end
    sys.rmdir(stage)
    B.invalidate()
    if not ok then refuse('COMMAND-FAILED') end
  end
  function B.clear_native_options()
    local rc,out=sys.exec({'uci','-q','changes','homensai_vpn'},{timeout=10})
    if rc~=0 or strip(out)~='' then return false end
    local batch="set homensai_vpn.main.native_enabled='0'\nset homensai_vpn.main.native_until='0'\nset homensai_vpn.main.native_trial=''\ncommit homensai_vpn\n"
    local ok=sys.exec({'uci','-q','batch'},{timeout=10,input=batch})==0
    B.invalidate()
    return ok
  end

  ------------------------------------------------------------------------------------------------------
  -- probes (temporary bridge to the Python monitor code), health, recovery readiness
  ------------------------------------------------------------------------------------------------------
  local function bridge(action,profile)
    local path=sys.RUNTIME..'/.bridge-'..sys.unique()..'.json'
    sys.write_private(path,canon.encode(profile))
    local rc,out=sys.exec({'python3',M.BRIDGE,action,path},{timeout=40})
    sys.remove(path)
    local last=nil
    for line in string.gmatch(out or '','[^\n]+') do last=line end
    local ok,value=pcall(canon.decode,last or '')
    if rc~=0 or not ok or not canon.is_object(value) then return nil end
    return value
  end
  B.bridge=bridge
  function B.probe(profile)
    local value=bridge('probe',profile)
    if not value then return canon.object({id=profile.id,code='SYSTEM-001',scope='router-originated',lan_path_verified=false}) end
    return value
  end
  function B.trace(profile)
    local value=bridge('trace',profile)
    if not value then refuse('NATIVE-SYSTEM-001') end
    if type(value.exit)=='string' then return value.exit end
    if type(value.code)=='string' and ctl.code_ok(value.code) then refuse(value.code) end
    refuse('NATIVE-SYSTEM-001')
  end
  local negative={}
  local positive={}
  function B.health(identifier,reuse)
    local row=negative[identifier]
    if row and sys.clock()-row.time>=0 and sys.clock()-row.time<M.HEALTH_NEGATIVE_SECONDS then return row.value end
    local good=positive[identifier]
    if reuse and good and sys.clock()-good>=0 and sys.clock()-good<reuse then return true end
    local profile=nil
    for _,p in ipairs(B.inventory().profiles) do if p.id==identifier then profile=p;break end end
    local value
    if not profile or not py.truthy(profile.interface) then value=false
    else
      local result=B.probe(profile)
      local hs=result.https_success;if hs==nil then hs=0 end
      if isnone(result.code) and result.dns_ok==true and (canon.number(hs) or 0)>=2 then value=true
      elseif result.code=='VPN-001' or result.code=='VPN-003' or result.code=='DNS-001' or result.code=='PROFILE-INACTIVE' then value=false
      else value=nil end
    end
    if value==true then negative[identifier]=nil;positive[identifier]=sys.clock()
    else negative[identifier]={time=sys.clock(),value=value};positive[identifier]=nil end
    return value
  end
  function B.recovery_ready(identifier,settings)
    local pair=require('pair')
    local policy=pair.recovery_normalized(settings)
    local status=B.status()
    local age=pair.valid_for(settings)
    local now=sys.wall()
    local resolved=diagnosis.resolve_pair(status,settings,canon.float(now),age,pair.settle_for(settings))
    local row=nil
    for _,role in ipairs({'source','target'}) do
      local r=resolved[role]
      if not isnone(r) and r.id==identifier then row=r;break end
    end
    if resolved.coordination.state~='READY' or row==nil then return false end
    local samples=status.samples;if samples==nil then samples=canon.array({}) end
    if not pair.stable_success(diagnosis.scoped_samples(samples,row),identifier,policy.primary_successes,policy.primary_stable,sys.wall(),age) then return false end
    return B.health(identifier)==true
  end

  ------------------------------------------------------------------------------------------------------
  -- pair helpers
  ------------------------------------------------------------------------------------------------------
  function B.selection_interfaces(selection) return identity.selection_interfaces(selection) end
  function B.instant_request(selection,after)
    local sections=policy_row().value.sections
    local names,tunnels=canon.object({}),{}
    for _,s in ipairs(sections) do
      local id=identity.section_id(s,B.process_bindings)
      names[id]=s['.name']
      local enabled=s.enabled;if enabled==nil then enabled='1' end
      if s['.type']=='rule' and enabled~='0' and py.truthy(s.tunnel_id) then tunnels[id]=py.str(s.tunnel_id) end
    end
    local order={}
    for _,id in ipairs(after) do if tunnels[id] then order[#order+1]=tunnels[id] end end
    if #order~=2 then refuse('FAST-RULES') end
    return names,canon.array(order)
  end
  function B.pair_preflight(settings)
    local brd=sys.read('/tmp/sysinfo/board_name')
    if not brd or strip(brd)~='glinet,mt3000-snand' then value_error('PAIR-PLATFORM-UNVERIFIED') end
    local version=sys.read('/etc/glversion')
    if not version or strip(version)~='4.11.0' then value_error('UNSUPPORTED-FIRMWARE') end
    local preparation=platform.preparation_snapshot(sys,settings)
    if preparation.state~='pass' then
      for _,row in ipairs(preparation.checks) do if row.state~='pass' then value_error(row.code) end end
      value_error('PAIR-PREPARATION-REQUIRED')
    end
    local model=settings.router_model;if model==nil then model='auto' end
    identity.validate_model(model,detect())
    local pins={}
    for name,sha in pairs(platform.PINS) do pins[name]=sha end
    local audit=platform.audit_pins(sys,M.LIB)
    for name,sha in pairs(audit) do pins[name]=sha end
    for name,sha in pairs(pins) do if platform.sha_file(sys,name)~=sha then value_error('VENDOR-CODE-CHANGED') end end
    local acceleration=B.acceleration()
    local loaded={};for _,m in ipairs(acceleration.loaded) do loaded[m]=true end
    if loaded.shortcut_fe or loaded.fast_classifier or ((loaded.mtkhnat or loaded.mtk_hnat) and acceleration.hnat_runtime~='disabled') then
      value_error('PAIR-PREPARATION-REQUIRED')
    end
    local data=B.policy()
    local errors=platform.assess(sys,board_info(),data)
    for _,code in ipairs(errors) do if code~='FW3-SELECTED-ZONE-UNVERIFIED' then value_error(code) end end
    local selection=identity.choose(data,B.inventory().profiles)
    identity.selection_interfaces(selection)
    B.use_process_bindings(getd_none(selection.process_bindings))
    return selection
  end
  function B.speed_active() return sys.lstat(sys.RUNTIME..'/speed-pause.json')~=nil end
  function B.vendor_busy() return platform.tunnel_switch_locks(sys) or sys.lstat(platform.RTP_LOCK)~=nil end
  -- A Python apply child of a journal written by the Python line: kill only that exact process group.
  function B.kill_apply_child(pid,tx)
    if not py.is_int(pid) or pid<=1 or type(tx)~='string' or not string.find(tx,'^[a-f0-9]+$') then return end
    local command=sys.read('/proc/'..string.format('%d',pid)..'/cmdline',8192)
    if command and string.find(kernel.decode(command),'native_switch.py\0apply\0'..tx,1,true) then
      sys.exec({'kill','-9','-'..string.format('%d',pid)},{timeout=5})
    end
  end

  ------------------------------------------------------------------------------------------------------
  -- env wiring
  ------------------------------------------------------------------------------------------------------
  function B.bind(e)
    env=e
    B.net=require('net').new(env,sys)
    local deps=require('deps').new(env,sys,B)
    B.deps=deps
    env.net=B.net;env.deps=deps
    return B
  end
  B.sys=sys
  B.VERSION=M.VERSION
  return B
end

return M
