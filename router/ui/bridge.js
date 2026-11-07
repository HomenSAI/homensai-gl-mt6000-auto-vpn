/* Module top level of the approved page: build identity, the bridges the legacy logic and the help module call
   (code links open the code window of this page), the page itself and the LuCI view. */
var HV_AGENT='__UI_AGENT__',HV_STYLE='__HV_STYLE__',HV_STYLESHEET='__HV_STYLESHEET__';
var activeTab='statistics';  // the history list is refreshed every 60 s: the home view shows events
function pageKeyNow(){return '';}
function showErrorCode(code){if(HVX&&HVX.showCode)HVX.showCode(code);}
var HVX=(function(){
/*@UI@*/
return {boot:boot,showCode:showCode,render:render,paintLive:paintLive,
  // Test seam (router/tests/test_approved_ui.js): the pure builders and actions, driven without a browser.
  _test:{HV:HV,snap:function(){V=snap();return V;},overall:overall,autoIndicator:autoIndicator,autoDetail:autoDetail,headLampsHTML:headLampsHTML,render:render,autoState:autoState,reading:reading,VER:VER,brandHTML:brandHTML,toolsHTML:toolsHTML,footerHTML:footerHTML,
    homeA:homeA,settingsA:settingsA,tabs:{ch:tabCh,auto:tabAuto,srv:tabSrv,log:tabLog,sys:tabSys},wizard:wizard,pickLocale:pickLocale,toggleAuto:toggleAuto,stopAuto:stopAuto,switchTo:switchTo,
    checkNow:checkNow,speedTest:speedTest,faultTest:faultTest,saveSection:saveSection,wizardSave:wizardSave,onClick:onClick,onInput:onInput,codeHint:codeHint,termsModal:termsModal,eventsHTML:eventsHTML,draft:D,setLocale:function(l){locale=l;},
    ADV:ADV,advAt:advAt,advCardHTML:advCardHTML,advSectionBody:advSectionBody,advClick:advClick,advInput:advInput,advTour:advTour,advChart:advChart,
    XD:XD,xdU:xdU,wizardSkip:wizardSkip,wizardNeeded:wizardNeeded,buildLine:buildLine,recStatsHTML:recStatsHTML,sensorsHTML:sensorsHTML,sensorBanner:sensorBanner,keyAccept:keyAccept,tgShow:tgShow,manualRetry:manualRetry,manualFeedback:manualFeedback,manualOperation:function(){return MANUAL_SWITCH_OPERATION;},evKind:evKind,B:B,
    refreshNow:refreshNow,reloadInventory:reloadInventory,discardSection:discardSection,restoreMonitor:restoreMonitor,stopFault:stopFault,speedCancel:speedCancel,paintLive:paintLive,overall:overall,readingOf:readingOf,joinedProfile:joinedProfile,speedPauseNow:speedPauseNow,sensorWan:sensorWan,sensorKeys:sensorKeys,switchAllowed:switchAllowed,speedHTML:speedHTML,faultHTML:faultHTML,monitorExtra:monitorExtra,sensorsHTML:sensorsHTML,lastSwitch:lastSwitch,readinessHTML:readinessHTML,statsTiles:statsTiles}};
})();
return view.extend({
  handleSave:null,handleSaveApply:null,handleReset:null,
  load:function(){return Promise.all([loadInventory(0),statusCall().catch(function(){return {rpc_error:'RPC-UNAVAILABLE'};})]);},
  render:function(data){
    if(typeof document!=='undefined'&&document.head&&!document.querySelector('link[data-hvx-css]'))document.head.appendChild(E('link',{'rel':'stylesheet','data-hvx-css':'1','href':L.resource('view/homensai-vpn/'+HV_STYLESHEET)}));
    var root=E('div',{'class':'hvx','id':'hvx'});HVX.boot(root,data);return root;
  }
});
