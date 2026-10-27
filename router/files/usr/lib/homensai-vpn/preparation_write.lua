-- Only fixed preparation options; no reload, service command or shell.
local j=require('cjson');local u=require('uci')
local root=os.getenv('HOMENSAI_PREPARATION_TEST_ROOT')
if root and not root:match('^/tmp/homensai%-preparation%-test%-[A-Za-z0-9_-]+$')then os.exit(1)end
local base=root or '/etc/config'
local raw=io.read(2097153)
if not raw or #raw>2097152 then os.exit(1)end
local ok=pcall(function()
 local q=j.decode(raw)
 local map={['wg-autostart']='network',['ovpn-autostart']='network',['source-autostart']='network',['target-autostart']='network',hnat='mtkhnat',['flow-offload']='firewall'}
 local package=map[q.action];assert(package)
 assert(type(q.expected)=='string'and #q.expected<=1048576)
 assert(type(q.stage)=='string'and q.stage:match('^/var/run/homensai%-vpn/preparation%-stage%-[A-Za-z0-9_-]+$')or root and type(q.stage)=='string'and q.stage:match('^/tmp/homensai%-preparation%-test%-[A-Za-z0-9_-]+/stage$'))
 assert(type(q.changes)=='table'and #q.changes>=1 and #q.changes<=32)
 local function disk()
  local f=assert(io.open(base..'/'..package,'rb'));local value=f:read(1048577);f:close()
  assert(value and #value<=1048576);return value
 end
 local function pending()
  local live=u.cursor()
  for _,p in ipairs({'network','firewall','mtkhnat','homensai_vpn','route_policy','wireguard','ovpnclient'})do
   local changed=live:changes(p);assert(not changed or next(changed)==nil)
  end
 end
 pending();assert(disk()==q.expected)
 local c=u.cursor(base,q.stage)
 local function value(v)return v==nil and j.null or v end
 local function rows(cursor)
  local result={};cursor:foreach(package,nil,function(s)s['.index']=nil;result[#result+1]=s end);return result
 end
 local before=rows(c);local allowed={}
 for _,row in ipairs(q.changes)do
  assert(type(row)=='table'and type(row.section)=='string'and row.section:match('^[A-Za-z0-9_]+$')and #row.section<=64)
  assert(row.after=='0'and(row.before==j.null or row.before=='0'or row.before=='1'))
  assert(c:get(package,row.section)==row.type)
  if q.action=='wg-autostart'or q.action=='ovpn-autostart'or q.action=='source-autostart'or q.action=='target-autostart'then
   local name=q.action=='wg-autostart'and'wgclient1'or'ovpnclient1'
   local proto=q.action=='wg-autostart'and'wgclient'or'ovpnclient'
   if q.action=='source-autostart'or q.action=='target-autostart'then
    local role=q.action=='source-autostart'and'source'or'target'
    local anchor=c:get('homensai_vpn','main','plan_'..role..'_tunnel');assert(type(anchor)=='string')
    local kind;kind,name=anchor:match('^(%a+):([A-Za-z0-9_]+)$')
    assert(kind=='wireguard'and name:match('^wgclient[1-9]%d*$')or kind=='openvpn'and name:match('^ovpnclient[1-9]%d*$'))
    assert(#name<=14);proto=kind=='wireguard'and'wgclient'or'ovpnclient'
   end
   assert(#q.changes==1 and row.section==name and row.type=='interface'and row.option=='auto'and c:get(package,name,'proto')==proto)
  elseif q.action=='hnat'then assert(#q.changes==1 and row.section=='global'and row.option=='enable')
  else assert(row.type=='defaults'and(row.option=='flow_offloading'or row.option=='flow_offloading_hw'))end
  local key=row.section..'.'..row.option;assert(not allowed[key]);allowed[key]=true
  assert(value(c:get(package,row.section,row.option))==row.before)
 end
 for _,row in ipairs(q.changes)do assert(c:set(package,row.section,row.option,'0'))end
 assert(c:save(package));pending();assert(disk()==q.expected)
 assert(c:commit(package))
 pending();local fresh=u.cursor(base,q.stage)
 for _,row in ipairs(q.changes)do assert(fresh:get(package,row.section,row.option)=='0')end
 local after=rows(fresh)
 local function strip(data)
  for _,section in ipairs(data)do for key in pairs(allowed)do
   local name,option=key:match('^([^.]+)%.(.+)$')
   if section['.name']==name then section[option]=nil end
  end end;return data
 end
 local function eq(a,b)
  if type(a)~=type(b)then return false end
  if type(a)~='table'then return a==b end
  for k,v in pairs(a)do if not eq(v,b[k])then return false end end
  for k in pairs(b)do if a[k]==nil then return false end end;return true
 end
 assert(eq(strip(before),strip(after)))
 io.write('OK')
end)
if not ok then os.exit(1)end
