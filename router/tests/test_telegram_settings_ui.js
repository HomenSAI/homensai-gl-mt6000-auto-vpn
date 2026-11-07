// Owner 05.11.2026, the Telegram section of the SHIPPED page: a pasted ID is forgiven on both write paths, the save dialog says what
// to do, and the section header tells one story: the form's values, marked until they are saved. The help names @userinfobot.
'use strict';
const fs=require('fs'),path=require('path'),assert=require('assert');
const {load,strip,ROOT,app}=require('./approved_page');
const flush=()=>new Promise(r=>setTimeout(r,30));
const reply=c=>c.method==='setup_telegram';

function page(opts){
  opts=opts||{};
  const p=load({lang:opts.lang||'ru',answers:Object.assign({setup_telegram:()=>({saved:true})},opts.answers||{}),mutate:({settings})=>Object.assign(settings,{telegram_enabled:false,telegram_destination:'',telegram_interval:60},opts.settings||{})});
  p.T.snap();
  return p;
}
async function saveWith(p,chat){
  p.T.draft().tgChat=chat;p.T.draft().tg=true;p.T.draft().tgToken='';
  await p.T.saveSection('tg');await flush();
  return p.calls.filter(reply).slice(-1)[0];
}

(async()=>{
// Explicit brief is recognized, rendered and saved through the settings RPC.
{
  const p=page({settings:{telegram_items:'brief'}});
  assert.equal(p.T.draft().tgItems,'brief');
  assert(p.T.settingsA().includes('Кратко по-русски'));
  const call=await saveWith(p,'123456789');
  assert(call.args.includes('brief'));
  const defaults=page();assert.equal(defaults.T.draft().tgItems,'maximum');
}
// ---------- item 2: pasted forms on the settings path ----------
for(const [pasted,sent] of [[' 123456789 ','123456789'],['Id: 123456789','123456789'],['id:123456789','123456789'],['Id: -1001234567','-1001234567'],
  ['@some_user\nId: 123456789\nFirst: Serhii\nLang: ru','123456789'],[' @example_channel ','@example_channel'],['https://example.com/?id=5','https://example.com/?id=5'],['Id: abc','Id: abc']]){
  const call=await saveWith(page(),pasted);
  assert.equal(call.args[1],sent,pasted);
}
// ---------- item 2: the wizard path sends the same cleaned value ----------
{
  const source=fs.readFileSync(path.join(ROOT,'router/ui/views.js'),'utf8');
  assert(source.includes('chat:tgChatClean(d.tgChat),enabled:d.tg===true'),'the wizard cleans the ID as the settings do');
  assert(!/String\(d\.tgChat/.test(source+fs.readFileSync(path.join(ROOT,'router/ui/settings.js'),'utf8')),'no raw read of the field is left');
}
// ---------- item 2: the save dialog shows the hint, the title alone is not enough ----------
{ // the row of the shipped table carries the hint
  const table=fs.readFileSync(path.join(ROOT,'router/error_table.inc.js'),'utf8');
  const row=table.split('\n').find(l=>l.includes("['TELEGRAM-DESTINATION-FORMAT'"));
  assert(row.includes('Используйте цифры (123456789')&&row.includes('Use digits (123456789'));
}
for(const lang of ['ru','en']){
  const hint=lang==='ru'?'Используйте цифры (123456789 или -100… для группы) или @имя_канала.':'Use digits (123456789, or -100… for a group) or @channel_name.';
  const p=page({lang,answers:{setup_telegram:()=>({saved:false,code:'TELEGRAM-DESTINATION-FORMAT'})}});
  // the optional module as it loads on the router: it installs the full table
  p.c.L.require=()=>Promise.resolve({create:ctx=>{ctx.installCatalogue({rows:[['TELEGRAM-DESTINATION-FORMAT','telegram','Chat ID looks wrong','ID чата выглядит неверно','w','ч','Use digits (123456789, or -100… for a group) or @channel_name.','Используйте цифры (123456789 или -100… для группы) или @имя_канала.']],groups:[],groupOf:{},state:{},persist(){}});return {helpTopics:()=>[]};}});
  const place={dataset:{codeHint:'TELEGRAM-DESTINATION-FORMAT'},innerHTML:''};
  p.c.document.querySelectorAll=s=>s==='[data-code-hint]'?[place]:[];
  await saveWith(p,'x');
  const first=p.modals[p.modals.length-1];
  assert(first.body.includes('data-code-hint="TELEGRAM-DESTINATION-FORMAT"'),'the dialog opens at once, with a place for the hint');
  assert.equal(place.innerHTML,hint,'the hint arrives as soon as the full table does');
  await saveWith(p,'x');
  assert(strip(p.modals[p.modals.length-1].body).includes(hint),'with the table loaded it is in the dialog from the start');
  assert.equal(p.T.codeHint('NO-SUCH-CODE-HERE'),'','no row, no text');
}
{ // the optional module cannot be loaded: the dialog still stands, with the code and the title
  const p=page({answers:{setup_telegram:()=>({saved:false,code:'TELEGRAM-DESTINATION-FORMAT'})}});
  p.c.L.require=()=>Promise.reject(new Error('offline'));
  await saveWith(p,'x');
  assert(p.modals[p.modals.length-1].body.includes('TELEGRAM-DESTINATION-FORMAT'));
}
// ---------- item 3: one story in the section header ----------
for(const lang of ['ru','en']){
  const words=lang==='ru'?{on:'включены · каждые 60 мин',off:'выключены',mark:'не сохранено',badge:'иногда'}:{on:'on · every 60 min',off:'off',mark:'not saved',badge:'sometimes'};
  const p=page({lang});
  const head=()=>{const html=p.T.settingsA(),at=html.indexOf('id="sec-tg"'),end=html.indexOf('</summary>',at);return strip(html.slice(at,end));};
  assert(head().includes(words.badge)&&head().includes(words.off),'saved state');
  assert(!head().includes(words.mark),'nothing to save yet');
  // the switch is pressed in the form: the subtitle changes, the level badge keeps its word
  const sub={textContent:words.off},badge={textContent:words.badge},seen=[];
  const toggle={dataset:{set:'tg'},type:'checkbox',checked:true,value:'on',matches:()=>false,closest:s=>s==='details.sec'||s==='[data-secid]'?(s==='[data-secid]'?{dataset:{secid:'tg'}}:null):null};
  const root=p.T.HV.root;
  p.T.HV.root={contains:()=>true,querySelector:s=>{seen.push(s);return s==='#sec-tg summary .t>span'?sub:s==='#sec-tg summary .t span'?badge:null;},querySelectorAll:()=>[]};
  p.T.onInput({target:toggle});
  p.T.HV.root=root;
  assert.equal(badge.textContent,words.badge,'the level badge is not overwritten');
  assert.equal(sub.textContent,words.on+' · '+words.mark,'the subtitle shows the form and says it is not saved');
  assert(head().includes(words.on)&&head().includes(words.mark),'a full render says the same');
}
// ---------- item 1: the first way to get the chat ID ----------
{
  const help=fs.readFileSync(path.join(ROOT,'router/help_panel.inc.js'),'utf8');
  const one=help.indexOf('Way 1, the simplest'),two=help.indexOf('Way 2, without a third-party bot');
  assert(one>0&&two>one,'the simple way first, PowerShell second');
  for(const part of ['@userinfobot','https://t.me/userinfobot','Id: 123456789','press Start','Recipient','third-party bot','press Start once','Способ 1, самый простой','«Получатель»','сторонний бот','один раз нажмите Start'])assert(help.includes(part),part);
  assert(help.includes('Способ 2, без стороннего бота')&&help.includes('Read-Host'),'the PowerShell way stays');
  const generated=fs.readFileSync(path.join(ROOT,'docs/BUILTIN-HELP.ru.md'),'utf8');
  assert(generated.includes('@userinfobot'),'the generated help follows');
  const lazy=fs.readFileSync(path.join(ROOT,'router/files/www/luci-static/resources/'+app.ui_lazy_modules.find(m=>/help[0-9]+\.js$/.test(m))),'utf8');
  assert(lazy.includes('@userinfobot'),'the words live in the optional module');
}
console.log('PASS: Telegram - a pasted ID is forgiven, the dialog has the hint, the header tells one story, the help starts with @userinfobot');
})().catch(e=>{console.error(e);process.exit(1);});
