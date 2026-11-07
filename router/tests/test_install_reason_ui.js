// Owner decisions 07.11.2026: a damaged update rolled back to the previous version (or refused without one) and a missing
// self-check tool (Auto not started) are red reason lines on the page with their catalogue code; RU and EN.
'use strict';
const assert=require('assert');
const {load,strip}=require('./approved_page');

function banner(mutate,lang){
  const {T}=load({scn:'ok',lang:lang||'ru',mutate});
  T.snap();
  return T.B.banner();
}

{ // nothing to report: no install reason line
  const html=banner(()=>{});
  assert.ok(!/data-install-reason/.test(html),html);
}
{ // rolled back: red line with both versions, the Auto rule and the code
  for(const lang of ['ru','en']){
    const html=banner(({status})=>{status.upgrade_result={code:'UPGRADE-ROLLED-BACK',reason:'INTEGRITY-PAYLOAD-DAMAGED',from:'2.1.0-alpha10-1',to:'2.1.0-alpha9',time:1};},lang);
    assert.match(html,/class="note bad warnbar" data-install-reason="UPGRADE-ROLLED-BACK"/);
    assert.match(html,/data-act="code" data-code="UPGRADE-ROLLED-BACK"/);
    const text=strip(html);
    assert.ok(text.includes('2.1.0-alpha10-1 → 2.1.0-alpha9'),text);
    assert.match(text,lang==='ru'?/Обновление повреждено, восстановлена прежняя версия/:/Update damaged, previous version restored/);
  }
}
{ // no previous version / restore failed: the service is off
  for(const code of ['UPGRADE-ROLLBACK-UNAVAILABLE','UPGRADE-ROLLBACK-FAILED']){
    const html=banner(({status})=>{status.upgrade_result={code,reason:'INTEGRITY-HELPER-FAILED',from:'',to:'',time:1};},'en');
    assert.match(html,new RegExp('data-install-reason="'+code+'"'));
    assert.match(strip(html),code==='UPGRADE-ROLLBACK-FAILED'?/restoring the previous version failed/:/no previous version to restore/);
  }
}
{ // an unknown code or a hostile version string is never shown
  const html=banner(({status})=>{status.upgrade_result={code:'UPGRADE-OTHER',from:'<img src=x>'};});
  assert.ok(!/data-install-reason/.test(html),html);
  const html2=banner(({status})=>{status.upgrade_result={code:'UPGRADE-ROLLED-BACK',from:'<img src=x onerror=1>',to:'"x"'};});
  assert.ok(!/<img/.test(html2)&&!/onerror/.test(html2),html2);
}
{ // the self-check tool is missing: Auto not started, monitoring works, reinstall
  for(const lang of ['ru','en']){
    const html=banner(({status})=>{status.integrity={code:'INTEGRITY-TOOL-MISSING',mode:'no-auto',restored:0,files:['/usr/sbin/homensai-vpn-integrity'],version:'',time:1};},lang);
    assert.match(html,/data-install-reason="INTEGRITY-TOOL-MISSING"/);
    assert.match(strip(html),lang==='ru'?/Нет инструмента самопроверки, Auto не запущен/:/Self-check tool missing, Auto not started/);
  }
  // a normal integrity report is not a reason line
  const ok=banner(({status})=>{status.integrity={code:'INTEGRITY-OK',mode:'normal',restored:0,files:[],version:'',time:1};});
  assert.ok(!/data-install-reason/.test(ok),ok);
}
{ // plan item 54: a package operation runs (Auto and the switching buttons wait) or was interrupted (power cut)
  for(const lang of ['ru','en']){
    const html=banner(({status})=>{status.maintenance={state:'active',code:'MAINTENANCE-IN-PROGRESS',action:'upgrade',since:1};},lang);
    assert.match(html,/data-install-reason="MAINTENANCE-IN-PROGRESS"/);
    assert.match(strip(html),lang==='ru'?/Идёт обновление пакета/:/Package update in progress/);
    const stale=banner(({status})=>{status.maintenance={state:'stale',code:'MAINTENANCE-INTERRUPTED',action:'upgrade',since:1,reason:'reboot'};},lang);
    assert.match(stale,/data-install-reason="MAINTENANCE-INTERRUPTED"/);
    assert.match(strip(stale),lang==='ru'?/Обновление пакета не завершилось/:/Package update did not finish/);
  }
  // after the service start the stale mark lives on as upgrade-result.json until the next good installation
  const kept=banner(({status})=>{status.upgrade_result={code:'MAINTENANCE-INTERRUPTED',reason:'reboot',action:'upgrade',from:'',to:'',time:1};},'en');
  assert.match(kept,/data-install-reason="MAINTENANCE-INTERRUPTED"/);
  // shown once even when both say so; an unknown state shows nothing
  const both=banner(({status})=>{status.maintenance={state:'stale',code:'MAINTENANCE-INTERRUPTED'};status.upgrade_result={code:'MAINTENANCE-INTERRUPTED'};},'en');
  assert.strictEqual((both.match(/data-install-reason="MAINTENANCE-INTERRUPTED"/g)||[]).length,1);
  assert.ok(!/data-install-reason/.test(banner(({status})=>{status.maintenance={state:'odd',code:'MAINTENANCE-IN-PROGRESS'};},'en')));
}
console.log('PASS: install reasons (rolled-back / refused update, missing self-check tool) are red lines with their code, RU and EN');
