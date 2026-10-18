(function(){
  try{localStorage.setItem('homensai-vpn-design',CFG.design);localStorage.setItem('homensai-vpn-theme',CFG.theme);}catch(e){}
  var f=document.getElementById('f'),errors=[];
  f.src='/?lang='+CFG.lang+'#'+CFG.tab;
  function lum(c){var a=c.map(function(v){v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);});return 0.2126*a[0]+0.7152*a[1]+0.0722*a[2];}
  function parse(s){
    var m=/^rgba?\(([^)]+)\)$/.exec(s);if(m){var p=m[1].split(/[ ,\/]+/).filter(Boolean).map(parseFloat);return [p[0],p[1],p[2],p.length>3?p[3]:1];}
    m=/^color\(srgb ([^)]+)\)$/.exec(s);if(m){var q=m[1].split(/[ \/]+/).filter(Boolean).map(parseFloat);return [q[0]*255,q[1]*255,q[2]*255,q.length>3?q[3]:1];}
    return null;
  }
  function blend(top,bot){var a=top[3];return [top[0]*a+bot[0]*(1-a),top[1]*a+bot[1]*(1-a),top[2]*a+bot[2]*(1-a),1];}
  function bgOf(el,win){
    var stack=[];for(var n=el;n&&n.nodeType===1;n=n.parentElement){var c=parse(win.getComputedStyle(n).backgroundColor);if(c&&c[3]>0){stack.push(c);if(c[3]>=0.99)break;}}
    var base=parse(win.getComputedStyle(win.document.body).backgroundColor);if(!base||base[3]<0.99)base=CFG.theme==='dark'?[20,20,20,1]:[255,255,255,1];
    var cur=stack.length&&stack[stack.length-1][3]>=0.99?stack.pop():base;
    while(stack.length)cur=blend(stack.pop(),cur);return cur;
  }
  function desc(el){return el.tagName.toLowerCase()+(el.className&&typeof el.className==='string'?'.'+el.className.trim().split(/\s+/).slice(0,2).join('.'):'')+' "'+(el.textContent||'').trim().slice(0,30)+'"';}
  function scrollParent(el,root){for(var n=el.parentElement;n&&n!==root;n=n.parentElement){var o=n.ownerDocument.defaultView.getComputedStyle(n).overflowX;if(o==='auto'||o==='scroll'||o==='hidden')return true;}return false;}
  function analyse(){
    var w=f.contentWindow,d=w.document,vw=w.innerWidth,de=d.documentElement,out={vw:vw,errors:errors};
    var root=d.querySelector('.hv-app');
    out.hasApp=!!root;if(!root){out.fatal='NO-APP: '+(d.body.textContent||'').slice(0,120);return out;}
    out.design=root.getAttribute('data-hv-design');out.active=root.getAttribute('data-hv-active');
    out.docOverflow=de.scrollWidth-vw;
    var off=[];root.querySelectorAll('*').forEach(function(el){
      if(el.closest('svg')&&el.tagName.toLowerCase()!=='svg')return;
      var r=el.getBoundingClientRect();if(!r.width||!r.height)return;var cs=w.getComputedStyle(el);if(cs.display==='none'||cs.visibility==='hidden'||cs.position==='fixed')return;
      if(r.right>vw+1&&!scrollParent(el,root))off.push(desc(el)+' right='+Math.round(r.right));});
    out.offenders=off.slice(0,6);var firstEl=null;root.querySelectorAll('*').forEach(function(el){if(firstEl)return;var r=el.getBoundingClientRect();if(r.width&&r.height&&r.right>vw+1&&w.getComputedStyle(el).position!=='fixed'&&!scrollParent(el,root))firstEl=el;});if(firstEl){var ch=[];for(var n=firstEl;n&&n!==d.body&&ch.length<12;n=n.parentElement){var cs2=w.getComputedStyle(n);ch.push(n.tagName.toLowerCase()+'.'+String(n.className||'').split(' ')[0]+' w='+Math.round(n.getBoundingClientRect().width)+' ox='+cs2.overflowX+' d='+cs2.display+' minw='+cs2.minWidth);}out.chain=ch;}out.offenderCount=off.length;
    var visible=function(sel){var e=d.querySelector(sel);if(!e)return false;var r=e.getBoundingClientRect();return r.width>0&&r.height>0&&w.getComputedStyle(e).visibility!=='hidden'&&w.getComputedStyle(e).display!=='none';};
    out.attribution=visible('.hv-attribution');out.footer=visible('.hv-brand-footer');out.badge=visible('.hv-version');
    out.designError=/DESIGN-VIEW-ERROR/.test(d.body.textContent||'');
    out.pageVisible=!!d.querySelector('[data-hv-page]:not([hidden])');
    out.dv=!!d.querySelector('[data-hv-page="overview"][data-hv-dv]');
    out.title=(d.querySelector('.hv-page-header h1')||{}).textContent||'';
    var low=[],warn=0,checked=0;
    var walker=d.createTreeWalker(root,NodeFilter.SHOW_TEXT);var seen=new Set();
    while(walker.nextNode()){
      var tn=walker.currentNode,el=tn.parentElement;if(!el||seen.has(el)||!/\S/.test(tn.textContent))continue;seen.add(el);
      if(el.closest('option,script,style,svg,[hidden],.hv-visually-hidden,.hv-sr'))continue;
      var r=el.getBoundingClientRect();if(r.width<3||r.height<3)continue;var cs=w.getComputedStyle(el);
      if(cs.visibility==='hidden'||cs.display==='none'||parseFloat(cs.opacity)===0)continue;
      var fg=parse(cs.color);if(!fg)continue;var bg=bgOf(el,w);if(fg[3]<1)fg=blend(fg,bg);
      var l1=lum(fg),l2=lum(bg),ratio=(Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05);checked++;
      var size=parseFloat(cs.fontSize),bold=parseInt(cs.fontWeight,10)>=700,large=size>=24||(size>=18.66&&bold);
      var need=large?3:4.5;
      if(ratio<3)low.push({t:(tn.textContent||'').trim().slice(0,34),r:+ratio.toFixed(2),c:desc(el).split(' "')[0]});else if(ratio<need)warn++;
    }
    out.lowContrast=low.slice(0,10);out.lowCount=low.length;out.warnCount=warn;out.checked=checked;
    var clip=[];root.querySelectorAll('h1,h2,h3,h4,b,strong,button,a,label,td,th,span,p').forEach(function(el){
      var cs=w.getComputedStyle(el);if(cs.display==='none'||cs.visibility==='hidden')return;
      if((cs.overflow==='hidden'||cs.textOverflow==='ellipsis')&&el.scrollWidth>el.clientWidth+2&&el.clientWidth>0)clip.push(desc(el));});
    out.clipped=clip.slice(0,5);
    return out;
  }
  window.addEventListener('error',function(e){errors.push(String(e.message).slice(0,120));});
  f.onload=function(){
    try{f.contentWindow.addEventListener('error',function(e){errors.push('app: '+String(e.message).slice(0,120));});}catch(e){}
    var t0=Date.now();(function wait(){var ready=false;try{var w=f.contentWindow,rt=w.document.querySelector('.hv-app');ready=!!rt&&!!w.getComputedStyle(rt).getPropertyValue('--dv-line').trim()&&!!w.document.querySelector('.hv-attribution');}catch(e){}if(!ready&&Date.now()-t0<30000){setTimeout(wait,500);return;}setTimeout(function(){var r;try{r=analyse();r.waitMs=Date.now()-t0;}catch(e){r={fatal:'ANALYSE '+e.message};}fetch('/__result/'+CFG.id,{method:'POST',body:JSON.stringify(r)});},1500);})();
  };
})();
