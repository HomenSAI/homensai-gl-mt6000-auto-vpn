-- HomenS.AI / Serhii Khomenko / https://homensai.com -- MIT
-- Root-only pipe, never a public RPC result. Read credentials/config atomically.
local c=require('uci').cursor()
local json=require('cjson')
local s=c:get_all('homensai_vpn','main') or {}
local out={}
for _,key in ipairs({'telegram_enabled','telegram_token','telegram_chat','telegram_interval',
  'telegram_schedule','telegram_hour','telegram_weekly','telegram_monthly','telegram_items'}) do
  out[key]=s[key] or ''
end
io.write(json.encode(out))
