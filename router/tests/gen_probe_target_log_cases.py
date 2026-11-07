"""Generate router/tests/probe_target_log_cases.json: the shared cases of the per-target probe log
(docs/architecture/PER-TARGET-PROBE-LOG-2026-11-04.ru.md).

The expected values come from the Python module probe_target_log.py; test_probe_target_log.py checks that the file is
current AND states the meaning of the important cases by hand; tests/lua/test_probe_target_log.lua replays every case
against the Lua twin (lua/probe_target_log.lua): byte-identical lines, the same parsing, the same ring.
Run: python router/tests/gen_probe_target_log_cases.py
"""
import json
import random
import sys
import tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
import probe_target_log as P  # noqa: E402

OUT=HERE/'probe_target_log_cases.json'
SEED=20261104
T0=1762243200


def check(target,result='ok',ms=None,**extra):
    detail={'target':target,'result':result}
    if ms is not None:detail['elapsed_ms']=ms
    detail.update(extra)
    return detail


def healthy(identifier='wireguard:peer_7',time=T0+0.4,**extra):
    row={'id':identifier,'time':time,'code':None,'dns_ok':True,'https_success':3,
         'probe_checks':[check('one.one.one.one','ok',143.5,http_status=200),check('dns.google','ok',61.2,http_status=200),
                         check('dns.quad9.net','ok',88.0,http_status=200)]}
    row.update(extra)
    return row


def encode_cases():
    named=[
        ('healthy channel',5,healthy(),False,None),
        ('dense pass',6,healthy(),True,None),
        ('heartbeat counters',7,healthy(),False,[10,0,10,1,0,0,0,0]),
        ('heartbeat all targets and others',8,healthy(),False,[4,1,4,0,3,3,2,2]),
        ('heartbeat without a sent echo is no data',9,healthy(),False,[0,0,0,0,0,0,0,0]),
        ('heartbeat of the wrong length',10,healthy(),False,[1,0,1,0]),
        ('heartbeat with a negative counter',11,healthy(),False,[1,0,1,-1,0,0,0,0]),
        ('heartbeat with a float counter',12,healthy(),False,[1,0,1,0.5,0,0,0,0]),
        ('heartbeat counter over the limit',13,healthy(),False,[65536,0,1,0,0,0,0,0]),
        ('heartbeat at the limit',14,healthy(),False,[65535,65535,0,0,0,0,0,0]),
        ('heartbeat is not a list',15,healthy(),False,'10,0'),
        ('one https target timed out',16,healthy(probe_checks=[check('one.one.one.one','ok',140.0),check('dns.google','timeout',3001.0),
                                                           check('dns.quad9.net','ok',90.0)]),False,None),
        ('two targets failed: VPN-003',17,healthy(code='VPN-003',https_success=1,probe_checks=[
            check('one.one.one.one','transport-error',12.3),check('dns.google','timeout',3000.4),check('dns.quad9.net','ok',70.0)]),False,None),
        ('dns failed: DNS-001',18,healthy(code='DNS-001',dns_ok=False),False,None),
        ('dns not measured',19,healthy(dns_ok=None),False,None),
        ('dns as a number is not a verdict',20,healthy(dns_ok=1),False,None),
        ('tunnel missing: no checks at all',21,{'id':'wireguard:peer_8','time':T0+1.0,'code':'VPN-001'},False,None),
        ('probe checks removed after an identity change',22,{'id':'wireguard:peer_8','time':T0+1.0,'code':'VENDOR-IDENTITY-CHANGED'},False,None),
        ('black hole VPN-MTU',23,healthy(code='VPN-MTU'),False,None),
        ('system error',24,{'id':'openvpn:1_2','time':T0+1.0,'code':'SYSTEM-001'},False,None),
        ('route and check codes',25,healthy(code='ROUTE-001'),False,None),
        ('check code',26,healthy(code='CHECK-001'),False,None),
        ('another code is verdict 9',27,healthy(code='PROFILE-INACTIVE'),False,None),
        ('an empty code is verdict 9',28,healthy(code=''),False,None),
        ('a numeric code is verdict 9',29,healthy(code=7),False,None),
        ('portal redirect marks the answer',30,healthy(code='VPN-003',probe_checks=[
            check('one.one.one.one','http-error',30.0,http_status=302,trust='portal-redirect'),
            check('dns.google','http-error',31.0,http_status=302,trust='portal-redirect'),
            check('dns.quad9.net','http-error',29.0,http_status=302,trust='portal-redirect')]),False,None),
        ('foreign certificate',31,healthy(code='VPN-003',probe_checks=[
            check('one.one.one.one','tls-error',44.0,trust='untrusted-certificate'),check('dns.google','tls-error',45.0),
            check('dns.quad9.net','tls-error',46.0,trust='untrusted-certificate')]),False,None),
        ('replayed trace',32,healthy(probe_checks=[check('one.one.one.one','invalid-response',50.0,trust='stale-response'),
                                                   check('dns.google','ok',61.0),check('dns.quad9.net','ok',88.0)]),False,None),
        ('unknown trust text is no mark',33,healthy(probe_checks=[check('one.one.one.one','ok',50.0,trust='made-up'),
                                                                 check('dns.google','ok',61.0),check('dns.quad9.net','ok',88.0)]),False,None),
        ('every result text',34,healthy(probe_checks=[check('one.one.one.one','http-unsupported',9.0),check('dns.google','invalid-response',9.0),
                                                      check('dns.quad9.net','unknown',9.0)]),False,None),
        ('an unlisted result text is unknown (7)',35,healthy(probe_checks=[check('one.one.one.one','brand-new',9.0),
                                                                          check('dns.google','ok',9.0),check('dns.quad9.net','ok',9.0)]),False,None),
        ('a result that is not a string is unknown (7)',36,healthy(probe_checks=[check('one.one.one.one',['ok'],9.0),
                                                                                check('dns.google','ok',9.0),check('dns.quad9.net','ok',9.0)]),False,None),
        ('a check without a result is unknown (7)',37,healthy(probe_checks=[{'target':'one.one.one.one','elapsed_ms':5.0},
                                                                           check('dns.google','ok',9.0),check('dns.quad9.net','ok',9.0)]),False,None),
        ('only one target reported',38,healthy(probe_checks=[check('dns.google','ok',61.0)]),False,None),
        ('no checks list',39,healthy(probe_checks=None),False,None),
        ('empty checks list',40,healthy(probe_checks=[]),False,None),
        ('checks is not a list',41,healthy(probe_checks={'target':'dns.google'}),False,None),
        ('an unknown target and junk entries are ignored',42,healthy(probe_checks=[check('example.org','ok',1.0),'x',7,None,
                                                                                 check('dns.google','ok',61.0)]),False,None),
        ('a repeated target: the last one counts',43,healthy(probe_checks=[check('dns.google','timeout',3000.0),check('dns.google','ok',61.0)]),False,None),
        ('rounding 142.5 up',44,healthy(probe_checks=[check('one.one.one.one','ok',142.5),check('dns.google','ok',0.49),check('dns.quad9.net','ok',0.5)]),False,None),
        ('latency clamps',45,healthy(probe_checks=[check('one.one.one.one','timeout',999999.9),check('dns.google','ok',-3.2),
                                                 check('dns.quad9.net','ok',600000.4)]),False,None),
        ('latency as an integer',46,healthy(probe_checks=[check('one.one.one.one','ok',143),check('dns.google','ok',0),check('dns.quad9.net','ok',7)]),False,None),
        ('latency that is text or a boolean is none',47,healthy(probe_checks=[check('one.one.one.one','ok','143'),check('dns.google','ok',True),
                                                                             check('dns.quad9.net','ok',None)]),False,None),
        ('whole second of the time is cut, not rounded',48,healthy(time=T0+0.999),False,None),
        ('time as an integer',49,healthy(time=T0),False,None),
        ('no time: the pass time is used',50,healthy(time=None),False,None),
        ('a time that is text: the pass time is used',51,healthy(time='x'),False,None),
        ('negative time and no pass time: no line',52,healthy(time=-1.0),False,None),
        ('time beyond twelve digits: no line',53,healthy(time=1e12),False,None),
        ('openvpn profile',54,healthy(identifier='openvpn:1_2'),False,None),
        ('id with a space: no line',55,healthy(identifier='wireguard:peer 7'),False,None),
        ('id with a quote: no line',56,healthy(identifier='wireguard:"x"'),False,None),
        ('empty id: no line',57,healthy(identifier=''),False,None),
        ('id of 65 characters: no line',58,healthy(identifier='a'*65),False,None),
        ('id of 64 characters',59,healthy(identifier='a'*64),False,None),
        ('id that is not a string: no line',60,healthy(identifier=7),False,None),
        ('no id: no line',61,{'time':T0},False,None),
        ('a result that is not an object: no line',62,'x',False,None),
        ('a big sequence number',63,healthy(),False,None),
    ]
    cases=[]
    for name,seq,row,dense,hb in named:
        case={'name':name,'seq':seq,'result':row,'dense':dense,'hb':hb,'now':T0+9.0}
        if name=='a big sequence number':case['seq']=123456789012345
        if name=='negative time and no pass time: no line':case['now']=None
        if name=='a time that is text: the pass time is used':case['now']=T0+9.9
        if name=='no time: the pass time is used':case['now']=T0+9.5
        cases.append(case)
    rng=random.Random(SEED)
    texts=['ok','ok','ok','ok','timeout','tls-error','invalid-response','transport-error','http-error','http-unsupported','unknown','weird']
    for index in range(300):
        checks=[]
        for target in P.TARGETS:
            if rng.random()<0.1:continue
            extra={}
            if rng.random()<0.1:extra['trust']=rng.choice(list(P.TRUST_REASONS)+['other'])
            ms=rng.choice([None,rng.randint(0,5000),round(rng.uniform(0,4000),1),round(rng.uniform(0,700000),1)])
            checks.append(check(target,rng.choice(texts),ms,**extra))
        rng.shuffle(checks)
        row={'id':rng.choice(['wireguard:peer_7','wireguard:peer_8','openvpn:1_2','wireguard:peer_%d'%rng.randint(0,99)]),
             'time':rng.choice([T0+rng.random()*1000,T0+rng.randint(0,1000)]),
             'code':rng.choice([None,None,None,'DNS-001','VPN-003','VPN-001','VPN-MTU','SYSTEM-001','X-1']),
             'dns_ok':rng.choice([True,True,False,None]),'probe_checks':checks}
        hb=rng.choice([None,[rng.randint(0,12) for _ in range(8)],[rng.randint(0,3) for _ in range(8)]])
        cases.append({'name':'random %d'%index,'seq':rng.randint(1,10**6),'result':row,'dense':rng.random()<0.3,'hb':hb,'now':T0+5.0})
    for case in cases:
        case['expected']=P.encode(case['seq'],case['result'],case['dense'],case['hb'],case['now'])
    return cases


def parse_cases():
    good=[P.encode(i,healthy(time=T0+i),i%2==0,[3,0,3,1,3,0,0,0] if i%3==0 else None) for i in range(1,7)]
    lines=[l.rstrip('\n') for l in good]
    lines+=[
        '','x','[]','[1]',lines[0]+' ',' '+lines[0],lines[0]+',',lines[0][:-1],lines[0][:-2],lines[0].replace('"wireguard:peer_7"','"wireguard:peer 7"'),
        lines[0].replace('"wireguard:peer_7"','wireguard:peer_7'),lines[0].replace('[0,144,0,61,0,88]','[0,144,0,61,0]'),
        lines[0].replace('[0,144,0,61,0,88]','[0,144,0,61,0,88,0]'),lines[0].replace('[0,144,0,61,0,88]','[0,1.5,0,61,0,88]'),
        lines[0].replace('[0,144,0,61,0,88]','[0,1234567,0,61,0,88]'),lines[0].replace('[0,144,0,61,0,88]','[0,-1,0,-123456,0,88]'),
        lines[0].replace('[0,144,0,61,0,88]','[0,-1234567,0,61,0,88]'),lines[0].replace('[0,144,0,61,0,88]','[100,144,0,61,0,88]'),
        lines[0].replace('[0,144,0,61,0,88]','[0,-,0,61,0,88]'),
        lines[2],lines[2].replace(',[3,0,3,1,3,0,0,0]]',',[3,0,3,1,3,0,0]]'),lines[2].replace(',[3,0,3,1,3,0,0,0]]',',[3,0,3,1,3,0,0,0,0]]'),
        lines[2].replace(',[3,0,3,1,3,0,0,0]]',',[3,0,3,1,3,0,0,100000]]'),lines[2].replace(',[3,0,3,1,3,0,0,0]]',',[3,0,3,1,3,0,0,99999]]'),
        lines[2].replace(',[3,0,3,1,3,0,0,0]]',',[3,0,3,1,3,0,0,-1]]'),
        '[1,2,"a",0,0,[0,1,0,1,0,1],0,[]]','[1,2,"a",0,0,[0,1,0,1,0,1],0,[]]]','[01,2,"a",0,0,[0,1,0,1,0,1],0,[]]',
        '[1,2,"a",100,0,[0,1,0,1,0,1],0,[]]','[1,2,"a",99,999,[99,1,99,1,99,1],99,[]]','[1,2,"a",0,1000,[0,1,0,1,0,1],0,[]]',
        '[1,2,"a",0,0,[100,1,0,1,0,1],0,[]]','[1,2,"a",0,0,[0,1,0,1,0,1],100,[]]','[1,2,"a",0,0,[0,1,0,1,0,1],0,[ ]]',
        '[1,2,"a",0,0,[0,1,0,1,0,1],0,[],0]','[1,1234567890123,"a",0,0,[0,1,0,1,0,1],0,[]]','[1,123456789012,"a",0,0,[0,1,0,1,0,1],0,[]]',
        '[1234567890123456,2,"a",0,0,[0,1,0,1,0,1],0,[]]','[123456789012345,2,"a",0,0,[0,1,0,1,0,1],0,[]]',
        '[1,2,"'+'a'*65+'",0,0,[0,1,0,1,0,1],0,[]]','[1,2,"'+'a'*64+'",0,0,[0,1,0,1,0,1],0,[]]','[1,2,"é",0,0,[0,1,0,1,0,1],0,[]]'.encode('ascii','backslashreplace').decode('ascii'),
        '[1,2,"a",0,0,[0,1,0,1,0,1],0,[]]\r','[1,2,"a",0,0,[0,1,0,1,0,1],0,[]]\t',
    ]
    return [{'line':line,'expected':P.parse_line(line)} for line in lines]


def select_cases():
    lines=[P.encode(i,dict(healthy(time=T0+i),id='wireguard:peer_%d'%(i%2+7)),False,None) for i in range(1,21)]
    old=''.join(lines[:10]);new=''.join(lines[10:])
    garbage='junk line\n'
    setups=[
        ('both segments',old,new),('only the current one','',new),('only the previous one',old,''),
        ('empty','',''),('a torn last line is dropped',old,new+lines[0][:30]),('a torn previous segment',old+lines[0][:30],new),
        ('garbage lines are skipped',old+garbage+garbage,garbage+new),('blank lines are skipped',old+'\n\n',new),
        ('a segment without a newline at all',lines[0].rstrip('\n'),''),
    ]
    cases=[]
    for name,o,n in setups:
        for after,limit in ((0,500),(0,3),(5,500),(5,4),(10,3),(19,500),(20,500),(100,500),(0,1),(0,1000)):
            cases.append({'name':'%s, after %d, limit %d'%(name,after,limit),'old':o,'new':n,'after':after,'limit':limit,
                          'expected':P.select(o,n,after,limit)})
    return cases


def argument_cases():
    requests=[{},{'after':0},{'after':7},{'limit':1},{'limit':1000},{'after':3,'limit':10},{'after':10**15},
              {'after':10**15+1},{'after':-1},{'after':1.5},{'after':True},{'after':'3'},{'after':None},{'after':[3]},
              {'limit':0},{'limit':1001},{'limit':-5},{'limit':2.5},{'limit':False},{'limit':'10'},{'limit':None},
              {'x':1},{'after':1,'x':1},{'after':1.0},{'limit':10.0},[],[1],None,'x',7]
    cases=[]
    for request in requests:
        try:expected=list(P.arguments(request))
        except ValueError as error:expected=str(error)
        cases.append({'request':request,'expected':expected})
    return cases


def ring_cases():
    """Batches of results through a Writer with a small segment: the files after each batch."""
    def batch(count,start,dense=False,hb=None):
        rows=[dict(healthy(time=T0+start+i),id='wireguard:peer_%d'%(7+i%2)) for i in range(count)]
        return {'results':rows,'hb':hb,'dense':dense,'now':T0+start}
    scenarios=[]
    plain=[batch(2,i*10) for i in range(8)]
    plain[3]=batch(2,30,True,{'wireguard:peer_7':[10,1,10,0,0,0,0,0],'wireguard:peer_8':[10,0,10,0,0,0,0,0]})
    plain[5]=batch(1,50)
    plain[6]={'results':[{'id':'bad id','time':T0},{'time':T0}],'hb':None,'dense':False,'now':T0+60}
    scenarios.append({'name':'rotation','segment':700,'initial':{'current':None,'previous':None},'batches':plain})
    scenarios.append({'name':'a segment that fits exactly never rotates early','segment':len(P.encode(1,healthy(),False,None))*2,
                      'initial':{'current':None,'previous':None},'batches':[batch(1,0),batch(1,10),batch(1,20),batch(1,30)]})
    scenarios.append({'name':'the sequence continues after a restart (current segment)','segment':700,
                      'initial':{'current':''.join(P.encode(i,healthy(time=T0+i),False,None) for i in range(41,44)),'previous':None},
                      'batches':[batch(2,100),batch(2,110)]})
    scenarios.append({'name':'the sequence continues after a restart (only the previous segment)','segment':700,
                      'initial':{'current':'','previous':''.join(P.encode(i,healthy(time=T0+i),False,None) for i in range(7,10))},
                      'batches':[batch(2,100)]})
    scenarios.append({'name':'a torn last line of the previous run is kept below the new lines','segment':700,
                      'initial':{'current':P.encode(1,healthy(),False,None)+P.encode(2,healthy(),False,None)[:20],'previous':None},
                      'batches':[batch(1,100)]})
    scenarios.append({'name':'no results: nothing is written','segment':700,'initial':{'current':None,'previous':None},
                      'batches':[{'results':[],'hb':None,'dense':False,'now':T0}]})
    out=[]
    for scenario in scenarios:
        with tempfile.TemporaryDirectory() as directory:
            current=Path(directory)/P.NAME;previous=Path(directory)/(P.NAME+'.1')
            for key,path in (('current',current),('previous',previous)):
                if scenario['initial'][key] is not None:path.write_bytes(scenario['initial'][key].encode('ascii'))
            writer=P.Writer(directory,scenario['segment'])
            states=[]
            for item in scenario['batches']:
                written=writer.record(item['results'],item['hb'],item['dense'],item['now'])
                states.append({'written':written,'current':current.read_bytes().decode('ascii') if current.exists() else None,
                               'previous':previous.read_bytes().decode('ascii') if previous.exists() else None})
        out.append(dict(scenario,states=states))
    return out


def build():
    return {'seed':SEED,'encode':encode_cases(),'parse':parse_cases(),'select':select_cases(),'arguments':argument_cases(),'ring':ring_cases()}


def text():
    return json.dumps(build(),ensure_ascii=True,indent=None,sort_keys=True,separators=(',',':'))+'\n'


if __name__=='__main__':
    OUT.write_bytes(text().encode('ascii'))
    print(OUT,len(text()))
