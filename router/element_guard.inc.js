/* Module-local E: LuCI renders null array children as text. Keep attributes intact.
   BH3-01: LuCI dom.append puts a single non-array, non-node child into innerHTML ('' + child); array items become text
   nodes. A scalar child (string/number/boolean) is therefore always wrapped as [String(x)] so it is text, never markup.
   Nodes (objects) and functions (LuCI calls them with the new element) pass through unchanged. */
function hvElementChildren(value){
  if(value===null||value===undefined)return [];
  if(!Array.isArray(value))return typeof value==='object'||typeof value==='function'?value:[String(value)];
  var result=[];
  value.forEach(function(child){
    if(child===null||child===undefined)return;
    if(Array.isArray(child)){var nested=hvElementChildren(child);Array.prototype.push.apply(result,nested);}
    else result.push(child);
  });return result;
}
/* CSP (F-77): a 'style' value goes through the CSSOM (style.setProperty), never into a style attribute. */
function hvCss(el,css){
  if(!el||css==null)return el;
  if(el.style&&typeof el.style.setProperty==='function')String(css).split(';').forEach(function(d){var i=d.indexOf(':'),v=d.slice(i+1).trim(),imp=/!important$/.test(v);if(i>0)el.style.setProperty(d.slice(0,i).trim(),imp?v.slice(0,-10).trim():v,imp?'important':'');});
  else if(el.setAttribute)el.setAttribute('style',String(css));  // test doubles without a CSSOM only
  return el;
}
var E=(function(nativeElement){
  nativeElement=nativeElement&&nativeElement.__homensaiRawElement||nativeElement;
  if(typeof nativeElement!=='function')throw new Error('DOM element factory unavailable');
  function element(){
    var args=Array.prototype.slice.call(arguments),a=args[1],css=null;
    if(a&&typeof a==='object'&&!Array.isArray(a)&&!a.nodeType&&typeof a.style==='string'){css=a.style;a=Object.assign({},a);delete a.style;args[1]=a;}
    if(Array.isArray(args[0]))args[0]=hvElementChildren(args[0]);
    if(args.length>2)args[2]=hvElementChildren(args[2]);
    else if(args.length===2&&Array.isArray(args[1]))args[1]=hvElementChildren(args[1]);
    /* LuCI takes a non-object 2nd argument as the children (E(tag,'text')): make it text too (BH3-01). */
    if(args.length>=2&&args[1]!=null&&typeof args[1]!=='object'&&typeof args[1]!=='function')args[1]=[String(args[1])];
    return hvCss(nativeElement.apply(null,args),css);
  }
  Object.defineProperty(element,'__homensaiRawElement',{value:nativeElement});return element;
})(typeof L!=='undefined'&&L.dom&&typeof L.dom.create==='function'?L.dom.create.bind(L.dom):typeof globalThis!=='undefined'?globalThis.E:window.E);
