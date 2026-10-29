"""Read-only, bounded pagination of persisted seven-day incident detail."""
import json
import time
from native_history import History,WEEK


def page(directory,arguments,now=None):
    if (set(arguments)!={'kind','after','until'} or arguments.get('kind') not in ('controller','failures','probe')
            or any(type(arguments.get(key)) is not int or not 0<=arguments[key]<2**53 for key in ('after','until'))):
        raise ValueError('STATISTICS-FIELDS')
    now=time.time() if now is None else now
    if arguments['kind']=='probe':
        from agent import read_json
        from probe_policy import history_page
        return history_page(directory,arguments,read_json,now)
    from retention_settings import configured_days
    detail_days=configured_days()
    if arguments['kind']=='controller':
        h=History(directory,detail_days=detail_days);data=h.load();h.migrate(data)
        events=data['events'];summary=h.public(data=data,now=now)
        summary.pop('events',None)
        saved=data.get('last_time');notice=None
    else:
        from agent import read_json,checksum
        from checkpoint_schema import validate
        from reliability import Reliability
        data=None;notice=None;saved=None
        for name in ('checkpoint.json','checkpoint.backup.json'):
            try:
                raw=read_json(directory/name)
                if raw is None:continue
                validate(raw)
                if raw.get('sha256')!=checksum(raw['data']):raise ValueError('STATISTICS-CHECKSUM')
                saved=raw['data']['saved'];data=raw['data']['accounting'].get('reliability')
                if name.endswith('backup.json'):notice='STORAGE-RECOVERED'
                break
            except (OSError,ValueError,KeyError,TypeError):notice='STORAGE-001'
        model=Reliability(data,detail_days=detail_days);model.prune(now);events=model.data['events'];summary=model.public();summary.pop('events',None)
    until=arguments['until'] or summary['sequence']
    if until>summary['sequence'] or arguments['after']>until:raise ValueError('STATISTICS-CURSOR')
    rows=[row for row in events if now-detail_days*86400<=row['time']<=now and arguments['after']<row['sequence']<=until]
    rows=rows[:101];selected=rows[:100]
    # Rich phase evidence can be large; enforce a byte bound without skipping rows.
    while len(selected)>1 and len(json.dumps(selected).encode())>96*1024:selected.pop()
    more=len(rows)>len(selected)
    return {'kind':arguments['kind'],'until':until,'events':selected,'next_after':selected[-1]['sequence'] if selected else arguments['after'],
            'has_more':more,'summary':summary,'detail_days':detail_days,'as_of':now,'checkpoint_saved':saved,
            'storage_notice':notice,'scope':'persisted observed events; missing intervals are unknown'}
