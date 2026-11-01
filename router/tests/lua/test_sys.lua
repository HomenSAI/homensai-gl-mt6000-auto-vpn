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
