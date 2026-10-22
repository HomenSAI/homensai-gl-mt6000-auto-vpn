"""Reject own configuration edits while native recovery may still need the service."""
from agent import RUNTIME, read_json
from native_switch import journal_read, Refused


def blocked(settings):
    from pair_auto import public_intent
    if public_intent():return 'CONFIG-STOP-AUTO-FIRST'
    try:
        journal=journal_read()
        state=read_json(RUNTIME/'native-status.json',{})
        intent=read_json(RUNTIME/'auto-control.json',{})
    except (Refused,OSError,ValueError,TypeError):return 'CONFIG-RECOVERY-UNVERIFIED'
    if any(not isinstance(value,dict) for value in (settings,journal,state,intent)):
        return 'CONFIG-RECOVERY-UNVERIFIED'
    if (settings.get('native_enabled') in (True,'1') or intent.get('mode')=='on'
            or (journal and journal.get('phase')!='ROLLED-BACK')
            or state.get('guard')=='closed' or state.get('state') in
               ('DEGRADED-ON-RESERVE','OBSERVING','ARMED','APPLYING','WAIT-CLIENT','COMMITTED','RESTORING','STOPPED-ON-RESERVE')):
        return 'CONFIG-STOP-AUTO-FIRST'
    return None
