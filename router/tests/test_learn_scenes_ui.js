const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{constructor(t,a={},kids=[]){this.tag=t;this.attrs=a;this.children=[];this.isConnected=true;this.disabled=a.disabled!=null;[].concat(kids).flat().filter(n=>n!=null).forEach(n=>this.appendChild(n));}appendChild(n){this.children.push(n);return n;}removeChild(n){this.children.splice(this.children.indexOf(n),1);}get firstChild(){return this.children[0];}setAttribute(k,v){this.attrs[k]=String(v);}get textContent(){return this.children.map(n=>n instanceof N?n.textContent:String(n)).join('');}set textContent(s){this.children=[String(s)];}getClientRects(){return this.hidden?[]:[{}];}}
const walk=n=>n instanceof N?[n,...n.children.flatMap(walk)]:[];
for(const lang of ['ru','en']){
 const timers=new Map(),saved={};let id=0;
 const c={E:(...a)=>new N(...a),bi:(en,ru)=>lang==='ru'?ru:en,richText:s=>s,helpCommand:s=>new N('code',{},s),document:{createElementNS:(_,t)=>new N(t)},window:{localStorage:{getItem:k=>saved[k]||null,setItem:(k,v)=>saved[k]=v}},setTimeout:f=>{timers.set(++id,f);return id;},clearTimeout:i=>timers.delete(i),rpc:{declare(){throw Error('training must not call router');}}};
 vm.createContext(c);for(const name of ['learn_scenes','learn_panel'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);
 const click=(root,key)=>walk(root).find(n=>n.attrs['data-scene-action']===key).attrs.click();
 const tick=()=>{const [key,fn]=timers.entries().next().value;timers.delete(key);fn();};
 for(let lesson=0;lesson<c.LEARN_LESSONS.length;lesson++){
  const scene=c.renderLearnScene(lesson);assert.equal(walk(scene).filter(n=>n.tag==='svg').length,1);assert.equal(scene.attrs['data-scene-step'],'0');
  click(scene,'next');assert.equal(scene.attrs['data-scene-step'],'1');click(scene,'back');assert.equal(scene.attrs['data-scene-step'],'0');
  click(scene,'play');assert.equal(timers.size,1);tick();assert.equal(scene.attrs['data-scene-step'],'1');click(scene,'play');assert.equal(timers.size,0,'pause cancels timer');
  click(scene,'play');while(timers.size)tick();assert.equal(scene.attrs['data-scene-step'],'3');assert(walk(scene).find(n=>n.attrs['data-scene-action']==='next').disabled);
  click(scene,'reset');assert.equal(scene.attrs['data-scene-step'],'0');click(scene,'play');scene.hidden=true;tick();assert.equal(timers.size,0,'hidden view pauses');scene.hidden=false;
  click(scene,'play');scene.hvDispose();assert.equal(timers.size,0,'lesson change cancels playback');click(scene,'next');assert.equal(scene.attrs['data-scene-step'],'0','stale scene inert');
 }
 const root=c.renderLearn();let button=label=>walk(root).find(n=>n.tag==='button'&&n.textContent===label);
 for(let lesson=0;lesson<c.LEARN_LESSONS.length;lesson++){
  assert(walk(root).some(n=>n.attrs['data-learn-scene']===String(lesson)),'scene in actual lesson');
  const play=walk(root).find(n=>n.attrs['data-scene-action']==='play');play.attrs.click();
  button(lesson===c.LEARN_LESSONS.length-1?c.bi('To the questions','К вопросам'):c.bi('Next','Дальше')).attrs.click();assert.equal(timers.size,0,'navigation disposes real scene');
 }
 for(let q=0;q<c.LEARN_QUIZ.length;q++){
  for(let i=0;i<c.LEARN_QUIZ[q].o.length;i++)if(c.LEARN_QUIZ[q].o[i][2]){const boxes=walk(root).filter(n=>n.tag==='input');boxes[i].checked=true;boxes[i].attrs.change();}
  button(c.bi('Check the answer','Проверить ответ')).attrs.click();button(q===c.LEARN_QUIZ.length-1?c.bi('See my result','Узнать результат'):c.bi('Next question','Следующий вопрос')).attrs.click();
 }
 assert(root.textContent.includes('100'));assert.equal(saved['homensai-vpn-learn-done'],'1');assert.equal(timers.size,0);
 assert(!c.LEARN_QUIZ[3].o[0][0].startsWith('The LAN trial'));
}
console.log('PASS: all eight interactive lessons and complete quiz EN/RU; play/pause/steps/end/reset/hidden/dispose; no router calls');
