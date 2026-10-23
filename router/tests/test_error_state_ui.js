const fs=require('fs'),vm=require('vm'),assert=require('assert');
class N{
 constructor(tag,attrs,kids){this.tag=tag;this.attrs=attrs||{};this.children=[];this.listeners={};this.value='';[].concat(kids||[]).flat().filter(v=>v!=null).forEach(v=>this.appendChild(v));}
 appendChild(node){this.children.push(node);if(node instanceof N)node.parent=this;return node;}
 removeChild(node){this.children.splice(this.children.indexOf(node),1);}
 get firstChild(){return this.children[0]||null;}
 get nextElementSibling(){return this.parent&&this.parent.children[this.parent.children.indexOf(this)+1];}
 setAttribute(k,v){this.attrs[k]=v;}
 addEventListener(k,fn){this.listeners[k]=fn;}
 set textContent(value){this.children=[value];}
 all(){return [this].concat(...this.children.filter(x=>x instanceof N).map(x=>x.all()));}
}
const storage={};function sandbox(){
 const c={bi:en=>en,AUTO_BLOCKERS:{},PLAN_BLOCKERS:{},E:(t,a,k)=>new N(t,a,k),sessionStorage:{getItem:k=>storage[k]||null,setItem:(k,v)=>storage[k]=v}};
 vm.createContext(c);vm.runInContext(fs.readFileSync('router/error_table.inc.js','utf8'),c);return c;
}
let c=sandbox(),root=c.renderErrorTable(),row=root.all().find(n=>n.attrs['data-error-code']==='DNS-001');
assert(row);let button=row.all().find(n=>n.tag==='button');assert(row.nextElementSibling.hidden);button.attrs.click();assert(!row.nextElementSibling.hidden);
const search=root.all().find(n=>n.tag==='input');search.value='DNS-001';search.listeners.input();row=root.all().find(n=>n.attrs['data-error-code']==='DNS-001');assert(!row.nextElementSibling.hidden,'filter/redraw retains expanded description');
c.ERROR_TABLE_STATE.selected='DNS-001';c.persistErrorTableState();c=sandbox();root=c.renderErrorTable();row=root.all().find(n=>n.attrs['data-error-code']==='DNS-001');
assert(!row.nextElementSibling.hidden,'full document reload restores expanded code');assert.equal(row.attrs.class,'hv-err-selected');assert.equal(root.all().find(n=>n.tag==='input').value,'DNS-001');
console.log('PASS: error description, filter and selected row survive redraw and full document reload');
