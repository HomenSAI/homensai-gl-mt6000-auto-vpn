-- Plan item 7: the real shell wrappers of speed.lua and telegram.lua with fake curl executables (no network):
-- background transfer with pid/status files, kill, the Telegram sender's -K config file and its cleanup.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/monitor_harness.lua')
local canon=t.canon
local speed=require('speed')
local telegram=require('telegram')

local dir=os.tmpname();os.remove(dir);dir=string.gsub(dir,'[^A-Za-z0-9_./-]','')..'-hvsh'
os.execute('mkdir -p '..dir..' && chmod 700 '..dir)
-- The offline CI sandbox mounts its tmpfs noexec: the fake programs below cannot run there (exit 126).
local function can_exec(folder)
  local p=folder..'/.exec-probe';local f=io.open(p,'wb');if not f then return false end
  f:write('#!/bin/sh\nexit 0\n');f:close();os.execute('chmod 700 '..p)
  local rc=os.execute(p..' >/dev/null 2>&1');os.remove(p);return rc==0 or rc==true
end
local EXEC=can_exec(dir)
canon.configure({runtime=dir})
local mio=require('monitor_io');mio.configure({RUNTIME=dir,PERSIST=dir})

local function script(name,body)
  local path=dir..'/'..name
  local f=assert(io.open(path,'wb'));f:write('#!/bin/sh\n'..body..'\n');f:close()
  os.execute('chmod 700 '..path)
  return path
end
local function read(path) local f=io.open(path,'rb');if not f then return nil end;local s=f:read('*a');f:close();return s end
local function files() local p=io.popen('ls -A '..dir);local s=p:read('*a');p:close();return s end

t.test('curl_start/curl_poll: the child runs in the background, its -w line and exit status come back',function()
  if not EXEC then print('  skipped: noexec temporary directory');return end
  local d=speed.router({io=mio,runtime=dir,persist=dir})
  local fake=script('fake-ok','printf "200 1024 0 0.125"; exit 0')
  local handle=d.curl_start({fake,'--interface','wgclient1'})
  local result=d.curl_wait(handle)
  t.eq(result.exit,0);t.eq(speed.parse_write_out(result.out).size_download,1024)
  t.eq(speed.parse_write_out(result.out).time_total,0.125)
  local failing=script('fake-fail','exit 28')
  t.eq(d.curl_wait(d.curl_start({failing})).exit,28)
  local slow=script('fake-slow','sleep 30')
  handle=d.curl_start({slow})
  t.eq(d.curl_poll(handle),nil,'still running')
  local deadline=os.time()+5
  while not read(handle.base..'.pid') and os.time()<deadline do os.execute('sleep 0.1') end
  d.curl_kill(handle)
  local killed=d.curl_wait(handle)
  t.truthy(killed.exit~=0,'killed transfer has a non-zero status')
  d.cleanup()
  t.eq(string.find(files(),'.speed-curl-',1,true),nil,'no leftovers: '..files())
end)

t.test('zero_file: exact payload size, created once per size, removed by cleanup',function()
  local d=speed.router({io=mio,runtime=dir,persist=dir})
  local path=d.zero_file(70000)
  t.eq(#read(path),70000);t.eq(d.zero_file(70000),path)
  t.eq(read(path),string.rep('\0',70000))
  d.cleanup();t.eq(read(path),nil)
end)

t.test('telegram sender: token only in the 0600 -K file, JSON body, answer classified, files removed',function()
  if not EXEC then print('  skipped: noexec temporary directory');return end
  local log=dir..'/curl-args.log'
  local fake=script('fake-telegram',[[
for a in "$@"; do printf '%s\n' "$a"; done >]]..log..[[

cfg=; out=; data=
while [ $# -gt 0 ]; do
  case "$1" in -K) cfg=$2; shift;; -o) out=$2; shift;; --data-binary) data=$2; shift;; esac; shift
done
mode=$(stat -c %a "$cfg")
grep -q 'url = "https://api.telegram.org/bot123:synthetic/sendMessage"' "$cfg" || exit 3
[ "$mode" = 600 ] || exit 4
cat "${data#@}" >]]..dir..[[/payload.copy
printf '{"ok":true,"result":{}}' >"$out"
printf 200]])
  local d=telegram.router({io=mio,runtime=dir,persist=dir})
  d.curl=fake
  telegram.send_message(d,{telegram_token='123:synthetic',telegram_chat='-100'},'Hello · Привет')
  local args=read(log)
  t.eq(string.find(args,'synthetic',1,true),nil,'the token is not an argument')
  t.truthy(string.find(args,'--interface',1,true)==nil,'Telegram goes through the router default route like Python')
  local payload=canon.decode(read(dir..'/payload.copy'))
  t.eq(payload.chat_id,'-100');t.eq(payload.text,'Hello · Привет')
  t.eq(string.find(files(),'.telegram-',1,true),nil,'config/payload/body/status removed: '..files())
  local rejecting=script('fake-401','for a in "$@"; do case "$prev" in -o) printf "{}" >"$a";; esac; prev=$a; done; printf 401')
  d.curl=rejecting
  local err=t.raises(telegram.send_message,d,{telegram_token='123:synthetic',telegram_chat='-100'},'x')
  t.eq(err.code,'TELEGRAM-TOKEN-REJECTED');t.eq(err.uncertain,false)
  d.curl=script('fake-dns','exit 6')
  t.eq(t.raises(telegram.send_message,d,{telegram_token='123:synthetic',telegram_chat='-100'},'x').code,'TELEGRAM-DNS')
  d.curl=script('fake-timeout','exit 28')
  err=t.raises(telegram.send_message,d,{telegram_token='123:synthetic',telegram_chat='-100'},'x')
  t.eq(err.code,'TELEGRAM-DELIVERY-UNKNOWN');t.eq(err.uncertain,true)
end)

t.test('a detached child never inherits the held control lock descriptor',function()
  t.eq(speed.closing(mio),'')
  local inside
  mio.try_lock(dir,function() inside=speed.closing(mio) end)
  t.truthy(string.find(inside,'^ %d+>&%-$'),'try_lock descriptor closed in the child: '..tostring(inside))
  t.eq(speed.closing(mio),'','released after the lock')
end)

t.test('cleanup',function() os.execute('rm -rf '..dir) end)
t.run()
