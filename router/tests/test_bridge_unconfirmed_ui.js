// BH3-02 (bug hunt third pass, 07.11.2026): when the Lua monitor's answer to a button is unclear (ubus timeout, failed
// reply write) the rpcd dispatcher no longer replays the click through agent.py; it answers
// {accepted:false,queued:false,code:'RPC-BRIDGE-UNCONFIRMED'}. The page must treat that as a LOST answer, not a refusal:
// the F-35 path re-reads the state, says "done" when the click took effect, otherwise offers Retry (manual: the same
// client id, so the router replays). Never resent by itself; never shown as "Switch refused".
'use strict';
const assert=require('assert');
const {load}=require('./approved_page');
const LOST={accepted:false,queued:false,code:'RPC-BRIDGE-UNCONFIRMED',blockers:['RPC-BRIDGE-UNCONFIRMED']};
const RESERVE='openvpn:1_2020';
const settle=async p=>{for(let i=0;i<6;i++)await p.flush();};
// Auto Start/Stop are answered by the preview fixture itself: put the dispatcher's answer in front of it (as
// test_auto_lost_answer_ui.js does), optionally letting the click reach the router first (a late Lua action).
function bridgeLost(p,method,reached){
  const inner=p.c.rpc.declare,sent=[];
  p.c.rpc.declare=spec=>{const f=inner(spec);return (...args)=>{
    if(spec.method!==method)return f(...args);
    sent.push(args);
    if(reached)p.c.HV_FIXTURE_CMD={on:method==='native_start',at:Date.now()/1000};
    return Promise.resolve(LOST);};};
  return sent;
}

(async()=>{
  { // manual switch: lost answer, nothing changed -> "No answer from the router" + Retry with the same id
    let n=0;
    const p=load({scn:'ok',answers:{pair_manual:()=>{n++;return n===1?LOST:{accepted:true,queued:true,completed:false,request_id:'b'.repeat(32),replayed:true};}}});
    p.T.switchTo('reserve');p.modals[0].buttons.find(b=>/pri/.test(b.cls)).fn();await settle(p);
    let sent=p.calls.filter(x=>x.method==='pair_manual');
    assert.equal(sent.length,1,'never resent by itself');
    const lost=p.modals[p.modals.length-1];
    assert.match(lost.title,/Ответ роутера не получен/,'a lost answer, not a refusal: '+lost.title);
    assert.ok(!/отклонено/.test(lost.title),'not "Switch refused"');
    assert.ok(JSON.stringify(lost).includes('MANUAL-REQUEST-UNCONFIRMED'));
    assert.ok(p.calls.map(x=>x.method).lastIndexOf('status')>p.calls.indexOf(sent[0]),'the state is re-read');
    lost.buttons.find(b=>/pri/.test(b.cls)).fn();await settle(p);
    sent=p.calls.filter(x=>x.method==='pair_manual');
    assert.equal(sent.length,2,'only the owner\'s Retry sends again');
    assert.equal(sent[1].args[3],sent[0].args[3],'Retry reuses the id: the router replays a click it already has');
  }
  { // manual switch: lost answer, but the late Lua action switched -> "done", no dialog, nothing resent
    let lostOnce=false;
    const p=load({scn:'ok',answers:{pair_manual:()=>{lostOnce=true;return LOST;},
      status:()=>{if(lostOnce)p.status.channel_path.active_profile_id=RESERVE;return p.status;}}});
    p.T.switchTo('reserve');p.modals[0].buttons.find(b=>/pri/.test(b.cls)).fn();await settle(p);
    assert.equal(p.calls.filter(x=>x.method==='pair_manual').length,1);
    assert.ok(p.toasts.some(m=>/Готово: трафик на канале/.test(m)),p.toasts.join(' | '));
    assert.equal(p.modals.length,1,'only the confirmation dialog');
  }
  { // Auto Stop: lost answer, nothing changed -> "The command did not reach the router" + Retry
    const p=load({scn:'ok'});const sent=bridgeLost(p,'native_stop',false);
    p.T.stopAuto();p.modals[0].buttons.find(b=>/danger/.test(b.cls)).fn();await settle(p);
    assert.equal(sent.length,1,'never resent by itself');
    const dialog=p.modals[p.modals.length-1];
    assert.match(dialog.title,/Команда не дошла до роутера/);
    assert.ok(dialog.buttons.some(b=>/pri/.test(b.cls)&&/Повторить/.test(b.t)));
  }
  { // Auto Start: lost answer after the router took it -> "received"/"done", no failure dialog
    const p=load({scn:'off'});const sent=bridgeLost(p,'native_start',true);
    p.T.toggleAuto();await settle(p);
    assert.equal(sent.length,1);
    assert.ok(!p.modals.some(m=>/не дошла|не запущен/.test(m.title||'')),JSON.stringify(p.modals.map(m=>m.title)));
    assert.ok(p.toasts.some(m=>/Роутер получил команду|Готово: Auto включён/.test(m)),p.toasts.join(' | '));
  }
  console.log('PASS: BH3-02 RPC-BRIDGE-UNCONFIRMED from the dispatcher is a lost answer on the page (manual switch, Auto Start/Stop): state re-read, "done" or Retry, never resent by itself');
})().catch(e=>{console.error(e);process.exit(1);});
