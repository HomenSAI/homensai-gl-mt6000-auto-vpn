-- net.configs / net.network with a fake router: F-41 / D07 - the cache of protected config digests and of the UCI
-- network read is keyed by the file CONTENT, not by (type, inode, size, mtime, ctime). Two same-size in-place
-- edits within one timestamp tick share the metadata tuple; Python hashes the contents on every tick and sees them.
local t=dofile((arg[0]:match('^(.*)/[^/]*$') or '.')..'/harness.lua')
package.preload['sys']=function() return {} end
local canon=require('canon')
local fake=require('backend_fake')
local net=require('net')
local identity=require('identity')

local function O(t_) return canon.object(t_) end
local function A(t_) return canon.array(t_) end
local function world()
  local w={runtime='/run/hv',files={},dirs={},chunks={},mtimes={},inodes={}}
  for _,name in ipairs(net.CONFIGS) do w.files['/etc/config/'..name]="config x '"..name.."'\n" end
  w.files['/etc/config/network']="config interface 'lan'\n"
  w.network=A({O({['.name']='wgclient1',proto='wgclient',disabled='0'})})
  w.chunks['pair_network_read']=function() return canon.encode(w.network) end
  return w
end
local function same_size(text,from,to) assert(#from==#to);return (string.gsub(text,from,to)) end

t.test('two same-size in-place edits with identical metadata change the protected digests',function()
  local w=world();local sys=fake.new(w);local n=net.new({},sys)
  local first=n.configs(identity.LEGACY)
  local key=sys.key('/etc/config/firewall')
  w.files['/etc/config/firewall']=same_size(w.files['/etc/config/firewall'],"'firewall'","'firewalL'")
  t.eq(sys.key('/etc/config/firewall'),key,'the fake metadata tuple is unchanged (same size, same times, same inode)')
  local second=n.configs(identity.LEGACY)
  t.truthy(second.firewall~=first.firewall,'the first edit is seen')
  w.files['/etc/config/firewall']=same_size(w.files['/etc/config/firewall'],"'firewalL'","'fireWalL'")
  local third=n.configs(identity.LEGACY)
  t.truthy(third.firewall~=second.firewall and third.firewall~=first.firewall,'the second edit is seen')
  t.eq(sys.key('/etc/config/firewall'),key)
  -- unchanged contents: the digest is not recomputed
  local hashes=0;local real=canon.sha256
  canon.sha256=function(text) hashes=hashes+1;return real(text) end
  local fourth=n.configs(identity.LEGACY)
  canon.sha256=real
  t.eq(hashes,0,'unchanged contents are not hashed again');t.eq(fourth,third)
  -- a different managed set is a different digest row, as before
  local other=n.configs(O({wgclient1='wgclient',ovpnclient2='ovpnclient'}))
  t.eq(other.firewall,third.firewall)
end)

t.test('the UCI network read is repeated after a same-size edit of /etc/config/network or of its delta',function()
  local w=world();local sys=fake.new(w);local n=net.new({},sys)
  n.network();n.network()
  t.eq(sys.calls['chunk:pair_network_read'],1,'unchanged: read once')
  w.files['/etc/config/network']=same_size(w.files['/etc/config/network'],"'lan'","'lam'")
  n.network()
  t.eq(sys.calls['chunk:pair_network_read'],2,'same-size edit: read again')
  w.files['/tmp/.uci/network']="network.wgclient1.disabled='1'\n"
  n.network()
  t.eq(sys.calls['chunk:pair_network_read'],3,'a delta appeared: read again')
  w.files['/tmp/.uci/network']="network.wgclient1.disabled='0'\n"
  n.network()
  t.eq(sys.calls['chunk:pair_network_read'],4,'same-size delta edit: read again')
  n.network()
  t.eq(sys.calls['chunk:pair_network_read'],4,'unchanged again: cached')
end)

t.test('an oversize or non-regular config file is never served from the cache',function()
  local w=world();local sys=fake.new(w);local n=net.new({},sys)
  n.network()
  w.links['/etc/config/network']=true
  n.network();n.network()
  t.eq(sys.calls['chunk:pair_network_read'],3,'a symlink in place of the config: no caching')
  w.links['/etc/config/firewall']=true
  t.code('PAIR-CONFIG-UNVERIFIED',n.configs,identity.LEGACY)
end)

t.run()
