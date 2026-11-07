-- The real sys.lua command lines (the backend tests replace sys with a fake, so they never build these).
-- guard_release must hand sh the same job as Python's schedule_release, which itself holds single quotes.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
local sys=require('sys')

t.test('guard_release passes the quoted nft element through sh -c',function()
  local seen
  local execute=os.execute
  os.execute=function(line) seen=line;return 0 end
  local ok,err=pcall(sys.guard_release,'0a1b2c3d',75,'homensai_guard')
  os.execute=execute
  t.truthy(ok,'no error: '..tostring(err))
  local job=[[sleep 75; nft delete element inet homensai_guard blocked_lan_0a1b2c3d '{ "br-lan" }' 2>/dev/null || :]]
  local word=string.match(seen,'^%(setsid sh %-c (.-) || sh %-c ')
  t.truthy(word,'setsid form')
  local p=io.popen('printf %s '..word)
  local back=p:read('*a');p:close()
  t.eq(back,job,'sh reads the job back unchanged')
end)

t.test('guard_release refuses a generation or table it did not check',function()
  local execute=os.execute
  local calls=0
  os.execute=function() calls=calls+1;return 0 end
  t.raises(sys.guard_release,"0a1b2c3'",75,'homensai_guard')
  t.raises(sys.guard_release,'0a1b2c3d',75,"x'; reboot")
  os.execute=execute
  t.eq(calls,0,'nothing ran')
end)

-- R2-01: a spawned command that does not finish is stopped and its exit confirmed; wait() alone never does that
t.test('spawn records the pid; terminate stops a sleeping writer and confirms its exit',function()
  local root=os.tmpname();os.remove(root);assert(os.execute("mkdir -p '"..root.."'"))
  local saved=sys.RUNTIME;sys.RUNTIME=root
  local handle=sys.spawn({'sleep','30'},{timeout=60})
  t.truthy(handle,'spawned')
  t.eq(sys.wait(handle,0.3),nil,'still running')
  t.eq(sys.finished(handle),false)
  local started=os.time()
  t.eq(sys.terminate(handle,4),true,'exit confirmed after the signal')
  t.truthy(os.time()-started<10,'did not wait for the sleep to end')
  t.eq(io.open(handle,'r'),nil,'status consumed');t.eq(io.open(handle..'.pid','r'),nil,'pid file removed')
  -- a finished command: its status is read back as before
  local quick=sys.spawn({'true'})
  t.eq(sys.wait(quick,3),0)
  sys.RUNTIME=saved
  os.execute("rm -rf '"..root.."'")
end)

-- R4-02 / R4-04 (night2 N3-regress 1, 4): no setsid on the MT3000 - the whole writer tree must be gone before a
-- termination counts as confirmed; a pid whose start time is not ours is never signalled; a finished writer is not signalled
local function sandbox()
  local root=os.tmpname();os.remove(root);assert(os.execute("mkdir -p '"..root.."'"))
  local saved={sys.RUNTIME,sys.have_setsid,sys.PROC}
  sys.RUNTIME=root
  return root,function() sys.RUNTIME,sys.have_setsid,sys.PROC=saved[1],saved[2],saved[3];os.execute("rm -rf '"..root.."'") end
end
local function recorded(handle)
  for _=1,30 do
    local f=io.open(handle..'.pid','r')
    if f then local text=f:read('*l') or '';f:close();local pid,start=string.match(text,'^(%d+)%s+(%d+)');if pid then return pid,start end end
    sys.sleep(0.1)
  end
  return nil
end
t.test('without setsid: terminate stops the grandchild too and confirms only once the whole tree is gone',function()
  local root,restore=sandbox()
  sys.have_setsid=false
  local handle=sys.spawn({'sh','-c','sleep 297 & exec sleep 298'})
  local pid,start=recorded(handle)
  t.truthy(pid,'pid recorded');t.truthy(start,'start time recorded with the pid')
  local tree
  for _=1,30 do tree=sys.process_tree(pid);local n=0;for _ in pairs(tree or {}) do n=n+1 end;if n>=2 then break end;sys.sleep(0.1) end
  local count=0;for _ in pairs(tree) do count=count+1 end
  t.eq(count,2,'the writer and its grandchild')
  t.eq(sys.terminate(handle,4),true,'confirmed')
  for p,st in pairs(tree) do t.eq(sys.process_alive(p,st),false,'process '..p..' is gone') end
  t.eq(io.open(handle,'r'),nil,'status consumed');t.eq(io.open(handle..'.tree','r'),nil,'tree file removed')
  restore()
end)
t.test('terminate is UNCONFIRMED when the process tree cannot be read, even though the exit status arrives',function()
  local root,restore=sandbox()
  sys.have_setsid=false
  local handle=sys.spawn({'sleep','296'})
  local pid,start=recorded(handle)
  sys.PROC=root..'/no-proc'
  t.eq(sys.terminate(handle,1),false,'not confirmed: identity and descendants unknown')
  t.eq(sys.finished(handle),false,'stays unresolved in this boot')
  sys.PROC='/proc'
  t.eq(sys.process_alive(pid,start),true,'a process whose identity could not be verified is never signalled')
  os.execute('kill -KILL '..pid..' >/dev/null 2>&1')
  restore()
end)
t.test('a reused pid (start time differs) is never signalled; a finished writer is not signalled at all',function()
  local root,restore=sandbox()
  sys.have_setsid=false
  local handle=sys.spawn({'sleep','295'})
  local pid,start=recorded(handle)
  local f=assert(io.open(handle..'.pid','w'));f:write(pid..' 1\n');f:close()  -- another start time: not our process
  t.eq(sys.terminate(handle,1),false,'nothing confirmed')
  t.eq(sys.process_alive(pid,start),true,'the process with the other start time was left alone')
  os.execute('kill -KILL '..pid..' >/dev/null 2>&1')
  local quick=sys.spawn({'true'})
  for _=1,30 do if sys.finished(quick) then break end;sys.sleep(0.1) end
  local kills=0
  local execute=os.execute
  os.execute=function(line) if string.find(line,'^kill ') then kills=kills+1 end;return execute(line) end
  local ok,confirmed=pcall(sys.terminate,quick,1)
  os.execute=execute
  t.truthy(ok,'no error');t.eq(confirmed,true);t.eq(kills,0,'a finished writer is not signalled')
  restore()
end)

t.test('exec still refuses a quote, newline or non-string argument',function()
  t.raises(sys.exec,{'echo',"a'b"})
  t.raises(sys.exec,{'echo','a\nb'})
  t.raises(sys.exec,{'echo',5})
end)

t.test('modestr_bits reads nixio modestr including setuid, setgid and sticky',function()
  t.eq(sys.modestr_bits('rwx------'),448)
  t.eq(sys.modestr_bits('rw-------'),384)
  t.eq(sys.modestr_bits('rwxr-xr-x'),493)
  t.eq(sys.modestr_bits('rwxrwxrwt'),1023)
  t.eq(sys.modestr_bits('rwsr-sr-T'),2048+1024+512+256+128+64+32+8+4)
  t.eq(sys.modestr_bits('rwx'),nil)
  t.eq(sys.modestr_bits('rwxrwxrwq'),nil)
end)

t.test('chunk gives the packaged source its stdin through io.read, never the daemon stdin',function()
  t.eq(sys.chunk('echo_stdin',"local x=io.read('*a');print(x)",'{"a":1}'),'{"a":1}\n')
  t.eq(sys.chunk('echo_stdin',"local x=io.read('*a');print(x)"),'\n','no stdin reads empty, like </dev/null')
  t.raises(sys.chunk,'read_line',"return io.read('*l')",'x')
  t.eq(sys.chunk('io_rest',"print(type(io.open))"),'function\n','the rest of io is untouched')
end)

t.run()
