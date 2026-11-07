-- HomenS.AI / Serhii Khomenko / https://homensai.com -- see LICENSE
-- diag_bundle.lua: masked diagnostic bundle (GL-SENSORS-2026-11-04.ru.md, item 5). Twin of diag_bundle.py (same
-- commands, same masking; shared cases router/tests/gl_sensors_cases.json). `homensai-vpn-diag` runs this file:
-- read-only outputs -> masked line by line -> /tmp/homensai-vpn-diag.tar.gz (0600), downloadable by the logged-in GL
-- page through /usr/share/gl-download.d/homensai-vpn. Never uploads, sends or changes anything.
if arg and arg[0] and string.find(arg[0],'diag_bundle%.lua$') then package.path='/usr/lib/homensai-vpn/lua/?.lua;'..package.path end
local M={}
M.OUTPUT='/tmp/homensai-vpn-diag.tar.gz'
M.LIMIT=2*1024*1024
M.MASK='***'
M.SECRET_PARTS={'private','preshared','password','passwd','passphrase','secret','token','psk','key','auth','telegram_chat',
  'endpoint','exit_ip','ssid','bssid','user','login','cookie','bearer','chat','description','comment','label',
  'session_id','sessionid'}
-- A public address becomes pub-<6 hex of djb2(SALT..address)>: one address, one label in every file of a bundle.
-- collect() draws a fresh SALT per bundle (twin of diag_bundle.py).
M.SALT=''
-- F-14 (owner decision 07.11.2026): the stored Telegram recipient and bot token are masked verbatim wherever they appear
-- (also a bare id in a log line); collect() reads them once per bundle (read_known) and restores the list (twin of .py).
M.KNOWN={}
M.KNOWN_OPTIONS={'telegram_chat','telegram_token'}

-- known_values(list) -> the stored secrets worth masking verbatim (destination id/@name, bot token), longest first
function M.known_values(values)
  local found,seen={},{}
  for _,v in ipairs(values or {}) do
    v=type(v)=='string' and (string.gsub(v,'^%s+',''):gsub('%s+$','')) or ''
    local ok=string.match(v,'^%-?%d+$') and #string.gsub(v,'^%-','')>=5 and #string.gsub(v,'^%-','')<=20
      or string.match(v,'^@%a[%w_]+$') and #v>=6 and #v<=33
      or string.match(v,'^%d+:[%w_%-]+$') and #string.match(v,'^(%d+)')>=6 and #string.match(v,'^%d+')<=15 and #string.match(v,':(.*)$')>=30 and #string.match(v,':(.*)$')<=100
    if ok and not seen[v] then seen[v]=true;found[#found+1]=v end
  end
  table.sort(found,function(a,b) if #a~=#b then return #a>#b end return a<b end)
  return found
end

function M.read_known()
  local values={}
  for i,option in ipairs(M.KNOWN_OPTIONS) do
    local pipe=io.popen('uci -q get homensai_vpn.main.'..option..' 2>/dev/null')
    values[i]=pipe and pipe:read('*a') or ''
    if pipe then pipe:close() end
  end
  return M.known_values(values)
end

local function replace_plain(line,value,with)
  local out,start='',1
  while true do
    local a,b=string.find(line,value,start,true)
    if not a then break end
    out=out..string.sub(line,start,a-1)..with;start=b+1
  end
  return out..string.sub(line,start)
end
-- whole names that are secrets although no secret word is inside (URL signature, session id, one-time code)
M.EXACT_SECRET={sig=true,sid=true,signature=true,otp=true,jwt=true}
M.WG_NAMES={['private key']=true,['preshared key']=true,['public key']=true,peer=true,endpoint=true}
M.COMMANDS={
  {'system.txt',{'cat','/etc/openwrt_release','/etc/glversion','/proc/uptime','/proc/loadavg'}},
  {'package.txt',{'cat','/usr/lib/opkg/info/homensai-auto-vpn.control'}},
  {'memory.txt',{'free'}},
  {'ip-rule.txt',{'ip','-4','rule','show'}},
  {'ip-route.txt',{'ip','-4','route','show','table','all'}},
  {'ip-addr.txt',{'ip','-4','addr','show'}},
  {'nft.txt',{'nft','list','ruleset'}},
  {'iptables-mangle.txt',{'iptables-save','-t','mangle'}},
  {'wg.txt',{'wg','show','all'}},
  {'tc.txt',{'tc','-s','qdisc','show'}},
  {'uci-route_policy.txt',{'uci','show','route_policy'}},
  {'uci-network.txt',{'uci','show','network'}},
  {'uci-homensai_vpn.txt',{'uci','show','homensai_vpn'}},
  {'uci-gl_timer.txt',{'uci','show','gl_timer'}},
  {'uci-kmwan.txt',{'uci','show','kmwan'}},
  {'kmwan.txt',{'cat','/proc/gl-kmwan/config'}},
  {'repeater.txt',{'ubus','call','repeater','status'}},
  {'logread-homensai.txt',{'logread','-e','homensai'}},
  {'logread-wireguard.txt',{'logread','-e','wireguard'}},
  {'dmesg.txt',{'dmesg'}},
  {'crash_log.txt',{'cat','/tmp/log/crash_log'}},
  {'status.json',{'cat','/var/run/homensai-vpn/status.json'}},
  {'native-status.json',{'cat','/var/run/homensai-vpn/native-status.json'}},
  {'wg-events.log',{'cat','/var/run/homensai-vpn/wg-events.log'}},
  {'service-run.json',{'cat','/etc/homensai-vpn/service-run.json'}},
  {'boot-resume.json',{'cat','/var/run/homensai-vpn/boot-resume.json'}},
  {'lua-monitor-crashes.json',{'cat','/var/run/homensai-vpn/lua-monitor-crashes.json'}},
}

function M.secret_name(name)
  local lowered=string.lower(name)
  if M.EXACT_SECRET[lowered] then return true end
  for _,part in ipairs(M.SECRET_PARTS) do if string.find(lowered,part,1,true) then return true end end
  return false
end

local HEX='[0-9A-Fa-f][0-9A-Fa-f]'
local MAC=HEX..':'..HEX..':'..HEX..':'..HEX..':'..HEX..':'..HEX
local function trim(s) return (string.gsub(s,'^%s+',''):gsub('%s+$','')) end

local function public_ipv4(a,b)
  return not (a==10 or a==127 or a==0 or a>=224 or (a==172 and b>=16 and b<=31) or (a==192 and b==168)
    or (a==100 and b>=64 and b<=127) or (a==169 and b==254))
end

local function label(text)
  local h=5381
  local s=M.SALT..text
  for i=1,#s do h=(h*33+string.byte(s,i))%4294967296 end
  return string.format('pub-%06x',h%16777216)
end

function M.mask_line(line)
  for _,value in ipairs(M.KNOWN) do line=replace_plain(line,value,M.MASK) end
  local q="'"..M.MASK.."'"
  local a,b,c=string.match(line,'^([%w_.@%[%]%-]+)%.([%w_]+)=(.*)$')
  if a and M.secret_name(b) then line=a..'.'..b..'='..q
  else
    local head,name,gap=string.match(line,'^(%s*option%s+)(%S+)(%s+)(.*)$')
    if not head then head,name,gap=string.match(line,'^(%s*list%s+)(%S+)(%s+)(.*)$') end
    if head and M.secret_name(name) then line=head..name..gap..q
    else
      local lead,wname,space=string.match(line,'^(%s*)([%a ]+):(%s+)(.+)$')
      if lead and M.WG_NAMES[string.lower(trim(wname))] then line=lead..wname..':'..space..M.MASK end
    end
  end
  line=string.gsub(line,'"([%w_%-]+)"(%s*:%s*)"([^"]*)"',function(k,sep,v)
    if M.secret_name(k) then return '"'..k..'"'..sep..'"'..M.MASK..'"' end
    return nil
  end)
  line=string.gsub(line,'()"([%w_%-]+)"(%s*:%s*)(%-?%d%d%d%d%d+)()',function(s,k,sep,v,e)
    local after=string.sub(line,e,e)
    if after=='.' or string.find(after,'^%d$') then return nil end
    if M.secret_name(k) then return '"'..k..'"'..sep..'"'..M.MASK..'"' end
    return nil
  end)
  line=string.gsub(line,'([%w_%.@%[%]%-]+)(%s*=%s*)([\'"]?)([^%s&"\',;]+)',function(name,eq,quote,value)
    local last=string.match(name,'([^%.]+)$') or name
    if not M.secret_name(last) or value==M.MASK then return nil end
    return name..eq..quote..M.MASK
  end)
  line=string.gsub(line,'([Cc][Hh][Aa][Tt][_ ]?[Ii][Dd])(%s*[=:]?%s*)(%-?%d%d%d%d%d+)',function(a,b) return a..b..M.MASK end)
  line=string.gsub(line,'([Ss][Ss][Ii][Dd])(%s+)\'[^\']*\'',function(a,b) return a..b.."'"..M.MASK.."'" end)
  line=string.gsub(line,'[%w%+/]+=',function(s) if #s==44 then return '<key>' end;return nil end)
  line=string.gsub(line,'%d+:[%w_%-]+',function(s)
    local digits,rest=string.match(s,'^(%d+):(.*)$')
    if #digits>=6 and #digits<=12 and #rest>=30 then return '<token>' end
    return nil
  end)
  line=string.gsub(line,'()(%d+)%.(%d+)%.(%d+)%.(%d+)()',function(s,a,b,c,d,e)
    if #a>3 or #b>3 or #c>3 or #d>3 then return nil end
    local before,after,after2=string.sub(line,s-1,s-1),string.sub(line,e,e),string.sub(line,e+1,e+1)
    if s>1 and (before=='.' or string.find(before,'^%d$')) then return nil end
    if after=='.' and string.find(after2,'^%d$') then return nil end
    local x,y,z,w=tonumber(a),tonumber(b),tonumber(c),tonumber(d)
    if x>255 or y>255 or z>255 or w>255 or not public_ipv4(x,y) then return nil end
    return label(a..'.'..b..'.'..c..'.'..d)
  end)
  line=string.gsub(line,'[%x:]+',function(token)
    local _,colons=string.gsub(token,':','')
    if not string.find(token,'::',1,true) and colons~=7 then return nil end
    if token=='::' or token=='::1' or string.lower(string.sub(token,1,3))=='ff0' then return nil end
    return '<ipv6>'
  end)
  line=string.gsub(line,MAC,function(s) return string.sub(s,1,8)..':xx:xx:xx' end)
  return line
end

function M.mask(text)
  local out={}
  for line in string.gmatch(text..'\n','([^\n]*)\n') do out[#out+1]=M.mask_line(line) end
  return table.concat(out,'\n')
end

local function quote(a)
  if type(a)~='string' or string.find(a,"[%z\n']") then error('unsafe argument',0) end
  return "'"..a.."'"
end

-- run(argv,dir) -> text (stdout and stderr, at most LIMIT bytes); never raises. The output is captured inside `dir`,
-- the private 0700 folder of the bundle being built (never a predictable /tmp name, R3-01).
function M.run(argv,dir)
  local parts={}
  for i,a in ipairs(argv) do parts[i]=quote(a) end
  if type(dir)~='string' or dir=='' then return 'unavailable: no private folder\n' end
  local out=dir..'/.out'
  local have_timeout=os.execute('command -v timeout >/dev/null 2>&1')==0
  os.execute((have_timeout and 'timeout 5 ' or '')..table.concat(parts,' ')..' </dev/null >'..quote(out)..' 2>&1')
  local f=io.open(out,'rb')
  local text=f and f:read(M.LIMIT) or ''
  if f then f:close() end
  os.remove(out)
  return text
end

function M.collect(options)
  options=options or {}
  local previous,previous_known=M.SALT,M.KNOWN
  -- the stored recipient/token: read from uci with the real collector; a test collector passes them (or nothing)
  local known=options.known
  if known==nil then known=options.run==nil and M.read_known() or {} end
  M.KNOWN=M.known_values(known)
  local urandom=io.open('/dev/urandom','rb')
  local seed=urandom and urandom:read(8) or tostring(os.time())..tostring(os.clock())
  if urandom then urandom:close() end
  M.SALT=(string.gsub(seed,'.',function(ch) return string.format('%02x',string.byte(ch)) end))
  local ok,result=pcall(M.pack,options)
  M.SALT,M.KNOWN=previous,previous_known
  if not ok then error(result,0) end
  return result
end

local function shell_ok(command)
  local ok=os.execute(command)
  return ok==0 or ok==true
end

-- Builds the bundle inside one private folder (mode 0700): a fresh `mktemp -d` beside the output, or options.work
-- created exclusively (an existing folder, file or planted symlink is an error, never reused or followed). The archive
-- is verified there and published by one os.rename (rename(2) replaces a symlink itself instead of writing through
-- it); an output that is a symlink or a folder is refused. Any failure removes the private folder and raises (R3-01).
function M.pack(options)
  local output=options.output or M.OUTPUT
  local run=options.run or M.run
  local private
  if options.work then
    if not shell_ok('umask 077 && mkdir -m 0700 '..quote(options.work)..' 2>/dev/null') then error('DIAG-BUNDLE-PRIVATE-DIR',0) end
    private=options.work
  else
    local dir=string.match(output,'^(.*)/[^/]+$') or '.'
    local prefix=dir..'/'..string.match(output,'([^/]+)$')..'.'
    local pipe=io.popen('umask 077 && mktemp -d '..quote(prefix..'XXXXXX')..' 2>/dev/null')
    local made=pipe and pipe:read('*l')
    if pipe then pipe:close() end
    if not made or string.sub(made,1,#prefix)~=prefix or not shell_ok('[ -d '..quote(made)..' ] && [ ! -L '..quote(made)..' ]') then
      error('DIAG-BUNDLE-PRIVATE-DIR',0)
    end
    private=made
  end
  local folder=private..'/homensai-vpn-diag'
  local ok,err=pcall(function()
    if not shell_ok('chmod 0700 '..quote(private)..' && mkdir -m 0700 '..quote(folder)) then error('DIAG-BUNDLE-PRIVATE-DIR',0) end
    for _,item in ipairs(options.commands or M.COMMANDS) do
      local text=run(item[2],private)
      local f=io.open(folder..'/'..item[1],'wb')
      if not f then error('DIAG-BUNDLE-FAILED',0) end
      f:write(M.mask(text));f:close()
    end
    local temporary=private..'/bundle.tar.gz'
    if not shell_ok('umask 077 && tar -czf '..quote(temporary)..' -C '..quote(private)..' homensai-vpn-diag && chmod 0600 '..quote(temporary)..
      ' && tar -tzf '..quote(temporary)..' >/dev/null 2>&1') then error('DIAG-BUNDLE-FAILED',0) end
    if shell_ok('[ -L '..quote(output)..' ] || [ -d '..quote(output)..' ]') then error('DIAG-BUNDLE-UNSAFE-OUTPUT',0) end
    local renamed,why=os.rename(temporary,output)
    if not renamed then error('DIAG-BUNDLE-FAILED: '..tostring(why),0) end
  end)
  os.execute('rm -rf '..quote(private))
  if not ok then error(err,0) end
  return output
end

if arg and arg[0] and string.find(arg[0],'diag_bundle%.lua$') and arg[1]=='collect' then
  local ok,result=pcall(M.collect)
  if ok then io.write(result,'\n') else io.stderr:write(tostring(result),'\n');os.exit(1) end
end

return M
