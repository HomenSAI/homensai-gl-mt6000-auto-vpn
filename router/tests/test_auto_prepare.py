"""Pressing Auto repairs restart-free preparation by itself with the reviewed writer."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'files/usr/lib/homensai-vpn'))
import preparation_control as prep


class AutoPrepare(unittest.TestCase):
    def run_with(self,checks,results):
        states=iter(checks);applied=[]
        def snapshot(settings=None):return {'checks':next(states)}
        def apply(arguments,automatic=False):
            self.assertTrue(automatic);applied.append(arguments['action']);return results.pop(0)
        with patch('preparation_status.snapshot',side_effect=snapshot),patch.object(prep,'context',side_effect=lambda a:{'action':a}),patch.object(prep,'apply',side_effect=apply),patch.object(prep,'control_lock'):
            return prep.auto_prepare({},'a'*32),applied

    def test_stock_boot_is_repaired_and_start_continues(self):
        result,applied=self.run_with([[{'code':'PREP-STOCK-VPN-BOOT','state':'fail'}],[{'code':'PREP-STOCK-VPN-BOOT','state':'pass'}]],[{'applied':True,'restart_required':False}])
        self.assertEqual(applied,['vpn-boot']);self.assertIsNone(result['code']);self.assertEqual(result['repaired'],['PREP-STOCK-VPN-BOOT'])

    def test_nothing_to_do_writes_nothing(self):
        result,applied=self.run_with([[{'code':'PREP-HNAT-CONFIG','state':'pass'}]],[])
        self.assertEqual(applied,[]);self.assertIsNone(result['code'])

    def test_refused_or_restart_only_fix_is_a_named_refusal(self):
        result,_=self.run_with([[{'code':'PREP-STOCK-VPN-BOOT','state':'fail'}]],[{'applied':False,'code':'PREPARATION-STALE-REVIEW'}])
        self.assertEqual(result['code'],'PREPARATION-STALE-REVIEW')
        result,_=self.run_with([[{'code':'PREP-SFE-BOOT','state':'fail'}]],[{'applied':True,'restart_required':True}])
        self.assertEqual(result['code'],'PREPARATION-RESTART-REQUIRED')
        result,applied=self.run_with([[{'code':'PREP-SFE-AUTOLOAD','state':'fail'}]],[])
        self.assertEqual(applied,[]);self.assertIsNone(result['code'],'not auto-repairable: the ordinary Start check names it')


if __name__=='__main__':unittest.main()
