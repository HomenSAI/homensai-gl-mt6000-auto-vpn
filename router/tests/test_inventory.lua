package.preload['uci']=function()
  local data={
    network={{['.name']='ovpnclient3',['.type']='interface',proto='ovpnclient',config='12_34'},
             {['.name']='wgclient1',['.type']='interface',proto='wgclient',config='peer_56'}},
    ovpnclient={{['.name']='12_34',name='Office',group_id='12',path='PRIVATE_PATH_SENTINEL',password='PASSWORD_SENTINEL'},
                {['.name']='groups',token='TOKEN_SENTINEL'}},
    wireguard={{['.name']='peer_56',name='Backup',group_id='90',private_key='PRIVATE_KEY_SENTINEL'}},
    homensai_vpn={{['.name']='main',['.type']='main',enabled='1'},
                  {['.name']='custom',['.type']='server',profile='openvpn:12_34',name='My office',channel='Work'}}
  }
  return {cursor=function()return {foreach=function(_,package,kind,fn)
    for _,s in ipairs(data[package] or {}) do if not kind or kind==s['.type'] then fn(s) end end
  end}end}
end
dofile(arg[1])
