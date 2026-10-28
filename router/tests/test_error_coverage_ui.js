const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
// Every diagnostic code that the router program can emit (Python and Lua sources) must have a row in the error table,
// or belong to a documented family, so a code shown anywhere on the page always opens its explanation.
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const page=menu['admin/services/homensai-vpn'].action.path.split('/').pop();
const src=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+page+'.js','utf8');
const prefix=src.slice(0,src.lastIndexOf('return view.extend({'));
const ctx={window:{localStorage:{getItem(){return null},setItem(){}},HomenS:{},location:{search:'',href:'http://x/',hash:''}},document:{createElement:()=>({}),addEventListener(){}},localStorage:{getItem(){return null}},E:()=>({}),URLSearchParams,URL,Intl,console,L:{},rpc:{declare:()=>()=>0},ui:{},poll:{},view:{extend:o=>o}};
vm.createContext(ctx);vm.runInContext(prefix,ctx);
// Eager titles cover notices immediately; the optional module contains the full explanations.
if(ctx.LAZY_HELP_NAME){
 const module=fs.readFileSync('router/files/www/luci-static/resources/'+ctx.LAZY_HELP_NAME.replace(/\./g,'/')+'.js','utf8');
 ctx.baseclass={extend:value=>value};
 vm.runInContext('(function(){'+module+'})()',ctx).create(ctx.lazyHelpContext());
}
const dir='router/files/usr/lib/homensai-vpn';
const rx=/['"]([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+)['"]/g;
const skip=c=>/^(SHA-|UTF-|X-|HTTP-)/.test(c);
const missing=new Set();let total=0;
for(const f of fs.readdirSync(dir).filter(n=>/\.(py|lua)$/.test(n))){
  const text=fs.readFileSync(path.join(dir,f),'utf8');let m;
  while((m=rx.exec(text))){const c=m[1];if(skip(c))continue;total++;
    const known=Object.prototype.hasOwnProperty.call(ctx.ERROR_GROUP_OF,c)||!!ctx.errorFamilyOf(c);if(!known)missing.add(c);}
}
assert.deepEqual([...missing].sort(),[],'codes without a row or family: '+[...missing].join(', '));
// Rows are complete: names, meanings and, for rows with a fix, both languages; examples come in pairs.
for(const r of ctx.ERROR_ROWS){
  assert(r.length>=6&&r[2]&&r[3]&&r[4]&&r[5],'row incomplete: '+r[0]);
  if(r[6])assert(r[7],'fix without Russian text: '+r[0]);
  if(r[8])assert(r[9],'example without Russian text: '+r[0]);
}
// The linker also recognises one-word states and family prefixes.
for(const word of ['COMMITTED','APPLYING','ARMED','ROLLED-BACK','WAIT-CLIENT','OFFLINE-FIXTURE','OBSERVING','BLOCKED'])assert(ctx.ERROR_GROUP_OF[word],'state/code not linked: '+word);
assert(ctx.errorFamilyOf('CASCADE-PROOF-EXPIRED')&&ctx.errorFamilyOf('MIGRATION-ANYTHING')&&!ctx.errorFamilyOf('DNS-001'));
console.log('PASS: '+total+' emitted code references covered by '+Object.keys(ctx.ERROR_GROUP_OF).length+' rows and '+ctx.ERROR_FAMILIES.length+' families; states and notices link');
// Rule: every code of the error table is found by the page linker, alone and inside a sentence (regression: DNS-001 was skipped by a pre-filter).
const notLinked=[];
for(const code of Object.keys(ctx.ERROR_GROUP_OF).filter(c=>!c.includes('*'))){
  for(const text of [code,'Сбой · '+code,'See '+code+'.']){
    const hits=ctx.findErrorCodes(text).map(h=>h.code);
    if(!hits.includes(code))notLinked.push(code+' in "'+text+'"');
  }
}
assert.deepEqual(notLinked.slice(0,10),[],'codes the linker cannot link: '+notLinked.slice(0,10).join('; '));
assert(ctx.findErrorCodes('DNS-001').length===1,'DNS-001 is linked');
console.log('PASS: every error-table code is found by the linker');
