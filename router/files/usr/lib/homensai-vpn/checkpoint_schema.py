"""Validate retained accounting before trust or backup rotation; checksum is not schema."""
from datetime import date
import math,re


def timestamp(value):
    if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=253370764799:raise ValueError('CHECKPOINT-TIME')


def accounting(value,nested=False):
    if not isinstance(value,dict):raise ValueError('CHECKPOINT-ACCOUNTING')
    for key in ('months','days','quality','activity','retention'):
        if not isinstance(value.get(key,{}),dict):raise ValueError('CHECKPOINT-COLLECTION')
    if type(value.get('gaps',0)) is not int or value.get('gaps',0)<0:raise ValueError('CHECKPOINT-GAPS')
    for key,row in value.get('months',{}).items():
        if not re.fullmatch(r'[0-9]{4}-(?:0[1-9]|1[0-2])',key) or not isinstance(row,dict):raise ValueError('CHECKPOINT-MONTH')
    def day_rows(rows):
        for key,row in rows.items():
            if date.fromisoformat(key).isoformat()!=key or not isinstance(row,dict):raise ValueError('CHECKPOINT-DAY')
    day_rows(value.get('days',{}))
    for row in list(value.get('months',{}).values())+list(value.get('days',{}).values()):
        for key in ('rx','tx','seconds'):
            if type(row.get(key,0)) not in (int,float) or row.get(key,0)<0:raise ValueError('CHECKPOINT-COUNTER')
    for profile in value.get('quality',{}).values():
        if not isinstance(profile,dict) or not isinstance(profile.get('buckets',{}),dict):raise ValueError('CHECKPOINT-QUALITY')
        if profile.get('last') is not None and not isinstance(profile['last'],dict):raise ValueError('CHECKPOINT-LAST')
        for key,row in profile.get('buckets',{}).items():
            if not re.fullmatch('[0-9]{1,12}',key) or not isinstance(row,dict):raise ValueError('CHECKPOINT-BUCKET')
    for profile in value.get('activity',{}).values():
        if not isinstance(profile,dict) or not isinstance(profile.get('days',{}),dict):raise ValueError('CHECKPOINT-ACTIVITY')
        timestamp(profile.get('last_seen',0));day_rows(profile.get('days',{}))
    wan=value.get('wan')
    if 'reliability' in value:
        from reliability import Reliability
        Reliability(value['reliability'])
    if wan is not None:
        if nested:raise ValueError('CHECKPOINT-WAN-DEPTH')
        accounting(wan,True)


def validate(envelope):
    if not isinstance(envelope,dict) or not isinstance(envelope.get('data'),dict):raise ValueError('CHECKPOINT-ENVELOPE')
    data=envelope['data']
    if type(data.get('version')) is not int or data['version']!=1:raise ValueError('CHECKPOINT-VERSION')
    timestamp(data.get('saved'));accounting(data.get('accounting'))
    remaining=[200000]
    def walk(value,depth=0):
        remaining[0]-=1
        if remaining[0]<0 or depth>12:raise ValueError('CHECKPOINT-BOUNDS')
        if isinstance(value,dict):
            for key,item in value.items():
                if not isinstance(key,str) or len(key)>256:raise ValueError('CHECKPOINT-KEY')
                walk(item,depth+1)
        elif isinstance(value,list):
            if len(value)>10000:raise ValueError('CHECKPOINT-LIST')
            for item in value:walk(item,depth+1)
        elif type(value) in (int,float):
            if not math.isfinite(value) or value<0 or value>1e30:raise ValueError('CHECKPOINT-NUMBER')
        elif isinstance(value,str):
            if len(value)>4096:raise ValueError('CHECKPOINT-STRING')
        elif value is not None and type(value) is not bool:raise ValueError('CHECKPOINT-VALUE')
    walk(data)
    return data
