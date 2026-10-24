const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{constructor(tag,attrs={},children=[]){this.tag=tag;this.attrs=attrs;this.children=[].concat(children).flat().filter(v=>v!=null);this.disabled=attrs.disabled!=null;}appendChild(n){this.children.push(n);return n;}removeChild(n){this.children.splice(this.children.indexOf(n),1);}get firstChild(){return this.children[0];}get textContent(){return this.children.map(n=>n instanceof N?n.textContent:String(n)).join('');}}
function walk(n){return n instanceof N?[n,...n.children.flatMap(walk)]:[];}
for(const lang of ['en','ru']){
 const saved={},c={E:(...a)=>new N(...a),bi:(en,ru)=>lang==='ru'?ru:en,richText:s=>s,helpCommand:s=>new N('code',{},s),window:{localStorage:{getItem:k=>k==='homensai-vpn-learn-seen'?'1':saved[k],setItem:(k,v)=>saved[k]=v}},rpc:{declare(){throw Error('Training must not invoke RPC');}}};vm.createContext(c);vm.runInContext(fs.readFileSync('router/learn_panel.inc.js','utf8'),c);
 const root=c.renderLearn(),button=label=>walk(root).find(n=>n.tag==='button'&&n.textContent===label),click=n=>{assert(n,'missing button');n.attrs.click();},qbutton=i=>button(c.bi('Q','В')+(i+1)),check=()=>button(c.bi('Check the answer','Проверить ответ'));
 click(qbutton(c.LEARN_QUIZ.length-1));assert(walk(root).some(n=>n.tag==='h2'&&n.textContent.includes(String(c.LEARN_QUIZ.length))));
 click(button(c.bi('Results','Результаты')));assert(root.textContent.includes(c.bi('Checked questions: ','Проверено вопросов: ')+'0 / '+c.LEARN_QUIZ.length));assert(!saved['homensai-vpn-learn-done'],'jumping to result is not a completed course');
 const wrong=new Set([1,8]);
 function answer(i,correct){
  const options=c.LEARN_QUIZ[i].o;let ids=options.map((o,j)=>j).filter(j=>correct?options[j][2]:!options[j][2]);if(!correct)ids=ids.slice(0,1);
  for(const j of ids){const boxes=walk(root).filter(n=>n.tag==='input');boxes[j].checked=true;boxes[j].attrs.change();}
  click(check());
 }
 for(let i=0;i<c.LEARN_QUIZ.length;i++){click(qbutton(i));assert(root.textContent.includes(c.bi('Before the question','Перед вопросом')));answer(i,!wrong.has(i));}
 click(button(c.bi('Results','Результаты')));
 assert(root.textContent.includes('82'));assert(root.textContent.includes(c.bi('Correct on first attempt: ','Верно с первой попытки: ')+'9 / 11'));
 const retry=walk(root).find(n=>n.tag==='button'&&n.attrs['data-learn-retry-wrong']==='1');assert(retry.textContent.endsWith('(2)'));click(retry);
 assert(walk(root).some(n=>n.tag==='h2'&&n.textContent===c.bi('Question ','Вопрос ')+'2 / 11'));answer(1,true);click(retry);assert(walk(root).some(n=>n.tag==='h2'&&n.textContent===c.bi('Question ','Вопрос ')+'2 / 11'),'stale retry cannot erase or redirect a newer review');
 click(button(c.bi('Next question','Следующий вопрос')));assert(walk(root).some(n=>n.tag==='h2'&&n.textContent===c.bi('Question ','Вопрос ')+'9 / 11'),'retry skips previously correct answers');answer(8,true);
 click(button(c.bi('See my result','Узнать результат')));assert(root.textContent.includes('100'));assert(root.textContent.includes(c.bi('Correct on first attempt: ','Верно с первой попытки: ')+'9 / 11'));assert(root.textContent.includes(c.bi('Total answer checks: ','Всего проверок ответов: ')+'13'));assert(!walk(root).some(n=>n.attrs['data-learn-retry-wrong']==='1'));assert.equal(saved['homensai-vpn-learn-done'],'1');
 const table=walk(root).find(n=>n.attrs.class==='table hv-learn-results');assert(table);assert.equal(walk(table).filter(n=>n.tag==='tr').length,12);
}
console.log('PASS: direct jump to any of11 questions from contents, explanation/question flow, incomplete result not passed, first-attempt and current scores, wrong-only retry preserves9correct answers and records13checks EN/RU; no RPC');
