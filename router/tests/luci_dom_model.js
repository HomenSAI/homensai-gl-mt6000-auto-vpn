// LuCI 21.02 luci.js E()/dom.create/dom.append semantics for the UI test doubles (BH3-01, 07.11.2026).
// The doubles used to keep the children argument as data, so a single string child looked like text in every test, while
// real LuCI does `node.innerHTML = '' + child` for it. This model follows luci.js:
//   E(tag, attr, data): a 2nd argument that is not an object (or is an array) is the data and attr becomes null;
//   append(node, data): array -> every item a node or a text node ('' + item, so null/undefined items become the text
//   'null'/'undefined'); function -> append(node, data(node)); node (any object here) -> appended; anything else ->
//   node.innerHTML = '' + data.
// Every innerHTML assignment is recorded in `sinks` ({tag, html}), so a test can require that none happens.
'use strict';
function isNode(x){return x!==null&&typeof x==='object';}
function append(node,data,sinks){
  if(Array.isArray(data)){for(const c of data)node.children.push(isNode(c)?c:''+c);return;}
  if(typeof data==='function')return append(node,data(node),sinks);
  if(isNode(data)){node.children.push(data);return;}
  if(data!==null&&data!==undefined){const html=''+data;node.innerHTML=html;sinks.push({tag:node.tag,html});}
}
// make(tag, attrs) must return a node with a `children` array.
function luciE(make,sinks){
  return function(tag,attr,data){
    if(!(attr!==null&&(typeof attr==='object'||typeof attr==='function'))||Array.isArray(attr)){data=attr;attr=null;}
    const node=make(tag,attr);
    if(!Array.isArray(node.children))node.children=[];
    append(node,data,sinks);
    return node;
  };
}
module.exports={luciE,append};
