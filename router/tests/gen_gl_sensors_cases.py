"""Generate router/tests/gl_sensors_cases.json: the shared cases of the GL sensors (GL-SENSORS-2026-11-04.ru.md).

The expected values come from the Python modules; test_gl_sensors.py checks that the file is current AND states the
meaning of the important cases by hand; tests/lua/test_gl_sensors.lua replays every case against the Lua twins.
Run: python router/tests/gen_gl_sensors_cases.py
"""
import itertools
import json
import random
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
import boot_cause  # noqa: E402
import diag_bundle  # noqa: E402
import failure_diagnosis  # noqa: E402
import interruption  # noqa: E402
import quorum  # noqa: E402
import stall  # noqa: E402
import wan_diag  # noqa: E402
import wg_events  # noqa: E402

OUT=HERE/'gl_sensors_cases.json'
SEED=20261104


def diagnose_cases():
    named=[
        ('healthy world',{'underlay':'ok','link':'up','kmwan':'online','primary':'ok','reserve':'ok'}),
        ('WAN proven down by the underlay echo',{'underlay':'fail','link':'up','primary':'bad','reserve':'bad'}),
        ('WAN link down',{'link':'down','primary':'bad','reserve':'bad'}),
        ('kmwan offline',{'kmwan':'offline','primary':'bad','reserve':'bad'}),
        ('captive portal and underlay fail',{'underlay':'fail','portal':'yes','primary':'bad','reserve':'bad'}),
        ('both bad without WAN evidence: unknown = no hold',{'primary':'bad','reserve':'bad'}),
        ('both bad, WAN proven up: provider',{'underlay':'ok','kmwan':'online','primary':'bad','reserve':'bad'}),
        ('primary bad, reserve ok, WAN up: hasten',{'underlay':'ok','primary':'bad','reserve':'ok'}),
        ('primary bad, reserve ok, no WAN evidence: no hasten',{'primary':'bad','reserve':'ok'}),
        ('primary bad, REKEY-GIVEUP, WAN up',{'underlay':'ok','primary':'bad','reserve':'ok','wg':'giveup'}),
        ('primary bad, fresh keypair, WAN up: server egress',{'underlay':'ok','primary':'bad','reserve':'ok','wg':'created'}),
        ('DNS on both',{'underlay':'ok','primary':'dns','reserve':'dns'}),
        ('underlay fail but reserve healthy: never hold',{'underlay':'fail','primary':'bad','reserve':'ok'}),
        ('underlay fail, primary healthy: never hold',{'underlay':'fail','primary':'ok','reserve':'bad'}),
        ('WAN down, reserve unknown',{'underlay':'fail','primary':'bad','reserve':'unknown'}),
        ('empty evidence',{}),
        ('garbage values are no evidence',{'underlay':'maybe','primary':1,'reserve':None,'kmwan':['offline']}),
    ]
    cases=[{'name':name,'evidence':ev,'enabled':True} for name,ev in named]
    cases+=[{'name':name+' (switched off)','evidence':ev,'enabled':False} for name,ev in named[:9]]
    rng=random.Random(SEED)
    axes=[('underlay',[None,'ok','fail']),('link',[None,'up','down']),('kmwan',[None,'online','offline']),('portal',[None,'yes','no']),
          ('primary',['unknown','ok','bad','dns']),('reserve',['unknown','ok','bad','dns']),('wg',[None,'giveup','timeout','created'])]
    combos=list(itertools.product(*[values for _,values in axes]))
    for combo in rng.sample(combos,400):
        ev={key:value for (key,_),value in zip(axes,combo) if value is not None}
        cases.append({'name':'combination','evidence':ev,'enabled':rng.random()<0.8})
    for case in cases:case['expected']=wan_diag.diagnose(case['evidence'],case['enabled'])
    return cases


def channel_cases():
    now=1000.0
    rows=[
        ('healthy',{'time':995.0,'code':None,'dns_ok':True,'https_success':3}),
        ('one https only',{'time':995.0,'code':None,'dns_ok':True,'https_success':1}),
        ('https failed',{'time':995.0,'code':'VPN-003','dns_ok':True,'https_success':0}),
        ('tunnel missing',{'time':995.0,'code':'VPN-001'}),
        ('black hole',{'time':995.0,'code':'VPN-MTU','dns_ok':True,'https_success':3}),
        ('dns only',{'time':995.0,'code':'DNS-001','dns_ok':False,'https_success':3}),
        ('stale',{'time':800.0,'code':'VPN-003'}),
        ('future',{'time':1001.0,'code':'VPN-003'}),
        ('unverified',{'time':995.0,'code':'CHECK-LIMIT'}),
        ('no time',{'code':'VPN-003'}),
        ('boolean successes',{'time':995.0,'code':None,'dns_ok':True,'https_success':True}),
    ]
    return [{'name':name,'row':row,'now':now,'age':90,'expected':wan_diag.channel_state(row,now,90)} for name,row in rows]


def evidence_cases():
    rows=[{'id':'a','time':995.0,'code':'VPN-003'},{'id':'b','time':995.0,'code':None,'dns_ok':True,'https_success':2},
          {'id':'c','time':995.0,'code':'DNS-001'}]
    cases=[
        {'name':'pair rows and sensors','rows':rows,'pair':{'source':'a','target':'b'},'sensors':{'uplink':{'state':'LINK-UP','time':990.0},'underlay':'ok','kmwan':'online','portal':'no','wg':'timeout'}},
        {'name':'uplink down','rows':rows,'pair':{'source':'a','target':'c'},'sensors':{'uplink':{'state':'DOWN','time':999.0}}},
        {'name':'stale uplink','rows':rows,'pair':{'source':'a','target':'b'},'sensors':{'uplink':{'state':'DOWN','time':800.0}}},
        {'name':'odd uplink state','rows':rows,'pair':{'source':'a','target':'b'},'sensors':{'uplink':{'state':'UNKNOWN','time':999.0}}},
        {'name':'unknown sensor values dropped','rows':rows,'pair':{'source':'b','target':'a'},'sensors':{'underlay':'down','kmwan':'yes','wg':'rekey'}},
        {'name':'no pair','rows':rows,'pair':{},'sensors':{}},
        {'name':'missing rows','rows':[],'pair':{'source':'a','target':'b'},'sensors':{'underlay':'fail'}},
    ]
    for case in cases:
        case['now']=1000.0;case['age']=90
        case['expected']=wan_diag.evidence(case['rows'],case['pair'],1000.0,90,**case['sensors'])
    return cases


def simple_cases():
    return {
        'kmwan':[[t,wan_diag.kmwan_verdict(t)] for t in [None,'','wan online metric 10','WAN OFFLINE','wan: offline\nwwan: online','garbage']],
        'portal':[[v,wan_diag.portal_verdict(v)] for v in [None,{'portal':True},{'portal':False},{'portal':'true'},{},[True]]],
        'grace':[[s,wan_diag.grace_seconds(s)] for s in [None,{},{'wan_recover_grace':0},{'wan_recover_grace':120},{'wan_recover_grace':121},
                                                        {'wan_recover_grace':-1},{'wan_recover_grace':'30'},{'wan_recover_grace':45}]],
    }


def run_underlay(ops):
    u=wan_diag.Underlay();out=[]
    for op in ops:
        kind=op[0]
        if kind=='bind':u.bind(op[1]);out.append(None)
        elif kind=='record':u.record(op[1],op[2],op[3]);out.append(None)
        elif kind=='state':out.append(u.state(op[1]))
        elif kind=='due':out.append(u.due(op[1],op[2]))
        elif kind=='target':out.append(u.target())
    return out


def underlay_cases():
    seqs=[
        ('never answered: a firewall is no WAN failure',[['bind','apcli0'],['record',False,'1.1.1.1',10],['record',False,'8.8.8.8',12],
            ['record',False,'9.9.9.9',14],['state',14]]),
        ('calibrated, then three failures over two targets',[['bind','apcli0'],['record',True,'1.1.1.1',0],['state',1],
            ['record',False,'8.8.8.8',10],['state',10],['record',False,'9.9.9.9',12],['state',12],['record',False,'208.67.222.222',14],['state',14],
            ['record',True,'1.1.1.1',16],['state',16]]),
        ('three failures to one target are not enough',[['bind','eth1'],['record',True,'1.1.1.1',0],['record',False,'8.8.8.8',2],
            ['record',False,'8.8.8.8',4],['record',False,'8.8.8.8',6],['state',6]]),
        ('ok ages out; stale is unknown',[['bind','eth1'],['record',True,'1.1.1.1',0],['state',30],['state',31],['state',61]]),
        ('a new device starts uncalibrated',[['bind','eth1'],['record',True,'1.1.1.1',0],['bind','apcli0'],['state',1],
            ['record',False,'8.8.8.8',2],['record',False,'9.9.9.9',4],['record',False,'1.1.1.1',6],['state',6]]),
        ('cadence and targets',[['due',0,False],['bind','eth1'],['due',0,False],['target'],['record',True,'1.1.1.1',0],['target'],
            ['due',5,False],['due',10,False],['due',1,True],['due',2,True],['state',-1]]),
    ]
    return [{'name':name,'ops':ops,'expected':run_underlay(ops)} for name,ops in seqs]


def run_tracker(ops):
    t=wan_diag.Tracker();out=[]
    for op in ops:out.append(t.update({'hold':op[0],'code':op[1]},op[2],op[3],op[4]))
    return out


def tracker_cases():
    seqs=[
        ('down, back, primary healthy at once',[[False,None,0,None,30],[True,'WAN-DOWN',10,None,30],[True,'WAN-DOWN',20,None,30],
            [False,'DIAG-UNSURE',30,None,30],[False,None,40,35,30],[False,None,50,45,30]]),
        ('back, primary still failing: grace ends the hold',[[True,'WAN-DOWN',10,None,30],[False,'DIAG-TUNNEL-DOWN',20,None,30],
            [False,'DIAG-TUNNEL-DOWN',40,None,30],[False,'DIAG-TUNNEL-DOWN',50,None,30],[False,'DIAG-TUNNEL-DOWN',60,None,30]]),
        ('grace 0: no recovering hold',[[True,'WAN-DOWN',10,None,0],[False,None,20,None,0]]),
        ('grace ends exactly at grace seconds',[[True,'WAN-DOWN',10,None,30],[False,None,20,None,30],[False,None,49,None,30],[False,None,50,None,30]]),
        ('old healthy sample does not end the hold',[[True,'WAN-DOWN',10,None,30],[False,None,20,15,30],[False,None,25,20,30],[False,None,26,25.5,30]]),
    ]
    return [{'name':name,'ops':ops,'expected':run_tracker(ops)} for name,ops in seqs]


def stall_cases():
    seqs=[
        ('tx grows, rx flat 3 s: stall',[[0,1000,5000],[1,1000,5200],[2,1000,5400],[3,1000,5600],[4,1000,5800]]),
        ('rx moves: no stall',[[0,1000,5000],[1,1100,5200],[2,1200,5400],[3,1300,5600],[4,1400,5800]]),
        ('rx flowing 10 kbit/s: veto',[[0,0,0],[1,1300,100],[2,2600,200],[3,3900,300],[4,5200,400]]),
        ('rx stops: the veto ends at once',[[0,0,0],[1,4000,100],[2,8000,200],[3,12000,300],[4,16000,400],[5,16000,500],[6,16000,600]]),
        ('slow rx 4 kbit/s is no veto',[[0,0,0],[1,500,100],[2,1000,200],[3,1500,300],[4,2000,400],[5,2500,500]]),
        ('only rx drops (new device): starts again',[[0,1000,5000],[1,1000,5200],[2,10,5400],[3,10,5600],[4,10,5800],[5,10,6000]]),
        ('idle tunnel: no tx, no stall',[[0,1000,5000],[1,1000,5000],[2,1000,5000],[3,1000,5000],[4,1000,5010]]),
        ('counter reset starts again',[[0,1000,5000],[1,1000,5200],[2,10,10],[3,10,400],[4,10,600],[5,10,800]]),
        ('gap starts again',[[0,1000,5000],[1,1000,5200],[9,1000,5400],[10,1000,5600],[12,1000,5800]]),
        ('unreadable counter resets',[[0,1000,5000],[1,None,5200],[2,1000,5400],[3,1000,5600],[4,1000,5800],[5,1000,6000]]),
        ('negative tx after own echoes taken out resets',[[0,1000,5000],[1,1000,-4],[2,1000,400],[3,1000,500]]),
    ]
    out=[]
    for name,feeds in seqs:
        s=stall.Stall()
        out.append({'name':name,'feeds':feeds,'expected':[s.feed(*f) for f in feeds]})
    return out


def run_quorum(start,beats):
    p=quorum.Pool(start=start);out=[]
    for answered,now in beats:
        verdict=p.judge({t:True for t in answered},now)
        out.append({'verdict':verdict,'targets':p.targets(),'rotations':p.rotations})
    return out


def quorum_cases():
    seqs=[
        ('all answer',0,[[['1.1.1.1','8.8.8.8','9.9.9.9'],1],[['1.1.1.1','8.8.8.8','9.9.9.9'],2]]),
        ('one silent target rotates out after 3 misses',0,[[['1.1.1.1','8.8.8.8'],1],[['1.1.1.1','8.8.8.8'],2],[['1.1.1.1','8.8.8.8'],3],
            [['1.1.1.1','8.8.8.8','208.67.222.222'],4]]),
        ('two silent: the beat is lost, nothing rotates',0,[[['1.1.1.1'],1],[['1.1.1.1'],2],[['1.1.1.1'],3],[[],4]]),
        ('misses outside the window do not add up',0,[[['1.1.1.1','8.8.8.8'],1],[['1.1.1.1','8.8.8.8'],70],[['1.1.1.1','8.8.8.8'],140]]),
        ('start offset and wrap',6,[[['149.112.112.112','208.67.220.220'],1],[['149.112.112.112','208.67.220.220'],2],[['149.112.112.112','208.67.220.220'],3],[['149.112.112.112','208.67.220.220','8.8.8.8'],4]]),
        ('misses count inside the window only, answers in between do not clear them',0,[[['1.1.1.1','8.8.8.8'],1],[['1.1.1.1','8.8.8.8','9.9.9.9'],2],
            [['1.1.1.1','8.8.8.8'],61],[['1.1.1.1','8.8.8.8'],62]]),
    ]
    return [{'name':name,'start':start,'beats':beats,'expected':run_quorum(start,beats)} for name,start,beats in seqs]


def wg_cases():
    text=('12.50 REKEY-TIMEOUT wgclient1\n13.00 KEYPAIR-CREATED wgclient2\nbad line\n14 REKEY-GIVEUP wgclient1\n'
          '15.1234 REKEY-TIMEOUT wgclient1\n16. REKEY-TIMEOUT wgclient1\n17 REKEY-TIMEOUT wg client\n18 UP wgclient1\n'
          '19 KEYPAIR-CREATED wgclient1\r\n20 REKEY-TIMEOUT  wgclient1\n1234567890 REKEY-TIMEOUT wgclient1\n')
    parsed=wg_events.parse(text)
    latest=[[d,n,w,wg_events.latest(parsed,d,n,w)] for d,n,w in [('wgclient1',20,120),('wgclient1',13.5,120),('wgclient2',13,0),
                                                                 ('wgclient2',200,120),('wgclient3',20,120),('wgclient1',10,120)]]
    reads=[]
    r=wg_events.Reader()
    for chunk in ['10 REKEY-TIMEOUT wgclient1\n','10 REKEY-TIMEOUT wgclient1\n11 REKEY-GIVEUP wgclient1\n12 KEYPAIR-CREATED wgclient2\n',
                  '10 REKEY-TIMEOUT wgclient1\n11 REKEY-GIVEUP wgclient1\n12 KEYPAIR-CREATED wgclient2\n','3 REKEY-TIMEOUT wgclient2\n',
                  '3 REKEY-TIMEOUT wgclient2\n4 REKEY-TIMEOUT wgclient2\n','']:
        fresh=r.new(wg_events.parse(chunk))
        reads.append([chunk,[list(e) for e in fresh],wg_events.suspicions(fresh,[{'id':'wireguard:peer_1','device':'wgclient1'},
                                                                                 {'id':'wireguard:peer_2','device':'wgclient2'},{'device':'wgclient2'}])])
    return {'text':text,'parsed':[list(e) for e in parsed],'latest':latest,'reads':reads}


def boot_cases():
    texts=[None,'','a','crash record\n'+'x'*500,'~'*3000+'\n<6>[  12.5] Oops']
    fingerprints=[[t,boot_cause.fingerprint(t)] for t in texts]
    log='Kernel panic - not syncing: Fatal exception\n'
    fp=boot_cause.fingerprint(log)
    evidence=[]
    for names,data,remembered in [([],log,fp),([],log,None),([],log+'more\n',fp),([],None,fp),(['dmesg-ramoops-0'],log,fp),
                                  (['console-ramoops-0'],log,fp),(['dmesg-ramoops-x'],None,''),([],None,''),([],log,''),([],log,7)]:
        evidence.append([names,data,remembered,list(boot_cause.crash_evidence(names,data,remembered))])
    timer={'enable':'1','hour':'03','min':'00','week':'0 1 2 3 4 5 6'}
    planned=[]
    for t,w,h,m in [(timer,1,3,0),(timer,1,3,3),(timer,1,3,4),(timer,1,2,59),(dict(timer,enable='0'),1,3,0),(dict(timer,week='1 3'),2,3,1),
                    (dict(timer,week='1,3'),3,3,1),(dict(timer,week='7'),0,3,0),(dict(timer,week='0'),0,3,2),(dict(timer,hour='3'),4,3,0),
                    (dict(timer,hour='x'),1,3,0),(dict(timer,week='1 x'),1,3,0),({'enable':'1'},1,3,0),(None,1,3,0),(dict(timer,min='59',hour='23'),5,23,59)]:
        planned.append([t,w,h,m,boot_cause.planned(t,w,h,m),boot_cause.shutdown_reason(t,w,h,m)])
    return {'fingerprint':fingerprints,'evidence':evidence,'planned':planned}


def classify_cases():
    base={'fresh':True,'previous':'running','stopped_since':False,'phase':None,'auto_on':True,'reason':None,'crash':False}
    variants=[
        ('planned reboot',dict(base,previous='stopped',reason='planned-reboot')),
        ('plain reboot',dict(base,previous='stopped',reason='reboot')),
        ('planned reason without a fresh boot is a clean restart',dict(base,fresh=False,previous='stopped',reason='planned-reboot')),
        ('kernel crash during operation',dict(base,crash=True)),
        ('kernel crash during a switch',dict(base,crash=True,phase='APPLYING')),
        ('crash flag never hides a first start',dict(base,previous=None,crash=True)),
        ('crash flag is ignored for a clean stop',dict(base,previous='stopped',crash=True)),
        ('power cut stays a power cut',dict(base)),
        ('process restart',dict(base,fresh=False,crash=True)),
    ]
    reasons=[[t,interruption.previous_reason(t)] for t in [None,'{"state":"stopped","time":1}','{"state":"stopped","time":1,"reason":"planned-reboot"}',
             '{"state":"stopped","reason":"reboot"}','{"state":"running","reason":"reboot"}','{"state":"stopped","reason":"other"}','not json']]
    return {'classify':[{'name':n,'facts':f,'expected':interruption.classify(f)} for n,f in variants],'reasons':reasons}


def mask_cases():
    key='aGVsbG8gd29ybGQgdGhpcyBpcyBhIHRlc3Qga2V5MTI='
    lines=[
        "network.wgclient1.private_key='%s'"%key,
        "network.wgclient1.addresses='10.0.0.2/32'",
        "homensai_vpn.main.telegram_token='1234567:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsawQ'",
        "homensai_vpn.main.telegram_chat='-100123'",
        "homensai_vpn.main.interval='10'",
        "wireless.@wifi-iface[0].key='supersecret'",
        "wireless.@wifi-iface[0].ssid='HomeNet'",
        "\toption password 'p@ss word'",
        "  list preshared_key 'abc'",
        "  option interval '10'",
        "interface: wgclient1",
        "  public key: %s"%key,
        "  private key: (hidden)",
        "  endpoint: 203.0.113.7:51820",
        "  latest handshake: 1 minute ago",
        'peer: %s'%key,
        '{"exit_ip":"198.51.100.4","code":null,"token":"abc","name":"x"}',
        'bot 9876543:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef12345 sent at 12:34:56',
        'lladdr aa:bb:cc:dd:ee:ff and AA:BB:CC:11:22:33',
        'short= base64= %s= not44'%('A'*40),
        'blob %s tail'%key,
        'Chain INPUT (policy ACCEPT): 0 packets',
        '',
        'unicode été key=value',
        # security audit 04.11.2026 (F6): public addresses, free-text secrets, EUI-64, user names, chat ids
        'default via 203.0.113.1 dev eth0 proto static',
        '203.0.113.57 dev wgclient1 scope link',
        'ip rule: from all to 187.40.16.19 lookup main',
        '\t\tip daddr 187.40.16.19 accept',
        'private 192.168.8.1 10.0.0.1 172.16.5.5 100.64.0.1 127.0.0.1 169.254.1.1 224.0.0.251 0.0.0.0 255.255.255.0; public 172.32.0.1',
        'not addresses: 1.2.3.4.5 999.1.1.1 1234.1.1.1 version 5.4.211',
        '{"exit": {"ip": "203.0.113.9"}, "wan_ip": "198.51.100.4"}',
        'inet6 fe80::9683:c4ff:fe12:3456/64 scope link',
        'inet6 2001:db8::1/64 and ::1 and ff02::1 and fd00:1:2:3:4:5:6:7',
        'Nov  4 10:00:00 homensai: password=hunter2hunter2 token=abcdef123456',
        'Nov  4 10:00:00 homensai: url https://x.example/?token=abcdef0123456789&x=1',
        "curl 'https://x.example/?key=abcdef&sig=zzzzzz&auth=qqqqqq' ok",
        "wpa_supplicant: SSID 'HomeNet' psk=%s"%('0123456789abcdef'*4),
        'chat_id=-1001234567890 sent',
        'chat id: 1234567',
        "\toption username 'myvpnuser'",
        "network.wgclient1.description='Kyiv ua65'",
        '{"username": "bob", "chat_id": -1001234567890, "count": 1234567, "comment": "my server"}',
        "network.wg_key1.mtu='1420' keepalive=25 interval=10",
    ]
    return [[line,diag_bundle.mask_line(line)] for line in lines]+[['multi\nline\n','\n'.join(diag_bundle.mask_line(x) for x in 'multi\nline\n'.split('\n'))]]


def diagnose_status_cases():
    def status(wan,code='VPN-003'):
        s={'time':1000.0,'profiles':[{'id':'a','interface':'wgclient1','time':999.0,'code':code,'vendor_state':'SETTLED'}],
           'observation_valid_for':90}
        if wan is not None:s['wan_diagnosis']=wan
        return s
    items=[
        ('WAN-DOWN holds',status({'hold':True,'code':'WAN-DOWN','time':999.0})),
        ('WAN-RECOVERING holds',status({'hold':True,'code':'WAN-RECOVERING','time':999.0})),
        ('stale WAN verdict is ignored',status({'hold':True,'code':'WAN-DOWN','time':800.0})),
        ('hold false is ignored',status({'hold':False,'code':'WAN-DOWN','time':999.0})),
        ('another code is ignored',status({'hold':True,'code':'DIAG-TUNNEL-DOWN','time':999.0})),
        ('code must be a string',status({'hold':True,'code':['WAN-DOWN'],'time':999.0})),
        ('no WAN verdict: previous behaviour',status(None)),
        ('WAN-DOWN also over a healthy row',status({'hold':True,'code':'WAN-DOWN','time':999.0},code=None)),
    ]
    return [{'name':n,'status':s,'now':1000.0,'expected':failure_diagnosis.diagnose(s,'a',1000.0)} for n,s in items]


def build():
    return {'seed':SEED,'diagnose':diagnose_cases(),'channel_state':channel_cases(),'evidence':evidence_cases(),'simple':simple_cases(),
            'underlay':underlay_cases(),'tracker':tracker_cases(),'stall':stall_cases(),'quorum':quorum_cases(),'wg':wg_cases(),
            'boot':boot_cases(),'interruption':classify_cases(),'mask':mask_cases(),'diagnose_status':diagnose_status_cases()}


def text():
    return json.dumps(build(),ensure_ascii=True,indent=None,sort_keys=True,separators=(',',':'))+'\n'


if __name__=='__main__':
    OUT.write_bytes(text().encode('ascii'))
    print(OUT,len(text()))
