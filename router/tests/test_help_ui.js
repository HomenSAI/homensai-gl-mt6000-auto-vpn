const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{constructor(tag,attrs,children){this.tag=tag;this.attrs=attrs||{};this.children=[].concat(children===undefined?[]:children).flat();}
  text(){return this.children.map(c=>typeof c==='string'?c:c.text()).join(' ');}
  all(){return [this].concat(...this.children.filter(c=>typeof c!=='string').map(c=>c.all()));}}
const context={bi:(en)=>en,E:(tag,attrs,children)=>new Node(tag,attrs,children),navigator:{}};
vm.createContext(context);
vm.runInContext(fs.readFileSync('router/help_panel.inc.js','utf8'),context);
const topics=context.HELP_TOPICS;
const ids=new Set(topics.map(t=>t.id));
assert.equal(ids.size,topics.length);
for(const need of ['no-internet','ssh','reserve','auto-refuses','helper','stale','outside-change','telegram','clock','backup','remove','report'])assert(ids.has(need),'missing topic '+need);
const cyrillic=/[А-Яа-я]/;
for(const topic of topics){
  for(const pair of [topic.title,topic.when]){assert.equal(pair.length,2);assert(pair[0].length>5&&!cyrillic.test(pair[0]));assert(cyrillic.test(pair[1]),topic.id);}
  assert(topic.steps.length>=2,topic.id);
  for(const step of topic.steps){assert.equal(step.t.length,2);assert(step.t[0].length>10&&!cyrillic.test(step.t[0]),topic.id);assert(cyrillic.test(step.t[1]),topic.id+': '+step.t[0]);
    if(step.c)assert(typeof step.c==='string'&&step.c.length>1&&!cyrillic.test(step.c));}
}
// Commands must only use subcommands the shipped emergency helper really has, and never carry secrets.
const script=fs.readFileSync('router/files/usr/sbin/homensai-vpn-emergency','utf8');
const known=new Set([...script.matchAll(/^([a-z-]+)\)/gm)].map(m=>m[1]));
for(const topic of topics)for(const step of topic.steps){
  const m=step.c&&/^homensai-vpn-emergency ([a-z-]+)$/.exec(step.c);
  if(m)assert(known.has(m[1]),'unknown helper command '+m[1]);
  assert(!/password\s*[:=]|token\s*[:=]|BEGIN [A-Z ]*PRIVATE KEY/i.test(JSON.stringify(step)),'secret-like text in help');
}
for(const command of ['show','start','stop-auto','remove-guard','close-journal'])assert(known.has(command),command);
// Rendering: every topic is a details element with its steps; copy buttons exist only for commands.
const page=context.renderHelp();
const details=page.all().filter(n=>n.tag==='details');
assert.equal(details.length,topics.length);
assert.equal(details.filter(n=>n.attrs.open).length,1);assert(details[0].attrs.id==='help-no-internet');
const commands=topics.reduce((n,t)=>n+t.steps.filter(s=>s.c).length,0);
assert.equal(page.all().filter(n=>n.tag==='pre').length,commands);
assert.equal(page.all().filter(n=>n.tag==='button').length,commands);
// The page is wired into the generated dashboard.
const menu=JSON.parse(fs.readFileSync('router/files/usr/share/luci/menu.d/luci-app-homensai-vpn.json','utf8'));
const dashboard=fs.readFileSync('router/files/www/luci-static/resources/view/homensai-vpn/'+menu['admin/services/homensai-vpn'].action.path.split('/').pop()+'.js','utf8');
assert(dashboard.includes("['help','?'")&&dashboard.includes("put('help',helpNode||(helpNode=renderHelp()))"));
console.log('PASS: help page has '+topics.length+' topics, '+commands+' copyable commands, English/Russian text and only real helper commands');
