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


def settle_for(settings=None):
    """Use the same validated scan cadence for vendor stability evidence."""
    return max(30,min(600,valid_for(settings)*2//3))


def attach(status,settings=None):
    """Annotate existing observations without changing their measurement time."""
    age=valid_for(settings) if settings is not None else cached(status)
    status['observation_valid_for']=age
    rows=status.get('profiles',[])
    for row in rows if isinstance(rows,list) else []:
        if isinstance(row,dict):row['observation_valid_for']=age
    return status
