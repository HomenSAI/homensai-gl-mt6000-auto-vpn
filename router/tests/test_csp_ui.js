// Plan item 55, finding F-77 (07.11.2026): the SHIPPED page code works under a Content-Security-Policy without
// 'unsafe-eval' and without inline style attributes. Scans the packaged files (the selected page module, its lazy
// help module and the server module) and checks the CSSOM paths that replace style attributes.
// LuCI's own L.require still compiles modules with eval; that is LuCI, not this page (router/tests/CSP-NOTE.md).
'use strict';
const fs=require('fs'),vm=require('vm'),path=require('path'),assert=require('assert');
const {pageSource,ROOT,app}=require('./approved_page');
const lazyRoot=path.join(ROOT,'router/files/www/luci-static/resources');
const number=app.ui_module.replace(/^dashboard/,'');
const files={[app.ui_module+'.js']:pageSource()};
for(const m of app.ui_lazy_modules)files[path.basename(m)]=fs.readFileSync(path.join(lazyRoot,m),'utf8');
files['pick'+number+'.js']=fs.readFileSync(path.join(lazyRoot,'homensai-vpn/pick'+number+'.js'),'utf8');
assert(Object.keys(files).length>=3,'page, help and server modules scanned');
const page=files[app.ui_module+'.js'],help=files['help'+number+'.js'];
assert(help,'the lazy help module is listed in VERSION.json');

// Every exception is listed here with its reason; anything else fails.
const ALLOW=[
  // hvCss fallback for test doubles without a CSSOM: every browser element (HTML, SVG) has style.setProperty,
  // so a browser never reaches it (proved below with a CSSOM element).
  {file:app.ui_module+'.js',re:/setAttribute\(\s*['"]style['"]/g,count:1,near:"else if(el.setAttribute)el.setAttribute('style',String(css));  // test doubles"},
  // the printable incident report is a separate downloaded file with its own CSP meta; a <style> element, not an attribute
  {file:app.ui_module+'.js',re:/<style\b/gi,count:1,near:'<meta http-equiv="Content-Security-Policy" content="default-src \\\'none\\\'; style-src \\\'unsafe-inline\\\''},
];
const RULES=[
  ['new Function',/\bnew\s+Function\b|\bFunction\s*\(/g],
  ['eval(',/\beval\s*\(/g],
  ['string timer',/\bset(?:Timeout|Interval)\s*\(\s*['"`]/g],
  ['inline style attribute in an HTML string',/\sstyle\s*=\s*(?:\\?["'`]|[^\s>=])/gi],
  ['setAttribute style',/setAttribute\(\s*['"]style['"]/g],
  ['style.cssText',/\.style\.cssText\b/g],
  ['style property replaced',/\.style\s*=(?!=)/g],
  ['style element',/<style\b/gi],
];
for(const [name,text] of Object.entries(files)){
  for(const [rule,re] of RULES){
    const hits=[...text.matchAll(re)];
    const allow=ALLOW.find(a=>a.file===name&&String(a.re)===String(re));
    if(allow){
      assert.equal(hits.length,allow.count,name+': '+rule+' only at the listed exception');
      const near=text.indexOf(allow.near);assert(near>=0&&Math.abs(near-hits[0].index)<600,name+': '+rule+' exception moved');
    }else assert.equal(hits.length,0,name+': '+rule+' at '+hits.map(h=>text.slice(0,h.index).split('\n').length).join(','));
  }
}
console.log('PASS: no new Function, eval, string timers, inline style attributes, setAttribute(style) or cssText in '+Object.keys(files).join(', ')+' (2 listed exceptions)');

// ---------- style values given as object keys go only to the CSSOM factories ----------
// The page module's E and the two SVG helpers of the help module apply 'style' through style.setProperty (checked below).
function enclosingCall(text,at){
  let depth=0;
  for(let i=at-1;i>=0;i--){
    const ch=text[i];
    if(ch==='\''||ch==='"'){let j=i-1;for(;j>=0;j--){if(text[j]===ch){let b=0,k=j-1;while(k>=0&&text[k]==='\\'){b++;k--;}if(b%2===0)break;}}i=j;continue;}
    if(ch===')'||ch===']'||ch==='}')depth++;
    else if(ch==='('||ch==='['||ch==='{'){if(depth>0)depth--;else if(ch==='(')return /([A-Za-z_$][\w$]*)\s*$/.exec(text.slice(Math.max(0,i-40),i))?.[1]||'';}
  }
  return '';
}
const FACTORIES=new Set(['E','measureSvg','coreSvg']);
let keys=0;
for(const [name,text] of Object.entries(files)){
  for(const m of text.matchAll(/(['"]?)style\1\s*:\s*['"]/g)){
    keys++;const call=enclosingCall(text,m.index);
    assert(FACTORIES.has(call),name+': a style value at line '+text.slice(0,m.index).split('\n').length+' goes to '+(call||'?')+', not to a CSSOM factory');
  }
}
assert(keys>=9,'the known style values were found ('+keys+')');
console.log('PASS: all '+keys+' style values given as object keys go to E/measureSvg/coreSvg');

// ---------- the CSSOM paths ----------
function cssomElement(log){
  const props=[];
  return {nodeType:1,style:{setProperty(k,v,p){props.push([k,v,p||'']);}},setAttribute(k,v){log.push([k,String(v)]);},props};
}
const guard=page.slice(page.indexOf('function hvCss('),page.indexOf('var E=(function(nativeElement){'))+
  page.slice(page.indexOf('var E=(function(nativeElement){'),page.indexOf('\n',page.indexOf('})(typeof L!==\'undefined\'&&L.dom'))+1);
const children=page.slice(page.indexOf('function hvElementChildren('),page.indexOf('function hvCss('));
const attrs=[];const sandbox={L:{dom:{create(tag,a){const el=cssomElement(attrs);el.tag=tag;Object.keys(a&&typeof a==='object'&&!Array.isArray(a)?a:{}).forEach(k=>el.setAttribute(k,a[k]));return el;}}}};
vm.createContext(sandbox);vm.runInContext(children+guard+';this.E=E;this.hvCss=hvCss;',sandbox);
{
  const given={'readonly':'readonly','rows':'12','style':'width:100%;box-sizing:border-box'};
  const el=sandbox.E('textarea',given,[]);
  assert.deepEqual(el.props,[['width','100%',''],['box-sizing','border-box','']],'E: style declarations through style.setProperty');
  assert(!attrs.some(a=>a[0]==='style'),'E: no style attribute');assert(attrs.some(a=>a[0]==='readonly')&&attrs.some(a=>a[0]==='rows'),'E: other attributes kept');
  assert.equal(given.style,'width:100%;box-sizing:border-box','E: the caller object is not changed');
  const dot=sandbox.E('i',{'style':'background:#139c75'});assert.deepEqual(dot.props,[['background','#139c75','']]);
  const fill=sandbox.hvCss(cssomElement(attrs),'--hv-fill:40%;color:red !important');
  assert.deepEqual(fill.props,[['--hv-fill','40%',''],['color','red','important']],'custom properties and !important');
  assert(!attrs.some(a=>a[0]==='style'),'no style attribute anywhere');
}
console.log('PASS: E applies style through the CSSOM, keeps other attributes, leaves the caller object as given');
{
  for(const helper of ['measureSvg','coreSvg']){
    const src=new RegExp('function '+helper+'\\(tag,attrs\\)\\{[^\\n]*?return n;\\}').exec(help);assert(src,helper+' in the help module');
    const log=[];const box={hvCss:sandbox.hvCss,document:{createElementNS:()=>cssomElement(log)}};vm.createContext(box);
    vm.runInContext(src[0]+';this.f='+helper+';',box);
    const svg=box.f('svg',{viewBox:'0 0 10 10',role:'img',style:'width:100%;height:auto;display:block'});
    assert.deepEqual(svg.props,[['width','100%',''],['height','auto',''],['display','block','']],helper+': style through the CSSOM');
    assert.deepEqual(log,[['viewBox','0 0 10 10'],['role','img']],helper+': other attributes as before, no style attribute');
  }
  const fill=/function retentionFill\(input,min,max\)\{[^\n]*?\}/.exec(help);assert(fill,'retention slider fill');
  const log=[];const box={hvCss:sandbox.hvCss};vm.createContext(box);vm.runInContext(fill[0]+';this.f=retentionFill;',box);
  const input=cssomElement(log);input.value='30';box.f(input,0,60);
  assert.deepEqual(input.props,[['--hv-fill','50%','']],'retention fill through the CSSOM');assert.equal(log.length,0);
  assert(/hvCss\(bar,'width:'\+/.test(help),'retention room bar width through the CSSOM');
  assert(/^var hvCss=ctx\.hvCss;$/m.test(help)&&/\bhvCss:hvCss\b/.test(page),'the help module receives hvCss from the page');
}
console.log('PASS: SVG helpers and the retention bars of the help module set style through the CSSOM');

// ---------- the lazy help retry asks LuCI by name (no eval) ----------
{
  const name=/var LAZY_HELP_NAME='([^']+)'/.exec(page)[1];
  const fn=/function lazyHelpRetryName\(attempt\)\{[\s\S]*?\n\}/.exec(page);assert(fn,'retry name function');
  assert(/function lazyHelpRequire\(retry\)\{return L\.require\(retry\?lazyHelpRetryName\(LAZY_HELP\.attempt\):LAZY_HELP_NAME\);\}/.test(page),'retry goes through L.require');
  const box={LAZY_HELP_NAME:name};vm.createContext(box);vm.runInContext(fn[0]+';this.f=lazyHelpRetryName;',box);
  const seen=new Set();
  for(let attempt=2;attempt<130;attempt++){
    const n=box.f(attempt);assert(!seen.has(n)&&n!==name,'a fresh LuCI module name for retry '+attempt);seen.add(n);
    assert.equal(decodeURIComponent(n.replace(/\./g,'/')),name.replace(/\./g,'/'),'the same pinned file: '+n);
    assert(/^[A-Za-z0-9_%\/-]+$/.test(n)&&!n.includes('.'),'no dot: LuCI turns dots into path separators');
  }
  assert.equal(box.f(2),name.replace('.','/'),'the first retry needs no percent decoding');
}
console.log('PASS: Help retry asks L.require for the same pinned file under 128 fresh names, without eval');
