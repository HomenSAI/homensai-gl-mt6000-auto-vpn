-- A fake router for backend.lua / platform.lua / net.lua / recovery.lua tests: the same table shape as sys.lua.
-- world = {
--   files = {[path]=text},  dirs = {[path]={names...}},  links = {[path]=true},
--   ubus = {['system board']=table, ['network.interface.X status']=table},
--   commands = {[argv joined by ' ']={rc=, out=}},   -- exact argv match; `handlers` may compute replies
--   scripts = {[path]=text},  chunks = {[name]=text}, uci = cursor factory (optional),
--   wall=, clock=, machine='aarch64' }
-- Every exec/ubus/script call is counted in fake.calls (name -> count) and logged in fake.log.
local canon=require('canon')
local F={}

function F.new(world)
  world.files=world.files or {}
  world.dirs=world.dirs or {}
  world.links=world.links or {}
  world.ubus=world.ubus or {}
  world.commands=world.commands or {}
  world.scripts=world.scripts or {}
  world.chunks=world.chunks or {}
  local S={RUNTIME=world.runtime or '/run/hv',LIB='/usr/lib/homensai-vpn',close_fds={},world=world,calls={},log={},writes={},spawned={}}
  local generation=0
  local function count(name) S.calls[name]=(S.calls[name] or 0)+1;S.log[#S.log+1]=name end
  local function mtime(path) return world.mtimes and world.mtimes[path] or 1 end
  function S.wall() return world.wall or 1761830400 end
  function S.clock() return world.clock or 1000 end
  function S.sleep(s) world.clock=(world.clock or 1000)+s;world.wall=(world.wall or 1761830400)+s end
  function S.read(path,maximum)
    count('read:'..path)
    local text=world.files[path]
    if text==nil then return nil end
    if maximum and #text>maximum then error(setmetatable({code='OVERSIZE-FILE',value_error=true},require('auto_control').Refused),0) end
    return text
  end
  function S.lstat(path)
    if world.links[path] then return {type='lnk',size=0,ino=1,dev=1,mtime=1,ctime=1,uid=0,mode=511} end
    local text=world.files[path]
    if text~=nil then return {type='reg',size=#text,ino=world.inodes and world.inodes[path] or 7,dev=world.devs and world.devs[path] or 1,mtime=mtime(path),ctime=mtime(path),uid=world.uid or 0,mode=world.modes and world.modes[path] or 384} end
    if world.dirs[path] then return {type='dir',size=0,ino=8,dev=1,mtime=mtime(path),ctime=1,uid=world.uid or 0,mode=world.modes and world.modes[path] or 493} end
    return nil
  end
  S.lstat_exact=S.lstat
  S.stat=function(path) if world.links[path] then return nil end;return S.lstat(path) end
  function S.euid() return world.uid or 0 end
  function S.key(path)
    local st=S.lstat(path)
    if not st then return 'absent' end
    return table.concat({st.type,tostring(st.ino),tostring(st.size),tostring(st.mtime),tostring(st.ctime),tostring(world.files[path] and #world.files[path] or 0)},':')
  end
  function S.exists(path) return S.stat(path)~=nil end
  function S.dir(path) local d=world.dirs[path];if not d then return nil end;local out={};for i,x in ipairs(d) do out[i]=x end;return out end
  function S.remove(path) world.files[path]=nil;S.writes[#S.writes+1]={'remove',path} end
  function S.write_private(path,text) world.files[path]=text;S.writes[#S.writes+1]={'write',path,text} end
  function S.mkdir(path) world.dirs[path]=world.dirs[path] or {};return true end
  function S.rmdir(path) world.dirs[path]=nil end
  function S.unique() generation=generation+1;return string.format('%08x',generation)..'-'..generation end
  function S.create_exclusive(path,text) if world.files[path] then return false end;world.files[path]=text or '';return true end
  function S.exec(argv,opts)
    local line=table.concat(argv,' ')
    count('exec:'..argv[1])
    S.log[#S.log]='exec:'..line
    if world.handler then
      local rc,out=world.handler(argv,opts,S)
      if rc~=nil then return rc,out or '' end
    end
    local reply=world.commands[line]
    if reply==nil then return 127,'' end
    if type(reply)=='function' then return reply(argv,opts,S) end
    return reply.rc or 0,reply.out or ''
  end
  function S.command(argv,opts)
    local rc,out=S.exec(argv,opts)
    if rc~=0 then error(setmetatable({code=opts and opts.code or 'COMMAND-FAILED',value_error=true},require('auto_control').Refused),0) end
    return out
  end
  function S.spawn(argv,opts)
    local rc=S.exec(argv,opts)
    S.spawned[#S.spawned+1]=table.concat(argv,' ')
    return {rc=rc}
  end
  function S.wait(handle) return handle and handle.rc or nil end
  function S.guard_release(generation_) count('guard_release');world.released=generation_;return true end
  function S.ubus(object,method)
    count('ubus:'..object)
    local v=world.ubus[object..' '..method]
    if type(v)=='function' then return v() end
    return v
  end
  function S.uci_cursor(confdir,savedir) if world.uci then return world.uci(confdir,savedir) end;return nil end
  function S.script(path) count('script:'..path);local t=world.scripts[path];if t==nil then error('no script '..path) end;if type(t)=='function' then return t() end;return t end
  function S.chunk(name,source,stdin)
    count('chunk:'..name)
    local t=world.chunks[name]
    if type(t)=='function' then return t(stdin) end
    if t==nil then error('no chunk '..name) end
    return t
  end
  function S.machine() return world.machine or 'aarch64' end
  return S
end

-- uci show / iptables-save are read by backend.apply_fast through runner.lua; tests replace runner functions.
return F
