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
{
  const ctx={bi:(en)=>en,E:(t,a,c)=>({t,a,c})};vm.createContext(ctx);
  vm.runInContext(fs.readFileSync('router/learn_panel.inc.js','utf8'),ctx);
  const commands=ctx.LEARN_LESSONS.filter(l=>l.cmds).flatMap(l=>l.cmds);
  assert(commands.length>=3);
  for(const [cmd,text] of commands){assert(/^(homensai-vpn-emergency [a-z-]+|winget install Microsoft\.PowerShell|pwsh -NoProfile -File \.\\start-lan-helper\.ps1)$/.test(cmd),cmd);assert(text.length===2&&cy2(text[1]));}
  // No lesson text may embed a bare helper command: commands live in command blocks.
  for(const l of ctx.LEARN_LESSONS)for(const p of l.body)assert(!/homensai-vpn-emergency/.test(p[0]));
  function cy2(t){return /[А-Яа-я]/.test(t);}
  console.log('command block tests OK');
}
{
  const ctx={bi:(en)=>en,E:(t,a,c)=>({t,a,c})};vm.createContext(ctx);
  vm.runInContext(fs.readFileSync('router/summary_panel.inc.js','utf8'),ctx);
  const plan=fs.readFileSync('router/files/usr/lib/homensai-vpn/failover_plan.py','utf8');
  const codes=[...plan.slice(plan.indexOf('BLOCKERS'),plan.indexOf(']',plan.indexOf('BLOCKERS'))).matchAll(/'([A-Z0-9-]+)'/g)].map(m=>m[1]);
  assert(codes.length>=8);
  for(const code of codes){const r=ctx.PLAN_BLOCKERS[code];assert(r&&r.length===4&&/[А-Яа-я]/.test(r[3]),'unexplained planning code '+code);}
  console.log('planning blocker table OK');
}
{
  const ctx={bi:(en)=>en,E:(t,a,c)=>({t,a,c}),window:{}};vm.createContext(ctx);
  for(const f of ['auto_panel.inc.js','summary_panel.inc.js','error_table.inc.js'])vm.runInContext(fs.readFileSync('router/'+f,'utf8'),ctx);
  const rows=ctx.ERROR_ROWS,byCode={};for(const r of rows){assert.equal(r.length,8,r[0]);assert(!byCode[r[0]],'duplicate code '+r[0]);byCode[r[0]]=r;}
  for(const r of rows){assert(r[2]&&r[4]&&r[5]&&/[А-Яа-я]/.test(r[5]),'row text '+r[0]);if(r[6])assert(/[А-Яа-я]/.test(r[7]),'fix ru '+r[0]);}
  for(const code of Object.keys(ctx.AUTO_BLOCKERS))assert(byCode[code]&&ctx.AUTO_NAMES[code]||byCode[code][1]!=='switch'||code==='HISTORY-001'||code==='JOURNAL-INTEGRITY-FAILED','no readable name for '+code);
  for(const [plan,failures] of Object.entries(ctx.PLAN_FAILURE_CODES)){assert(byCode[plan],'plan code missing in error table '+plan);for(const f of failures)assert(byCode[f],'failure code missing in error table '+f);}
  // Check states: pending while listed, verified when not listed, failed with the reported failure code.
  assert.equal(ctx.planCheckState('KILLSWITCH-UNVERIFIED',['KILLSWITCH-UNVERIFIED'],[]).state,'pending');
  assert.equal(ctx.planCheckState('KILLSWITCH-UNVERIFIED',[],[]).state,'verified');
  const failed=ctx.planCheckState('KILLSWITCH-UNVERIFIED',['KILLSWITCH-UNVERIFIED'],['KILLSWITCH-NOT-ENABLED']);
  assert.equal(failed.state,'failed');assert.equal(failed.failure,'KILLSWITCH-NOT-ENABLED');
  console.log('error table and planning check tests OK ('+rows.length+' codes)');
}
{
  const ctx={bi:(en)=>en,E:(t,a,c)=>({t,a,c}),navigator:{},window:{},document:{}};vm.createContext(ctx);
  vm.runInContext('var HELP_TOPICS=[];'+fs.readFileSync('router/ai_prompt.inc.js','utf8'),ctx);
  const en=ctx.AI_PROMPT_EN,ru=ctx.AI_PROMPT_RU;
  for(const section of ['=== 0.','=== 1.','=== 2.','=== 3.','=== 4.','=== 5.','=== 6.','=== 7.','=== 8.','=== 9.','=== 10.']){assert(en.includes(section),'EN section '+section);assert(ru.includes(section),'RU section '+section);}
  for(const text of [en,ru]){
    assert(/Auto/.test(text)&&/05-emergency\.sh/.test(text)&&/BotFather/.test(text)&&/sha256/i.test(text)&&/gl-mt6000/i.test(text));
    assert(!/\d{8,12}:[A-Za-z0-9_-]{30,}/.test(text),'token-like text in the prompt');
    assert(!/(password|token)\s*[:=]\s*[^\s=]/i.test(text.replace(/telegram_token=<hidden>|telegram_token=\.\*/g,'')),'secret assignment in the prompt');
    assert(!text.includes('${')&&!text.includes('`'));
  }
  assert(/never enable Auto|NEVER enable Auto/i.test(en)&&/НИКОГДА не включайте Auto/.test(ru));
  assert(ctx.renderAiPrompt());assert.equal(ctx.HELP_TOPICS[0].id,'ai-prompt');
  console.log('AI prompt tests OK ('+en.length+' / '+ru.length+' characters)');
}
