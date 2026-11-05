"""LAN DNS through both tunnels (dns_dual.py): the shared cases of dns_dual_cases.json (the same as
lua/test_dns_dual.lua), follow() over a real mangle graph, the real file access in a temp directory, and the Linux
backend wiring (dns_mark_follow installs, unguard removes)."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))
import dns_dual as dd  # noqa: E402
from kernel_policy import parse_mangle,fields  # noqa: E402

RAW=(HERE/'dns_dual_cases.json').read_text(encoding='utf8').replace('@H@',dd.HEADER)
CASES=json.loads(RAW)
MANGLE='\n'.join(['*mangle',':PREROUTING ACCEPT [0:0]',':ROUTE_POLICY - [0:0]',':TUNNEL4192_ROUTE_POLICY - [0:0]',
  ':TUNNEL5841_ROUTE_POLICY - [0:0]',
  '-A ROUTE_POLICY -m connmark ! --mark 0x0/0xf000 -j CONNMARK --restore-mark --nfmask 0xf000 --ctmask 0xf000',
  '-A ROUTE_POLICY -p udp -m addrtype --dst-type LOCAL -m udp --dport 53 -j RETURN',
  '-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL5841_ROUTE_POLICY',
  '-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL4192_ROUTE_POLICY',
  '-A TUNNEL4192_ROUTE_POLICY -m comment --comment "TUNNEL4192 rule for set mark" -m mark --mark 0x0/0xf000 -j MARK --set-xmark 0xb000/0xf000',
  '-A TUNNEL4192_ROUTE_POLICY -m mark --mark 0x0/0xf000 -j DROP',
  '-A TUNNEL5841_ROUTE_POLICY -m comment --comment "TUNNEL5841 rule for set mark" -m mark --mark 0x0/0xf000 -j MARK --set-xmark 0x1000/0xf000',
  '-A TUNNEL5841_ROUTE_POLICY -m mark --mark 0x0/0xf000 -j DROP','COMMIT',''])
ON="config main 'main'\n    option dns_dual '1'\n"


class Fake:
    """Files as a dict (None = absent), commands answered from a table, every command recorded."""
    def __init__(self,files=None,run=None,fail_write=()):
        self.files=dict(CASES['gl_files'])
        for path,text in (files or {}).items():
            if text is None:self.files.pop(path,None)
            else:self.files[path]=text
        self.answers=dict(CASES['run_default']);self.answers.update(run or {})
        self.fail_write=set(fail_write);self.calls=[]
    def read(self,path):return self.files.get(path)
    def write(self,path,text):
        if path in self.fail_write:raise OSError('write')
        self.files[path]=text
    def remove(self,path):self.files.pop(path,None)
    def run(self,argv,timeout):
        self.calls.append(list(argv))
        rc,out=self.answers.get(' '.join(argv),[0,''])
        return rc,out
    def io(self):return {'read':self.read,'write':self.write,'remove':self.remove,'run':self.run}


class SharedCases(unittest.TestCase):
    def tearDown(self):dd.MEMO.clear()
    def test_enabled(self):
        for text,expected in CASES['enabled']:self.assertIs(dd.enabled(text),expected,repr(text))
    def test_instance_of(self):
        for mark,expected in CASES['instance_of']:self.assertEqual(dd.instance_of(mark),expected,repr(mark))
    def test_valid_server(self):
        for entry,expected in CASES['valid_server']:self.assertIs(dd.valid_server(entry),expected,repr(entry))
    def test_servers_of(self):
        for case in CASES['servers_of']:
            self.assertEqual(dd.servers_of(case['config'],case['files'].get),case['expected'],case['name'])
    def test_snippet(self):
        for case in CASES['snippet']:self.assertEqual(dd.snippet(case['peers']),case['expected'])
    def check(self,case,result,fake):
        expected=case['expected']
        self.assertEqual(result,expected['result'],case['name'])
        for path,text in expected['files'].items():self.assertEqual(fake.files.get(path),text,case['name']+': '+path)
        self.assertEqual(fake.calls,expected['calls'],case['name'])
        self.assertEqual(dd.MEMO,expected['memo'],case['name'])
    def test_sync(self):
        for case in CASES['sync']:
            dd.MEMO.clear();dd.MEMO.update(case.get('memo') or {})
            fake=Fake(case['files'],case['run'],case.get('fail_write',()))
            self.check(case,dd.sync(case['marks'],case['active'],**fake.io()),fake)
    def test_off(self):
        for case in CASES['off']:
            dd.MEMO.clear();dd.MEMO.update(case.get('memo') or {})
            fake=Fake(case['files'],case['run'])
            self.check(case,dd.off(**fake.io()),fake)
    def test_every_written_line_is_bound_to_a_tunnel(self):
        """The leak property: a snippet has only `all-servers`, the header and server=<IPv4>[#port]@<GL tunnel>."""
        for case in CASES['sync']:
            dd.MEMO.clear()
            fake=Fake(case['files'],case['run'],case.get('fail_write',()))
            dd.sync(case['marks'],case['active'],**fake.io())
            for path,text in fake.files.items():
                if not path.endswith('/'+dd.FILE):continue
                for line in text.rstrip('\n').split('\n'):
                    if line in (dd.HEADER,'all-servers'):continue
                    self.assertRegex(line,r'^server=[0-9.#]+@(wgclient|ovpnclient)[1-5]$')
                    server,device=line[7:].split('@')
                    self.assertTrue(dd.valid_server(server),line)
                    self.assertNotEqual(path,dd.CONFDIR+device+'/'+dd.FILE,'own tunnel listed: '+line)


class Follow(unittest.TestCase):
    def tearDown(self):dd.MEMO.clear()
    def test_marks_from_chains(self):
        self.assertEqual(dd.marks_from_chains(parse_mangle(MANGLE),fields),['0x1000','0xb000'])
        self.assertEqual(dd.marks_from_chains({},fields),[])
        self.assertEqual(dd.marks_from_chains(None,fields),[])
    def test_option_off_removes_leftovers(self):
        fake=Fake({'/tmp/dnsmasq.d.wgclient1/'+dd.FILE:dd.HEADER+'\nall-servers\nserver=1.1.1.1@ovpnclient2\n',
                   dd.SETTINGS:"config main 'main'\n    option dns_dual '0'\n"})
        result=dd.follow(parse_mangle(MANGLE),fields,'0x1000',**fake.io())
        self.assertEqual((result['enabled'],result['changed'],result['code']),(False,1,None))
        self.assertNotIn('/tmp/dnsmasq.d.wgclient1/'+dd.FILE,fake.files)
    def test_option_missing_means_off(self):
        fake=Fake()
        result=dd.follow(parse_mangle(MANGLE),fields,'0x1000',**fake.io())
        self.assertEqual((result['enabled'],result['changed'],fake.calls),(False,0,[]))
    def test_option_on_installs_both(self):
        fake=Fake({dd.SETTINGS:ON})
        result=dd.follow(parse_mangle(MANGLE),fields,'0x1000',**fake.io())
        self.assertEqual((result['enabled'],result['changed'],result['code']),(True,2,None))
        self.assertEqual(fake.calls[1],['/etc/init.d/dnsmasq','restart','ovpnclient2'])
        self.assertEqual(fake.calls[4],['/etc/init.d/dnsmasq','restart','wgclient1'])
        self.assertIn('server=103.86.99.100@ovpnclient2',fake.files['/tmp/dnsmasq.d.wgclient1/'+dd.FILE])
        self.assertIn('DNS-DUAL-SYNC: enabled true changed 2 code none instances wgclient1+,ovpnclient2+',dd.summary(result))


class RealFiles(unittest.TestCase):
    def test_write_is_atomic_and_remove_verified(self):
        with tempfile.TemporaryDirectory() as base:
            path=os.path.join(base,dd.FILE)
            dd._default_write(path,'all-servers\n')
            self.assertEqual(dd._default_read(path),'all-servers\n')
            self.assertEqual(sorted(os.listdir(base)),[dd.FILE])  # no temporary file left
            dd._default_remove(path);dd._default_remove(path)
            self.assertIsNone(dd._default_read(path))
            Path(path).write_bytes(b'x'*(dd.MAX_TEXT+1))
            self.assertIsNone(dd._default_read(path))
            with self.assertRaises(OSError):dd._default_write(os.path.join(base,'missing','x'),'y')
    def test_run_reports_failure_as_255(self):
        self.assertEqual(dd._default_run(['/nonexistent/binary'],5),(255,''))


class Backend(unittest.TestCase):
    def setUp(self):
        import native_switch
        self.n=native_switch;self.backend=native_switch.Linux()
    def test_follow_after_dns_mark(self):
        self.backend.attested_mangle=MANGLE
        with mock.patch.object(self.backend,'dns_mark_sync',return_value={'active':'0xb000'}) as mark, \
             mock.patch('dns_dual.follow',return_value={'enabled':True,'code':None,'changed':0,'instances':[]}) as follow:
            self.assertEqual(self.backend.dns_mark_follow(),{'active':'0xb000'})
        mark.assert_called_once_with(MANGLE)
        self.assertEqual(follow.call_args[0][2],'0xb000')
        self.assertEqual(follow.call_args[0][0],parse_mangle(MANGLE))
        self.assertEqual(self.backend.dns_dual['enabled'],True)
    def test_no_attestation_no_follow(self):
        with mock.patch('dns_dual.follow') as follow:self.assertIsNone(self.backend.dns_mark_follow())
        follow.assert_not_called()
    def test_follow_never_raises_and_logs(self):
        with mock.patch('dns_dual.follow',side_effect=RuntimeError('boom')), \
             mock.patch.object(self.n.subprocess,'run') as run:
            result=self.backend.dns_dual_follow(MANGLE,None)
        self.assertEqual(result['code'],dd.UNVERIFIED)
        self.assertIn('DNS-DUAL-SYNC',run.call_args[0][0][-1])
    def test_unguard_removes_the_snippets(self):
        calls=[]
        with mock.patch.object(self.backend,'guard_exists',side_effect=[True,False]), \
             mock.patch.object(self.n,'command',side_effect=lambda argv,**k:calls.append(argv) or b''), \
             mock.patch('dns_dual.off',return_value={'enabled':False,'code':None,'changed':1,'instances':[]}) as off, \
             mock.patch.object(self.n.subprocess,'run'):
            self.backend.unguard()
        self.assertEqual(calls,[['nft','delete','table','inet',self.n.TABLE]])
        off.assert_called_once_with()
    def test_unguard_unconfirmed_keeps_the_snippets(self):
        with mock.patch.object(self.backend,'guard_exists',side_effect=[True,True]), \
             mock.patch.object(self.n,'command',return_value=b''), mock.patch('dns_dual.off') as off:
            with self.assertRaises(self.n.Refused):self.backend.unguard()
        off.assert_not_called()


if __name__=='__main__':unittest.main()
