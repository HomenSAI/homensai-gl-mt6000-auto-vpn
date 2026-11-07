// F-35, owner decision 07.11.2026: no answer to Auto Start/Stop. The page re-reads the router state first: when the command
// took effect it says "done"; otherwise it offers Retry. It never sends the command again by itself.
'use strict';
const assert=require('assert');
const {load}=require('./approved_page');

// native_start / native_stop answer through the fixture; a wrapper in front of it loses the answer (and optionally lets the
// command reach the router first, as a reply lost on the way back would).
function lossy(p,method,reached){
  const inner=p.c.rpc.declare,sent=[];
  p.c.rpc.declare=spec=>{const f=inner(spec);return (...args)=>{
    if(spec.method!==method)return f(...args);
    sent.push(args);
    if(reached)p.c.HV_FIXTURE_CMD={on:method==='native_start',at:Date.now()/1000};
    return Promise.reject(new Error('XHR timeout'));};};
  return sent;
}
const settle=async p=>{for(let i=0;i<6;i++)await p.flush();};

(async()=>{
  { // Stop lost, nothing changed: one call, a re-read, a Retry dialog with the code; Retry sends one more Stop
    const p=load({scn:'ok'});const sent=lossy(p,'native_stop',false);
    p.T.stopAuto();p.modals[0].buttons.find(b=>/danger/.test(b.cls)).fn();await settle(p);
    assert.equal(sent.length,1,'never resent by itself');
    const dialog=p.modals[p.modals.length-1];
    assert.match(dialog.title,/Команда не дошла до роутера/);
    assert.ok(JSON.stringify(dialog).includes('AUTO-CONTROL-FAILED'));
    assert.ok(JSON.stringify(dialog).includes('ничего не изменилось'),JSON.stringify(dialog));
    dialog.buttons.find(b=>/pri/.test(b.cls)).fn();await settle(p);
    assert.equal(sent.length,2,'only the owner\'s Retry sends again');
  }
  { // Stop lost on the way back (the router took it): "done", no failure dialog, nothing resent
    const p=load({scn:'ok'});const sent=lossy(p,'native_stop',true);
    p.T.stopAuto();p.modals[0].buttons.find(b=>/danger/.test(b.cls)).fn();await settle(p);
    assert.equal(sent.length,1);
    assert.equal(p.modals.length,1,'only the confirmation dialog');
    assert.ok(p.toasts.some(m=>/Готово: Auto выключен/.test(m)),p.toasts.join(' | '));
  }
  { // Start lost, nothing changed: Retry offered; Start lost after the router took it: "received" or "done"
    const p=load({scn:'off'});const sent=lossy(p,'native_start',false);
    p.T.toggleAuto();await settle(p);
    assert.equal(sent.length,1);
    const dialog=p.modals[p.modals.length-1];
    assert.match(dialog.title,/Команда не дошла до роутера/);
    assert.ok(dialog.buttons.some(b=>/pri/.test(b.cls)&&/Повторить/.test(b.t)));
    const q=load({scn:'off'});const sent2=lossy(q,'native_start',true);
    q.T.toggleAuto();await settle(q);
    assert.equal(sent2.length,1);
    assert.ok(!q.modals.some(m=>/не дошла/.test(m.title||'')),'no failure dialog when the router took it');
    assert.ok(q.toasts.some(m=>/Роутер получил команду|Готово: Auto включён/.test(m)),q.toasts.join(' | '));
  }
  console.log('PASS: F-35 Auto Start/Stop with a lost answer - state re-read first, "done" when it took effect, otherwise Retry; never resent by itself');
})().catch(e=>{console.error(e);process.exit(1);});
