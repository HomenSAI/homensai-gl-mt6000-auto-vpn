"""HomenS.AI VPN · © 2026 Serhii Khomenko · https://homensai.com/
What one monitor pass measures and when (study wave 3 no. 5, WAVE3-PRODUCT-2026-11-04.ru.md). Pure, no I/O.

The product has one pass per interval T, and both Auto channels start in it at the same instant (2 workers): the study's
"both passes together". Three decisions:

Absolute grid (option probe_spread): the next pass is planned from the previous SLOT + T, not from the end of a pass, so
timer lateness does not add up. A pass an event started early (dense, scan, new settings) moves the grid to itself.

Phases (option probe_spread, default on): the i-th measurement of a pass starts i*min(T/K, SPREAD_CAP) s after it. The
carrying primary is measured LAST, right before the status is published, so its evidence is exactly as fresh as before
and its period is still T; only the idle reserve's evidence is older, by far less than valid_for. SPREAD_CAP: a pass is one
blocking job (Python) and a health check takes about a second, so T/K beyond it would only delay what the pass publishes.

Reserve budget (option reserve_probe_interval, seconds, 0 = off = default): while the primary carries and everything is
clean the idle reserve is measured every R s instead of every pass (square-root law). Never in a dense episode, a boost,
a firmware wait, a failed or suspected channel, a changed identity or outside OBSERVING: the reserve is then measured in
the very next pass (the out-of-turn probe). The evidence contract stays: R is cut to valid_for - T, so the row and the
streak of the reserve never go stale for any reader (resolve_pair, manual buttons, accounting). At T=10 that means
20 s, not 60 s: see the document for what 60 s would have to change.
Lua twin: lua/probe_plan.lua (tests/probe_plan_cases.json)."""

SPREAD_CAP=3.0
SLOT_TOLERANCE=1.5   # a pass this far from its slot was started by an event: the grid moves to it
RESERVE_RANGE=(20,120)
SLACK=2.0            # pass lateness that must not turn "every second pass" into "every pass"


def spread_enabled(settings):
    return isinstance(settings,dict) and settings.get('probe_spread') is not False


def reserve_interval(settings):
    """The configured R, or 0 (off): out-of-range and malformed values are off, never a guess."""
    value=settings.get('reserve_probe_interval') if isinstance(settings,dict) else None
    if isinstance(value,str) and value.isdigit():value=int(value)
    if type(value) is not int or not RESERVE_RANGE[0]<=value<=RESERVE_RANGE[1]:return 0
    return value


def effective_reserve(settings,interval,valid_for):
    """R cut to the evidence contract: the row is at most valid_for old at any reader. 0 = measure every pass."""
    wanted=reserve_interval(settings)
    if wanted<=0:return 0
    limit=min(wanted,valid_for-interval)
    return limit if limit>interval else 0


def begin_slot(expected,now):
    """The slot of the pass that starts now: the planned one, or now when an event moved it."""
    if expected is None or abs(now-expected)>SLOT_TOLERANCE:return now
    return expected


def next_slot(slot,interval,now):
    """(slot of the next pass, seconds until it). Never overlaps a pass: at least 1 s; a late pass restarts the grid."""
    planned=slot+interval
    if planned-now<1:return now+1,1
    return planned,planned-now


def idle(context):
    """True while the primary carries, both channels are clean and nothing is being confirmed."""
    source=context.get('source');target=context.get('target')
    return (source is not None and target is not None and source!=target and context.get('native')=='OBSERVING'
            and context.get('source_clean') is True and context.get('target_clean') is True
            and not context.get('dense') and not context.get('boost') and not context.get('waiting'))


def clean(row):
    """A channel with nothing to confirm: last check healthy, vendor settled, no suspicion of the failure model."""
    if not isinstance(row,dict) or row.get('code') is not None or row.get('dns_ok') is not True:return False
    https=row.get('https_success')
    if type(https) is not int or https<2 or row.get('vendor_state')!='SETTLED':return False
    model=row.get('failure_model')
    return not (isinstance(model,dict) and (model.get('suspect') is True or model.get('failed') is True))


def carried(row,observation):
    """The reserve's last measured row for a pass that skipped it, or None when its tunnel moved since: a success is never
    attached to another generation (the pass then reports it unmeasured and the next pass measures it)."""
    groups=observation.get('groups') if isinstance(observation,dict) else None
    if not isinstance(row,dict) or not isinstance(groups,list) or row.get('vendor_state')!='SETTLED':return None
    for group in groups:
        if isinstance(group,dict) and group.get('id')==row.get('vendor_tunnel_id'):
            same=(group.get('state')=='SETTLED' and group.get('current_profile')==row.get('id')
                  and group.get('generation') is not None and group.get('generation')==row.get('vendor_generation')
                  and group.get('changed_at')==row.get('vendor_changed_at'))
            return row if same else None
    return None


def plan(ids,context,settings):
    """-> {'skip': ids not measured in this pass, 'order': ids in start order, 'offsets': seconds per position of 'order'}.
    ids: this pass's bound profile ids in their order. context: interval, valid_for, now, source, target, native, dense,
    boost, waiting, source_clean, target_clean, reserve_time (when the reserve was last measured, None unknown)."""
    interval=context['interval'];now=context['now']
    is_idle=idle(context);source=context.get('source');target=context.get('target')
    skip=[]
    if is_idle and target in ids:
        every=effective_reserve(settings,interval,context['valid_for'])
        stamp=context.get('reserve_time')
        if every and stamp is not None and 0<=now-stamp and now-stamp+interval<=every+SLACK:skip=[target]
    every_id=list(ids)
    if is_idle and source in every_id and len(every_id)>1:every_id=[x for x in every_id if x!=source]+[source]
    step=0.0
    if spread_enabled(settings) and is_idle and len(every_id)>1:step=min(float(interval)/len(every_id),SPREAD_CAP)
    # A skipped channel keeps its phase empty: the primary stays on one phase and its period stays exactly T.
    kept=[(x,index*step) for index,x in enumerate(every_id) if x not in skip]
    return {'skip':skip,'order':[x for x,_ in kept],'offsets':[offset for _,offset in kept]}
