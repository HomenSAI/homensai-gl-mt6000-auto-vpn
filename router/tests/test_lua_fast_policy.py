"""The Lua core (files/usr/lib/homensai-vpn/lua, line 2.0.0-lua) against the Python code it ports.

One Lua process evaluates every generated case; Python compares with the real modules:
fast_policy.py (the fixtures and every refusal case of test_fast_policy.py, systematic variants and
seeded mutations), kernel_policy.parse_mangle/fields, bytes.decode('utf8','replace'), repr(float),
canonical JSON (native_history.encoded / native_switch.digest) + hashlib, Linux.reorder's moves,
native_switch.journal_write/journal_read in both directions, auto_control.control_lock (fcntl.flock)
against control.lua, and runner.lua with fake iptables-restore/conntrack/uci programs on PATH.
Also runs the plain Lua suites tests/lua/test_*.lua.
"""
import fcntl
import json
import os
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'files/usr/lib/homensai-vpn'))
import fast_policy as f
import kernel_policy as kp
from native_history import encoded
import native_switch as n
from agent import read_json
from test_fast_policy import UCI,MANGLE

LUA=shutil.which('lua5.1')
DRIVER=HERE/'lua'/'differential.lua'
CLIENT=HERE/'lua'/'runner_client.lua'
SEED=20261030

J5='-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL5841_ROUTE_POLICY'
J4='-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL4192_ROUTE_POLICY'
SET='gid-owner 20000 -j MARK --set-xmark 0x1000/0xf000'
APPLIED=MANGLE.replace(J5+'\n'+J4,J4+'\n'+J5).replace(SET,SET.replace('0x1000/','0xb000/'))


def python_outcome(fn,*args):
    try:result=fn(*args)
    except f.Unsupported as error:return {'unsupported':str(error)}
    except n.Refused as error:return {'refused':str(error)}
    except Exception as error:return {'error':type(error).__name__}
    return {'ok':list(result) if isinstance(result,tuple) else [result]}


def same_outcome(python,lua):
    """Equal results and equal refusal codes; any other exception only has to be an exception on both sides."""
    if 'error' in python or 'error' in lua:return set(python)==set(lua)
    return python==lua


# --- fast_policy cases ---------------------------------------------------------------------------------
def uci_variants():
    return [UCI,
            # the refusal cases of test_fast_policy.Plan.test_anything_unexpected_falls_back
            UCI.replace("@rule[1].tunnel_id='5841'","@rule[1].tunnel_id='4192'"),
            UCI.replace("gl_process_vpn.mark='0xb000'","gl_process_vpn.mark='bad'"),
            UCI+"route_policy.@rule[2].tunnel_id='7'\n",
            # systematic variants
            '',UCI.replace('\n','\r\n'),UCI.replace('\n','\r'),UCI.replace('\n','\x0b'),UCI.replace('\n','\x1c'),
            UCI.replace('\n','\u2028'),UCI.replace('\n','\x85'),UCI.replace('\n','\u2029'),UCI.replace('\n','\x1e'),
            UCI.replace('@rule[1]','@rule[01]'),UCI.replace('@rule[0]','@rule[10]'),UCI.replace('@rule[0]','@rule[2]'),
            UCI.replace('@rule[0]','@rule[99999999999999999999999]'),
            UCI+"route_policy.@rule[0].enabled='0'\n",UCI+"route_policy.@rule[0].enabled='1'\n",
            UCI+"route_policy.@rule[2].tunnel_id='7'\nroute_policy.@rule[2].enabled='0'\n",
            UCI+"route_policy.@rule[2].enabled='1'\n",UCI+"route_policy.@rule[1].tunnel_id='9'\n",
            UCI.replace("gl_process_vpn.enabled='1'","gl_process_vpn.enabled='0'"),
            UCI.replace("gl_process_vpn.enabled='1'","gl_process_vpn.enabled=''"),
            UCI.replace("route_policy.gl_process_vpn.enabled='1'\n",''),
            UCI.replace("route_policy.gl_process_vpn.mark='0xb000'\n",''),
            UCI.replace("gl_process_vpn.mark='0xb000'","gl_process_vpn.mark='0xB000'"),
            UCI.replace("gl_process_vpn.mark='0xb000'","gl_process_vpn.mark='0x123456789'"),
            UCI.replace("gl_process_vpn.mark='0xb000'","gl_process_vpn.mark='0x12345678'"),
            UCI.replace("gl_process_vpn.mark='0xb000'","gl_process_vpn.mark='0x'"),
            UCI.replace("gl_process_vpn.tunnel_id='10100'","gl_process_vpn.tunnel_id='123456789'"),
            UCI.replace("gl_process_vpn.tunnel_id='10100'","gl_process_vpn.tunnel_id='12345678'"),
            UCI.replace("tunnel_id='4192'","tunnel_id='41a2'"),UCI.replace("tunnel_id='4192'","tunnel_id='4=2'"),
            UCI.replace("tunnel_id='4192'","tunnel_id=x'4192'"),UCI.replace(".tunnel_id='4192'",".tunnel_idx='4192'"),
            UCI.replace("tunnel_id='4192'","tunnel_id='4192' "),UCI.replace("tunnel_id='4192'","tunnel_id=='4192'"),
            UCI.replace("tunnel_id='4192'","tunnel_id='\u0664\u0661\u0669\u0662'"),
            UCI.replace('route_policy.@rule[0].tunnel_id','ROUTE_policy.@rule[0].tunnel_id'),
            UCI.replace("route_policy.gl_process_vpn.tunnel_id='10100'","route_policy.gl_process_vpn.tunnel_id='1'\nroute_policy.gl_process_vpn.tunnel_id='10100'"),
            UCI.replace("route_policy.@rule[0].tunnel_id='4192'","route_policy.@rule[0].tunnel_id='4192'\u2028x")]


def mangle_variants():
    return [MANGLE,APPLIED,
            # the refusal cases of test_fast_policy.Plan.test_anything_unexpected_falls_back
            MANGLE.replace('-j TUNNEL4192_ROUTE_POLICY\n','-j TUNNEL9999_ROUTE_POLICY\n'),
            MANGLE.replace('-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL4192_ROUTE_POLICY\n',''),
            MANGLE.replace('--set-xmark 0x1000/0xf000\n-A TUNNEL10100_LOCAL_POLICY -m connmark','--set-xmark 0x1000/0xffff\n-A TUNNEL10100_LOCAL_POLICY -m connmark'),
            # systematic variants
            '',MANGLE.replace('\n','\r\n'),MANGLE.replace('\n','\u2028'),MANGLE.replace('\n','\x0c'),
            MANGLE.replace(J5+'\n',J5+'\n-A ROUTE_POLICY -j RETURN\n'),
            MANGLE.replace(J4+'\n',J4+'\n'+J4.replace('4192','7777')+'\n'),
            MANGLE.replace(J4,J4+' '),MANGLE.replace(J4,J4.replace('4192','123456789')),MANGLE.replace(J4,J4.replace('4192','12345678')),
            MANGLE.replace(J4,J4.replace(' -j ','  -j ')),MANGLE.replace(J5,J5.replace('5841','4192')),
            MANGLE.replace('-A ROUTE_POLICY -p udp','-A ROUTE_POLICY -m comment --comment "x_ROUTE_POLICY" -p udp'),
            MANGLE.replace('-A ROUTE_POLICY -p udp','-A ROUTE_POLICY -m x -j -j _ROUTE_POLICY\n-A ROUTE_POLICY -p udp'),
            MANGLE.replace(SET,SET.replace('0x1000/','0x123456789/')),MANGLE.replace(SET,SET.replace('0x1000/','0xABCD/')),
            MANGLE.replace(SET,SET.replace('0x1000/','0x/')),MANGLE.replace(SET,SET.replace('0x1000/','0x12345678/')),
            MANGLE.replace(SET,SET.replace(' -j MARK',' -j  MARK')),MANGLE.replace(SET,SET+' '),
            MANGLE.replace(SET,SET+'\n-A TUNNEL10100_LOCAL_POLICY -j MARK --set-xmark 0x2000/0xf000'),
            MANGLE.replace('-A TUNNEL10100_LOCAL_POLICY','-A TUNNEL10101_LOCAL_POLICY'),
            MANGLE.replace('-A TUNNEL5841_ROUTE_POLICY -m comment','-A TUNNEL5841_ROUTE_POLICY  -m comment'),
            MANGLE.replace('-A TUNNEL5841_ROUTE_POLICY -m comment --comment "TUNNEL5841 rule for set mark" -m mark --mark 0x0/0xf000 ','-A TUNNEL5841_ROUTE_POLICY '),
            MANGLE.replace('--comment "TUNNEL10100 rule for set mark"','--comment "rule\u2028for set mark"'),
            MANGLE.replace('TUNNEL5841 rule','TUNNEL5841 r\u00e8gle \U0001F600'),
            MANGLE.replace('*mangle\n','*mangle\n-A ROUTE_POLICY\n-A ROUTE_POLICY  -j TUNNEL1_ROUTE_POLICY\n')]


def mutate(rng,text):
    pool=[' ','-','j','0','f','x','_','\n','\r',"'",'=','A','9','\u2028','/','.','[',']','@','\x85']
    tokens=[' -j ','_ROUTE_POLICY','/0xf000','--set-xmark 0x','TUNNEL','\n-A ROUTE_POLICY ',"='",
            "\nroute_policy.@rule[3].tunnel_id='12'",'-A TUNNEL10100_LOCAL_POLICY ','0xb000']
    lines=text.split('\n')
    for _ in range(rng.randint(1,3)):
        op=rng.randrange(5);i=rng.randrange(len(lines))
        if op==0 and len(lines)>1:del lines[i]
        elif op==1:lines.insert(i,lines[i])
        elif op==2 and len(lines)>1:
            j=rng.randrange(len(lines));lines[i],lines[j]=lines[j],lines[i]
        elif op==3 and lines[i]:
            k=rng.randrange(len(lines[i]));lines[i]=lines[i][:k]+rng.choice(pool)+lines[i][k+1:]
        else:
            k=rng.randrange(len(lines[i])+1);lines[i]=lines[i][:k]+rng.choice(tokens)+lines[i][k:]
    return '\n'.join(lines)


def fast_policy_cases():
    rng=random.Random(SEED)
    ucis=uci_variants()+[mutate(rng,UCI) for _ in range(400)]
    mangles=mangle_variants()
    orders=[['4192','5841'],['5841','4192'],['4192','4192'],['4192'],['1','2'],[],['4192','5841','7']]
    plans=[[m,o,t,k] for m in mangles for o in orders for t in ('10100','10101') for k in ('0xb000','0x1000')]
    plans+=[[mutate(rng,MANGLE),['4192','5841'],'10100','0xb000'] for _ in range(600)]
    marks=[[m,t] for m in mangles for t in ('5841','4192','10100','9999','58','')]
    marks+=[[mutate(rng,MANGLE),'5841'] for _ in range(300)]
    # Command output as bytes, decoded like apply_fast does; invalid UTF-8 and U+0085 inside lines.
    raw=[(UCI.encode(),MANGLE.encode()),(UCI.encode(),APPLIED.encode())]
    for bad in (b'\xff',b'\xc2\x85',b'\xe2\x80',b'\xed\xa0\x80',b'\xe2\x80\xa8',b'\xf4\x90\x80\x80',b'\xc0\xaf',b'\x00'):
        raw.append((UCI.encode(),MANGLE.encode().replace(b'TUNNEL10100 rule',b'TUNNEL10100'+bad+b'rule')))
        raw.append((UCI.encode(),MANGLE.encode().replace(b'TUNNEL5841 rule',b'TUNNEL5841'+bad+b'rule')))
        raw.append((UCI.encode().replace(b"'ovpnclient2'",b"'ovpn"+bad+b"'"),MANGLE.encode()))
        raw.append((UCI.encode().replace(b"tunnel_id='4192'",b"tunnel_id='4192"+bad+b"'"),MANGLE.encode()))
    for _ in range(200):
        data=bytearray(MANGLE.encode());k=rng.randrange(len(data))
        data[k:k+1]=bytes(rng.choice([0x80,0xc2,0xe2,0xed,0xf0,0xff,0x85,0xa8,0x0a,0x0d]) for _ in range(rng.randint(1,3)))
        raw.append((UCI.encode(),bytes(data)))
    return {'uci_rules':ucis,'plan':plans,'mark_of':marks,'prepare':[[u.hex(),m.hex()] for u,m in raw]}


FULL='\n'.join(['*mangle',':PREROUTING ACCEPT [0:0]',':ROUTE_POLICY - [0:0]',':TUNNEL4192_ROUTE_POLICY - [0:0]',
    ':TUNNEL5841_ROUTE_POLICY - [0:0]',':TUNNEL10100_LOCAL_POLICY - [0:0]']+[l for l in MANGLE.splitlines() if l.startswith('-A ')]+[
    '-A TUNNEL4192_ROUTE_POLICY -m mark --mark 0x0/0xf000 -j DROP','-A TUNNEL5841_ROUTE_POLICY -m mark --mark 0x0/0xf000 -j DROP','COMMIT',''])


def mangle_parse_cases(rng):
    edits=['-A ROUTE_POLICY -m comment --comment "a \\"b\\" c" -j RETURN',"-A ROUTE_POLICY -m comment --comment 'x y' -j RETURN",
           '-A ROUTE_POLICY -m comment --comment "open -j RETURN','-A ROUTE_POLICY -j RETURN \\','-A ROUTE_POLICY -m mark --mark 0x10/0xFFFF -j RETURN',
           '-A ROUTE_POLICY ! ! -j RETURN','-A ROUTE_POLICY -m mark -m mark -j RETURN','-A ROUTE_POLICY -p tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu',
           '-A ROUTE_POLICY -j MARK --set-xmark 0x123456789abcdef0/0xf000','-A NOPE -j RETURN',':ROUTE_POLICY - [0:0]',':PREROUTING DROP [0:0]',
           '# comment','','-A ROUTE_POLICY -j','-A ROUTE_POLICY --unknown x','-A ROUTE_POLICY -m comment -j RETURN','*mangle','-A ROUTE_POLICY -o br\\ lan -j RETURN']
    route_only='\n'.join(l for l in FULL.split('\n') if 'gid-owner' not in l)  # kernel_policy.fields has no --gid-owner
    texts=[route_only,FULL,FULL.replace('COMMIT\n',''),FULL.replace('*mangle\n',''),FULL.replace('\n','\r\n'),FULL+'-A ROUTE_POLICY -j RETURN\n','']
    lines=FULL.split('\n')
    for edit in edits:
        texts.append('\n'.join(lines[:7]+[edit]+lines[7:]))
    for _ in range(300):texts.append(mutate(rng,FULL))
    return texts


def python_parse(text):
    try:
        chains=kp.parse_mangle(text)
        rows=[]
        for name in chains:
            for tokens in chains[name]:
                fields=kp.fields(tokens)
                if '-m' in fields:fields['-m']=list(fields['-m'])
                rows.append(fields)
    except ValueError:return {'refused':'KERNEL-POLICY-UNVERIFIED'}
    return {'ok':[chains,rows]}


def python_prepare(uci,mangle):
    order,local_tunnel,local_mark=f.uci_rules(uci.decode('utf8','replace'))
    text=mangle.decode('utf8','replace')
    payload,old_first,changed=f.plan(text,order,local_tunnel,local_mark)
    return {'order':order,'local_tunnel':local_tunnel,'local_mark':local_mark,'payload_hex':payload.encode('utf8').hex(),
            'old_first':old_first,'changed':changed,'old_mark':f.mark_of(text,old_first) if changed else None}


# --- encoding cases ------------------------------------------------------------------------------------
def decode_cases(rng):
    pool=[0x00,0x41,0x7f,0x80,0x8f,0x90,0x9f,0xa0,0xbf,0xc1,0xc2,0xdf,0xe0,0xed,0xef,0xf0,0xf4,0xf5,0xff]
    cases=[bytes([a]) for a in pool]+[bytes([a,b]) for a in pool for b in pool]
    cases+=[bytes([a,b,c]) for a in (0xe0,0xe1,0xed,0xef,0xf0,0xf4) for b in pool for c in pool]
    cases+=[bytes(rng.choice(pool) for _ in range(rng.randint(4,9))) for _ in range(3000)]
    return cases


def float_cases(rng):
    values=[0.0,-0.0,5e-324,2.2250738585072014e-308,1.7976931348623157e308,0.1,1/3,1e16,1e15,1e-5,1e-4,1e22,1e23]
    values+=[2.0**e for e in range(-1074,1024)]+[-(2.0**e) for e in range(-1074,1024,7)]
    values+=[10.0**e for e in range(-300,301)]
    values+=[1761830400+rng.random() for _ in range(500)]+[round(1761830400+rng.random(),3) for _ in range(200)]
    values+=[rng.random()*1000 for _ in range(300)]+[float(rng.getrandbits(rng.randint(1,64))) for _ in range(300)]
    for _ in range(4000):
        bits=rng.getrandbits(64)
        if (bits>>52)&0x7ff==0x7ff:bits^=1<<62
        values.append(struct.unpack('>d',struct.pack('>Q',bits))[0])
    return values


def random_string(rng):
    alphabet=['a','Z','0',' ','"','\\','/','\x00','\x01','\x1f','\x7f','\x80','\xe9','\u0416','\u2028','\ufeff',
              '\uffff','\U0001F600','\U0010FFFF','\ud800','\udbff','\udc00','\udfff']
    return ''.join(rng.choice(alphabet) for _ in range(rng.randrange(6)))


def random_value(rng,depth=0):
    kind=rng.randrange(8 if depth<4 else 5)
    if kind==0:return rng.choice([None,True,False])
    if kind==1:return rng.choice([0,1,-1,2**53,-(2**53),rng.randrange(-10**6,10**6),rng.randrange(2**53)])
    if kind==2:return rng.choice([0.0,-0.0,1e-7,1e22,2.0,rng.random(),1761830400+rng.random(),float(rng.randrange(10**9)),
                                  struct.unpack('>d',struct.pack('>Q',rng.getrandbits(63)&~(0x7ff<<52)|(rng.randrange(2046)<<52)))[0]])
    if kind in (3,4):return random_string(rng)
    if kind==5:return [random_value(rng,depth+1) for _ in range(rng.randrange(4))]
    return {random_string(rng):random_value(rng,depth+1) for _ in range(rng.randrange(4))}


def json_texts(rng):
    texts=[]
    for _ in range(400):
        value=random_value(rng)
        text=json.dumps(value)
        try:
            if rng.random()<0.5:text=json.dumps(value,ensure_ascii=False,indent=rng.choice([None,1]));text.encode('utf8')
        except UnicodeEncodeError:text=json.dumps(value)
        texts.append(text)
    texts+=['{"a":1,"a":2}','NaN','[Infinity]','-Infinity','1e400','[1,]','01','"\x01"','\ufeff{}','{} x','','"\\x"',
            '"\\u12"','{"a" 1}','[1 2]','tru','nul','1.','1.e5','-','1e','1e+','[1e5]','[-0]','[-0.0]','[1E-7]',
            ' \t\r\n{ "b" : [ ] , "a" : { } }\n','"\\ud800\\u0041"','"\\udc00\\ud800"','"\\ud83d\\ude00"','"\\uD83D\\uDE00"',
            '['*64+']'*64,'['*65+']'*65,'['*66+']'*66,'{"x":'*64+'1'+'}'*64,'{"x":'*65+'1'+'}'*65,'"\x7f"','{"":null}',
            '9007199254740992','-9007199254740992','[0.30000000000000004]','[1e-400]','[123456789012345678901234567890.0]']
    return texts


def read_json_text(text):
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'value.json';path.write_bytes(text.encode('utf8','surrogatepass'))
        return read_json(path)


def python_json(text):
    """agent.read_json(): the parse the journal reader uses; None when it refuses."""
    with tempfile.TemporaryDirectory() as directory:
        path=Path(directory)/'value.json';path.write_bytes(text.encode('utf8','surrogatepass'))
        try:value=read_json(path)
        except ValueError:return None
    return json.dumps(value,sort_keys=True,separators=(',',':'))


# --- reorder reference: the real Linux.reorder over a fake policy --------------------------------------
class FakeLinux(n.Linux):
    def __init__(self,names):
        super().__init__()
        self.sections=[{'.name':name,'.type':'rule','.anonymous':False,'enabled':'1'} for name in names]
        self.calls=[]
    def policy(self):return {'sections':[dict(s) for s in self.sections]}


def python_reorder(current,desired):
    backend=FakeLinux(current)
    def write(args,timeout=5):
        if args[:2]==['uci','reorder']:
            name,index=args[2].split('.',1)[1].split('=');index=int(index)
            section=next(s for s in backend.sections if s['.name']==name)
            backend.sections.remove(section);backend.sections.insert(index,section);backend.calls.append([name,index])
        return b''
    backend.reorder(desired,write_command=write)
    return backend.calls,[s['.name'] for s in backend.sections]


def reorder_cases(rng):
    cases=[[['a','b'],['b','a']],[['a','b','c'],['c','b','a']],[['a','b'],['a','c']],[['a','b'],['a','b','b']],[['a','b'],['a','b']]]
    for _ in range(300):
        names=['s%d'%i for i in range(rng.randint(2,7))];desired=list(names);rng.shuffle(desired)
        cases.append([names,desired])
    return cases


def run_lua(cases):
    with tempfile.TemporaryDirectory() as directory:
        source=Path(directory)/'cases.json';target=Path(directory)/'results.json'
        source.write_text(json.dumps(cases),encoding='ascii')
        result=subprocess.run([LUA,str(DRIVER),str(source),str(target)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=600)
        if result.returncode:raise AssertionError(result.stderr.decode(errors='replace'))
        return json.loads(target.read_text(encoding='utf8'))


@unittest.skipUnless(LUA,'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class LuaSuites(unittest.TestCase):
    def test_plain_lua_suites(self):
        scripts=sorted((HERE/'lua').glob('test_*.lua'))
        self.assertGreaterEqual(len(scripts),5)
        for script in scripts:
            with self.subTest(script.name):
                result=subprocess.run([LUA,str(script)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=300)
                self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode(errors='replace'))
                self.assertIn(b'tests OK',result.stdout)


@unittest.skipUnless(LUA,'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class SameAsPython(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        rng=random.Random(SEED)
        cls.cases=fast_policy_cases()
        cls.cases['decode']=[b.hex() for b in decode_cases(rng)]
        cls.floats=float_cases(rng)
        cls.cases['repr']=[struct.pack('>d',x).hex() for x in cls.floats]
        cls.cases['json']=json_texts(rng)
        cls.cases['sha256']=[bytes(rng.getrandbits(8) for _ in range(k)).hex() for k in list(range(0,130))+[200,511,512,1000,4096]]
        cls.cases['reorder']=reorder_cases(rng)
        cls.cases['parse_mangle']=mangle_parse_cases(rng)
        started=time.monotonic();cls.results=run_lua(cls.cases);cls.seconds=time.monotonic()-started

    def compare(self,name,reference):
        cases,results=self.cases[name],self.results[name]
        self.assertEqual(len(cases),len(results))
        mismatches=[]
        for case,lua in zip(cases,results):
            python=reference(case)
            if not same_outcome(python,lua):mismatches.append((case,python,lua))
        self.assertEqual(mismatches[:3],[],'%d of %d %s cases differ'%(len(mismatches),len(cases),name))
        return results

    def test_uci_rules(self):
        results=self.compare('uci_rules',lambda text:python_outcome(f.uci_rules,text))
        self.assertEqual(results[0],{'ok':[['4192','5841'],'10100','0xb000']})
        codes={next(iter(r.values())) for r in results if 'unsupported' in r}
        self.assertEqual(codes,{'FAST-RULES','FAST-LOCAL-RULE'})

    def test_plan_and_every_refusal_of_the_python_tests(self):
        results=self.compare('plan',lambda c:python_outcome(f.plan,*c))
        codes={r['unsupported'] for r in results if 'unsupported' in r}
        self.assertEqual(codes,{'FAST-ROUTE-CHAIN','FAST-LOCAL-CHAIN'})
        # the three refused mangles of test_fast_policy (cases 2..4 of mangle_variants) refuse in Lua too
        for index in (2,3,4):
            row=self.cases['plan'].index([mangle_variants()[index],['4192','5841'],'10100','0xb000'])
            self.assertIn('unsupported',results[row])
        self.assertGreater(sum(1 for r in results if 'ok' in r and r['ok'][2]),10)

    def test_mark_of(self):
        results=self.compare('mark_of',lambda c:python_outcome(f.mark_of,*c))
        self.assertEqual(results[0],{'ok':['0x1000']})
        self.assertTrue(any(r.get('unsupported')=='FAST-MARK' for r in results))

    def test_prepare_from_command_bytes(self):
        reference=lambda c:python_outcome(lambda u,m:(python_prepare(bytes.fromhex(u),bytes.fromhex(m)),),*c)
        results=self.compare('prepare',reference)
        self.assertTrue(results[0]['ok'][0]['changed']);self.assertEqual(results[0]['ok'][0]['old_mark'],'0x1000')

    def test_decode_replace(self):
        self.compare('decode',lambda h:bytes.fromhex(h).decode('utf8','replace').encode('utf8').hex())

    def test_float_repr(self):
        mismatches=[(x,repr(x),lua) for x,lua in zip(self.floats,self.results['repr']) if repr(x)!=lua]
        self.assertEqual(mismatches[:5],[],'%d of %d floats differ'%(len(mismatches),len(self.floats)))

    def test_canonical_json_and_digest(self):
        known_divergence={'[123456789012345678901234567890.0]'}  # none: a float, kept for the record
        for text,lua in zip(self.cases['json'],self.results['json']):
            python=python_json(text)
            with self.subTest(text=text[:60]):
                if python is None:self.assertIn('error',lua)
                elif text in known_divergence:continue
                else:
                    self.assertEqual(lua.get('ok'),python)
                    self.assertEqual(lua['sha256'],__import__('hashlib').sha256(python.encode()).hexdigest())

    def test_sha256(self):
        import hashlib
        self.compare('sha256',lambda h:hashlib.sha256(bytes.fromhex(h)).hexdigest())

    def test_parse_mangle_and_fields(self):
        results=self.compare('parse_mangle',python_parse)
        self.assertIn('ok',results[0]);self.assertGreater(sum('refused' in r for r in results),10)

    def test_canonical_text_is_native_history_encoded(self):
        checked=0
        for text,lua in zip(self.cases['json'],self.results['json']):
            if 'ok' in lua and python_json(text) is not None:
                self.assertEqual(lua['ok'].encode(),encoded(read_json_text(text)));checked+=1
        self.assertGreater(checked,300)

    def test_reorder_moves(self):
        self.compare('reorder',lambda c:python_outcome(python_reorder,*c))

    def test_one_lua_process_is_fast(self):
        total=sum(len(v) for v in self.cases.values())
        self.assertGreater(total,15000)
        self.assertLess(self.seconds,300)


def valid_journal():
    return {'tx':'0123456789abcdef0123456789abcdef','phase':'APPLYING','before':['cfg0a1b2c','rule_b','cfg0c3d4e'],
            'after':['rule_b','cfg0a1b2c','cfg0c3d4e'],'hash':'0'*64,'source':'wg-main','target':'ovpn:res','deadline':1761830520.25,
            'monotonic_deadline':12345.678901234,'lease_monotonic_until':12400.5,'trial':False,'trial_nonce':'pair-1','pid':None,
            'started':1761830400.1234567,'vendor_identity':'ab'*32,'process_bindings':{'wgclient1':4096,'ovpnclient2':45056},
            'proof_scope':'router-probed-ipv4','control_revision':'cd'*16,'manual_request_id':'ef'*16,'kernel_before_fingerprint':'12'*32,
            'kernel_before_verified':True,'forward_policy_touched':True,'rtp_dispatched':True,'transition_source':'manual','manual_instant':True,
            'failure_detail':{'text':'\u041f\u0440\u0438\u0432\u0435\u0442 \u2028 /slash "q" \\ \x01 \U0001F600 \ud800',
                              'nested':[1,2.0,-0.0,1e-7,1e22,[],{},None,True],'big':9007199254740992,'small':-3}}


@unittest.skipUnless(LUA,'Lua 5.1 runtime absent; use homensai-vpn-python39:local')
class JournalBothWays(unittest.TestCase):
    """native_switch writes, Lua reads and writes the next phase, native_switch reads it back."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        for name,value in (('RUNTIME',self.root/'run'),('PERSIST',self.root/'persist')):
            p=patch.object(n,name,value);p.start();self.addCleanup(p.stop)
        (self.root/'persist').mkdir(mode=0o700)

    def read_python(self,path):
        with patch.object(n,'JOURNAL',path):return n.journal_read()

    def test_python_journal_held_by_lua_reads_back_in_python(self):
        written=self.root/'persist/native-transaction.json'
        journal=valid_journal()
        with patch.object(n,'JOURNAL',written):n.journal_write(journal)  # adds phase_evidence like the real write
        held=self.root/'persist/held.json'
        result=run_lua({'journal_hold':[{'input':str(written),'output':str(held),'now':1761830401.5,'instant':0.412}]})
        digest=result['journal_hold'][0]['ok'][0]
        value=self.read_python(held)
        self.assertEqual(digest,n.digest(value))
        self.assertEqual((value['phase'],value['reason'],value['reserve_healthy']),('HELD-ON-RESERVE','OPERATOR-MANUAL',True))
        self.assertIs(type(value['confirmed']),float);self.assertEqual(value['instant_seconds'],0.412)
        self.assertEqual(value['phase_evidence'],journal['phase_evidence']+[{'phase':'HELD-ON-RESERVE','time':1761830401.5}])
        for key in journal:
            if key not in ('phase','phase_evidence'):
                self.assertEqual(json.dumps(value[key],sort_keys=True),json.dumps(journal[key],sort_keys=True),key)  # same types too

    def test_lua_built_journal_is_read_by_python(self):
        text=json.dumps(dict(valid_journal(),phase='HELD-ON-RESERVE'))
        output=self.root/'persist/fresh.json'
        result=run_lua({'journal_fresh':[{'value':text,'output':str(output),'now':1761830402.0}]})
        value=self.read_python(output)
        self.assertEqual(result['journal_fresh'][0]['ok'][0],n.digest(value))
        self.assertIs(type(value['pid']),type(None));self.assertIs(type(value['process_bindings']['wgclient1']),int)
        self.assertEqual(json.dumps(value['failure_detail'],sort_keys=True),json.dumps(valid_journal()['failure_detail'],sort_keys=True))

    def test_tampered_journal_is_refused_by_both(self):
        output=self.root/'persist/fresh.json'
        run_lua({'journal_fresh':[{'value':json.dumps(valid_journal()),'output':str(output),'now':1.0}]})
        output.write_bytes(output.read_bytes().replace(b'"wg-main"',b'"wg-mainx"'))
        with self.assertRaises(n.Refused):self.read_python(output)
        self.assertEqual(run_lua({'journal_read':[str(output)]})['journal_read'][0],{'refused':'JOURNAL-INTEGRITY-FAILED'})

    def test_lua_refuses_what_python_refuses(self):
        output=self.root/'persist/bad.json'
        for change in ({'phase':'DONE'},{'target':'wg-main'},{'pid':1},{'started':True},{'hash':'x'}):
            bad=dict(valid_journal(),**change)
            with self.assertRaises(n.Refused) as python:n.validate_journal(dict(bad))
            lua=run_lua({'journal_fresh':[{'value':json.dumps(bad),'output':str(output),'now':1.0}]})['journal_fresh'][0]
            self.assertEqual(lua,{'refused':str(python.exception)},change)


@unittest.skipUnless(LUA and shutil.which('flock'),'Lua 5.1 or flock(1) absent; use homensai-vpn-python39:local')
class ControlLockWithPython(unittest.TestCase):
    """runner.lua's lock is the same flock(2) lock as auto_control.control_lock."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.dir=Path(self.tmp.name)

    def client(self,*args,**kwargs):
        return subprocess.Popen([LUA,str(CLIENT),str(self.dir)]+list(args),stdout=subprocess.PIPE,**kwargs)

    def test_python_holder_blocks_lua(self):
        from auto_control import control_lock
        with control_lock(self.dir):
            process=self.client('wait');time.sleep(.5)
            self.assertIsNone(process.poll(),'Lua must wait for the Python holder')
        output,_=process.communicate(timeout=10);process.stdout.close()
        self.assertEqual(output,b'acquired\n')

    def test_lua_holder_blocks_python(self):
        process=self.client('hold',stdin=subprocess.PIPE)
        self.assertEqual(process.stdout.readline(),b'held\n')
        fd=os.open(str(self.dir/'auto-control.lock'),os.O_RDWR)
        try:
            with self.assertRaises(BlockingIOError):fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            process.stdin.write(b'release\n');process.stdin.flush();process.wait(10)
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)  # released when Lua closed its descriptor
        finally:
            os.close(fd);process.stdin.close();process.stdout.close()

    def test_fenced_writer_checks_the_revision_under_the_lock(self):
        (self.dir/'auto-control-revision.json').write_text(json.dumps({'revision':'a'*32}))
        stale,_=self.client('fenced','b'*32).communicate(timeout=10)
        self.assertEqual(stale,b'CLIENT-STOP\n');self.assertFalse((self.dir/'ran').exists())
        fresh,_=self.client('fenced','a'*32).communicate(timeout=10)
        self.assertEqual(fresh,b'ok\n');self.assertTrue((self.dir/'ran').exists())

    def fake_programs(self,fail_restore=False):
        bin_dir=self.dir/'bin';bin_dir.mkdir(exist_ok=True)
        programs={'iptables-restore':'cat > "%s/restored"; exit %d'%(self.dir,4 if fail_restore else 0),
                  'conntrack':'printf "%%s\\n" "$@" > "%s/conntrack.args"; exit 1'%self.dir,
                  'uci':'printf "%%s\\n" "$@" > "%s/uci.args"; cat > "%s/uci.batch"; exit 0'%(self.dir,self.dir)}
        for name,body in programs.items():
            path=bin_dir/name;path.write_text('#!/bin/sh\n'+body+'\n');path.chmod(0o755)
        probe=bin_dir/'probe';probe.write_text('#!/bin/sh\nexit 0\n');probe.chmod(0o755)
        try:subprocess.run([str(probe)],timeout=5,check=True)
        except (OSError,subprocess.SubprocessError):
            # The offline CI sandbox mounts its tmpfs noexec: fake programs cannot run there.
            self.skipTest('temporary directory is mounted noexec: fake programs cannot run')
        return dict(os.environ,PATH=str(bin_dir)+':'+os.environ.get('PATH',''))

    def run_client(self,*args,env=None):
        return subprocess.run([LUA,str(CLIENT),str(self.dir)]+list(args),stdout=subprocess.PIPE,env=env,timeout=20).stdout.decode()

    def test_runner_constant_commands_and_pipes(self):
        self.assertEqual(self.run_client('capture').split('\n')[:3],['exact','COMMAND-FAILED','unknown'])
        env=self.fake_programs()
        payload='*mangle\n:ROUTE_POLICY - [0:0]\n-A ROUTE_POLICY -m comment --comment "$(touch PWNED)" -j RETURN\nCOMMIT\n'
        self.assertEqual(self.run_client('restore',payload,env=env),'ok\n')
        self.assertEqual((self.dir/'restored').read_text(),payload)  # through the pipe, byte for byte
        self.assertEqual(self.run_client('restore','x',env=self.fake_programs(fail_restore=True)),'COMMAND-FAILED\n')
        self.assertEqual(self.run_client('conntrack','0x1000',env=env),'false\n')  # exit 1: nothing deleted
        self.assertEqual((self.dir/'conntrack.args').read_text(),'-D\n-m\n0x1000/0xf000\n')
        for bad in ('0x1000; touch PWNED','$(touch PWNED)','0x123456789','1000'):
            self.assertEqual(self.run_client('conntrack-bad',bad,env=env),'FAST-MARK\n')
        self.assertEqual(self.run_client('batch',env=env),'ok\n')
        self.assertEqual((self.dir/'uci.args').read_text(),'batch\n')
        self.assertEqual((self.dir/'uci.batch').read_text(),'reorder route_policy.cfg01=1\ncommit route_policy\n')
        self.assertFalse(list(Path('.').glob('PWNED'))+list(self.dir.glob('PWNED')))
        self.assertEqual([p.name for p in self.dir.iterdir() if p.name.startswith('.')],[])  # status/mark/batch files removed

    def test_runner_files_hash_and_lock_descriptor(self):
        text='{"x":"\u2028"}'
        self.assertEqual(self.run_client('sha',text).strip(),__import__('hashlib').sha256(text.encode()).hexdigest())
        self.assertEqual(self.run_client('atomic',text),'same\n')
        self.assertEqual((self.dir/'state.json').stat().st_mode&0o777,0o600)
        self.assertEqual([p.name for p in self.dir.iterdir() if p.name.endswith('.pending')],[])
        self.assertEqual(self.run_client('fds'),'closed\n')

if __name__=='__main__':unittest.main()
