-- Root-only stdin; only the application's UCI config is writable here.
local testroot=os.getenv('HOMENSAI_SETUP_TEST_ROOT')
if testroot and not testroot:match('^/tmp/homensai%-setup%-test%-[A-Za-z0-9_-]+$') then os.exit(1) end
local c=testroot and require('uci').cursor(testroot..'/config',testroot..'/delta') or require('uci').cursor()
local json=require('cjson')
local input=io.read(65537)
if not input or #input>65536 then os.exit(1) end
local ok=pcall(function()
  local data=json.decode(input)
  local allowed={checkpoint=true,probe_limit=true,plan_enabled=true,recovery_failures=true,recovery_successes=true,recovery_cooldown=true,recovery_min_dwell=true,recovery_return_policy=true,recovery_primary_successes=true,recovery_primary_stable=true,enabled=true,plan_source=true,plan_target=true,interval=true,native_duration=true,
    native_session_loss=true,setup_complete=true,telegram_chat=true,telegram_token=true,
    telegram_enabled=true,telegram_interval=true,telegram_schedule=true,telegram_hour=true,telegram_weekly=true,telegram_monthly=true,speed_enabled=true,speed_auto_new=true,
    speed_budget_mib=true,speed_duration=true,speed_streams=true,speed_daily_mib=true,speed_busy_mbps=true}
  for key,value in pairs(data.main) do
    assert(allowed[key] and type(value)=='string')
    assert(c:set('homensai_vpn','main',key,value))
  end
  local existing={}
  c:foreach('homensai_vpn','server',function(s) existing[s.profile]=s['.name'] end)
  for _,row in ipairs(data.servers) do
    local section=existing[row.profile] or row.section
    assert(section:match('^[A-Za-z0-9_]+$'))
    if not c:get('homensai_vpn',section) then assert(c:set('homensai_vpn',section,'server')) end
    for _,key in ipairs({'profile','name','channel','priority','enabled'}) do assert(c:set('homensai_vpn',section,key,row[key])) end
  end
  assert(c:save('homensai_vpn'));assert(c:commit('homensai_vpn'))
end)
if not ok then c:revert('homensai_vpn');os.exit(1) end
io.write('OK')
