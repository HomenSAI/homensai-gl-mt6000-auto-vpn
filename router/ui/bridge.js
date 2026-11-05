/* Module top level of the approved page: build identity, the bridges the legacy logic and the help module call
   (code links open the code window of this page), the page itself and the LuCI view. */
var HV_BUILD='__UI_BUILD__',HV_AGENT='__UI_AGENT__',HV_STYLE='__HV_STYLE__',HV_STYLESHEET='__HV_STYLESHEET__';
var activeTab='statistics';  // the history list is refreshed every 60 s: the home view shows events
function pageKeyNow(){return '';}
function showErrorCode(code){if(HVX&&HVX.showCode)HVX.showCode(code);}
var HVX=(function(){
/*@UI@*/
return {boot:boot,showCode:showCode,render:render,paintLive:paintLive,
  // Test seam (router/tests/test_approved_ui.js): the pure builders and actions, driven without a browser.
  _test:{HV:HV,snap:function(){V=snap();return V;},overall:overall,autoState:autoState,reading:reading,VER:VER,brandHTML:brandHTML,toolsHTML:toolsHTML,footerHTML:footerHTML,
    homeA:homeA,settingsA:settingsA,tabs:{ch:tabCh,auto:tabAuto,srv:tabSrv,log:tabLog,sys:tabSys},wizard:wizard,pickLocale:pickLocale,toggleAuto:toggleAuto,stopAuto:stopAuto,switchTo:switchTo,
    checkNow:checkNow,speedTest:speedTest,faultTest:faultTest,saveSection:saveSection,wizardSave:wizardSave,onClick:onClick,termsModal:termsModal,eventsHTML:eventsHTML,draft:D,setLocale:function(l){locale=l;}}};
})();
return view.extend({
  handleSave:null,handleSaveApply:null,handleReset:null,
  load:function(){return Promise.all([loadInventory(0),statusCall().catch(function(){return {rpc_error:'RPC-UNAVAILABLE'};})]);},
  render:function(data){
    if(typeof document!=='undefined'&&document.head&&!document.querySelector('link[data-hvx-css]'))document.head.appendChild(E('link',{'rel':'stylesheet','data-hvx-css':'1','href':L.resource('view/homensai-vpn/'+HV_STYLESHEET)}));
    var root=E('div',{'class':'hvx','id':'hvx'});HVX.boot(root,data);return root;
  }
});
