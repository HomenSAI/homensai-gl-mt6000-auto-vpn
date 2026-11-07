-- Plan item 54 (audit F-16/F-17): the package maintenance marker, maintenance.lua.
-- Shared cases: ../maintenance_cases.json; Python twin: tests/test_maintenance.py (maintenance.py, the same cases).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local M=require('maintenance')
local NULL=canon.null

local function read_file(path) local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s end
local DATA=canon.decode(read_file(t.here..'/../maintenance_cases.json'))
local function plain(v)
  if v==NULL then return nil end
  if type(v)~='string' and canon.number(v)~=nil then return canon.number(v) end
  return v
end

local function marker_of(case)
  local value=case.marker
  if value=='UNREADABLE' then return false end
  if canon.is_object(value) and (value.boot_id=='BOOT' or value.boot_id=='OTHER') then
    value=canon.decode(canon.encode(value))
    value.boot_id=(value.boot_id=='BOOT') and DATA.boot or DATA.other_boot
  end
  return value
end

t.test('maintenance: the shared cases (maintenance_cases.json)',function()
  for _,case in ipairs(DATA.cases) do
    local boot=DATA.boot
    if case.boot~=nil then boot=plain(case.boot) end
    local got=M.classify(marker_of(case),boot,plain(case.uptime),plain(case.now))
    for key,value in pairs(case.expect) do t.eq(plain(got[key]),plain(value),case.name..' '..key) end
    if got.state=='active' then t.eq({got.code,got.reason},{'MAINTENANCE-IN-PROGRESS',nil},case.name)
    elseif got.state=='stale' then t.eq(got.code,'MAINTENANCE-INTERRUPTED',case.name);t.truthy(got.reason,case.name)
    else t.eq(got.state,'none',case.name) end
  end
end)

local function mark(fields)
  local row=canon.object({action='upgrade',boot_id=DATA.boot,uptime=canon.float(90),time=canon.float(990)})
  for k,v in pairs(fields or {}) do row[k]=v end
  return canon.encode(row)
end

t.test('maintenance: proc readers, blocker and public view',function()
  local files={['/proc/sys/kernel/random/boot_id']=DATA.boot..'\n',['/proc/uptime']='100.25 300.00\n'}
  local function read(p) return files[p] end
  t.eq(M.boot_id(read),DATA.boot);t.eq(M.uptime(read),100.25)
  t.eq(M.blocker(read,'/etc',1000),nil);t.eq(M.public(read,'/etc',1000),NULL)
  files['/etc/maintenance.json']=mark()
  t.eq(M.blocker(read,'/etc',1000),'MAINTENANCE-IN-PROGRESS')
  local v=M.public(read,'/etc',1000)
  t.eq({v.state,v.code,v.action,canon.number(v.since)},{'active','MAINTENANCE-IN-PROGRESS','upgrade',990})
  files['/etc/maintenance.json']=mark({boot_id=DATA.other_boot})     -- the power cut: the next boot never blocks
  t.eq(M.blocker(read,'/etc',1000),nil)
  t.eq(M.public(read,'/etc',1000).reason,'reboot')
  files['/etc/maintenance.json']='{"action":'
  t.eq(M.public(read,'/etc',1000).reason,'invalid')
  files['/etc/maintenance.json']=string.rep(' ',5000)..'{}'
  t.eq(M.public(read,'/etc',1000).reason,'invalid')
  -- a reader that raises is an unreadable marker, never a crash
  t.eq(M.blocker(function() error('io') end,'/etc',1000),nil)
end)

t.test('maintenance: clear_stale reports and removes only a stale marker',function()
  local dir=os.tmpname();os.remove(dir)
  os.execute('mkdir -p '..dir..'/proc/sys/kernel/random')
  local function put(p,s) local f=assert(io.open(p,'wb'));f:write(s);f:close() end
  put(dir..'/proc/sys/kernel/random/boot_id',DATA.boot..'\n');put(dir..'/proc/uptime','100.25 300.00\n')
  t.eq(M.clear_stale(dir,1000,nil,dir..'/proc'),nil)
  put(dir..'/maintenance.json',mark())
  t.eq(M.clear_stale(dir,1000,nil,dir..'/proc'),nil)
  local still=io.open(dir..'/maintenance.json','rb');t.truthy(still,'an active marker stays');still:close()
  put(dir..'/maintenance.json',mark({boot_id=DATA.other_boot}))
  local record=M.clear_stale(dir,1000,nil,dir..'/proc')
  t.eq(io.open(dir..'/maintenance.json','rb'),nil)
  local stored=canon.decode(read_file(dir..'/upgrade-result.json'))
  t.eq({stored.code,stored.reason,stored.action,stored['from'],stored.to,canon.number(stored.since)},
       {'MAINTENANCE-INTERRUPTED','reboot','upgrade','','',990})
  t.eq(record.code,'MAINTENANCE-INTERRUPTED')
  os.execute('rm -rf '..dir)
end)

-- IR-06 (integration review 07.11.2026): the marker file as read from disk with the default reader; Python twin:
-- test_maintenance.py SharedFiles (the same maintenance_cases.json "files"). Before, Lua followed a symlink.
t.test('maintenance: the shared file cases (symlink never followed, maintenance_cases.json files)',function()
  local function put(p,s) local f=assert(io.open(p,'wb'));f:write(s);f:close() end
  local function exists(p) return os.execute('[ -e '..p..' ] || [ -L '..p..' ]')==0 end
  for _,case in ipairs(DATA.files) do
    local dir=os.tmpname();os.remove(dir)
    os.execute('mkdir -p '..dir..'/etc '..dir..'/proc/sys/kernel/random')
    put(dir..'/proc/sys/kernel/random/boot_id',DATA.boot..'\n')
    put(dir..'/proc/uptime',tostring(plain(case.uptime))..' 1.0\n')
    local persist,path,target=dir..'/etc',dir..'/etc/maintenance.json',dir..'/elsewhere.json'
    local marker=marker_of(case)
    local text=marker~=NULL and canon.encode(marker) or nil
    if case.layout=='regular' then put(path,text)
    elseif case.layout=='symlink' then put(target,text);os.execute('ln -s '..target..' '..path)
    elseif case.layout=='dangling' then os.execute('ln -s '..dir..'/missing.json '..path)
    elseif case.layout=='directory' then os.execute('mkdir '..path) end
    local want=case.expect
    t.eq(M.read_marker(M.read_file,persist)==false,want.read=='invalid',case.name..': read')
    local view=M.current(M.read_file,persist,plain(case.now),dir..'/proc')
    t.eq(view.state,want.state,case.name..': state')
    if want.reason~=nil then t.eq(view.reason,want.reason,case.name..': reason') end
    t.eq(M.blocker(M.read_file,persist,plain(case.now),dir..'/proc'),plain(want.blocker),case.name..': blocker')
    if want.clear_stale~=nil then
      local record=M.clear_stale(persist,plain(case.now),nil,dir..'/proc')
      if want.clear_stale==NULL then t.eq(record,nil,case.name);t.truthy(exists(path),case.name..': kept')
      else
        for k,v in pairs(want.clear_stale) do t.eq(record[k],v,case.name..': clear_stale '..k) end
        t.eq(exists(path),false,case.name..': the link itself is removed')
      end
    end
    if case.layout=='symlink' then t.eq(read_file(target),text,case.name..': the target is never touched') end
    os.execute('rm -rf '..dir)
  end
end)

t.run()
