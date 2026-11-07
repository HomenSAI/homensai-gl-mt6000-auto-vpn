// Plan item 53 (07.11.2026): no answer from the router for 60 s -> both header lamps GREY "router not answering" with the time of the
// last answer; an answer returns -> normal lamps. Page-local clock (HV.answerAt / HV.shownAt), no extra timer.
'use strict';
const assert=require('assert');
const {load,strip}=require('./approved_page');

// A controllable wall clock inside the page's vm context (the page reads Date.now()).
function clock(p,start){
  const Real=p.c.Date;let at=start;
  class FakeDate extends Real{constructor(...a){a.length?super(...a):super(at*1000);}static now(){return at*1000;}}
  p.c.Date=FakeDate;
  return {set:t=>{at=t;},get:()=>at};
}
const T0=Date.UTC(2026,10,7,13,2,31)/1000;  // last answer, 13:02:31 UTC = 14:02:31 Berlin
function setup(){
  const p=load({scn:'ok'});const ck=clock(p,T0);
  p.T.HV.answerAt=T0;p.T.HV.shownAt=T0-3600;
  return {p,ck};
}
const lamps=p=>{p.T.snap();return {ov:p.T.overall(),au:p.T.autoIndicator(),detail:p.T.autoDetail()};};

(async()=>{
  { // answer present: normal lamps (never the silent state)
    const {p,ck}=setup();ck.set(T0+5);
    const r=lamps(p);
    assert.notEqual(r.ov.key,'silent');assert.notEqual(r.au.key,'silent');
    assert.ok(['g','y','r'].includes(r.ov.lamp)||r.ov.key!=='silent');
  }
  { // 59 s without an answer: unchanged (same lamps as with the answer)
    const {p,ck}=setup();ck.set(T0+5);const before=lamps(p);
    ck.set(T0+59);const after=lamps(p);
    assert.equal(after.ov.key,before.ov.key);assert.equal(after.ov.lamp,before.ov.lamp);
    assert.equal(after.au.key,before.au.key);assert.equal(after.au.lamp,before.au.lamp);
  }
  { // 60 s and more: both lamps grey, last-answer time in RU and EN, state does not fall back to green/yellow
    for(const lang of ['ru','en']){
      const {p,ck}=setup();p.T.setLocale(lang);ck.set(T0+60);
      let r=lamps(p);
      assert.equal(r.ov.lamp,'n');assert.equal(r.ov.key,'silent');assert.equal(r.au.lamp,'n');assert.equal(r.au.key,'silent');
      const word=lang==='ru'?/последний ответ 14:02:31/:/last answer 14:02:31/;
      assert.match(r.ov.sub,word);assert.match(r.au.reason,word);assert.match(r.detail,word);
      assert.match(r.ov.title,lang==='ru'?/Роутер не отвечает/:/Router not answering/);
      assert.match(r.au.text,lang==='ru'?/роутер не отвечает/:/router not answering/);
      ck.set(T0+3600);r=lamps(p);assert.equal(r.ov.lamp,'n');assert.equal(r.au.lamp,'n');
      assert.match(strip(r.ov.sub),word);
    }
  }
  { // an answer returns: normal lamps again
    const {p,ck}=setup();ck.set(T0+120);assert.equal(lamps(p).ov.key,'silent');
    p.T.HV.answerAt=T0+121;ck.set(T0+122);
    const r=lamps(p);assert.notEqual(r.ov.key,'silent');assert.notEqual(r.au.key,'silent');
  }
  { // refreshNow(): a good reply stamps the answer time and clears the grey; a failed call does not
    const p=load({scn:'ok'});const ck=clock(p,T0);p.T.HV.answerAt=T0;p.T.HV.shownAt=T0-3600;
    ck.set(T0+200);assert.equal(lamps(p).ov.key,'silent');
    await p.T.refreshNow();await p.flush();
    assert.equal(p.T.HV.answerAt,T0+200,'a good reply is an answer');
    assert.notEqual(lamps(p).ov.key,'silent');
    const q=load({scn:'ok',answers:{status:()=>{throw new Error('XHR timeout');}}});const ck2=clock(q,T0);q.T.HV.answerAt=T0;q.T.HV.shownAt=T0-3600;
    ck2.set(T0+200);await q.T.refreshNow();await q.flush();
    assert.equal(q.T.HV.answerAt,T0,'a failed call is not an answer');assert.equal(lamps(q).ov.key,'silent');
  }
  { // time in a hidden tab does not count: coming back restarts the window
    const {p,ck}=setup();p.T.HV.shownAt=T0+3000;ck.set(T0+3010);
    assert.notEqual(lamps(p).ov.key,'silent');
    ck.set(T0+3060);assert.equal(lamps(p).ov.key,'silent');
  }
  { // no answer ever on this page: grey after 60 s, honest wording, no invented time
    const p=load({scn:'ok'});const ck=clock(p,T0);p.T.HV.shownAt=T0;p.T.HV.answerAt=undefined;
    ck.set(T0+61);const r=lamps(p);
    assert.equal(r.ov.key,'silent');assert.match(r.ov.sub,/ещё не было/);
  }
  console.log('PASS: grey "router not answering" lamps after 60 s with the last-answer time (RU+EN); 59 s unchanged; an answer restores the normal lamps');
})().catch(e=>{console.error(e);process.exit(1);});
