// Integration 2.1.0-alpha8 (03.11.2026): the approved page exposes the settings the merged branches added -
// recovery_rescue_stable (rescue-tune) in «Свои значения», and the expert block of «Система и диагностика» with the
// channel failure detector failure_model (hmm-detector: standard default, fast and the previous rule selectable) and the
// best-server pick model server_pick_model (bayes-pick: simple default). Plus rescue-tune's Auto-off hint.
'use strict';
const assert=require('assert');
const {load,strip,pageSource}=require('./approved_page');
const src=pageSource();

(async()=>{
const flush=()=>new Promise(r=>setTimeout(r,20));
// ---------- the fields, in the mockups' markup, RU and EN ----------
for(const lang of ['ru','en']){
  const {T}=load({lang});
  const html=T.settingsA();
  assert(html.includes('data-set="rescue"')&&html.includes('min="0" max="60"'),'rescue_stable field 0..60 '+lang);
  assert(html.includes('<details class="more"')&&html.includes('data-open="detectMore"')&&html.includes('data-secid="detect"'),'expert block in the mockup markup '+lang);
  assert(html.includes('data-set="failModel"')&&html.includes('data-set="pickModel"'),'both selects '+lang);
  const text=strip(html);
  if(lang==='ru'){
    for(const s of ['Свои значения (11 параметров)','Стабильность основного, если резерв отказал','Эксперт: детектор сбоя и выбор сервера',
      'Стандартный — модель HMM (по умолчанию)','Быстрый — модель HMM, уходит раньше','Прежнее правило: ошибки подряд','Простой — правило 20 % (по умолчанию)','Байесовский — реже лишние смены и пробы'])
      assert(text.includes(s),'RU: '+s);
    // review R3-05: the field saves recovery_failures; the HMM "or N" rule reads hmm_or_failures, a separate setting
    assert(text.includes('это поле её не меняет')&&text.includes('hmm_or_failures'),'RU: the hint does not claim the field sets the HMM extra rule');
    assert(!text.includes('и как добавка «или N ошибок подряд»'),'RU: old wrong hint gone');
  }else{
    for(const s of ['Custom values (11 parameters)','Primary stability when the reserve failed','Expert: failure detector and server pick',
      'Standard — HMM model (default)','Fast — HMM model, leaves earlier','Previous rule: failures in a row','Simple — the 20 % rule (default)','Bayesian — fewer useless changes and probes'])
      assert(text.includes(s),'EN: '+s);
    assert(text.includes('this field does not change it')&&text.includes('hmm_or_failures'),'EN: the hint does not claim the field sets the HMM extra rule');
    assert(!text.includes('and as the extra'),'EN: old wrong hint gone');
    assert(!/[А-Яа-яЁё]/.test(text.slice(text.indexOf('Expert: failure detector'),text.indexOf('Expert: failure detector')+600)),'clean EN in the expert block');
  }
  // the expert block lives in the expert section «Система и диагностика» (level x), the rescue field in the rules section
  assert(/id="sec-system"[\s\S]*data-open="detectMore"/.test(html)&&/id="sec-rules"[\s\S]*data-set="rescue"[\s\S]*id="sec-load"/.test(html),'placement');
}
{ // values come from the router inventory; the defaults when the router has none
  const {T}=load({mutate:({settings})=>{settings.recovery_rescue_stable=25;settings.failure_model='hmm-fast';settings.server_pick_model='bayes';}});
  T.HV.draft=null;const d=T.draft();assert.deepEqual([d.rescue,d.failModel,d.pickModel],[25,'hmm-fast','bayes']);
  const html=T.settingsA();assert(/<option value="hmm-fast" selected>/.test(html)&&/<option value="bayes" selected>/.test(html));
}
{
  const {T}=load({mutate:({settings})=>{delete settings.recovery_rescue_stable;delete settings.failure_model;delete settings.server_pick_model;delete settings.recovery_primary_stable;settings.failure_model='weird';}});
  T.HV.draft=null;const d=T.draft();assert.deepEqual([d.stab,d.rescue,d.failModel,d.pickModel],[120,10,'hmm','simple'],'defaults 120 s / 10 s / hmm / simple');
}
{ // the presets carry rescue_stable (recovery_presets.json) and «Значения по умолчанию» restores 120 s / 10 s
  const {T,c}=load({});
  assert(/var REC_DEFAULTS=\{[^}]*primary_stable:120[^}]*rescue_stable:10\}/.test(src));
  assert(/defaults:function\(\)\{Object\.assign\(D\(\),\{[^}]*stab:120,rescue:10,[^}]*preset:'balanced'\}\)/.test(src),'«Значения по умолчанию» restores 120 s / 10 s');
  T.HV.draft=null;const d=T.draft();assert.equal(d.preset,'custom','the fixture keeps the owner value 30 s: custom');
  const presets=JSON.parse(/var RECOVERY_PRESETS=(\{.*?\});\n/.exec(src)[1]);
  assert(Object.keys(presets).length>=2);for(const k of Object.keys(presets))assert(Number.isInteger(presets[k].rescue_stable),'preset '+k+' carries rescue_stable');
}
// ---------- saving the expert block ----------
{ // only the pick model changed: setup_response with server_pick_model, Auto may stay on (no stop needed)
  const {T,calls,modals,methods}=load({scn:'ok'});T.HV.draft=null;T.draft().pickModel='bayes';await T.saveSection('detect');for(let i=0;i<5;i++)await flush();
  const r=calls.find(x=>x.method==='setup_response');assert(r,'setup_response');
  assert.deepEqual(r.params,['metric','server_pick_model']);assert.deepEqual(r.args.slice(1),['bayes']);
  assert(!methods().includes('setup_recovery')&&!modals.some(m=>/Сначала остановить Auto/.test(m.title||'')),'no rules write, no stop');
  assert(!methods().includes('native_start')&&!methods().includes('terms_accept'));
}
{ // the detector changed while Auto runs: "Stop Auto first", nothing written before the owner agrees
  const {T,modals,methods}=load({scn:'ok'});T.HV.draft=null;T.draft().failModel='hmm-fast';T.saveSection('detect');
  assert(/Сначала остановить Auto/.test(modals[0].title));assert.deepEqual(methods(),[]);
}
{ // Auto off: the detector is saved with the STORED rules (an unsaved rules draft is not written along)
  const {T,calls,flush}=load({scn:'off'});T.HV.draft=null;const d=T.draft();d.failModel='consecutive';d.fails=7;
  T.saveSection('detect');for(let i=0;i<8;i++)await flush();
  const r=calls.find(x=>x.method==='setup_recovery');assert(r,'setup_recovery');
  assert.deepEqual(r.params,['failures','successes','cooldown','min_dwell','return_policy','primary_successes','primary_stable','attempt_limit','attempt_window','rescue_stable','interval','failure_model']);
  assert.deepEqual(r.args,[3,2,60,60,'healthy_primary',2,30,3,15,10,20,'consecutive']);
  assert(!calls.some(x=>x.method==='setup_response'),'the pick model did not change');
}
{ // the wizard sends rescue_stable with the recovery rules
  assert(/recovery:\{failures:Number\(d\.fails\)[^}]*rescue_stable:Number\(d\.rescue\)/.test(src),'first-run wizard saves rescue_stable');
}
// ---------- Auto off and a pair tunnel down: the tunnels are brought up by Auto (rescue-tune hint) ----------
{
  const {T}=load({scn:'off',mutate:({status,inventory})=>{const s=inventory.settings;for(const p of status.profiles)if(p.id===s.plan_source){p.administrative_state='disabled';}}});
  const a=T.autoState();assert.equal(a.text,'Auto выключен');assert(/Туннели поднимает Auto — нажмите Start\. · TUNNEL-DISCONNECTED/.test(a.sub),a.sub);
  const b=load({scn:'off'}).T.autoState();assert(!/TUNNEL-DISCONNECTED/.test(b.sub),'no hint while the tunnels are up');
}
console.log('PASS: alpha8 settings on the approved page - rescue_stable field, expert failure detector and pick model (RU/EN, mockup markup), saving rules, Auto-off tunnel hint');
})().catch(e=>{console.error(e);process.exitCode=1;});
