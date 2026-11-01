-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- dns_mark.lua: LAN DNS follows the active channel (dns_mark.py, the same behaviour).
--
-- GL's kernel module dns_mark marks every LAN DNS query sent to the router; the mark then selects the per-tunnel
-- dnsmasq in `iptables -t nat policy_redirect` (0x1000 -> :2153 wgclient1, 0xb000 -> :4253 ovpnclient2). Its rules
-- (/proc/dns_mark/rule<tunnel_id>/mark) have empty blacklists, so the FIRST rule of /proc/dns_mark/dump wins. The fast
-- switch reorders only ROUTE_POLICY, so after a switch LAN DNS kept the primary tunnel (measured 01.11.2026: 0 of 6
-- lookups during a primary outage). sync() writes the active route's mark into EVERY rule's `mark` file:
--   * never `clear`/`create` (between them unmarked DNS would reach the main dnsmasq and leak to the WAN);
--   * writes only a differing value, then reads every rule back;
--   * /proc/dns_mark absent (other firmware): no-op, code DNS-MARK-UNAVAILABLE;
--   * a write or read-back failure: code DNS-MARK-UNVERIFIED - logged, never a reason to roll a traffic switch back;
--   * values are 0x[0-9a-f]+, rule names rule[0-9]+; no shell.
-- active_from_chains(chains): the mark of the tunnel whose ROUTE_POLICY jump is first (the kernel's live choice).
local canon=require('canon')

local M={}
M.ROOT='/proc/dns_mark'
M.UNAVAILABLE='DNS-MARK-UNAVAILABLE'
M.UNVERIFIED='DNS-MARK-UNVERIFIED'
M.MAX_RULES=64
M.last=nil  -- the last sync() result in this process (native-status channel_path.dns_mark); never UNAVAILABLE
local NULL=canon.null

local function valid_value(value)
  return type(value)=='string' and #value>=3 and #value<=10 and string.find(value,'^0x[0-9a-f]+$')~=nil
end
M.valid_value=valid_value
function M.valid_rule(name)
  return type(name)=='string' and #name>=5 and #name<=16 and string.find(name,'^rule[0-9]+$')~=nil
end

-- number -> '0x..' (lower case), nil when not a positive 31-bit integer
function M.format(number)
  if type(number)~='number' or number~=number or number<=0 or number>0x7fffffff or number%1~=0 then return nil end
  return string.format('0x%x',number)
end

-- the text of a `mark` file -> number or nil ('0x1000', '4096', 'Mark: 0xb000', with any whitespace)
function M.parse(text)
  if type(text)~='string' or #text>256 then return nil end
  local s=string.match(text,'^%s*(.-)%s*$')
  local hex=string.match(s,'^0[xX]([0-9a-fA-F]+)$') or string.match(s,'^[Mm]ark:%s*0[xX]([0-9a-fA-F]+)$')
  if hex then if #hex>8 then return nil end;return tonumber(hex,16) end
  if string.find(s,'^[0-9]+$') and #s<=10 then return tonumber(s,10) end
  return nil
end

-- rule names in dump order ("Rule 5841: ... Mark: 0x1000"), each once
function M.rules_of(dump)
  local out,seen={},{}
  for line in string.gmatch(dump..'\n','([^\n]*)\n') do
    local id=string.match(line,'^%s*Rule%s+([0-9]+):')
    if id then
      local name='rule'..id
      if M.valid_rule(name) and not seen[name] then seen[name]=true;out[#out+1]=name end
    end
  end
  return out
end

-- default file access; tests pass opts.io or opts.root
local function default_read(path)
  local f=io.open(path,'rb')
  if not f then return nil end
  local text=f:read(4096)
  f:close()
  return text or ''
end
local function default_write(path,text)
  local f=io.open(path,'wb')
  if not f then return false end
  local ok=f:write(text)
  local closed=f:close()
  return ok~=nil and ok~=false and closed~=nil and closed~=false
end

-- available(opts): the module's dump is readable (callers skip their iptables read otherwise)
function M.available(opts)
  opts=opts or {}
  local ok,dump=pcall(opts.read or default_read,(opts.root or M.ROOT)..'/dump')
  return ok and type(dump)=='string'
end

-- failed(): the result of a sync that could not run to its end (an unexpected Lua error)
function M.failed()
  M.last=canon.object({active=NULL,rules=canon.array({}),verified=false,code=M.UNVERIFIED,written=0})
  return M.last
end

-- sync(active, opts) -> {active, rules=[{rule, mark}], verified, code, written}
function M.sync(active,opts)
  opts=opts or {}
  local root=opts.root or M.ROOT
  local read=opts.read or default_read
  local write=opts.write or default_write
  local result=canon.object({active=valid_value(active) and active or NULL,rules=canon.array({}),verified=false,code=NULL,written=0})
  local function done(code)
    result.code=code or NULL;result.verified=code==nil
    if code~=M.UNAVAILABLE then M.last=result end  -- other firmware publishes nothing
    return result
  end
  local ok,dump=pcall(read,root..'/dump')
  if not ok or type(dump)~='string' then return done(M.UNAVAILABLE) end
  if not valid_value(active) then return done(M.UNVERIFIED) end
  local want=tonumber(string.sub(active,3),16)
  local names=M.rules_of(dump)
  if #names>M.MAX_RULES then return done(M.UNVERIFIED) end
  local failed=false
  for _,name in ipairs(names) do
    local path=root..'/'..name..'/mark'
    local rok,text=pcall(read,path)
    local current=rok and M.parse(text) or nil
    if current~=want then
      local wok,wrote=pcall(write,path,active..'\n')
      if wok and wrote then result.written=result.written+1 else failed=true end
      rok,text=pcall(read,path)
      current=rok and M.parse(text) or nil
    end
    if current~=want then failed=true end
    result.rules[#result.rules+1]=canon.object({rule=name,mark=current and M.format(current) or NULL})
  end
  return done(failed and M.UNVERIFIED or nil)
end

-- chains: kernel.parse_mangle(); fields: kernel.fields. The mark ('0x..') of the first TUNNEL<id>_ROUTE_POLICY
-- jump of ROUTE_POLICY, or nil when it cannot be read exactly.
function M.active_from_chains(chains,fields)
  if type(chains)~='table' or type(chains.ROUTE_POLICY)~='table' then return nil end
  for _,tokens in ipairs(chains.ROUTE_POLICY) do
    local ok,entry=pcall(fields,tokens)
    if not ok then return nil end
    local target=entry['-j']
    local id=type(target)=='string' and string.match(target,'^TUNNEL([0-9]+)_ROUTE_POLICY$')
    if id then
      for _,rule in ipairs(chains[target] or {}) do
        local fok,set=pcall(fields,rule)
        if not fok then return nil end
        if set['-j']=='MARK' and type(set['--set-xmark'])=='string' then
          local value=string.match(set['--set-xmark'],'^([0-9]+)/[0-9]+$')
          return M.format(value and tonumber(value) or nil)
        end
      end
      return nil
    end
  end
  return nil
end

-- project(value): the checked copy of a published dns_mark block (native-status channel_path.dns_mark), or nil.
-- The page and the bench read only this shape: {active, rules=[{rule, mark}], verified, code, written}.
function M.project(value)
  if not canon.is_object(value) or not canon.is_array(value.rules) or #value.rules>M.MAX_RULES then return nil end
  local active=value.active
  if active~=NULL and not valid_value(active) then return nil end
  local code=value.code
  if code~=NULL and code~=M.UNVERIFIED and code~=M.UNAVAILABLE then return nil end
  local written=value.written
  if type(written)~='number' or written<0 or written>M.MAX_RULES or written%1~=0 then return nil end
  if value.verified~=(code==NULL) then return nil end
  local rules=canon.array({})
  for i,row in ipairs(value.rules) do
    if not canon.is_object(row) or not M.valid_rule(row.rule) or (row.mark~=NULL and not valid_value(row.mark)) then return nil end
    rules[i]=canon.object({rule=row.rule,mark=row.mark})
  end
  return canon.object({active=active,rules=rules,verified=value.verified,code=code,written=written})
end

-- the published view of the last result (copy), or nil
function M.view()
  if M.last==nil then return nil end
  return canon.decode(canon.encode(M.last))
end

return M
