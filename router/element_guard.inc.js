/* Module-local E: LuCI renders null array children as text. Keep attributes intact. */
function hvElementChildren(value){
  if(value===null||value===undefined)return [];
  if(!Array.isArray(value))return value;
  var result=[];
  value.forEach(function(child){
    if(child===null||child===undefined)return;
    if(Array.isArray(child)){var nested=hvElementChildren(child);Array.prototype.push.apply(result,nested);}
    else result.push(child);
  });return result;
}
var E=(function(nativeElement){
  nativeElement=nativeElement&&nativeElement.__homensaiRawElement||nativeElement;
  if(typeof nativeElement!=='function')throw new Error('DOM element factory unavailable');
  function element(){
    var args=Array.prototype.slice.call(arguments);
    if(Array.isArray(args[0]))args[0]=hvElementChildren(args[0]);
    if(args.length>2)args[2]=hvElementChildren(args[2]);
    else if(args.length===2&&Array.isArray(args[1]))args[1]=hvElementChildren(args[1]);
    return nativeElement.apply(null,args);
  }
  Object.defineProperty(element,'__homensaiRawElement',{value:nativeElement});return element;
})(typeof L!=='undefined'&&L.dom&&typeof L.dom.create==='function'?L.dom.create.bind(L.dom):typeof globalThis!=='undefined'?globalThis.E:window.E);
