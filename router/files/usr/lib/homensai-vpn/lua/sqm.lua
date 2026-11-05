-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- sqm.lua: optional SQM (cake) on the VPN tunnel egress for the Lua monitor; twin of sqm.py (same decisions, shared
-- cases tests/sqm_cases.json). Off by default; on only with uci options sqm_enabled='1' AND sqm_upload_kbit
-- (1000..1000000). Per monitor pass, for every probed tunnel device (route binding device + ifindex):
--   tc qdisc replace dev <tunnel> root cake bandwidth <kbit>kbit besteffort triple-isolate nat
-- only over the kernel default root (handle 0:) or a cake this app recorded (RUNTIME/sqm-state.json, with the
-- ifindex); any other root qdisc is left alone (SQM-ROOT-QDISC-BUSY). Back to the kernel default
-- (`tc qdisc del dev <tunnel> root`, only where the root is still cake) when the setting goes off or the rate
-- changes (next pass), at service stop/opkg removal (init script sqm_release from the state file) and, by the
-- kernel itself, when a tunnel restart recreates the device (the record is dropped on the new ifindex).
-- execute(argv) -> rc, text (monitor_io.exec on the router). Nothing runs while SQM is off and nothing is recorded.
local canon=require('canon')

local M={}
M.STATE_NAME='sqm-state.json'
M.VERIFY=300
M.MIN_KBIT=1000
M.MAX_KBIT=1000000
M.CODES={busy='SQM-ROOT-QDISC-BUSY',failed='SQM-APPLY-FAILED',['restore-failed']='SQM-RESTORE-FAILED'}

local function device_name(s) return type(s)=='string' and #s>=1 and #s<=15 and string.find(s,'^[A-Za-z0-9_.-]+$')~=nil end
local function is_int(v) return type(v)=='number' and v==v and v%1==0 and v~=math.huge and v~=-math.huge end
local function sorted_keys(t) local keys={};for k in pairs(t) do keys[#keys+1]=k end;table.sort(keys);return keys end

function M.config(settings)
  if type(settings)~='table' or settings.sqm_enabled~=true then return nil,'SQM-OFF' end
  local kbit=settings.sqm_upload_kbit
  if not is_int(kbit) or kbit<M.MIN_KBIT or kbit>M.MAX_KBIT then return nil,'SQM-BANDWIDTH-UNSET' end
  return kbit,nil
end

function M.cake_argv(device,kbit)
  return {'tc','qdisc','replace','dev',device,'root','cake','bandwidth',string.format('%dkbit',kbit),'besteffort','triple-isolate','nat'}
end
function M.delete_argv(device) return {'tc','qdisc','del','dev',device,'root'} end
function M.show_argv(device) return {'tc','qdisc','show','dev',device,'root'} end

function M.root_qdisc(text)
  if type(text)~='string' then return nil end
  for line in string.gmatch(text,'[^\r\n]+') do
    local fields={};for word in string.gmatch(line,'%S+') do fields[#fields+1]=word end
    if #fields>=4 and fields[1]=='qdisc' then
      for i=4,#fields do if fields[i]=='root' then return {fields[2],fields[3]} end end
    end
  end
  return nil
end

function M.live_devices(rows)
  local live={}
  for _,row in ipairs(type(rows)=='table' and rows or {}) do
    if type(row)=='table' then
      local device,ifindex=row.device,row.ifindex
      if device_name(device) and is_int(ifindex) and ifindex>0 and live[device]==nil then live[device]=ifindex end
    end
  end
  return live
end

function M.records(state)
  local result={}
  local list=type(state)=='table' and state.devices or nil
  for _,row in ipairs(type(list)=='table' and list or {}) do
    local ifindex,kbit,checked=type(row)=='table' and canon.number(row.ifindex),type(row)=='table' and canon.number(row.kbit),
      type(row)=='table' and canon.number(row.checked)
    -- a whole-number float (12.0) is not an int in Python's records(): the same refusal here
    if type(row)=='table' and device_name(row.device) and is_int(ifindex) and not canon.is_float(row.ifindex) and ifindex>0
      and is_int(kbit) and not canon.is_float(row.kbit) and type(checked)=='number' and checked==checked
      and checked~=math.huge and checked~=-math.huge then
      result[row.device]={device=row.device,ifindex=ifindex,kbit=kbit,checked=checked}
    end
  end
  return result
end

function M.state_of(kept)
  local list=canon.array()
  for _,name in ipairs(sorted_keys(kept)) do
    local r=kept[name]
    list[#list+1]=canon.object({device=r.device,ifindex=r.ifindex,kbit=r.kbit,checked=canon.float(r.checked)})
  end
  return canon.object({schema=1,devices=list})
end

local function show(device,execute)
  local rc,text=execute(M.show_argv(device))
  if rc~=0 then return nil end
  return M.root_qdisc(text)
end

function M.restore(device,execute)
  local root=show(device,execute)
  if root==nil or root[1]~='cake' then return true end
  local rc=execute(M.delete_argv(device))
  local after=show(device,execute)
  return rc==0 and (after==nil or after[1]~='cake')
end

function M.sync(settings,rows,state,execute,now)
  local kbit,code=M.config(settings)
  local live,known,kept,devices=M.live_devices(rows),M.records(state),{},{}
  for _,name in ipairs(sorted_keys(known)) do
    local record=known[name]
    if live[name]==nil then kept[name]=record
    elseif live[name]~=record.ifindex then -- recreated: the kernel default already
    elseif kbit~=nil and record.kbit==kbit then kept[name]=record
    elseif not M.restore(name,execute) then kept[name]=record;devices[name]='restore-failed' end
  end
  if kbit~=nil then
    for _,name in ipairs(sorted_keys(live)) do
      local record=kept[name]
      local ours=record~=nil and record.ifindex==live[name]
      if ours and record.kbit==kbit and now-record.checked>=0 and now-record.checked<M.VERIFY then devices[name]='applied'
      else
        local root=show(name,execute)
        if root==nil then devices[name]='failed'
        elseif ours and root[1]=='cake' then
          kept[name]={device=name,ifindex=record.ifindex,kbit=record.kbit,checked=now};devices[name]='applied'
        else
          if ours then kept[name]=nil end
          if root[2]~='0:' then devices[name]='busy'
          else
            local rc=execute(M.cake_argv(name,kbit))
            local after=show(name,execute)
            if rc~=0 or after==nil or after[1]~='cake' then devices[name]='failed'
            else kept[name]={device=name,ifindex=live[name],kbit=kbit,checked=now};devices[name]='applied' end
          end
        end
      end
    end
  end
  local problem=nil
  for _,name in ipairs(sorted_keys(devices)) do
    if problem==nil and M.CODES[devices[name]] then problem=M.CODES[devices[name]] end
  end
  local report=canon.object({enabled=type(settings)=='table' and settings.sqm_enabled==true,kbit=kbit==nil and canon.null or kbit,
    code=(problem or code) or canon.null,devices=canon.object(devices)})
  return M.state_of(kept),report
end

function M.release(state,execute)
  local known,failed,names=M.records(state),{},{}
  for _,name in ipairs(sorted_keys(known)) do
    if not M.restore(name,execute) then failed[name]=known[name];names[#names+1]=name end
  end
  return M.state_of(failed),names
end

function M.active(settings,state)
  return M.config(settings)~=nil or next(M.records(state))~=nil
end

return M
