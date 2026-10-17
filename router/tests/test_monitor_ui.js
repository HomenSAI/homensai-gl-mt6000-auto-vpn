const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{constructor(tag,attrs,children){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children===undefined?[]:children).flat();}}
const context={bi:(en)=>en,E:(t,a,c)=>new Node(t,a,c),window:{sessionStorage:{getItem:()=>null}}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('router/monitor_panel.inc.js','utf8')+'\n'+fs.readFileSync('router/setup_guides.inc.js','utf8'),context);
const model=(s,i,n,r)=>context.monitorLightModel(s,i,n,r);
const now=1000;
assert.equal(model({time:now-5},{settings:{enabled:true}},now,false).lamp,'green');
assert.equal(model({rpc_error:true},{settings:{enabled:true}},now,false).lamp,'red');
assert.equal(model({time:now-200},{settings:{enabled:true}},now,false).lamp,'yellow');
assert.equal(model({time:now-200},{settings:{enabled:true}},now,true).lamp,'yellow');
assert.equal(model({time:now-4000},{settings:{enabled:true}},now,false).lamp,'red');
assert.equal(model({time:now-4000},{settings:{enabled:false}},now,false).lamp,null);
assert.equal(model({time:now-5},{settings:{enabled:false}},now,false).key,'transition');
assert.equal(model({},{settings:{enabled:true}},now,false).lamp,'red');
const cyrillic=/[А-Яа-я]/;
for(const key of ['system','recovery','monitoring','telegram','speed']){
  const g=context.SETUP_GUIDES[key];assert(g.fields.length>=3,key);
  for(const f of g.fields)for(const pair of f){assert.equal(pair.length,2);assert(cyrillic.test(pair[1])||/^[\d\s·—.()]+$/.test(pair[1])||pair[1]===pair[0],key+pair[0]);}
  assert(context.setupGuide(key));
}
assert(JSON.stringify(context.SETUP_GUIDES.telegram).includes('BotFather'));
console.log('monitor and guide tests OK');
{
  const ctx={bi:(en)=>en,E:(t,a,c)=>({t,a,c})};vm.createContext(ctx);
  vm.runInContext(fs.readFileSync('router/learn_panel.inc.js','utf8'),ctx);
  const quiz=ctx.LEARN_QUIZ,cy=/[А-Яа-я]/;
  assert(ctx.LEARN_LESSONS.length>=7&&quiz.length>=7);
  for(const l of ctx.LEARN_LESSONS){for(const pair of [l.title,l.example,l.tip,...l.body]){assert.equal(pair.length,2);assert(cy.test(pair[1]));}}
  for(const q of quiz){assert(cy.test(q.q[1])&&q.o.some(o=>o[2]===true)&&q.o.some(o=>o[2]===false));}
  const right=quiz.map(q=>q.o.map((o,i)=>o[2]?i:-1).filter(i=>i>=0));
  assert.equal(ctx.learnScore(quiz,right).percent,100);
  assert.equal(ctx.learnScore(quiz,[]).percent,0);
  const g=ctx.learnGrade(quiz[1],[0,2]);
  assert.equal(g.ok,false);assert.deepEqual(Array.from(g.marks),['right','missed','wrong','missed']);
  const wrong=right.map((r,i)=>i===0?[1]:r);assert.equal(ctx.learnScore(quiz,wrong).correct,quiz.length-1);
  console.log('learn tests OK');
}
