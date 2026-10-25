const fs=require('fs'),vm=require('vm'),assert=require('assert');
for(const lang of ['en','ru']){
 let top=850,focus=null,removals=0,hash='#help';
 class N{constructor(tag,attrs={},children=[]){this.tag=tag;this.tagName=tag.toUpperCase();this.attrs=attrs;this.children=[];this.disabled=attrs.disabled!=null;this.checked=false;[].concat(children).filter(x=>x!=null).forEach(n=>this.appendChild(n));}appendChild(n){this.children.push(n);return n;}removeChild(n){this.children.splice(this.children.indexOf(n),1);if((this.attrs.class||'').includes('hv-learn')){removals++;top=0;focus=null;}}get firstChild(){return this.children[0];}get textContent(){return this.children.map(n=>n instanceof N?n.textContent:String(n)).join('');}getAttribute(k){return this.attrs[k]??null;}contains(n){return walk(this).includes(n);}querySelectorAll(){return walk(this).filter(n=>['button','input','select'].includes(n.tag));}focus(options){focus=this;if(!options||!options.preventScroll)top=0;}}
 const walk=n=>n instanceof N?[n,...n.children.flatMap(walk)]:[];
 const saved={},c={Number,Array,Object,Date,E:(...a)=>new N(...a),bi:(en,ru)=>lang==='ru'?ru:en,richText:s=>s,helpCommand:s=>new N('code',{},s),window:{scrollTo(){throw Error('checkbox must not call scrollTo');},location:{get hash(){return hash;},set hash(v){hash=v;}},localStorage:{getItem:()=>null,setItem:(k,v)=>saved[k]=v}},rpc:{declare(){throw Error('training must not invoke router RPC');}}};vm.createContext(c);
 for(const name of ['learn_panel','viewport_state'])vm.runInContext(fs.readFileSync('router/'+name+'.inc.js','utf8'),c);
 const root=c.renderLearn(),button=label=>walk(root).find(n=>n.tag==='button'&&n.textContent===label);
 for(let q=0;q<c.LEARN_QUIZ.length;q++){
   button(c.bi('Q','В')+(q+1)).attrs.click();const inputs=walk(root).filter(n=>n.tag==='input'),check=button(c.bi('Check the answer','Проверить ответ')),nodes=walk(root).slice(),question=walk(root).find(n=>n.tag==='h2');top=850+q*20;const scroll=top,removed=removals;
   for(const box of inputs){
     for(const value of [true,true,false,true,false]){focus=box;box.checked=value;box.attrs.change();assert.equal(top,scroll);assert.equal(focus,box);assert.equal(hash,'#help');assert.equal(removals,removed);assert.strictEqual(walk(root).find(n=>n.tag==='h2'),question);assert.deepEqual(walk(root),nodes,'selection does not replace any node');assert.strictEqual(button(c.bi('Check the answer','Проверить ответ')),check);}
   }
   assert(check.disabled);check.attrs.click();assert(!button(c.bi('Next question','Следующий вопрос')),'empty disabled action cannot grade');
   const correct=c.LEARN_QUIZ[q].o.map((o,i)=>o[2]?i:-1).filter(i=>i>=0);for(const i of correct){inputs[i].checked=true;inputs[i].attrs.change();}assert(!check.disabled,'same initially-disabled button becomes usable');
   // A monitor redraw reattaches the cached course; two checkboxes can have
   // identical empty accessibility text. The focused second one must survive.
   const box=inputs[1],oldFocus={page:'help',node:box,tag:'INPUT',label:null,text:''};focus=null;c.restorePageControlFocus({help:root},oldFocus);assert.equal(focus,box);assert.equal(top,scroll);
   check.attrs.click();assert(walk(root).some(n=>(n.attrs.class||'').includes('hv-quiz-result-ok')));const gradeRemovals=removals;for(let i=0;i<10;i++)check.attrs.click();assert.equal(removals,gradeRemovals,'old grade action is single-use');
   inputs[0].checked=false;inputs[0].attrs.change();assert.equal(removals,gradeRemovals,'stale choice cannot redraw or change graded answer');
 }
 const builder=fs.readFileSync('router/build_sidebar_ui.py','utf8');assert(builder.includes('node:document.activeElement'));assert(builder.includes('restorePageControlFocus(pages,controlFocus);'));
}
console.log('PASS: all11questions EN/RU select/deselect/bursts preserve exact DOM, scroll, hash and focus; same Check button gates dynamically; poll restores exact checkbox; scoring/stale callbacks safe, no router RPC');
