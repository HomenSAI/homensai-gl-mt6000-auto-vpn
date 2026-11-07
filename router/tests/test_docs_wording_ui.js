// F-81, F-83..F-93 (review of 2026-11-06): wording of the error catalogue, the built-in help and the guides must match the code facts
// named in the review. Text-level checks on the sources and on the generated documents (scripts/sync-documentation.py keeps both
// equal; run it with --check as well). The code facts are quoted next to each check.
'use strict';
const fs=require('fs'),assert=require('assert');
const read=f=>fs.readFileSync(f,'utf8').replace(/\r\n/g,'\n');
const section=(md,code)=>{const i=md.indexOf('\n## '+code+'\n');assert(i>=0,'section '+code);const j=md.indexOf('\n## ',i+5);return md.slice(i,j<0?undefined:j);};
const codes=read('docs/ERROR_CODES.md'),rows=read('router/error_rows_extra.inc.js'),table=read('router/error_table.inc.js');
const helpEn=read('docs/BUILTIN-HELP.en.md'),helpRu=read('docs/BUILTIN-HELP.ru.md');

// F-81: a failed request is an unconfirmed result, not proof of "no change" (fool_guard.inc.js rejects after side effects too)
{
  const s=section(codes,'UI-ACTION-FAILED');
  assert(!/Nothing was changed by this press/.test(s)&&!/ничего не изменило/.test(s),'no claim of "nothing was changed"');
  assert(/unconfirmed/.test(s)&&/не подтверждён/.test(s),'says unconfirmed in EN and RU');
  assert(/result is not confirmed/.test(read('router/fool_guard.inc.js'))&&/результат не подтверждён/.test(read('router/fool_guard.inc.js')),'the notification says so too');
}
// F-83: return timing (settings.js REC_DEFAULTS primary_stable 120, rescue_stable 10; recovery_settings.stable_seconds uses min(...) for a failed reserve)
{
  assert(/return after 2 checks and 120 s of a stable primary, or 10 s if the reserve itself failed/.test(helpEn)&&/возврат после 2 проверок и 120 с стабильного основного, или 10 с/.test(helpRu));
  assert(!/return after 2 checks over 30 s/.test(helpEn)&&!/2 проверок за 30 с/.test(helpRu),'the old 30 s figure is gone from the defaults');
  const m=read('router/measurements_help.inc.js');assert(!/without waiting/.test(m)&&!/Auto returns at once/.test(m),'no "at once" for the rescue return');
  assert(/this consent is required to start Auto at all/.test(helpEn),'session-loss consent is a start prerequisite (pair_auto.py SESSION-LOSS-NOT-ACCEPTED)');
  assert(/primary_stable. \(120 s by default\)/.test(read('docs/HOW-IT-WORKS.en.md')),'HOW-IT-WORKS: shortened, not skipped');
}
// F-84 / F-85: the quick start measured the previous detector; HMM is a probability, not a hard rule
{
  assert(/historical measurement made with the previous "failures in a row" detector/.test(read('docs/AUTO-QUICKSTART.en.md'))&&/историческое измерение с прежним детектором/.test(read('docs/AUTO-QUICKSTART.ru.md')));
  assert(/not a guarantee/.test(read('docs/HOW-IT-WORKS.en.md'))&&/а не гарантия/.test(read('docs/HOW-IT-WORKS.ru.md')));
  assert(!/does not leave on 15-20 s blips/.test(read('docs/HOW-IT-WORKS.en.md')),'no absolute exclusion');
}
// F-86: WAN-RECOVERING holds even with a healthy reserve (wan_diag.py Tracker)
{
  assert(!/never holds|there is never a hold/.test(helpEn+read('docs/HOW-IT-WORKS.en.md')),'no "never a hold"');
  assert(/WAN-DOWN is not declared/.test(helpEn)&&/even when the reserve is healthy/.test(helpEn));
}
// F-87: speed pause is the job budget (speed_test.py: 35 + min(300, profiles*(2*duration+15)), speed_pause.py: +25 s to resume)
{
  const s=section(codes,'MONITOR-DATA-STALE');assert(!/up to a minute/.test(s)&&/335 s/.test(s)&&/25 s more/.test(s)&&/335 с/.test(s));
}
// F-88: shared codes: the proof depends on the mode (lua/transaction.lua publishes COMMITTED / CLIENT-CONFIRMED from router probes)
{
  for(const c of ['COMMITTED','CLIENT-CONFIRMED']){const s=section(codes,c);assert(/router-probed/.test(s)&&/проверка с роутера/.test(s),c+' names both proof modes');}
  assert(!/your computer confirmed it: traffic/.test(section(codes,'COMMITTED')));
}
// F-89: the scientific guide: values of the product today
{
  const en=read('docs/PRINCIPLES-SCIENCE.en.md'),ru=read('docs/PRINCIPLES-SCIENCE.ru.md');
  assert(!/limit 3 \+ 1/.test(en)&&!/лимит 3 \+ 1/.test(ru)&&/limit 2 within a 60 min window/.test(en)&&/лимит 2 за окно 60 мин/.test(ru),'flap_limit 2 / flap_window 60 (recovery_settings.py)');
  assert(!/not yet committed to git/.test(en)&&/in the product since alpha9/.test(en)&&/есть в продукте с alpha9/.test(ru),'slider and advisor are shipped');
  assert(/implemented, default, not proven\*\* \(`retry_policy.py`/.test(en)&&/implemented, default, not proven\*\* \(`probe_plan.py`/.test(en)&&/реализовано, по умолчанию, не доказано\*\* \(`retry_policy.py`/.test(ru)&&/реализовано, по умолчанию, не доказано\*\* \(`probe_plan.py`/.test(ru),'Fibonacci retry and phase spreading are defaults and are labelled not proven');
}
// F-90: result freshness 1.5 x interval + 15 s (website_response.py configure)
assert(!/at most45 seconds/.test(helpEn)&&/1\.5 × the measurement interval plus 15 seconds/.test(helpEn)&&/1,5 интервала измерения плюс 15 секунд/.test(helpRu));
// F-91: the directional start rule is the same in both entries (lua/pair.lua carrying_unaccepted)
{
  const a=table.slice(table.indexOf("'SERVER-KEY-CHANGED'"),table.indexOf("'SERVER-KEY-CHANGED'")+2200);
  assert(/a key only on the other channel does not stop the start/.test(a)&&/ключ только у другого канала запуск не останавливает/.test(a));
  assert(!/Auto does not start with this pair/.test(section(codes,'SERVER-KEY-CHANGED')));
}
// F-92: the codes the Lua core emits are in the catalogue (lua/hv_core.lua HV-CORE-FALLBACK, HV-CORE-WATCHDOG)
for(const c of ['HV-CORE-FALLBACK','HV-CORE-WATCHDOG']){
  assert(rows.includes("['"+c+"','service'"),c+' row in the catalogue source');
  const s=section(codes,c);assert(/lua_core_process/.test(s)&&/\*\*RU:\*\*/.test(s)&&/\*\*EN:\*\*/.test(s),c+' in the generated document, RU and EN');
}
// F-93: stale "current" statements are marked historical
{
  const status=read('docs/CURRENT-STATUS.md'),cur=read('docs/handoff/CURRENT.md');
  assert(/Everything below this line is historical/.test(status)&&/Всё ниже — историческое/.test(status)&&/Кандидат 2\.0\.0-beta5 \(историческое\)/.test(status));
  assert(!/\*\*Актуальная линия разработки \(01\.11\.2026\)/.test(cur)&&/Всё ниже в этом файле — историческое/.test(cur),'handoff: alpha24 is no longer called the current line');
}
// F-59 (documents): the estimate and the bound are two things
assert(/P95 \(estimate\)/.test(read('docs/HOW-IT-WORKS.en.md'))&&/P95 \(оценка\)/.test(read('docs/HOW-IT-WORKS.ru.md'))&&/upper bound, 95 % confidence/.test(read('docs/HOW-IT-WORKS.en.md')));
console.log('PASS: F-81, F-83..F-93 - catalogue, help and guides say what the code does (EN and RU)');
