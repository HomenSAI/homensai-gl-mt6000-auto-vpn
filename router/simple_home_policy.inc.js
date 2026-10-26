/* Display access is unconditional. Evidence describes what may be displayed;
   only the existing controller can authorize Start/Stop. No RPC or acceptance. */
function simpleHomeEntry(evidence){
  var e=evidence&&typeof evidence==='object'?evidence:{};
  var fresh=e.statusFresh===true&&e.controllerFresh===true;
  return {page:'home',showCard:true,
    reason:!fresh?'CURRENT-STATUS-REQUIRED':e.autoRunning===true?'AUTO-READY-RUNNING':'AUTO-NOT-CONFIRMED-RUNNING',
    statusFresh:e.statusFresh===true,controllerFresh:e.controllerFresh===true,
    autoRunning:fresh&&e.autoRunning===true};
}
