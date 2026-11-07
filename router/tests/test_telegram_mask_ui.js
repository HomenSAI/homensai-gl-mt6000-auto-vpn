// F-14, owner decision 07.11.2026: the Telegram recipient is shown masked (first 2 + last 2 characters, e.g. 12…89); the full
// value only after an explicit "show" click (write-ACL telegram_destination), never automatically; a lost answer shows a code.
'use strict';
const assert=require('assert');
const {load,strip}=require('./approved_page');
const flush=()=>new Promise(r=>setTimeout(r,30));

function page(answers,destination){
  const p=load({lang:'en',answers:Object.assign({setup_telegram:()=>({saved:true})},answers||{}),
    mutate:({settings})=>Object.assign(settings,{telegram_enabled:true,telegram_destination:destination===undefined?'12…89':destination,telegram_configured:true,telegram_interval:60})});
  p.T.snap();
  p.T.HV.open['sec-tg']=true;
  return p;
}

(async()=>{
  { // the masked value is in the field, a "show" button next to it; rendering never asks for the full value
    const p=page();
    const html=p.T.settingsA();
    assert.equal(p.T.draft().tgChat,'12…89');
    assert.match(html,/value="12…89"/);
    assert.match(html,/data-act="tgshow"/);
    assert.ok(strip(html).includes('Show recipient'));
    assert.equal(p.calls.filter(c=>c.method==='telegram_destination').length,0,'no automatic reveal');
  }
  { // explicit click: one write-ACL call, the full value goes into the draft (and is what a save sends)
    const p=page({telegram_destination:()=>({destination:'123456789',configured:true,masked:'12…89'})});
    p.T.tgShow();await flush();
    assert.equal(p.calls.filter(c=>c.method==='telegram_destination').length,1);
    assert.equal(p.T.draft().tgChat,'123456789');
    await p.T.saveSection('tg');await flush();
    const save=p.calls.filter(c=>c.method==='setup_telegram').slice(-1)[0];
    assert.equal(save.args[1],'123456789');
  }
  { // without the click the mask itself is sent back (the router keeps the stored recipient)
    const p=page();
    await p.T.saveSection('tg');await flush();
    const save=p.calls.filter(c=>c.method==='setup_telegram').slice(-1)[0];
    assert.equal(save.args[1],'12…89');
  }
  { // a lost answer or an empty one: a coded failure, the mask stays
    for(const answer of [()=>Promise.reject(new Error('timeout')),()=>({destination:'',configured:false,masked:''})]){
      const p=page({telegram_destination:answer});
      p.T.tgShow();await flush();
      assert.equal(p.T.draft().tgChat,'12…89');
      assert.ok(p.modals.some(m=>JSON.stringify(m).includes('RPC-UNAVAILABLE')),JSON.stringify(p.modals));
    }
  }
  { // no stored recipient (or an unmasked draft): no "show" button
    const p=page({},'');
    assert.ok(!/data-act="tgshow"/.test(p.T.settingsA()));
  }
  console.log('PASS: F-14 recipient masked as 12…89, full value only after the explicit "show" click, lost answer coded');
})().catch(e=>{console.error(e);process.exit(1);});
