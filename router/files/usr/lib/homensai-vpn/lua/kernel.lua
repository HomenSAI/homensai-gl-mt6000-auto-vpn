-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- kernel.lua: the mangle table of the Lua core (kernel_policy.py subset + Linux.apply_fast planning).
--
--   decode(bytes)            bytes.decode('utf8','replace'), as apply_fast reads command output
--   snapshot(bytes)          one decode + one split of `iptables-save -t mangle` per read; every later
--                            step (plan, old mark, parse, attest) reuses the same lines
--   parse_mangle(snapshot)   kernel_policy.parse_mangle (shlex.split per rule line)
--   fields(tokens)           kernel_policy.fields
--   attest_route(chains,order)  the part of kernel_policy.attest the fast switch relies on:
--                            ROUTE_POLICY == [restore-mark, DNS return, jump A, jump B] and every
--                            TUNNEL<id>_ROUTE_POLICY == [set mark, DROP] with two distinct marks
--   prepare(rules, snapshot) plan + old mark, as apply_fast before its write
--   payload_ok / verify      the restore payload and the read-back check
-- Pure: no I/O. Refusals are fast_policy.Unsupported (fall back to the vendor rebuild) or
-- Refused('KERNEL-POLICY-UNVERIFIED' / 'FAST-PATH-UNVERIFIED'), the Python codes.
local fp=require('fast_policy')

local M={}
M.MASK=0xf000

local Refused={}
Refused.__index=Refused
Refused.__tostring=function(e) return e.code end
M.Refused=Refused
local function refuse(code) error(setmetatable({code=code},Refused),0) end
function M.is_refused(e) return type(e)=='table' and getmetatable(e)==Refused end
local function unverified() refuse('KERNEL-POLICY-UNVERIFIED') end

------------------------------------------------------------------------------------------------------
-- bytes.decode('utf8','replace'): every maximal invalid subpart becomes U+FFFD (CPython's decoder)
------------------------------------------------------------------------------------------------------
local REPLACEMENT='\239\191\189'
function M.decode(bytes)
  if not string.find(bytes,'[\128-\255]') then return bytes end
  local out,n,i,len={},0,1,#bytes
  while i<=len do
    local b=string.byte(bytes,i)
    if b<0x80 then
      local j=string.find(bytes,'[\128-\255]',i) or len+1
      n=n+1;out[n]=string.sub(bytes,i,j-1);i=j
    else
      local need,lo,hi=0,0x80,0xBF
      if b>=0xC2 and b<=0xDF then need=1
      elseif b==0xE0 then need=2;lo=0xA0
      elseif (b>=0xE1 and b<=0xEC) or b==0xEE or b==0xEF then need=2
      elseif b==0xED then need=2;hi=0x9F
      elseif b==0xF0 then need=3;lo=0x90
      elseif b>=0xF1 and b<=0xF3 then need=3
      elseif b==0xF4 then need=3;hi=0x8F end
      if need==0 then
        n=n+1;out[n]=REPLACEMENT;i=i+1
      else
        local k=1
        while k<=need do
          local c=string.byte(bytes,i+k)
          local l,h=0x80,0xBF
          if k==1 then l,h=lo,hi end
          if not c or c<l or c>h then break end
          k=k+1
        end
        if k>need then n=n+1;out[n]=string.sub(bytes,i,i+need);i=i+need+1
        else n=n+1;out[n]=REPLACEMENT;i=i+k end
      end
    end
  end
  return table.concat(out)
end

M.MAX_TEXT=2*1024*1024
function M.snapshot(bytes)
  if type(bytes)~='string' or #bytes>M.MAX_TEXT then unverified() end
  local text=M.decode(bytes)
  return {text=text,lines=fp.splitlines(text)}
end

------------------------------------------------------------------------------------------------------
-- shlex.split(line) (posix, whitespace_split, no comments); nil on "No closing quotation" etc.
------------------------------------------------------------------------------------------------------
local WHITE={[' ']=true,['\t']=true,['\r']=true,['\n']=true}
function M.shlex_split(line)
  local tokens,buf,state,have={},{},' ',false
  local i,n=1,#line
  while i<=n do
    local c=string.sub(line,i,i)
    if state==' ' then
      if WHITE[c] then
        if have then tokens[#tokens+1]=table.concat(buf);buf={};have=false end
      elseif c=='\\' then
        if i==n then return nil end  -- No escaped character
        buf[#buf+1]=string.sub(line,i+1,i+1);have=true;i=i+1
      elseif c=="'" then state="'";have=true
      elseif c=='"' then state='"';have=true
      else buf[#buf+1]=c;have=true end
    elseif state=="'" then
      if c=="'" then state=' ' else buf[#buf+1]=c end
    else  -- inside double quotes: a backslash escapes only " and \
      if c=='"' then state=' '
      elseif c=='\\' then
        if i==n then return nil end
        local d=string.sub(line,i+1,i+1)
        if d=='"' or d=='\\' then buf[#buf+1]=d else buf[#buf+1]='\\'..d end
        i=i+1
      else buf[#buf+1]=c end
    end
    i=i+1
  end
  if state~=' ' then return nil end  -- No closing quotation
  if have then tokens[#tokens+1]=table.concat(buf) end
  return tokens
end

------------------------------------------------------------------------------------------------------
-- kernel_policy.number / numeric / fields
------------------------------------------------------------------------------------------------------
function M.number(value)
  if type(value)~='string' then unverified() end
  local x
  if string.find(value,'^0x[0-9a-fA-F]+$') then
    if #value>15 then unverified() end  -- beyond 2^53 a double is inexact; Python's int is not: fail closed
    x=tonumber(string.sub(value,3),16)
  elseif string.find(value,'^[0-9]+$') then
    if #value>15 then unverified() end
    x=tonumber(value,10)
  else unverified() end
  return x
end
function M.numeric(value)
  local slash=string.find(value,'/',1,true)
  if slash then
    return string.format('%.0f/%.0f',M.number(string.sub(value,1,slash-1)),M.number(string.sub(value,slash+1)))
  end
  return string.format('%.0f',M.number(value))
end

local UNARY={['--restore-mark']=true,['--save-mark']=true,['--clamp-mss-to-pmtu']=true}
local BINARY={}
for _,k in ipairs({'-i','-o','-p','-j','--dst-type','--dport','--mark','--set-xmark','--nfmask','--ctmask','--ctstate',
                   '--ttl-set','--ttl-inc','--ttl-dec','--tcp-flags','--set-mss'}) do BINARY[k]=true end
local NUMERIC={['--mark']=true,['--set-xmark']=true,['--nfmask']=true,['--ctmask']=true}

-- Returns a table: option -> value (string or true), and ['-m'] = sorted module list.
function M.fields(tokens)
  local result,modules,seen={},{},{}
  local index,negated=1,false
  while index<=#tokens do
    local token=tokens[index];index=index+1
    if token=='!' then
      if negated then unverified() end
      negated=true
    elseif token=='-m' then
      if negated or index>#tokens then unverified() end
      local module=tokens[index];index=index+1
      if module=='comment' then
        if tokens[index]~='--comment' or index+1>#tokens then unverified() end
        index=index+2
      else
        if seen[module] then unverified() end
        seen[module]=true;modules[#modules+1]=module
      end
    else
      local key=(negated and '! ' or '')..token;negated=false
      if result[key]~=nil then unverified() end
      if UNARY[token] then result[key]=true
      elseif BINARY[token] then
        local count=(token=='--tcp-flags') and 2 or 1
        if index+count-1>#tokens then unverified() end
        local value=table.concat(tokens,' ',index,index+count-1);index=index+count
        if NUMERIC[token] then value=M.numeric(value) end
        result[key]=value
      else unverified() end
    end
  end
  if negated then unverified() end
  if #modules>0 then table.sort(modules);result['-m']=modules end
  return result
end

-- kernel_policy.parse_mangle: chain -> list of token lists. The snapshot's split lines are reused.
function M.parse_mangle(snapshot)
  local chains,order={},{}
  local opened,committed=false,false
  for _,line in ipairs(snapshot.lines) do
    if line=='' or string.sub(line,1,1)=='#' then
      -- skipped, as in Python
    elseif line=='*mangle' then
      if opened then unverified() end
      opened=true
    elseif line=='COMMIT' then committed=true
    else
      if not opened or committed then unverified() end
      if string.sub(line,1,1)==':' then
        local name,policy=string.match(line,'^:([A-Za-z0-9_-]+) ([A-Z-]+) %[[0-9]+:[0-9]+%]$')
        if not name or #name>64 or not (policy=='ACCEPT' or policy=='DROP' or policy=='-') or chains[name] then unverified() end
        if name=='PREROUTING' and policy~='ACCEPT' then unverified() end
        chains[name]={};order[#order+1]=name
      else
        local tokens=M.shlex_split(line)
        if not tokens or #tokens<4 or tokens[1]~='-A' or not chains[tokens[2]] then unverified() end
        local rule={}
        for k=3,#tokens do rule[#rule+1]=tokens[k] end
        local list=chains[tokens[2]];list[#list+1]=rule
      end
    end
  end
  if not opened or not committed then unverified() end
  return chains,order
end

local function same_fields(a,b)
  for k,v in pairs(a) do
    local w=b[k]
    if type(v)=='table' then
      if type(w)~='table' or #v~=#w then return false end
      for i=1,#v do if v[i]~=w[i] then return false end end
    elseif v~=w then return false end
  end
  for k in pairs(b) do if a[k]==nil then return false end end
  return true
end

-- attest subset: the LAN catch-all marking in the expected order (tunnel ids from uci, first wins).
function M.attest_route(chains,order)
  local mask=string.format('%.0f',M.MASK)
  local restore={['-m']={'connmark'},['! --mark']='0/'..mask,['-j']='CONNMARK',['--restore-mark']=true,['--nfmask']=mask,['--ctmask']=mask}
  local dns={['-m']={'addrtype','udp'},['--dst-type']='LOCAL',['-p']='udp',['--dport']='53',['-j']='RETURN'}
  local expected={restore,dns}
  local marks,seen={},{}
  for _,tunnel in ipairs(order) do
    if not string.find(tunnel,'^[0-9]+$') or #tunnel>12 then unverified() end
    local chain='TUNNEL'..tunnel..'_ROUTE_POLICY'
    expected[#expected+1]={['-m']={'addrtype'},['! --dst-type']='LOCAL',['-j']=chain}
    local rules=chains[chain]
    if not rules or #rules~=2 then unverified() end
    local set,drop=M.fields(rules[1]),M.fields(rules[2])
    local value=set['--set-xmark'] and string.match(set['--set-xmark'],'^([0-9]+)/'..mask..'$')
    if not value or not same_fields(set,{['-m']={'mark'},['--mark']='0/'..mask,['-j']='MARK',['--set-xmark']=value..'/'..mask})
       or not same_fields(drop,{['-m']={'mark'},['--mark']='0/'..mask,['-j']='DROP'}) or seen[value] then
      unverified()
    end
    seen[value]=true;marks[tunnel]=tonumber(value)
  end
  local route=chains.ROUTE_POLICY
  if not route or #route~=#expected then unverified() end
  for i=1,#route do if not same_fields(M.fields(route[i]),expected[i]) then unverified() end end
  return {verified=true,first=order[1],marks=marks}
end

------------------------------------------------------------------------------------------------------
-- fast swap planning (Linux.apply_fast before and after its write)
------------------------------------------------------------------------------------------------------
-- rules: {order=, local_tunnel=, local_mark=} from fast_policy.uci_rules*.
function M.prepare(rules,snapshot)
  local payload,old_first,changed=fp.plan_lines(snapshot.lines,rules.order,rules.local_tunnel,rules.local_mark)
  local plan={payload=payload,old_first=old_first,changed=changed}
  if changed then plan.old_mark=fp.mark_of_lines(snapshot.lines,old_first) end
  return plan
end

-- After the restore: the same plan must have nothing left to change.
function M.verify(rules,snapshot)
  local _,_,still=fp.plan_lines(snapshot.lines,rules.order,rules.local_tunnel,rules.local_mark)
  if still then refuse('FAST-PATH-UNVERIFIED') end
  return true
end

return M
