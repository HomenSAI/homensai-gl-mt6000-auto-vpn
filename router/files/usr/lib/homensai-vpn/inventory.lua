-- Metadata only. Never emit path, endpoint credentials, passwords or private keys.
local uci=require('uci').cursor()
local json=require('cjson')
local interfaces={}
uci:foreach('network','interface',function(s)
  if (s.proto=='ovpnclient' or s.proto=='wgclient') and s.config then
    interfaces[s.config]={logical=s['.name'],protocol=s.proto=='wgclient' and 'wireguard' or 'openvpn'}
  end
end)
local profiles={}
for _,entry in ipairs({{'ovpnclient','openvpn'},{'wireguard','wireguard'}}) do
  uci:foreach(entry[1],nil,function(s)
    local section=s['.name'] or ''
    local a,b=section:match('^(%d+)_(%d+)$')
    local peer=section:match('^peer_(%d+)$')
    if (entry[2]=='openvpn' and a and b) or (entry[2]=='wireguard' and peer) then
      local bound=interfaces[section]
      profiles[#profiles+1]={id=entry[2]..':'..section,section=section,protocol=entry[2],
        name=s.name or s.description or s.remark or section,
        group_id=tostring(s.group_id or a or ''),profile_id=tostring(b or peer or ''),
        interface=bound and bound.logical or json.null}
    end
  end)
end
local channels={}
uci:foreach('homensai_vpn','server',function(s)
  channels[#channels+1]={id=s['.name'],profile=s.profile or '',name=s.name or '',channel=s.channel or 'default',
    priority=tonumber(s.priority) or 100,enabled=s.enabled~='0'}
end)
local main={enabled=false,interval=30,checkpoint=900,probe_limit=16,timezone='CET-1CEST,M3.5.0,M10.5.0/3'}
uci:foreach('homensai_vpn','main',function(s)
  main.enabled=s.enabled=='1'
  main.plan_enabled=s.plan_enabled=='1'
  main.plan_source=s.plan_source or ''
  main.plan_target=s.plan_target or ''
  main.telegram_configured=type(s.telegram_token)=='string' and #s.telegram_token>20 and type(s.telegram_chat)=='string' and #s.telegram_chat>0
  main.interval=math.max(10,math.min(300,tonumber(s.interval) or 30))
  main.checkpoint=math.max(300,math.min(3600,tonumber(s.checkpoint) or 900))
  main.probe_limit=math.max(1,math.min(32,tonumber(s.probe_limit) or 16))
end)
print(json.encode({profiles=profiles,servers=channels,settings=main}))
