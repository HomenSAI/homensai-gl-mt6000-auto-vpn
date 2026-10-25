const fs=require('fs'),vm=require('vm'),assert=require('assert');
for(const lang of ['en','ru']){
 let root=null,x=31,y=0,focus=null,tail=0,scrolls=0,timers=[];
 const walk=n=>n instanceof N?[n,...n.children.flatMap(walk)]:[];
 function maximum(){return root?Math.max(0,120+root.getBoundingClientRect().height+tail-500):10000;}
 function clamp(){y=Math.min(y,maximum());}
 class N{
  constructor(tag,attrs={},children=[]){this.tag=tag;this.tagName=tag.toUpperCase();this.attrs=attrs;this.children=[];this.parent=null;this.connected=false;this.disabled=attrs.disabled!=null;this.hidden=attrs.hidden!=null;let min='';this.style={};Object.defineProperty(this.style,'minHeight',{get:()=>min,set:v=>{min=v;clamp();}});[].concat(children).flat().filter(n=>n!=null).forEach(n=>this.appendChild(n));}
  get isConnected(){return this.connected||!!(this.parent&&this.parent.isConnected);}
  appendChild(n){if(n instanceof N){if(n.parent)n.parent.removeChild(n);n.parent=this;}this.children.push(n);clamp();return n;}
  removeChild(n){if(n instanceof N){if(n.contains(focus))focus=null;n.parent=null;}this.children.splice(this.children.indexOf(n),1);clamp();}
  get firstChild(){return this.children[0];}get textContent(){return this.children.map(n=>n instanceof N?n.textContent:String(n)).join('');}set textContent(v){while(this.firstChild)this.removeChild(this.firstChild);this.children=[String(v)];clamp();}
  getAttribute(k){return this.attrs[k]??null;}setAttribute(k,v){this.attrs[k]=String(v);}contains(n){return walk(this).includes(n);}
  querySelectorAll(selector){const tags=selector.split(',');return walk(this).filter(n=>tags.includes(n.tag));}querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
  getBoundingClientRect(){const count=walk(this).filter(n=>!n.hidden).length;return {height:Math.max(200+count*8,parseFloat(this.style.minHeight)||0),top:120-y};}
  focus(options){if(this.disabled)return;focus=this;if(!options||!options.preventScroll)y=0;}
 }
 const c={E:(...a)=>new N(...a),Number,Array,Date,bi:(en,ru)=>lang==='ru'?ru:en,richText:t=>t,helpCommand:t=>new N('code',{},t),setTimeout:fn=>{timers.push(fn);return timers.length;},clearTimeout:()=>{},window:{get scrollX(){return x;},get scrollY(){return y;},innerHeight:500,scrollTo:v=>{scrolls++;x=v.left;y=Math.min(v.top,maximum());},location:{hash:'#help'},localStorage:{getItem:()=>null,setItem(){}}},document:{get activeElement(){return focus;},scrollingElement:{get scrollHeight(){return maximum()+500;}},createElementNS:(_ns,tag)=>new N(tag)},rpc:{declare(){throw Error('learning must not invoke RPC');}}};
 vm.createContext(c);vm.runInContext(fs.readFileSync('router/learn_panel.inc.js','utf8'),c);root=c.renderLearn();root.connected=true;
 const button=text=>walk(root).find(n=>n.tag==='button'&&n.textContent===text),named=(en,ru)=>button(c.bi(en,ru));
 function act(node,label){assert(node,label);assert(!node.disabled,label);y=Math.min(180,Math.max(0,maximum()-5));x=31;focus=node;const before=y;node.attrs.click();assert.equal(y,before,label+' preserves viewport');assert.equal(x,31);assert.equal(c.window.location.hash,'#help');assert(focus===null||root.contains(focus),label+' leaves focus in current course');}
 act(named('Next','Дальше'),'lesson next');act(named('Back','Назад'),'lesson back');
 for(let i=0;i<c.LEARN_LESSONS.length;i++)act(button(String(i+1)),'lesson chip '+i);
 act(named('To the questions','К вопросам'),'open quiz');
 for(let q=0;q<c.LEARN_QUIZ.length;q++){
  act(button(c.bi('Q','В')+(q+1)),'question chip '+q);
  const inputs=walk(root).filter(n=>n.tag==='input');let selected=c.LEARN_QUIZ[q].o.map((o,i)=>(q===1?!o[2]:o[2])?i:-1).filter(i=>i>=0);if(q===1)selected=selected.slice(0,1);
  selected.forEach(i=>{inputs[i].checked=true;inputs[i].attrs.change();});act(named('Check the answer','Проверить ответ'),'grade '+q);
  if(q<c.LEARN_QUIZ.length-1)act(named('Next question','Следующий вопрос'),'next question '+q);
 }
 act(named('See my result','Узнать результат'),'result');assert(root.textContent.includes('91'));
 act(walk(root).find(n=>n.attrs['data-result-question']==='1'),'result table question');act(named('Results','Результаты'),'result chip');
 act(walk(root).find(n=>n.attrs['data-learn-retry-wrong']==='1'),'retry wrong');let inputs=walk(root).filter(n=>n.tag==='input');c.LEARN_QUIZ[1].o.forEach((o,i)=>{if(o[2]){inputs[i].checked=true;inputs[i].attrs.change();}});act(named('Check the answer','Проверить ответ'),'grade retry');act(named('See my result','Узнать результат'),'retry result');assert(root.textContent.includes('100'));
 act(named('Take the training again','Пройти обучение заново'),'restart');act(named('☰ Contents','☰ Оглавление'),'contents');act(named('Start from the beginning','Начать с самого начала'),'contents restart');
 // Shrinking the document must not force a jump at a deep reading position.
 y=maximum();const deep=y;act(named('Results','Результаты'),'grow results');y=maximum();const old=y;focus=named('Take the training again','Пройти обучение заново');focus.attrs.click();assert.equal(y,old,'shorter content retains enough height to keep current position');
 // Scene controls and timer frames use the same viewport transaction.
 tail=10000;vm.runInContext(fs.readFileSync('router/learn_scenes.inc.js','utf8'),c);const scene=c.renderLearnScene(0);root.appendChild(scene);
 const sceneButton=name=>walk(scene).find(n=>n.attrs['data-scene-action']===name);
 for(const name of ['next','back','reset','play','play']){const n=sceneButton(name);y=500;focus=n;const before=scrolls;n.attrs.click();assert.equal(y,500,'scene '+name);if(name!=='play')assert(scrolls>before);}
 // Help expand/collapse retains the same cached course and page position.
 vm.runInContext(fs.readFileSync('router/help_panel.inc.js','utf8'),c);root=c.renderHelpTraining();root.connected=true;const toggle=walk(root).find(n=>n.tag==='button');act(toggle,'help expand');const cached=walk(root).find(n=>n.attrs.class==='hv-chart-card hv-learn');act(toggle,'help collapse');act(toggle,'help reopen');assert(root.contains(cached));
 assert(scrolls>40,'all internal redraw actions used viewport preservation');
}
console.log('PASS: grading,11question/8lesson navigation, contents/results/table/retry/restart, shrink-at-bottom, scene controls and Help expand/collapse preserve viewport EN/RU, scores and focus safe, no router RPC');
