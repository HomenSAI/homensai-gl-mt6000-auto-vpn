"""Reject own configuration edits while native recovery may still need the service."""
from agent import RUNTIME, read_json
from native_switch import journal_read, Refused


def pair_active():
    """The pair as the durable records say, fail-closed (review F-11, 06.11.2026).

    True while the pair intent is on or the saved pair session is not terminal (STARTING, RUNNING, STOPPING, HELD):
    a HELD session still owns interfaces and a guard until the owner's Start or Stop resolves it. Both records are
    read through the validated readers; an unreadable or invalid intent raises instead of counting as "off".
    """
    from pair_auto import intent, read_state, TERMINAL
    requested=intent()
    owned=read_state()
    if not isinstance(requested,dict) or not isinstance(owned,dict):raise ValueError('PAIR-STATE-UNVERIFIED')
    return requested.get('mode')=='on' or bool(owned) and owned.get('phase') not in TERMINAL


def blocked(settings):
    from speed_pause import public as pause_status
    if pause_status().get('active'):return 'SPEED-BUSY'
    try:
        if pair_active():return 'CONFIG-STOP-AUTO-FIRST'
    except (OSError,ValueError,TypeError,KeyError):return 'CONFIG-RECOVERY-UNVERIFIED'
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
