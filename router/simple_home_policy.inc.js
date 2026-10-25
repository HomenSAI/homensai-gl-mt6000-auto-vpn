/* Pure display policy. Callers must obtain evidence from the current router,
   not browser preferences or a queued command. No RPC or implicit acceptance. */
function simpleHomeEntry(evidence){
  var e=evidence&&typeof evidence==='object'?evidence:{};
  function result(page,reason){return {page:page,reason:reason,showCard:page==='home'};}
  if(e.termsAccepted!==true)return result('terms','TERMS-NOT-ACCEPTED');
  if(e.onboardingComplete!==true||e.setupComplete!==true||e.pairValid!==true||e.pairDeferred===true)return result('setup','SETUP-INCOMPLETE');
  if(e.testsPassed!==true||e.testsMatchCurrentPair!==true)return result('tests','CURRENT-PAIR-TESTS-REQUIRED');
  if(e.statusFresh!==true||e.controllerFresh!==true)return result('full','CURRENT-STATUS-REQUIRED');
  if(e.autoRunning!==true||e.commandPending===true||e.transitioning===true)return result('full','AUTO-NOT-CONFIRMED-RUNNING');
  if(e.activePathConfirmed!==true||['source','target'].indexOf(e.selectedRole)<0)return result('full','ACTIVE-CHANNEL-NOT-CONFIRMED');
  return result('home','AUTO-READY-RUNNING');
}
