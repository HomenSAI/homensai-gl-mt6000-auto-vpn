const fs=require('fs'),vm=require('vm');
class N{
 constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children==null?[]:children).flat().filter(n=>n!=null);}
 appendChild(n){this.children.push(n);return n;}addEventListener(){}setAttribute(k,v){this.attrs[k]=v;}
}
const c={URL,locale:'en',E:(...a)=>new N(...a),navigator:{},window:{location:{href:'http://192.168.8.1:8080/cgi-bin/luci/admin/services/homensai-vpn#help'}},localStorage:{getItem:()=>null,setItem:()=>{}},bi:(en,ru)=>c.locale==='ru'?ru:en};vm.createContext(c);
const agent=fs.readFileSync('router/files/usr/lib/homensai-vpn/agent.py','utf8'),termsVersion=/TERMS_VERSION\s*=\s*['"]([^'"]+)/.exec(agent)[1];
for(const file of ['auto_panel','summary_panel','readiness_panel','help_panel','ai_prompt','terms_panel','error_rows_extra','error_table']){
 let text=fs.readFileSync('router/'+file+'.inc.js','utf8').replaceAll('__TERMS_VERSION__',termsVersion);vm.runInContext(text,c);
}
function plain(n){if(typeof n==='string'||typeof n==='number')return String(n);if(!(n instanceof N))return '';if(n.tag==='button')return '';if(n.tag==='textarea')return '\n```text\n'+(n.value||'')+'\n```\n';if(n.tag==='pre')return '\n```text\n'+n.children.map(plain).join('')+'\n```\n';const t=n.children.map(plain).join(n.tag==='tr'?' | ':'');if(['p','h2','h3','h4','section','article','li','tr'].includes(n.tag))return '\n'+t+'\n';return t;}
const languages={};
for(const lang of ['en','ru']){c.locale=lang;languages[lang]={topics:c.HELP_TOPICS.map(topic=>({id:topic.id,title:c.bi(...topic.title),when:c.bi(...topic.when),steps:topic.steps.map(s=>({text:c.bi(...s.t),command:s.c||null})),custom:topic.custom&&topic.id!=='ai-prompt'?plain(topic.custom()):null,diagnostic:topic.id==='diagnose-all'?c.generalDiagnosticPrompt():c.helpDiagnosticPrompt(topic)})),install:lang==='en'?c.AI_PROMPT_EN:c.AI_PROMPT_RU,lan:lang==='en'?c.AI_LAN_PROMPT_EN:c.AI_LAN_PROMPT_RU};}
process.stdout.write(JSON.stringify({termsVersion,errorRows:c.ERROR_ROWS,languages}));
