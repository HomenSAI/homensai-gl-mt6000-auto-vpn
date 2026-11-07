-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- retry_policy.lua: the pause before the next pass after a failed supervisor pass (retry_policy.py, the same rules and
-- tests/retry_policy_cases.json): min(15, 2*F(n)) with full jitter, option retry_backoff 'fixed' keeps the former 5 s.
local M={}
M.CAP=15;M.BASE=2;M.FLOOR=0.5;M.FIXED=5;M.RESET=60
M.FIBONACCI={1,1,2,3,5,8}

function M.mode(settings)
  return type(settings)=='table' and settings.retry_backoff=='fixed' and 'fixed' or 'fibonacci'
end

function M.base(failures)
  local index=math.min(math.max(failures,1),#M.FIBONACCI)
  return math.min(M.CAP,M.BASE*M.FIBONACCI[index])
end

-- The failures in a row including this one: count, now. last: the time of the previous failed pass or nil.
function M.count(failures,last,now)
  if last~=nil and now-last>=0 and now-last<M.RESET then return failures+1,now end
  return 1,now
end

-- [0, 1) from the kernel: math.random is not seeded here, every router would draw the same pauses.
function M.uniform()
  local f=io.open('/dev/urandom','rb')
  local data=f and f:read(2) or nil
  if f then f:close() end
  if not data or #data<2 then return math.random() end
  return (string.byte(data,1)*256+string.byte(data,2))/65536
end

-- Seconds before the next pass after the failures-th failed pass in a row.
function M.pause(failures,settings,uniform)
  if M.mode(settings)=='fixed' then return M.FIXED end
  return math.max(M.FLOOR,(uniform or M.uniform)()*M.base(failures))
end

return M
