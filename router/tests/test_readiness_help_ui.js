const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{
  constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children).flat().filter(v=>v!=null);}
  all(){return [this,...this.children.flatMap(v=>v instanceof N?v.all():[])];}
  text(){return this.children.map(v=>v instanceof N?v.text():String(v)).join(' ');}
}
async function main(){
  for(const language of ['en','ru']){
    let copied='';const c={locale:language,bi:(a,b)=>language==='ru'?b:a,E:(...a)=>new N(...a),navigator:{clipboard:{writeText:t=>{copied=t;return Promise.resolve();}}},HELP_TOPICS:[],helpLink:(id,label)=>new N('a',{'data-help':id},label)};
    vm.createContext(c);vm.runInContext(fs.readFileSync('router/readiness_panel.inc.js','utf8'),c);
    vm.runInContext(fs.readFileSync('router/help_panel.inc.js','utf8'),c);
    for(const code of Object.keys(c.READINESS_CHECKS)){
      const tile=c.readinessTile(code,'fail'),target=tile.all().find(n=>n.attrs['data-help']);
      assert.equal(target.attrs['data-help'],'dependency-'+code);
      const topic=c.HELP_TOPICS.find(t=>t.id===target.attrs['data-help']);assert(topic,'every failed check has its own explanation');
      const body=topic.custom(),input=body.all().find(n=>n.tag==='textarea'),button=body.all().find(n=>n.tag==='button');
      assert(input.value.includes(code)&&input.value.includes(c.READINESS_GUIDES[code].verify));
      await button.attrs.click();assert.equal(copied,input.value,'copy matches the displayed repair prompt');
      assert(!/opkg upgrade|force flags/.test(c.READINESS_GUIDES[code].install));
      if(['CONFIG-STORAGE-FREE','RPC-PLUGIN'].includes(code))assert.equal(c.READINESS_GUIDES[code].install,'','non-package failures do not suggest arbitrary installation');
    }
    const codes=Object.keys(c.PREPARATION_CHECKS),status={time:100,system_readiness:{time:100,preparation:{scope:'persistent-mt3000-preparation',state:'pass',checks:codes.map((code,i)=>({code,state:i===0?'fail':'pass'}))}}};
    const table=c.renderPreparation(status,101).all().find(n=>n.tag==='table');assert(table);
    assert.equal(table.all().filter(n=>n.tag==='th').length,5);
    assert.equal(table.all().filter(n=>n.attrs['data-preparation-code']).length,7);
    assert.equal(c.preparationModel(status,191).state,'unknown','table does not promote stale preparation');
  }
  console.log('PASS: eight exact help targets and copyable repair prompts EN/RU; non-package diagnoses, five-column preparation table and stale-state fence');
}
main().catch(e=>{console.error(e);process.exit(1);});
