"""LAN DNS follows the active channel (dns_mark.py) against a fake /proc/dns_mark tree in a temp directory: the same
cases as lua/test_dns_mark.lua, a Python-vs-Lua differential over the same trees, Linux.dns_mark_sync/follow, and the
channel_path projection."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))
import dns_mark as dm  # noqa: E402
from kernel_policy import parse_mangle,fields  # noqa: E402

LUA=shutil.which('lua5.1') or shutil.which('lua')
DUMP='Rule 5841: macs: none ifnames: none domains: none Mark: 0x1000\nRule 4192: macs: none ifnames: none domains: none Mark: 0xb000\n'
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
SWAPPED=MANGLE.replace('-j TUNNEL5841_ROUTE_POLICY\n-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL4192_ROUTE_POLICY',
                       '-j TUNNEL4192_ROUTE_POLICY\n-A ROUTE_POLICY -m addrtype ! --dst-type LOCAL -j TUNNEL5841_ROUTE_POLICY')


def tree(base,dump=DUMP,marks=None,directory_mark=None):
    root=Path(base)/'dns_mark';root.mkdir()
    (root/'dump').write_text(dump)
    for name in ('create','clear','debug'):(root/name).write_text('untouched-'+name)
    for rule,value in (('rule5841','0x1000'),('rule4192','0xb000'),('rule12x','0x1000')):
        (root/rule).mkdir()
        if rule==directory_mark:(root/rule/'mark').mkdir()
        else:(root/rule/'mark').write_text((marks or {}).get(rule,value)+'\n')
        for name in ('ifnames','macs','mac_flag','domains','domain_flag','dump'):(root/rule/name).write_text('')
    return root


def rules(result):return [(r['rule'],r['mark']) for r in result['rules']]


def never(*args):raise AssertionError('must not write')


class DnsMark(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.base=self.tmp.name
    def tearDown(self):self.tmp.cleanup()
    def untouched(self,root):
        for name in ('create','clear','debug'):self.assertEqual((root/name).read_text(),'untouched-'+name)
        self.assertEqual((root/'rule12x/mark').read_text(),'0x1000\n')

    def test_reserve_then_primary(self):
        root=tree(self.base)
        r=dm.sync('0xb000',root=root)
        self.assertEqual((r['active'],r['verified'],r['code'],r['written']),('0xb000',True,None,1))
        self.assertEqual(rules(r),[('rule5841','0xb000'),('rule4192','0xb000')])
        self.assertEqual([(root/x/'mark').read_text() for x in ('rule5841','rule4192')],['0xb000\n','0xb000\n'])
        self.assertIs(dm.LAST,r)
        r=dm.sync('0x1000',root=root)
        self.assertEqual((r['verified'],r['code'],r['written']),(True,None,2))
        self.assertEqual(rules(r),[('rule5841','0x1000'),('rule4192','0x1000')])
        self.untouched(root)

    def test_module_absent(self):
        dm.LAST=None
        r=dm.sync('0xb000',root='/nonexistent/dns_mark')
        self.assertEqual((r['verified'],r['code'],r['written'],r['rules']),(False,'DNS-MARK-UNAVAILABLE',0,[]))
        self.assertIsNone(dm.LAST);self.assertFalse(dm.available('/nonexistent/dns_mark'))

    def test_already_correct_no_write(self):
        root=tree(self.base,marks={'rule5841':'0xb000','rule4192':'45056'})
        r=dm.sync('0xb000',root=root,write=never)
        self.assertEqual((r['verified'],r['code'],r['written']),(True,None,0))
        self.assertEqual(rules(r),[('rule5841','0xb000'),('rule4192','0xb000')])
        self.assertEqual((root/'rule4192/mark').read_text(),'45056\n')

    def test_write_failure(self):
        root=tree(self.base,directory_mark='rule4192')
        r=dm.sync('0x1000',root=root)
        self.assertEqual((r['verified'],r['code'],r['written']),(False,'DNS-MARK-UNVERIFIED',0))
        self.assertEqual(rules(r),[('rule5841','0x1000'),('rule4192',None)])
        shutil.rmtree(str(root));root=tree(self.base)
        r=dm.sync('0xb000',root=root,write=lambda path,text:True)
        self.assertEqual((r['verified'],r['code'],r['written']),(False,'DNS-MARK-UNVERIFIED',1))
        self.assertEqual(rules(r),[('rule5841','0x1000'),('rule4192','0xb000')])

    def test_malformed_refused(self):
        root=tree(self.base,dump=DUMP+'Rule 12x: Mark: 0x1000\nRule -3: Mark: 0x1000\nrule 77: Mark: 0x1000\nRule 1234567890123: Mark: 0x1000\n')
        for bad in ('0xB000','b000','0x','0x123456789','0xb000;reboot',45056,None):
            r=dm.sync(bad,root=root,write=never)
            self.assertEqual((r['active'],r['verified'],r['code'],r['written'],r['rules']),(None,False,'DNS-MARK-UNVERIFIED',0,[]),bad)
        self.assertEqual(rules(dm.sync('0xb000',root=root)),[('rule5841','0xb000'),('rule4192','0xb000')])
        self.assertEqual([dm.valid_rule(x) for x in ('rule5841','rule12x','rule','../rule1')],[True,False,False,False])
        self.untouched(root)

    def test_formats(self):
        self.assertEqual([dm.parse(x) for x in ('0x1000\n','4096','Mark: 0xb000',' 0XB000 ')],[4096,4096,45056,45056])
        self.assertEqual([dm.parse(x) for x in ('0x','zz','','0x123456789',None)],[None]*5)
        self.assertEqual([dm.format_mark(x) for x in (4096,45056,0,-1,1.5)],['0x1000','0xb000',None,None,None])

    def test_active_from_first_jump(self):
        self.assertEqual(dm.active_from_chains(parse_mangle(MANGLE),fields),'0x1000')
        self.assertEqual(dm.active_from_chains(parse_mangle(SWAPPED),fields),'0xb000')
        self.assertIsNone(dm.active_from_chains({},fields))
        self.assertIsNone(dm.active_from_chains(parse_mangle(MANGLE.replace('-j MARK --set-xmark 0x1000/0xf000','-j DROP')),fields))

    def test_project(self):
        root=tree(self.base)
        r=dm.sync('0xb000',root=root)
        self.assertEqual(dm.project(json.loads(json.dumps(r))),r)
        edits=(lambda v:v.update(active='0xB000'),lambda v:v.update(code='X'),lambda v:v.update(verified=False),
               lambda v:v['rules'][0].update(rule='rule1;x'),lambda v:v['rules'][0].update(mark='4096'),lambda v:v.update(written=-1))
        for edit in edits:
            v=json.loads(json.dumps(r));edit(v);self.assertIsNone(dm.project(v))


DRIVER=r'''
package.path=arg[1]..'/?.lua;'..package.path
local canon=require('canon')
local dm=require('dns_mark')
local active=arg[3]
if active=='nil' then active=nil elseif active=='number' then active=45056 end
io.write(canon.encode(dm.sync(active,{root=arg[2]})),'\n')
'''


@unittest.skipUnless(LUA,'lua5.1 not installed')
class Parity(unittest.TestCase):
    """The same tree, the same call: the same result and the same files in Python and Lua."""
    def run_both(self,make,active):
        out=[]
        for side in ('python','lua'):
            with tempfile.TemporaryDirectory() as base:
                root=make(base)
                if side=='python':result=dm.sync(None if active in ('nil',) else 45056 if active=='number' else active,root=root)
                else:
                    driver=Path(base)/'driver.lua';driver.write_text(DRIVER)
                    text=subprocess.run([LUA,str(driver),str(LIB/'lua'),str(root),active],stdout=subprocess.PIPE,check=True,timeout=30).stdout
                    result=json.loads(text.decode())
                files={}
                for dirpath,dirnames,filenames in os.walk(str(root)):
                    for name in filenames:
                        path=Path(dirpath)/name;files[str(path.relative_to(root))]=path.read_text()
                out.append((result,files))
        return out

    def test_cases(self):
        cases=[(lambda b:tree(b),'0xb000'),(lambda b:tree(b),'0x1000'),(lambda b:tree(b,marks={'rule5841':'0xb000','rule4192':'45056'}),'0xb000'),
               (lambda b:tree(b,directory_mark='rule4192'),'0x1000'),(lambda b:tree(b,directory_mark='rule5841'),'0xb000'),
               (lambda b:tree(b,dump=DUMP+'Rule 12x: x\nRule 99: Mark: 0x1000\n'),'0xb000'),
               (lambda b:tree(b,marks={'rule5841':'Mark: 0x1000','rule4192':'garbage'}),'0x1000'),
               (lambda b:tree(b),'0xB000'),(lambda b:tree(b),'nil'),(lambda b:tree(b),'number'),
               (lambda b:Path(b)/'absent','0xb000')]
        for index,(make,active) in enumerate(cases):
            with self.subTest(case=index,active=active):
                python,lua=self.run_both(make,active)
                self.assertEqual(python,lua)


class Backend(unittest.TestCase):
    """native_switch.Linux: apply's sync reads the live kernel graph; follow() only after a verified attestation."""
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=tree(self.tmp.name)
        import native_switch
        self.n=native_switch
    def tearDown(self):self.tmp.cleanup()

    def test_sync_and_follow(self):
        backend=self.n.Linux()
        with mock.patch.object(dm,'ROOT',str(self.root)),mock.patch.object(self.n,'command',return_value=SWAPPED.encode()) as command,\
                mock.patch.object(self.n.subprocess,'run'):
            r=backend.dns_mark_sync()
            self.assertEqual((r['active'],r['verified'],r['written']),('0xb000',True,1))
            self.assertEqual(command.call_args[0][0],['iptables-save','-t','mangle'])
            self.assertIsNone(backend.dns_mark_follow())
            backend.attested_mangle=MANGLE
            command.reset_mock()
            r=backend.dns_mark_follow()
            self.assertEqual((r['active'],r['written']),('0x1000',2));command.assert_not_called()
            command.side_effect=OSError('x')
            self.assertEqual(backend.dns_mark_sync()['code'],'DNS-MARK-UNVERIFIED')
        with mock.patch.object(dm,'ROOT','/nonexistent/dns_mark'),mock.patch.object(self.n,'command') as command:
            self.assertEqual(backend.dns_mark_sync()['code'],'DNS-MARK-UNAVAILABLE');command.assert_not_called()

    def test_public_status_carries_the_block(self):
        import channel_path
        block={'active':'0xb000','rules':[{'rule':'rule5841','mark':'0xb000'}],'verified':True,'code':None,'written':1}
        status={'native_failover':{'channel_path':{'dns_mark':block}}}
        with mock.patch.object(channel_path,'route_status',side_effect=lambda s:{'confirmed':False}):
            self.assertEqual(channel_path.public_status(status)['dns_mark'],block)
            status['native_failover']['channel_path']['dns_mark']=dict(block,active='rm -rf')
            self.assertNotIn('dns_mark',channel_path.public_status(status))


if __name__=='__main__':unittest.main()
