/* Every known diagnostic code anywhere on the page becomes a link to its row in the error table (name, meaning, how to fix). */
var errorLinkObserver=null,errorLinkTimer=null;
var ERROR_LINK_SKIP='a,button,script,style,textarea,input,select,option,.hv-errtable,.hv-ai-prompt,.hv-cmd,.hv-errlink';
function linkifyErrorCodes(root){
  if(!root||typeof ERROR_GROUP_OF==='undefined')return;
  var walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,null),nodes=[],node;
  while((node=walker.nextNode())){
    if(!node.nodeValue||node.nodeValue.length<5)continue;
    var parent=node.parentElement;if(!parent||parent.closest(ERROR_LINK_SKIP))continue;
    if(/[A-Z][A-Z0-9]{3,}/.test(node.nodeValue))nodes.push(node);
  }
  if(!nodes.length)return;
  if(errorLinkObserver)errorLinkObserver.disconnect();
  nodes.forEach(function(textNode){
    var text=textNode.nodeValue,pattern=/\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*\b/g,match,last=0,frag=document.createDocumentFragment(),changed=false;
    while((match=pattern.exec(text))){
      var code=match[0];
      if(code.length<5||!(Object.prototype.hasOwnProperty.call(ERROR_GROUP_OF,code)||(typeof errorFamilyOf==='function'&&errorFamilyOf(code))))continue;
      if(match.index>last)frag.appendChild(document.createTextNode(text.slice(last,match.index)));
      var link=document.createElement('a');link.href='#events';link.className='hv-errlink hv-errlink-inline';link.textContent=code;link.title=bi('Open the description of this code','Открыть описание этого кода');
      (function(c){link.addEventListener('click',function(ev){ev.preventDefault();showErrorCode(c);});})(code);
      frag.appendChild(link);last=match.index+code.length;changed=true;
    }
    if(!changed)return;
    if(last<text.length)frag.appendChild(document.createTextNode(text.slice(last)));
    textNode.parentNode.replaceChild(frag,textNode);
  });
  if(errorLinkObserver)errorLinkObserver.observe(root,{childList:true,subtree:true});
}
function installErrorLinks(root){
  if(!root||typeof MutationObserver==='undefined')return;
  if(errorLinkObserver)errorLinkObserver.disconnect();
  errorLinkObserver=new MutationObserver(function(){if(errorLinkTimer)clearTimeout(errorLinkTimer);errorLinkTimer=setTimeout(function(){linkifyErrorCodes(root);},120);});
  errorLinkObserver.observe(root,{childList:true,subtree:true});
  linkifyErrorCodes(root);
}
