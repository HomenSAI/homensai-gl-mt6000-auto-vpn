'use strict';
// Owner review 01.11.2026 on the built page: the forecast checkbox is explained, the WAN traffic option says it is the
// provider uplink including the encrypted VPN, the sidebar has no "Real IPv4 router measurements" caption (version and
// developer stay), and the statistics blocks with a reset backend carry a reset marker.
const fs=require('fs'),assert=require('assert');
const built=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+JSON.parse(fs.readFileSync('VERSION.json','utf8')).application.ui_module+'.js','utf8');
const lazy=fs.readFileSync('router/files/www/luci-static/resources/homensai-vpn/'+JSON.parse(fs.readFileSync('VERSION.json','utf8')).application.ui_lazy_modules[0].split('/').pop(),'utf8');
// (3) plan_enabled = failover_plan dry-run forecast
assert(!built.includes('Show what Auto would do (no switching)')&&!built.includes('Показывать, что сделал бы Auto'));
assert(built.includes('Forecast mode: show whether Auto would switch now (nothing is switched)')&&built.includes('Режим прогноза: показывать, переключил бы Auto сейчас (ничего не переключается)'));
assert(built.includes("'data-plan-hint':'1'")&&built.includes('Только наблюдение: по свежим проверкам монитор вычисляет'));
// (7) WAN = provider uplink incl. tunnel packets, not LAN traffic outside the VPN
assert(!built.includes('Через WAN (провайдер)'));
assert(built.includes('Provider uplink (WAN), including encrypted VPN')&&built.includes('Канал провайдера (WAN), включая зашифрованный VPN'));
assert(built.includes('Это не трафик устройств мимо VPN'));
// (13) sidebar caption removed; version/developer kept
assert(!built.includes('Real IPv4 router measurements')&&!built.includes('Реальные IPv4-измерения роутера'));
assert(built.includes("bi('Developer · Serhii Khomenko'"));
// (8/11) reset markers: traffic, latency, server uptime (quality), events (auto), switch statistics (auto, lazy page)
for(const marker of ["'data-stats-reset':'traffic'","'data-stats-reset':'latency'","'data-stats-reset':'auto'","setAttribute('data-stats-reset','quality')","'data-event-history':'1','data-stats-reset':'auto'"])assert(built.includes(marker),marker);
assert(lazy.includes("'class':'hv-switch-stats','data-stats-reset':'auto'"));
assert(built.includes("bi('Reset statistics','Сброс статистики')"));
console.log('PASS: owner wording (forecast, WAN uplink, no IPv4 caption) and reset markers on the built page');
