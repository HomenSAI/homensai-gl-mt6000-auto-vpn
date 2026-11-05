-- server_pick.lua: the Bayesian server pick (owner setting server_pick_model 'bayes'). The cases are shared with
-- tests/test_server_pick_bayes.py (tests/server_pick_bayes_cases.json): Lua and Python update, decide, plan and
-- publish the same, down to the bytes of the model file.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local S=require('server_pick')
local NULL=canon.null

local function read_file(path) local f=assert(io.open(path,'rb'));local text=f:read('*a');f:close();return text end
local CASES=canon.decode(read_file(t.here..'/../server_pick_bayes_cases.json'))
local function plain(v) if v==nil or v==NULL then return nil end;return canon.is_float(v) and canon.number(v) or v end
local function r(x,scale) if x==nil then return NULL end;return math.floor(x*scale+0.5) end
local function states_of(entries,now) local out={};for i,e in ipairs(entries) do out[i]=S.model_state(plain(e),now) end;return out end
local function rows_of(list)
  local out={}
  for i,row in ipairs(list) do out[i]={profile=row.profile,current=plain(row.current),alive=plain(row.alive),switchable=plain(row.switchable)} end
  return out
end
local function samples_of(v) if plain(v)==nil then return nil end;local out={};for i,x in ipairs(v) do out[i]=canon.number(x) end;return out end

t.test('model_update (shared cases)',function()
  for _,c in ipairs(CASES.model_update) do
    t.eq(canon.encode(S.model_update(plain(c.entry),canon.number(c.now),samples_of(c.samples))),canon.encode(c.expect),c.name)
  end
end)
t.test('posterior and availability (shared cases)',function()
  for _,c in ipairs(CASES.posterior) do
    local st=S.model_state(plain(c.entry),canon.number(c.now))
    local p=S.posterior(st)
    local got=canon.object({mu_e6=p and r(p[1],1e6) or NULL,var_e9=p and r(p[2],1e9) or NULL,availability_e6=st and r(S.availability(st),1e6) or NULL})
    t.eq(canon.encode(got),canon.encode(c.expect),c.name)
  end
end)
t.test('probe_plan (shared cases)',function()
  for _,c in ipairs(CASES.probe_plan) do
    local plan=S.probe_plan(rows_of(c.rows),states_of(c.entries,c.now),c.now)
    local got=canon.array({});for i=1,#c.rows do got[i]=plan[i]==true end
    t.eq(canon.encode(got),canon.encode(c.expect),c.name)
  end
end)
t.test('decide_bayes (shared cases)',function()
  for _,c in ipairs(CASES.decide) do
    local target=S.decide_bayes(rows_of(c.rows),states_of(c.entries,c.now))
    t.eq(target and target.profile or nil,plain(c.expect),c.name)
  end
end)
t.test('model file read and text (shared cases)',function()
  for _,c in ipairs(CASES.model_read) do
    local files={};if plain(c.text) then files['/run/'..S.MODEL]=c.text end
    local got=S.model_read({runtime='/run',read=function(p) return files[p] end})
    local obj=canon.object();for k,v in pairs(got) do obj[k]=v end
    t.eq(canon.encode(obj),canon.encode(c.expect),c.name)
  end
  for _,c in ipairs(CASES.model_text) do
    local model={};for k,v in pairs(c.model) do model[k]=v end
    t.eq(S.model_text(model,c.now),c.expect,c.name)
  end
end)
t.test('constants are the Python ones',function()
  t.eq({S.HALF_LIFE,S.PRIOR_A,S.PRIOR_B_E4,S.MARGIN_PCT,S.Z_CHANGE_E3,S.Z_PLAUSIBLE_E3,S.STALE,S.AVAILABLE_PCT},{3600,2,1600,0,1645,2000,3600,80})
  t.eq(S.model_name('bayes'),'bayes');t.eq(S.model_name('simple'),'simple');t.eq(S.model_name(nil),'simple');t.eq(S.model_name(NULL),'simple')
  t.eq(S.model_name('Bayes'),'simple')
end)

local function world(c)
  local w={files={},writes={},exec=canon.array({}),logs={},used={}}
  for k,v in pairs(c.files) do w.files[k]=v end
  local fail={};for _,p in ipairs(c.write_fail or {}) do fail[p]=true end
  w.io={runtime='/run',
    read=function(path) return w.files[path] end,
    write=function(path,text) if fail[path] then return false end;w.files[path]=text;w.writes[path]=text;return true end,
    exec=function(argv,seconds)
      local copy=canon.array({});for i,a in ipairs(argv) do copy[i]=a end;w.exec[#w.exec+1]=copy
      if argv[1]=='uci' and argv[2]=='-q' and argv[3]=='-X' and argv[4]=='show' then
        local text=c.uci[argv[5]];if text then return 0,text end;return 1,''
      end
      if argv[1]=='ping' then
        local text=c.ping[argv[#argv]]
        return (text and string.find(text,'round-trip',1,true)) and 0 or 1,text or ''
      end
      return plain((c.rc or {})[table.concat(argv,' ')]) or 0,''
    end,
    tcp=function(host,port,timeout,device)
      w.exec[#w.exec+1]=canon.array({'tcp',host,tostring(port),device or ''})
      local key=host..':'..port;local v=c.tcp[key]
      if canon.is_array(v) then
        local i=(w.used[key] or 0)+1;w.used[key]=i
        return plain(v[i])
      end
      return plain(v)
    end,
    alive=function(pid) return false end,
    wan=function() return plain(c.wan) end,
    active_mark=function() return plain(c.active_mark) end,
    log=function(line) w.logs[#w.logs+1]=line end}
  return w
end

for _,c in ipairs(CASES.job) do
  t.test('job: '..c.name,function()
    local w=world(c)
    local result=S.job(w.io,c.request,plain(c.now))
    t.eq(canon.encode(result),canon.encode(c.expect.result),'result')
    local writes=canon.object();for k,v in pairs(w.writes) do writes[k]=v end
    t.eq(canon.encode(writes),canon.encode(c.expect.writes),'writes')
    t.eq(canon.encode(w.exec),canon.encode(c.expect.exec),'commands')
    local logs=canon.array({});for i,l in ipairs(w.logs) do logs[i]=l end
    t.eq(canon.encode(logs),canon.encode(c.expect.logs),'logs')
  end)
end

t.run()
