// F-35: the manual click sends a fresh client_request_id. Owner decision 07.11.2026: a lost answer is NEVER resent by
// itself; the page re-reads the router state and either says "done" / "received" or offers Retry, which reuses the SAME id
// (the router replays a request it already has, so it can never switch twice). A new click gets a new id; the legacy
// manual_switch call stays unchanged.
'use strict';
const assert=require('assert');
const {load}=require('./approved_page');
const RESERVE='openvpn:1_2020';

(async()=>{
  { // a lost answer, nothing changed on the router: exactly one call, a Retry button; Retry sends the same id once
    let attempts=0;
    const {T,calls,modals,flush}=load({scn:'ok',answers:{pair_manual:()=>{attempts++;return attempts===1?Promise.reject(new Error('XHR timeout')):{accepted:true,queued:true,completed:false,request_id:'b'.repeat(32),replayed:true};}}});
    T.switchTo('reserve');modals[0].buttons.find(b=>/pri/.test(b.cls)).fn();for(let i=0;i<5;i++)await flush();
    let sent=calls.filter(x=>x.method==='pair_manual');
    assert.equal(sent.length,1,'no automatic resend');
    assert.deepEqual(sent[0].params,['direction','control_revision','request_source','client_request_id']);
    assert.match(sent[0].args[3],/^[a-f0-9]{32}$/,'a valid id for the router (8-64 of [A-Za-z0-9_-])');
    assert.deepEqual(sent[0].args.slice(0,3),['reserve','0123456789abcdef0123456789abcdef','manual']);
    assert.ok(calls.map(x=>x.method).lastIndexOf('status')>calls.indexOf(sent[0]),'the router state is re-read after the lost answer');
    const lost=modals[modals.length-1];
    assert.match(lost.title,/Ответ роутера не получен/);
    assert.ok(JSON.stringify(lost).includes('MANUAL-REQUEST-UNCONFIRMED'));
    T.snap();assert.match(T.B.manual(),/data-act="manualretry"/,'the Retry button stays next to the channels');
    assert.equal(T.manualOperation(),null);
    lost.buttons.find(b=>/pri/.test(b.cls)).fn();for(let i=0;i<5;i++)await flush();
    sent=calls.filter(x=>x.method==='pair_manual');
    assert.equal(sent.length,2,'Retry sends once');
    assert.equal(sent[1].args[3],sent[0].args[3],'Retry reuses the id of the same action');
    T.snap();assert.ok(!/manualretry/.test(T.B.manual()),'no Retry once the request is accepted');
  }
  { // two separate clicks never share an id; a refusal is not retried
    const ids=[];
    const {T,calls,modals,flush}=load({scn:'ok',answers:{pair_manual:()=>({accepted:false,queued:false,completed:false,blockers:['PAIR-MANUAL-COOLDOWN']})}});
    for(let n=0;n<2;n++){
      T.switchTo('reserve');modals[modals.length-1].buttons.find(b=>/pri/.test(b.cls)).fn();for(let i=0;i<5;i++)await flush();
      const sent=calls.filter(x=>x.method==='pair_manual');ids.push(sent[sent.length-1].args[3]);
      assert.equal(sent.length,n+1,'a refusal is an answer, not a lost reply: no retry');
      modals.length=0;
    }
    assert.notEqual(ids[0],ids[1],'a new user action gets a fresh id');
  }
  { // the answer is lost but the switch already happened: "done", no Retry, nothing resent
    let lostOnce=false;
    const {T,calls,modals,toasts,status,flush}=load({scn:'ok',answers:{
      pair_manual:()=>{lostOnce=true;return Promise.reject(new Error('down'));},
      status:()=>{if(lostOnce)status.channel_path.active_profile_id=RESERVE;return status;}}});
    T.switchTo('reserve');modals[0].buttons.find(b=>/pri/.test(b.cls)).fn();for(let i=0;i<5;i++)await flush();
    assert.equal(calls.filter(x=>x.method==='pair_manual').length,1);
    assert.ok(toasts.some(m=>/Готово: трафик на канале/.test(m)),toasts.join(' | '));
    assert.equal(modals.length,1,'only the confirmation, no failure dialog');
    T.snap();assert.ok(!/manualretry/.test(T.B.manual()));
  }
  { // the answer is lost but the router has the request (status shows it): "received", waiting, nothing resent
    let lostOnce=false;
    const {T,calls,modals,toasts,status,flush}=load({scn:'ok',answers:{
      pair_manual:()=>{lostOnce=true;return Promise.reject(new Error('down'));},
      status:()=>{if(lostOnce)status.manual_switch={request_id:'e'.repeat(32),direction:'reserve',state:'APPLYING',completed:false,requested_at:status.server_time,updated_at:status.server_time};return status;}}});
    T.switchTo('reserve');modals[0].buttons.find(b=>/pri/.test(b.cls)).fn();for(let i=0;i<5;i++)await flush();
    assert.equal(calls.filter(x=>x.method==='pair_manual').length,1);
    assert.ok(toasts.some(m=>/Роутер получил запрос/.test(m)),toasts.join(' | '));
    assert.equal(T.manualOperation().request_id,'e'.repeat(32));
    assert.equal(modals.length,1);
  }
  { // BH-07: Retry gets a REPLAYED refusal (the router's earlier answer): "earlier answer", a new click sends a fresh id
    let n=0;
    const {T,calls,modals,flush}=load({scn:'ok',answers:{pair_manual:()=>{n++;
      if(n===1)return Promise.reject(new Error('XHR timeout'));
      if(n===2)return {accepted:false,queued:false,completed:false,blockers:['PAIR-MANUAL-COOLDOWN'],replayed:true};
      return {accepted:true,queued:true,completed:false,request_id:'c'.repeat(32)};}}});
    T.switchTo('reserve');modals[0].buttons.find(b=>/pri/.test(b.cls)).fn();for(let i=0;i<5;i++)await flush();
    modals[modals.length-1].buttons.find(b=>/pri/.test(b.cls)).fn();for(let i=0;i<5;i++)await flush();  // Retry, same id
    let sent=calls.filter(x=>x.method==='pair_manual');
    assert.equal(sent.length,2);assert.equal(sent[1].args[3],sent[0].args[3]);
    const earlier=modals[modals.length-1];
    assert.match(earlier.title,/Прежний ответ на это нажатие/);
    assert.ok(JSON.stringify(earlier).includes('PAIR-MANUAL-COOLDOWN'));
    assert.ok(/новое нажатие проверит всё заново/.test(earlier.body),earlier.body);
    assert.equal(calls.filter(x=>x.method==='pair_manual').length,2,'nothing is sent by itself');
    earlier.buttons.find(b=>/pri/.test(b.cls)).fn();for(let i=0;i<5;i++)await flush();
    sent=calls.filter(x=>x.method==='pair_manual');
    assert.equal(sent.length,3,'the new click sends once');
    assert.notEqual(sent[2].args[3],sent[0].args[3],'the new click has a fresh id');
    assert.match(sent[2].args[3],/^[a-f0-9]{32}$/);
  }
  { // a refusal that is NOT replayed keeps the old "Switch refused" dialog without a new-click button
    const {T,modals,flush}=load({scn:'ok',answers:{pair_manual:()=>({accepted:false,queued:false,completed:false,blockers:['PAIR-MANUAL-COOLDOWN']})}});
    T.switchTo('reserve');modals[0].buttons.find(b=>/pri/.test(b.cls)).fn();for(let i=0;i<5;i++)await flush();
    assert.match(modals[modals.length-1].title,/Переключение отклонено/);
  }
  console.log('PASS: manual click carries one client_request_id; a lost answer is re-read (done / received / Retry with the same id), never resent by itself');
})().catch(e=>{console.error(e);process.exit(1);});
