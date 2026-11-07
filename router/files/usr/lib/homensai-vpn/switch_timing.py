"""Average duration of a confirmed channel switch, kept on flash for the page countdown.

Manual and automatic switches use the same transaction, so one average serves both. One small write per
confirmed switch (rare); a failed or abandoned switch never changes it. Display only: no decision reads it.
"""
import json,math,os,time
from pathlib import Path

NAME='switch-timing.json'
WEIGHT=0.3  # recent switches matter more; a single slow one moves the average by 30%
HIGH=600  # seconds; the lower bound is exclusive zero (sub-second switches are real, review F-51)


def valid_seconds(value):
    """A switch duration or average: a finite number with 0 < value <= HIGH. Fast swaps finish below one second (F-51)."""
    return type(value) in (int,float) and math.isfinite(value) and 0<value<=HIGH


def display(value):
    """Milliseconds for the page only, half up exactly like the Lua twin (math.floor(x*1000+0.5)/1000)."""
    return math.floor(value*1000+.5)/1000


def load(persist):
    """The stored state with its unrounded accumulator, or None when absent or damaged."""
    try:value=json.loads((Path(persist)/NAME).read_text(encoding='utf8'))
    except (OSError,ValueError):return None
    if (not isinstance(value,dict) or type(value.get('count')) is not int or value['count']<1
            or not valid_seconds(value.get('avg_seconds'))):return None
    return value


def read(persist):
    value=load(persist)
    if value is None:return None
    return {'avg_seconds':display(value['avg_seconds']),'count':value['count'],'last_seconds':value.get('last_seconds'),'updated':value.get('updated')}


def write_durable(path,raw):
    """Power-cut safe replace (as agent.atomic_json): unique temporary file, fsync, rename, fsync of the directory."""
    import tempfile
    fd,pending=tempfile.mkstemp(dir=str(path.parent),prefix='.'+path.name+'.',suffix='.pending')
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(pending,str(path))
    except BaseException:
        try:os.unlink(pending)
        except OSError:pass
        raise
    directory=os.open(str(path.parent),os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(directory)
    finally:os.close(directory)


def record(persist,seconds,now=None):
    """Fold one confirmed switch into the average. Never raises: timing must not affect switching."""
    try:
        if not valid_seconds(seconds):return None
        current=load(persist)
        # Exponential average on the unrounded accumulator: A1 = s1, An = 0.7*A(n-1) + 0.3*sn. Rounding happens only in
        # read() for the page; a rounded value fed back would bias every later average (review F-52).
        average=float(seconds) if current is None else current['avg_seconds']*0.7+seconds*WEIGHT
        value={'avg_seconds':average,'count':(current['count'] if current else 0)+1,'last_seconds':float(seconds),
               'updated':time.time() if now is None else now}
        write_durable(Path(persist)/NAME,json.dumps(value).encode('utf8'))
        return value
    except (OSError,ValueError,TypeError):return None
