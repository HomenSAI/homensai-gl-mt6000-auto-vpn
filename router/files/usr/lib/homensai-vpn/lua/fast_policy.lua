-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- fast_policy.lua: Lua 5.1 port of fast_policy.py (Lua line 2.0.0-lua, branch feat/lua-core-20261030).
--
-- Same three functions, same results and the same Unsupported codes as the Python module:
--   uci_rules(text)                          -> order, local_tunnel, local_mark
--   plan(mangle, order, local_tunnel, mark)  -> payload, old_first, changed
--   mark_of(mangle, tunnel)                  -> '0x....'
-- Input is text as Python sees it: valid UTF-8 (fastswap.decode() gives Python's decode('utf8','replace')).
-- Python regular expressions are replaced by explicit byte checks with the same meaning; every place
-- where Lua patterns and Python `re` differ (split, `$`, alternation, {1,8}) is spelled out below.
-- Pure: no I/O, no globals, no router-only modules. tests/test_lua_fast_policy.py runs it against
-- fast_policy.py on the same fixtures and on generated variants.
local M={}

local Unsupported={}
Unsupported.__index=Unsupported
Unsupported.__tostring=function(e) return e.code end
M.Unsupported=Unsupported

local function unsupported(code) error(setmetatable({code=code},Unsupported),0) end
function M.is_unsupported(e) return type(e)=='table' and getmetatable(e)==Unsupported end

-- str.splitlines(): \n, \r, \r\n, \v, \f, \x1c, \x1d, \x1e, U+0085, U+2028, U+2029; no trailing empty line.
local BREAK='[\n\r\11\12\28\29\30\194\226]'
function M.splitlines(text)
  local lines,n,start,pos=({}),0,1,1
  while true do
    local i=string.find(text,BREAK,pos)
    if not i then break end
    local b=string.byte(text,i);local width=1
    if b==13 then
      if string.byte(text,i+1)==10 then width=2 end
    elseif b==194 then
      width=(string.byte(text,i+1)==133) and 2 or 0
    elseif b==226 then
      local b2,b3=string.byte(text,i+1,i+2)
      width=(b2==128 and (b3==168 or b3==169)) and 3 or 0
    end
    if width>0 then
      n=n+1;lines[n]=string.sub(text,start,i-1);start=i+width;pos=start
    else
      pos=i+1
    end
  end
  if start<=#text then n=n+1;lines[n]=string.sub(text,start) end
  return lines
end

local function starts(s,prefix) return string.sub(s,1,#prefix)==prefix end

local function digits(s,low,high)  -- fullmatch [0-9]{low,high}
  return type(s)=='string' and #s>=low and #s<=high and string.find(s,'^[0-9]+$')~=nil
end

local function is_hex(b) return b and ((b>=48 and b<=57) or (b>=97 and b<=102)) end  -- [0-9a-f]

local function valid_mark(mark)  -- MARK.fullmatch: ^0x[0-9a-f]{1,8}$
  if type(mark)~='string' or not starts(mark,'0x') or #mark<3 or #mark>10 then return false end
  for i=3,#mark do if not is_hex(string.byte(mark,i)) then return false end end
  return true
end
M._valid_mark=valid_mark

-- re.search(LEAD..'[0-9a-f]{1,8}/0xf000$', line): LEAD ends with 'x', which is not a hex digit, so the
-- hex run is the maximal run before '/0xf000'. Returns the index where LEAD starts and the hex digits.
local TAIL='/0xf000'
local function hex_tail(line,lead)
  local n=#line
  if n<#TAIL or string.sub(line,n-#TAIL+1)~=TAIL then return nil end
  local last=n-#TAIL;local first=last
  while first>=1 and is_hex(string.byte(line,first)) do first=first-1 end
  local count=last-first
  if count<1 or count>8 then return nil end
  local at=first-#lead+1
  if at<1 or string.sub(line,at,first)~=lead then return nil end
  return at,string.sub(line,first+1,last)
end

-- Python str.split(sep)[-1]: separators are found left to right without overlap (' -j -j ' differs
-- from "text after the last occurrence").
local function last_field(line,sep)
  local pos,last=1,1
  while true do
    local i=string.find(line,sep,pos,true)
    if not i then break end
    last=i+#sep;pos=last
  end
  return string.sub(line,last)
end

-- Python int() keys of @rule[N]: '01' and '1' are the same rule; arbitrary size, numeric order.
local function index_key(raw)
  local trimmed=string.gsub(raw,'^0+','')
  return trimmed=='' and '0' or trimmed
end
local function index_less(a,b)
  if #a~=#b then return #a<#b end
  return a<b  -- equal-length ASCII digit strings: byte order is numeric order
end

function M.uci_rules(text)
  local rules,keys,process={},{},{}
  for _,line in ipairs(M.splitlines(text)) do
    -- ^route_policy\.@rule\[([0-9]+)\]\.(tunnel_id|enabled)='([^']*)'$
    local index,key,value=string.match(line,"^route_policy%.@rule%[([0-9]+)%]%.([^=]*)='([^']*)'$")
    if index and (key=='tunnel_id' or key=='enabled') then
      local k=index_key(index)
      if not rules[k] then rules[k]={};keys[#keys+1]=k end
      rules[k][key]=value
    else
      -- ^route_policy\.gl_process_vpn\.(tunnel_id|mark|enabled)='([^']*)'$
      local name,setting=string.match(line,"^route_policy%.gl_process_vpn%.([^=]*)='([^']*)'$")
      if name=='tunnel_id' or name=='mark' or name=='enabled' then process[name]=setting end
    end
  end
  table.sort(keys,index_less)
  local ordered={}
  for i,k in ipairs(keys) do ordered[i]=rules[k] end
  return M.rules_result(ordered,process)
end

-- The checks of uci_rules over rules in list order ({tunnel_id=,enabled=} strings) and the
-- gl_process_vpn options; shared by the `uci show` text reader and the libuci reader.
function M.rules_result(rules,process)
  local order={}
  for _,rule in ipairs(rules) do
    if (rule.enabled==nil or rule.enabled~='0') and rule.tunnel_id~=nil then order[#order+1]=rule.tunnel_id end
  end
  if #order~=2 or order[1]==order[2] or not digits(order[1],1,8) or not digits(order[2],1,8) then unsupported('FAST-RULES') end
  if process.enabled=='0' or not digits(process.tunnel_id or '',1,8) or not valid_mark(process.mark or '') then
    unsupported('FAST-LOCAL-RULE')
  end
  return order,process.tunnel_id,process.mark
end

-- uci_rules() from libuci (no process): `uci show` prints `@rule[N]` only for anonymous sections of type
-- rule and quotes only single values, so named rule sections and list options are invisible to the
-- Python regex and are skipped here too; gl_process_vpn is matched by name, whatever its type.
function M.uci_rules_from_cursor(cursor)
  local rules,process={},{}
  cursor:foreach('route_policy','rule',function(s)
    if s['.anonymous'] then
      local rule={}
      if type(s.tunnel_id)=='string' and not string.find(s.tunnel_id,"'",1,true) then rule.tunnel_id=s.tunnel_id end
      if type(s.enabled)=='string' and not string.find(s.enabled,"'",1,true) then rule.enabled=s.enabled end
      rules[#rules+1]=rule
    end
  end)
  local own=cursor:get_all('route_policy','gl_process_vpn')
  if type(own)=='table' then
    for _,key in ipairs({'tunnel_id','mark','enabled'}) do
      if type(own[key])=='string' and not string.find(own[key],"'",1,true) then process[key]=own[key] end
    end
  end
  return M.rules_result(rules,process)
end

local JUMP='-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL'
local function jump_id(line)  -- JUMP.fullmatch(line).group(1)
  if not starts(line,JUMP) then return nil end
  local id=string.match(string.sub(line,#JUMP+1),'^([0-9]+)_ROUTE_POLICY$')
  if id and #id<=8 then return id end
  return nil
end

local function copy(list) local out={};for i=1,#list do out[i]=list[i] end;return out end
local function same(a,b)
  if #a~=#b then return false end
  for i=1,#a do if a[i]~=b[i] then return false end end
  return true
end

function M.plan(mangle,order,local_tunnel,local_mark)
  return M.plan_lines(M.splitlines(mangle),order,local_tunnel,local_mark)
end

-- plan() over already split lines: kernel.lua splits iptables-save once per transaction.
function M.plan_lines(lines,order,local_tunnel,local_mark)
  local route={}
  for _,l in ipairs(lines) do if starts(l,'-A ROUTE_POLICY ') then route[#route+1]=l end end
  local jumps={}
  for i,l in ipairs(route) do
    if string.find(last_field(l,' -j '),'_ROUTE_POLICY',1,true) then jumps[#jumps+1]=i end
  end
  local found,all={},true
  for k,i in ipairs(jumps) do found[k]=jump_id(route[i]);if not found[k] then all=false end end
  -- sorted(found ids)==sorted(order): with exactly two found ids this is multiset equality.
  local paired=all and #jumps==2 and #order==2 and
    ((found[1]==order[1] and found[2]==order[2]) or (found[1]==order[2] and found[2]==order[1]))
  if #jumps~=2 or not all or not paired or jumps[2]~=jumps[1]+1 then unsupported('FAST-ROUTE-CHAIN') end
  local old_first=found[1]
  local by_id={};by_id[found[1]]=route[jumps[1]];by_id[found[2]]=route[jumps[2]]
  local new_route=copy(route);new_route[jumps[1]]=by_id[order[1]];new_route[jumps[2]]=by_id[order[2]]
  local name='TUNNEL'..local_tunnel..'_LOCAL_POLICY'
  local prefix='-A '..name..' '
  local localrules={}
  for _,l in ipairs(lines) do if starts(l,prefix) then localrules[#localrules+1]=l end end
  local setters={}
  for i,l in ipairs(localrules) do if string.find(l,' -j MARK --set-xmark ',1,true) then setters[#setters+1]=i end end
  if #setters~=1 or not hex_tail(localrules[setters[1]],' -j MARK --set-xmark 0x') then unsupported('FAST-LOCAL-CHAIN') end
  -- re.sub('--set-xmark 0x[0-9a-f]{1,8}/0xf000$', '--set-xmark <mark>/0xf000'): the only possible match is
  -- the tail found above. local_mark comes from uci_rules (validated MARK, so no re template escapes).
  local line=localrules[setters[1]]
  local at=hex_tail(line,'--set-xmark 0x')
  local new_local=copy(localrules)
  new_local[setters[1]]=string.sub(line,1,at-1)..'--set-xmark '..local_mark..'/0xf000'
  local changed=not same(new_route,route) or not same(new_local,localrules)
  local payload='*mangle\n:ROUTE_POLICY - [0:0]\n'..table.concat(new_route,'\n')..'\n:'..name..' - [0:0]\n'
    ..table.concat(new_local,'\n')..'\nCOMMIT\n'
  return payload,old_first,changed
end

function M.mark_of(mangle,tunnel) return M.mark_of_lines(M.splitlines(mangle),tunnel) end

function M.mark_of_lines(lines,tunnel)
  -- ^-A TUNNEL<t>_ROUTE_POLICY .* -j MARK --set-xmark (0x[0-9a-f]{1,8})/0xf000$  (tunnel: digits from plan)
  local prefix='-A TUNNEL'..tunnel..'_ROUTE_POLICY '
  for _,line in ipairs(lines) do
    if starts(line,prefix) then
      local at,hex=hex_tail(line,' -j MARK --set-xmark 0x')
      if at and at>#prefix then return '0x'..hex end
    end
  end
  unsupported('FAST-MARK')
end

return M
