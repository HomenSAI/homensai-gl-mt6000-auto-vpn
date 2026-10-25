/* Pure display policy. Callers must obtain evidence from the current router,
   not browser preferences or a queued command. No RPC or implicit acceptance. */
function simpleHomeEntry(evidence){
  var e=evidence&&typeof evidence==='object'?evidence:{};
  function result(page,reason){return {page:page,reason:reason,showCard:page==='home'};}
  if(e.statusFresh!==true||e.controllerFresh!==true)return result('full','CURRENT-STATUS-REQUIRED');
  // Display access follows actual enabled Auto, never the completion checkboxes.
  // Starting Auto remains guarded independently by the existing controller.
  if(e.autoRunning!==true)return result('full','AUTO-NOT-CONFIRMED-RUNNING');
  return result('home','AUTO-READY-RUNNING');
}
