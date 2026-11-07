-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- probe_plan.lua: what one monitor pass measures and when (probe_plan.py: the rules and why; the same decisions over
-- tests/probe_plan_cases.json). Pure, no I/O. NULL (canon.null) and nil mean the same here.
local canon=require('canon')
local NULL=canon.null
local M={}
M.SPREAD_CAP=3.0;M.SLOT_TOLERANCE=1.5;M.RESERVE_LOW=20;M.RESERVE_HIGH=120;M.SLACK=2.0

local function value(t,k) local v=t[k];if v==NULL then return nil end;return v end

function M.spread_enabled(settings)
  return type(settings)=='table' and settings.probe_spread~=false
end

function M.reserve_interval(settings)
  local v=type(settings)=='table' and value(settings,'reserve_probe_interval') or nil
  if type(v)=='string' and string.find(v,'^%d+$') then v=tonumber(v) end
  if type(v)~='number' or v%1~=0 or v<M.RESERVE_LOW or v>M.RESERVE_HIGH then return 0 end
  return v
end

function M.effective_reserve(settings,interval,valid_for)
  local wanted=M.reserve_interval(settings)
  if wanted<=0 then return 0 end
  local limit=math.min(wanted,valid_for-interval)
  return limit>interval and limit or 0
end

function M.begin_slot(expected,now)
  if expected==nil or math.abs(now-expected)>M.SLOT_TOLERANCE then return now end
  return expected
end

-- -> slot of the next pass, seconds until it
function M.next_slot(slot,interval,now)
  local planned=slot+interval
  if planned-now<1 then return now+1,1 end
  return planned,planned-now
end

function M.idle(context)
  local source,target=value(context,'source'),value(context,'target')
  return source~=nil and target~=nil and source~=target and value(context,'native')=='OBSERVING'
    and context.source_clean==true and context.target_clean==true
    and not value(context,'dense') and not value(context,'boost') and not value(context,'waiting')
end

function M.clean(row)
  if type(row)~='table' or value(row,'code')~=nil or row.dns_ok~=true then return false end
  local https=value(row,'https_success')
  if type(https)~='number' or https%1~=0 or https<2 or row.vendor_state~='SETTLED' then return false end
  local model=row.failure_model
  return not (type(model)=='table' and (model.suspect==true or model.failed==true))
end

-- probe_plan.carried: the reserve's last measured row, or nil when its tunnel moved since.
function M.carried(row,observation)
  local groups=type(observation)=='table' and observation.groups or nil
  if type(row)~='table' or type(groups)~='table' or row.vendor_state~='SETTLED' then return nil end
  for _,group in ipairs(groups) do
    if type(group)=='table' and group.id==row.vendor_tunnel_id then
      local generation=value(group,'generation')
      if group.state=='SETTLED' and group.current_profile==row.id and generation~=nil and generation==value(row,'vendor_generation')
         and value(group,'changed_at')==value(row,'vendor_changed_at') then return row end
      return nil
    end
  end
  return nil
end

local function contains(list,x) for _,v in ipairs(list) do if v==x then return true end end;return false end

-- -> {skip=ids,order=ids,offsets=seconds per position of order}
function M.plan(ids,context,settings)
  local interval,now=context.interval,context.now
  local is_idle=M.idle(context)
  local source,target=value(context,'source'),value(context,'target')
  local skip={}
  if is_idle and contains(ids,target) then
    local every=M.effective_reserve(settings,interval,context.valid_for)
    local stamp=value(context,'reserve_time')
    if every>0 and stamp~=nil and now-stamp>=0 and now-stamp+interval<=every+M.SLACK then skip[1]=target end
  end
  local all={}
  for _,x in ipairs(ids) do all[#all+1]=x end
  if is_idle and contains(all,source) and #all>1 then
    local moved={}
    for _,x in ipairs(all) do if x~=source then moved[#moved+1]=x end end
    moved[#moved+1]=source;all=moved
  end
  local step=0.0
  if M.spread_enabled(settings) and is_idle and #all>1 then step=math.min(interval/#all,M.SPREAD_CAP) end
  -- a skipped channel keeps its phase empty: the primary stays on one phase and its period stays exactly T
  local order,offsets={},{}
  for index,x in ipairs(all) do
    if not contains(skip,x) then order[#order+1]=x;offsets[#offsets+1]=(index-1)*step end
  end
  return {skip=skip,order=order,offsets=offsets}
end

return M
