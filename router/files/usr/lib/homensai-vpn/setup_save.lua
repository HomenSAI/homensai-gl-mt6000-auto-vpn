-- Root-only stdin; only the application's UCI config is writable here.
local testroot=os.getenv('HOMENSAI_SETUP_TEST_ROOT')
if testroot and not testroot:match('^/tmp/homensai%-setup%-test%-[A-Za-z0-9_-]+$') then os.exit(1) end
local function cursor()
  return testroot and require('uci').cursor(testroot..'/config',testroot..'/delta') or require('uci').cursor()
end
local c=cursor()
-- A previous process may have died after save and before commit. Do not merge
-- those unacknowledged changes into a different operator request or discard them.
local savedir=type(c.get_savedir)=='function' and c:get_savedir() or nil
if type(savedir)~='string' or savedir:sub(1,1)~='/' then io.write('SETUP-DELTA-UNVERIFIED');os.exit(1) end
local pending,open_error,open_errno=io.open(savedir..'/homensai_vpn','r')
if pending then
  local byte,read_error=pending:read(1);pending:close()
  if byte then io.write('SETUP-PENDING-DELTA');os.exit(1) end
  if read_error then io.write('SETUP-DELTA-UNVERIFIED');os.exit(1) end
elseif open_errno~=2 then io.write('SETUP-DELTA-UNVERIFIED');os.exit(1) end
local json=require('cjson')
local input=io.read(65537)
if not input or #input>65536 then os.exit(1) end
local data,sections
local committed=false
local ok=pcall(function()
  data=json.decode(input)
  local allowed={probe_level=true,probe_boost=true,measure_interval=true,live_log_limit=true,history_days=true,checkpoint=true,probe_limit=true,plan_enabled=true,plan_source_tunnel=true,plan_target_tunnel=true,recovery_failures=true,recovery_successes=true,recovery_cooldown=true,recovery_min_dwell=true,recovery_return_policy=true,recovery_primary_successes=true,recovery_primary_stable=true,recovery_attempt_limit=true,recovery_attempt_window=true,enabled=true,plan_source=true,plan_target=true,interval=true,native_duration=true,
    native_session_loss=true,setup_complete=true,terms_version=true,terms_time=true,telegram_chat=true,telegram_token=true,
    telegram_enabled=true,telegram_interval=true,telegram_schedule=true,telegram_hour=true,telegram_weekly=true,telegram_monthly=true,telegram_items=true,speed_enabled=true,speed_auto_new=true,
    speed_budget_mib=true,speed_duration=true,speed_streams=true,speed_daily_mib=true,speed_busy_mbps=true,
    onboarding_version=true,onboarding_complete=true,onboarding_pair_deferred=true,
    appearance_language=true,appearance_design=true,appearance_theme=true,router_model=true}
  if data.main.router_model then
    local selected=data.main.router_model
    assert(selected=='auto' or selected=='mt6000' or selected=='mt3000')
    if selected~='auto' then
      local f=assert(io.open(testroot and testroot..'/board_name' or '/tmp/sysinfo/board_name','r'))
      local board=f:read(128);f:close()
      local actual=({['glinet,gl-mt6000']='mt6000',['glinet,mt3000-snand']='mt3000'})[(board or ''):match('^%s*(.-)%s*$')]
      assert(selected==actual)
    end
  end
  for key,value in pairs(data.main) do
    assert(allowed[key] and type(value)=='string')
    assert(c:set('homensai_vpn','main',key,value))
  end
  -- Only the stored Telegram token may be deleted, and only by an explicit own request.
  for _,key in ipairs(data.delete or {}) do
    assert(key=='telegram_token')
    assert(c:delete('homensai_vpn','main',key))
  end
  local existing={}
  c:foreach('homensai_vpn','server',function(s) existing[s.profile]=s['.name'] end)
  sections={}
  for index,row in ipairs(data.servers) do
    local section=existing[row.profile] or row.section
    sections[index]=section
    assert(section:match('^[A-Za-z0-9_]+$'))
    if not c:get('homensai_vpn',section) then assert(c:set('homensai_vpn',section,'server')) end
    for _,key in ipairs({'profile','name','channel','priority','enabled'}) do assert(c:set('homensai_vpn',section,key,row[key])) end
  end
  assert(c:save('homensai_vpn'));assert(c:commit('homensai_vpn'))
  committed=true
end)
if not ok then c:revert('homensai_vpn');os.exit(1) end
-- An acknowledgement must prove all requested values, not only the completion
-- flag. A new cursor reads the committed file, not the writer's staged cache.
local verified=pcall(function()
  local fresh=cursor()
  for key,value in pairs(data.main) do assert(fresh:get('homensai_vpn','main',key)==value) end
  for _,key in ipairs(data.delete or {}) do assert(fresh:get('homensai_vpn','main',key)==nil) end
  for index,row in ipairs(data.servers) do
    for _,key in ipairs({'profile','name','channel','priority','enabled'}) do
      assert(fresh:get('homensai_vpn',sections[index],key)==row[key])
    end
  end
end)
-- Once committed, a failed readback is uncertain, not a claim of rollback.
if committed and not verified then io.write('SETUP-SAVE-UNCONFIRMED');os.exit(1) end
io.write('OK')
