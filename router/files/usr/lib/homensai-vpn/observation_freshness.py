"""One health-observation age contract; kernel and response clocks stay separate."""
import re

LEGACY_VALID_FOR=90


def valid_for(settings=None):
    """Validated configured scan interval, matching native diagnostic limits."""
    value=settings.get('interval') if isinstance(settings,dict) else None
    if isinstance(value,str) and re.fullmatch(r'[0-9]{1,3}',value):value=int(value)
    if type(value) is not int or not 10<=value<=300:return LEGACY_VALID_FOR
    return max(30,min(900,value*3))


def cached(status):
    value=status.get('observation_valid_for') if isinstance(status,dict) else None
    return value if type(value) is int and 30<=value<=900 else LEGACY_VALID_FOR


# Owner decision 01.11.2026 (variant B): the vendor settle period follows the firmware, not the probe level.
# Two-thirds of the observation validity gave 120 s at probe level 1 (MT3000 soaks: every tunnel rebuild
# blocked Auto for 119-139 s) while the GL rebuild chain (fw3 reload, dnsmasq restarts) finishes in 20-33 s.
# The settle period is now at most SETTLE_MAX; the two equal observations (stable_samples) and the separate
# VENDOR-WORKER-BUSY quiet check stay. Lua: pair.settle_for.
SETTLE_MAX=45


def settle_for(settings=None):
    """Vendor stability period: two-thirds of the observation validity, 30..SETTLE_MAX seconds."""
    return max(30,min(SETTLE_MAX,valid_for(settings)*2//3))


def attach(status,settings=None):
    """Annotate existing observations without changing their measurement time."""
    age=valid_for(settings) if settings is not None else cached(status)
    status['observation_valid_for']=age
    rows=status.get('profiles',[])
    for row in rows if isinstance(rows,list) else []:
        if isinstance(row,dict):row['observation_valid_for']=age
    return status
