-- F-38: the Lua twins distinguish an ABSENT state file (nil -> default / {}) from an UNREADABLE one (a directory
-- or a symlink in its place, a read error): the latter is an error or a refusal, never 'no file'.
-- Python reference: agent.read_json (FileNotFoundError -> default; a symlink -> ValueError; other OSError raises).
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local canon=require('canon')
local runner=require('runner')
local ctl=require('auto_control')
local journal=require('journal')

local base=os.tmpname()
os.remove(base)
assert(os.execute('mkdir -p '..base)==0)
local absent=base..'/absent.json'
local dir=base..'/state.json';assert(os.execute('mkdir '..dir)==0)  -- a directory where the state file should be
local good=base..'/good.json'
do local f=assert(io.open(good,'wb'));f:write('{"a":1}');f:close() end

local function code_of(err) if type(err)=='table' then return err.code end;return tostring(err) end

t.test('runner.fs.read: nil only for a missing file',function()
  t.eq(runner.fs.read(absent),nil)
  t.eq(runner.fs.read(good),'{"a":1}')
  local ok,err=pcall(runner.fs.read,dir)
  t.eq(ok,false,'a directory in the place of the file is an error, not nil')
  t.truthy(string.find(tostring(err),'STATE%-READ%-FAILED'))
end)

t.test('auto_control.read_json: default only for a missing file, an error for an unreadable one',function()
  local run={fs=runner.fs}
  t.eq(ctl.read_json(run,absent,'dflt'),'dflt')
  t.eq(canon.encode(ctl.read_json(run,good,'dflt')),'{"a":1}')
  local ok,err=pcall(ctl.read_json,run,dir,'dflt')
  t.eq(ok,false,'a directory is never the default')
  t.truthy(code_of(err)=='STATE-FILE-UNREADABLE' or string.find(tostring(err),'STATE%-READ%-FAILED'))
  -- read_json_safe keeps its documented contract (Python: except (OSError,ValueError): row={})
  t.eq(ctl.read_json_safe(run,dir,'dflt'),'dflt')
end)

t.test('auto_control.read_json: a symlink reported by the fs is a coded refusal',function()
  -- the real symlink check needs nixio (lstat) on the router; here the fs reports it
  local fs={read=function() return '{"a":1}' end,unsafe=function(path,limit) return path=='/run/link.json' end}
  local ok,err=pcall(ctl.read_json,{fs=fs},'/run/link.json','dflt')
  t.eq(ok,false);t.eq(code_of(err),'STATE-FILE-UNREADABLE');t.eq(err.value_error,true);t.eq(err.detail,'link.json')
  t.eq(canon.encode(ctl.read_json({fs=fs},'/run/plain.json','dflt')),'{"a":1}')
end)

t.test('journal.read: {} only for a missing journal, a refusal for an unreadable one',function()
  t.eq(canon.encode(journal.read({fs=runner.fs,path=absent})),'{}')
  local ok,err=pcall(journal.read,{fs=runner.fs,path=dir})
  t.eq(ok,false,'a directory in the place of the journal is refused');t.eq(code_of(err),'JOURNAL-INTEGRITY-FAILED')
  local fs={read=function() return nil end,unsafe=function() return true end}
  ok,err=pcall(journal.read,{fs=fs,path='/j'})
  t.eq(ok,false,'a symlink reported by the fs is refused');t.eq(code_of(err),'JOURNAL-INTEGRITY-FAILED')
end)

t.test('cleanup',function() os.remove(good);os.execute('rmdir '..dir);os.execute('rmdir '..base) end)  -- t.run() exits
t.run()
