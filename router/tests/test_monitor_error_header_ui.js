// BH2-03 (bug hunt 07.11.2026): a status reply carrying `error` (SERVICE-STOPPED when the monitor is stopped, SYSTEM-001 when its status
// build failed) IS a router answer. Before the fix the page stamped HV.answerAt only for error-free replies, so 60 s after page open both
// header lamps went grey "Router not answering ... check power and network" and hid the owner's red "ERROR: monitoring is not running".
// Now: any object reply without rpc_error stamps the answer; the monitor-error state wins over grey (main light grey with the error and
// the Restore fix in words - channel state unknown, never red; the Auto indicator red with the code); a transport failure stays grey.
'use strict';
const assert=require('assert');
const {load}=require('./approved_page');
function clock(p,start){
  const Real=p.c.Date;let at=start;
  class FakeDate extends Real{constructor(...a){a.length?super(...a):super(at*1000);}static now(){return at*1000;}}
  p.c.Date=FakeDate;return {set:t=>{at=t;}};
}
const T0=Date.UTC(2026,10,7,13,2,31)/1000;
const lamps=p=>{const V=p.T.snap();return {ov:p.T.overall(),au:p.T.autoIndicator(),detail:p.T.autoDetail(),mon:V.monitor};};

(async()=>{
  for(const code of ['SERVICE-STOPPED','SYSTEM-001']){
    for(const lang of ['ru','en']){
      const p=load({scn:'ok',lang,answers:{status:()=>({version:'x',mode:'monitor',error:code})}});const ck=clock(p,T0);
      p.T.HV.answerAt=undefined;p.T.HV.shownAt=T0;
      // the router answers with the monitor error every 30 s for 120 s
      for(const dt of [30,60,90,120]){ck.set(T0+dt);await p.T.refreshNow();await p.flush();}
      assert.equal(p.T.HV.answerAt,T0+120,code+': a reply with error is an answer');
      const r=lamps(p);
      assert.notEqual(r.ov.key,'silent',code+' '+lang+': main light not "router not answering"');
      assert.notEqual(r.au.key,'silent',code+' '+lang+': Auto indicator not "router not answering"');
      assert.equal(r.ov.key,'monitor-down');assert.equal(r.ov.lamp,'n','channel state unknown: grey, never red/green');
      assert.match(r.ov.title,lang==='ru'?/ОШИБКА: мониторинг не работает/:/ERROR: monitoring is not running/);
      assert.match(r.ov.sub,lang==='ru'?/Восстановить мониторинг/:/Restore monitoring/);
      assert.ok(r.ov.sub.includes(code),'the code is named');
      assert.doesNotMatch(r.ov.sub,/питание|power/,'never sends the owner to check power/cables');
      assert.equal(r.au.key,'monitor-down');assert.equal(r.au.lamp,'r');assert.ok(r.detail.includes(code));
      // the monitor block below stays the red ERROR with the code
      assert.equal(r.mon.key,'problem');assert.equal(r.mon.lamp,'red');assert.equal(r.mon.code,code);
      // even if no answer is stamped (boot reply only, polling stopped), the monitor error wins over grey
      p.T.HV.answerAt=undefined;p.T.HV.shownAt=T0;ck.set(T0+600);
      assert.equal(lamps(p).ov.key,'monitor-down');assert.equal(lamps(p).au.key,'monitor-down');
    }
  }
  { // a transport failure after the monitor error is silence: grey "router not answering" after 60 s
    let fail=false;
    const p=load({scn:'ok',answers:{status:()=>{if(fail)throw new Error('XHR timeout');return {version:'x',mode:'monitor',error:'SERVICE-STOPPED'};}}});
    const ck=clock(p,T0);p.T.HV.answerAt=undefined;p.T.HV.shownAt=T0;
    ck.set(T0+10);await p.T.refreshNow();await p.flush();assert.equal(p.T.HV.answerAt,T0+10);
    fail=true;ck.set(T0+80);await p.T.refreshNow();await p.flush();
    assert.equal(p.T.HV.answerAt,T0+10,'a failed call is not an answer');
    const r=lamps(p);assert.equal(r.ov.key,'silent');assert.equal(r.au.key,'silent');
  }
  { // a healthy reply still stamps the answer and shows normal lamps
    const p=load({scn:'ok'});const ck=clock(p,T0);p.T.HV.answerAt=undefined;p.T.HV.shownAt=T0;
    ck.set(T0+90);await p.T.refreshNow();await p.flush();
    assert.equal(p.T.HV.answerAt,T0+90);const r=lamps(p);
    assert.notEqual(r.ov.key,'silent');assert.notEqual(r.ov.key,'monitor-down');assert.notEqual(r.au.key,'monitor-down');
  }
  console.log('PASS: a SERVICE-STOPPED / SYSTEM-001 reply is a router answer; the monitor error wins over grey (RU+EN); transport failure stays grey');
})().catch(e=>{console.error(e);process.exit(1);});
