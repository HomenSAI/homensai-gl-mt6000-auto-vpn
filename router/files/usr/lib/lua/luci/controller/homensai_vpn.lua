-- UI resource for 0.9.1-alpha34
-- Legacy LuCI 21.02 controller; newer LuCI can also discover menu.d metadata.
module('luci.controller.homensai_vpn',package.seeall)
function index()
  local parent=entry({'admin','services'},firstchild(),_('Services'),40)
  parent.dependent=false
  local page=entry({'admin','services','homensai-vpn'},view('homensai-vpn/dashboard110'),_('HomenS.AI Auto VPN'),70)
  page.dependent=false
  page.acl_depends={'luci-app-homensai-vpn'}
end
