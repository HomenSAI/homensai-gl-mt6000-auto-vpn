-- Helper process for tests/test_lua_fast_policy.py: runner.lua and control.lua against real processes,
-- the real Python lock and fake iptables-restore/conntrack/uci programs placed first on PATH.
-- Usage: lua5.1 runner_client.lua <directory> <mode> [argument]
local here=(arg[0]:match('^(.*)/[^/]*$') or '.')
package.path=here..'/../../files/usr/lib/homensai-vpn/lua/?.lua;'..package.path
local runner=require('runner')
local control=require('control')
local canon=require('canon')
local directory,mode,argument=arg[1],arg[2],arg[3]
runner.configure({runtime=directory})

local function code(fn,...)
  local ok,err=pcall(fn,...)
  if ok then return 'ok' end
  return type(err)=='table' and err.code or tostring(err)
end

if mode=='wait' then
  control.lock(function() io.write('acquired\n');io.flush() end,directory)
elseif mode=='hold' then
  control.lock(function() io.write('held\n');io.flush();io.read('*l') end,directory)
elseif mode=='fenced' then
  print(code(runner.fenced,argument,function() local f=assert(io.open(directory..'/ran','w'));f:close() end))
elseif mode=='capture' then
  runner.COMMANDS.test_text="printf 'a\nb'\"'\"'c'"  -- test-only constant
  runner.COMMANDS.test_fail="sh -c 'printf partial; exit 3'"
  print(runner.capture('test_text')=='a\nb\'c' and 'exact' or 'wrong')
  print(code(runner.capture,'test_fail'))
  print(code(runner.capture,'not_a_command'):match('unknown command') and 'unknown' or 'accepted')
elseif mode=='restore' then
  print(code(runner.restore,argument))
elseif mode=='conntrack' then
  print(tostring(runner.conntrack_delete(argument)))
elseif mode=='conntrack-bad' then
  print(code(runner.conntrack_delete,argument))
elseif mode=='batch' then
  print(code(runner.uci_batch,{'reorder route_policy.cfg01=1','commit route_policy'}))
elseif mode=='sha' then
  print(canon.sha256(argument))
elseif mode=='atomic' then
  runner.fs.write_atomic(directory..'/state.json',argument)
  print(runner.fs.read(directory..'/state.json')==argument and 'same' or 'different')
elseif mode=='fds' then
  -- a child started under the lock does not inherit the held descriptor
  runner.COMMANDS.test_fds='ls -l /proc/self/fd/'
  local listing=control.lock(function() return runner.capture('test_fds') end,directory)
  print(listing:find('auto-control.lock',1,true) and 'inherited' or 'closed')
end
