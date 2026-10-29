"""Average duration of a confirmed channel switch, kept on flash for the page countdown.

Manual and automatic switches use the same transaction, so one average serves both. One small write per
confirmed switch (rare); a failed or abandoned switch never changes it. Display only: no decision reads it.
"""
import json,math,os,time
from pathlib import Path

NAME='switch-timing.json'
WEIGHT=0.3  # recent switches matter more; a single slow one moves the average by 30%
LOW,HIGH=1,600


def read(persist):
    try:value=json.loads((Path(persist)/NAME).read_text(encoding='utf8'))
    except (OSError,ValueError):return None
    if (not isinstance(value,dict) or type(value.get('count')) is not int or value['count']<1
            or type(value.get('avg_seconds')) not in (int,float) or not LOW<=value['avg_seconds']<=HIGH):return None
    return {'avg_seconds':round(value['avg_seconds'],1),'count':value['count'],'last_seconds':value.get('last_seconds'),'updated':value.get('updated')}


def record(persist,seconds,now=None):
    """Fold one confirmed switch into the average. Never raises: timing must not affect switching."""
    try:
        if type(seconds) not in (int,float) or not math.isfinite(seconds) or not LOW<=seconds<=HIGH:return None
        current=read(persist)
        average=seconds if current is None else current['avg_seconds']*(1-WEIGHT)+seconds*WEIGHT
        value={'avg_seconds':round(average,2),'count':(current['count'] if current else 0)+1,'last_seconds':round(seconds,1),
               'updated':time.time() if now is None else now}
        path=Path(persist)/NAME;temporary=path.with_name(NAME+'.tmp')
        temporary.write_text(json.dumps(value),encoding='utf8');os.replace(temporary,path)
        return value
    except (OSError,ValueError,TypeError):return None
