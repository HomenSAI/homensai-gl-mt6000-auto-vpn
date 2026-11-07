// Source safety guidance and the shipped optional factory must agree. No RPC or settings changes.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const read=p=>fs.readFileSync(p,'utf8');
const c={URL,locale:'en',E:()=>({}),navigator:{},window:{location:{href:'http://127.0.0.1/#help'}},localStorage:{getItem:()=>null,setItem(){}},bi:(en,ru)=>c.locale==='ru'?ru:en};
vm.createContext(c);
const terms=/TERMS_VERSION\s*=\s*['"]([^'"]+)/.exec(read('router/files/usr/lib/homensai-vpn/agent.py'))[1];
for(const name of ['auto_panel','summary_panel','readiness_panel','help_panel','ai_prompt','terms_panel','error_rows_extra','error_table','journal_panel'])
 vm.runInContext(read('router/'+name+'.inc.js').replaceAll('__TERMS_VERSION__',terms),c);
c.ensureJournalDictionary();
const ids=['MONITOR-ALWAYS-ON','SETUP-STOP-FIRST','SERVER-KEY-UNACCEPTED','STATS-RESET-ARCHIVE-PATH','SQM-RESTORE-FAILED','LIFECYCLE-*','STATS-RESET-UNCONFIRMED'];
const canonical=new Map(c.ERROR_ROWS.map(r=>[r[0],Array.from(r)]));
const names=['E','bi','locale','richText','helpCommand','READINESS_GUIDES','READINESS_CHECKS','renderReadinessHelp','renderAutoRemedy','AUTO_BLOCKERS','AUTO_REMEDIES','autoRemedyKey','PLAN_BLOCKERS','errorCodeLink','ensureJournalDictionary','spanText'];
let installed;
const ctx={extraHelpTopics:[],installCatalogue:value=>{installed=value.rows;c.ERROR_ROWS=value.rows;c.ERROR_GROUP_OF=value.groupOf;}};
names.forEach(n=>ctx[n]=c[n]);c.baseclass={extend:o=>o};
const app=JSON.parse(read('VERSION.json')).application;
const modulePath=process.argv[2]||'router/files/www/luci-static/resources/homensai-vpn/help'+app.ui_module.replace('dashboard','')+'.js';
const api=vm.runInContext('(function(){'+read(modulePath)+'\n})()',c).create(ctx);
assert(installed,'actual optional factory installed its catalogue');
function action(code,index){return canonical.get(code)[index];}
for(const id of ids){
 const row=canonical.get(id),actual=installed.find(r=>r[0]===id);assert(row&&actual,id);
 assert.deepEqual(Array.from(actual),row,'source/generated guidance mismatch: '+id);
 for(const [lang,index] of [['en',6],['ru',7]]){
  const html=api.codeBody(actual,id,lang);
  assert(html.includes('class="code-steps"'),'steps in actual runtime '+id);
  assert(html.includes(row[index].split('. ')[0]),'current action in runtime '+id+' '+lang);
 }
}
for(const i of [6,7]){
 const archive=action('STATS-RESET-ARCHIVE-PATH',i),sqm=action('SQM-RESTORE-FAILED',i),key=action('SERVER-KEY-UNACCEPTED',i),reset=action('STATS-RESET-UNCONFIRMED',i);
 assert(!/^(?:Remove|Удалите)\b/i.test(archive),'archive refusal must not prescribe deletion');
 assert(/preserv|сохран/i.test(archive)&&/ownership|владельц/i.test(archive),'archive data and ownership are checked');
 assert(!/tc\s+qdisc\s+del/i.test(sqm),'no unconditional root queue deletion command');
 assert(/owner|владел/i.test(sqm)&&/identity|идентификатор/i.test(sqm),'current SQM ownership and interface identity matter');
 assert(!/\bwarn\b/i.test(key),'no enforcement downgrade remedy');
 assert(/verify|сверьте/i.test(key)&&/unused|неиспользуемым/i.test(key),'unverified key keeps channel unused');
 assert(/do not weaken|не ослабляйте/i.test(key),'trust checking is retained');
 assert(/unknown|неизвестен/i.test(reset)&&/do not submit another|не отправляйте новый/i.test(reset),'unknown reset outcome forbids replay');
 assert(/fresh.*result|свежий результат/i.test(reset),'inspect fresh reset result');
 for(const id of ['SETUP-STOP-FIRST','LIFECYCLE-*']){
  const text=action(id,i);
  assert(/retained reserve|reserve is retained|сохран[её]нн?[а-я]* резерв|сохран[её]н резерв/i.test(text),'retained reserve is acknowledged: '+id);
  assert(!/wait (?:until it returns|for the return)|дождитесь возврата/i.test(text),'Stop is not guaranteed primary return: '+id);
 }
}
// The full dynamic code must inherit the corrected current family, not an eager title cache.
const familyCtx={ERROR_ROWS:installed};vm.createContext(familyCtx);
vm.runInContext(read('router/lazy_help.inc.js').split('\n').find(l=>l.startsWith('function errorFamilyOf(')),familyCtx);
const dynamic=familyCtx.errorFamilyOf('LIFECYCLE-REVIEW-UNFINISHED');
assert(dynamic&&dynamic[6]===canonical.get('LIFECYCLE-*')[6]&&dynamic[7]===canonical.get('LIFECYCLE-*')[7]);
for(const i of [8,9])assert(/reserve|резерв/i.test(canonical.get('LIFECYCLE-*')[i]),'technical example must retain reserve context');
console.log('PASS: seven source/runtime safety rows EN/RU; ownership, trust, retained reserve, UNKNOWN reset and dynamic lifecycle guidance');
