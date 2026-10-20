const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Node{
  constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[];this.disabled=attrs.disabled!=null;(Array.isArray(children)?children:[children]).forEach(n=>this.appendChild(n));}
  appendChild(n){this.children.push(n);return n;}removeChild(n){this.children.splice(this.children.indexOf(n),1);}get firstChild(){return this.children[0];}
  get textContent(){return this.children.map(n=>n instanceof Node?n.textContent:String(n)).join('');}
}
const walk=n=>n instanceof Node?[n,...n.children.flatMap(walk)]:[];
const c={E:(...a)=>new Node(...a),bi:en=>en,richText:s=>s,helpCommand:s=>new Node('code',{},s),window:{localStorage:{getItem:()=>null,setItem(){}}}};
vm.createContext(c);vm.runInContext(fs.readFileSync('router/learn_panel.inc.js','utf8'),c);
const host=c.renderLearn(),button=text=>walk(host).find(n=>n.tag==='button'&&n.textContent===text),heading=()=>walk(host).find(n=>n.tag==='h2').textContent;
const click=node=>node.attrs.click();
const oldNext=button('Next');click(oldNext);const second=heading();for(let i=0;i<20;i++)click(oldNext);assert.equal(heading(),second,'old Next must not skip cards');
const oldBack=button('Back');click(oldBack);const first=heading();for(let i=0;i<20;i++)assert.doesNotThrow(()=>click(oldBack));assert.equal(heading(),first,'old Back must not make the index negative');
const beforeJump=button('Next');click(button('4'));const fourth=heading();click(beforeJump);assert.equal(heading(),fourth,'events from an earlier render cannot alter the new page');
click(button('?'));assert.equal(heading(),'Question 1 / '+c.LEARN_QUIZ.length);
const disabledCheck=button('Check the answer');assert(disabledCheck.disabled);click(disabledCheck);assert(!button('Next question'),'disabled action cannot grade an empty choice');
let choice=walk(host).find(n=>n.tag==='input');choice.checked=true;choice.attrs.change();const check=button('Check the answer');assert(!check.disabled);click(check);assert(button('Next question'));for(let i=0;i<20;i++)click(check);assert.equal(heading(),'Question 1 / '+c.LEARN_QUIZ.length,'old Check cannot skip questions');
choice.checked=false;choice.attrs.change();assert(button('Next question'),'stale checkbox must not change a graded answer');
const nextQuestion=button('Next question');click(nextQuestion);for(let i=0;i<20;i++)click(nextQuestion);assert.equal(heading(),'Question 2 / '+c.LEARN_QUIZ.length);
console.log('PASS: learning Back/Next bursts, stale render callbacks, chapter jumps, disabled quiz actions, answer grading and stale question inputs');
