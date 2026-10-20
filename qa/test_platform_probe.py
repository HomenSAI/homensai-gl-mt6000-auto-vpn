import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('platform_probe',Path(__file__).resolve().parents[1]/'scripts/classify-platform.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


class PlatformProbeTests(unittest.TestCase):
    def report(self,**changes):
        row=dict(schema='1',board_name='glinet,gl-mt3000',model='GL.iNet GL-MT3000',gl_firmware='4.8.2',openwrt_target='mediatek/filogic',
                 architecture='aarch64',tool_opkg='PRESENT',tool_apk='MISSING',overlay_free_kib='50000',
                 memory_available_kib='250000',openwrt_version='21.02-SNAPSHOT',kernel='5.4.211',
                 python_version='Python 3.11.6',lua_version='Lua 5.1.5 Copyright (C) 1994-2012 Lua.org, PUC-Rio',
                 nft_version='nftables v1.0.8 (Old Doc Yak)',package_architectures='arch all 1;arch aarch64_cortex-a53 10;',
                 bootloader_partition='PRESENT',bootloader_version='UNKNOWN',recovery_backup='NOT_OBTAINED',
                 native_switch='REFUSED_UNCERTIFIED_TARGET',installation='NOT_AUTHORIZED_BY_PROBE')
        for name in module.PACKAGES:row['package_'+name]='INSTALLED'
        for name in module.TOOLS:
            if name not in ('opkg','apk'):row['tool_'+name]='PRESENT'
        for path in module.VENDOR_PATHS:row['sha256:'+path]='a'*64
        row.update(changes)
        return '\n'.join(k+'\t'+v for k,v in row.items())

    def test_complete_synthetic_report_never_authorizes_install_or_native(self):
        result=module.classify(self.report())
        self.assertEqual(result['result'],'MONITOR-CANDIDATE-REVIEW')
        self.assertFalse(result['installation_authorized']);self.assertFalse(result['bootloader_verified'])
        self.assertEqual(result['native_switch'],'REFUSED_UNCERTIFIED_TARGET')

    def test_wrong_board_missing_storage_or_dependencies_blocks(self):
        for change in ({'board_name':'glinet,gl-mt6000'},{'gl_firmware':''},{'tool_apk':'PRESENT'},
                       {'overlay_free_kib':'unknown'},{'package_python3':'MISSING'},{'architecture':'UNKNOWN'}):
            with self.subTest(change=change):self.assertEqual(module.classify(self.report(**change))['result'],'BLOCKED')

    def test_ambiguous_or_oversized_reports_refuse(self):
        for text in ('schema\t1\nschema\t1','schema\t2','not tsv',self.report()+'\nfield\tbad\tdata','x'*16385):
            with self.subTest(text=text[:40]),self.assertRaises(ValueError):module.classify(text)

    def test_every_missing_observation_blocks(self):
        lines=self.report().splitlines()
        for key in module.REQUIRED-{'schema'}:
            with self.subTest(key=key):
                text='\n'.join(line for line in lines if not line.startswith(key+'\t'))
                self.assertEqual(module.classify(text)['result'],'BLOCKED')

    def test_contradictory_or_invalid_observations_block(self):
        for change in ({'model':'GL.iNet GL-MT6000'},{'model':'GL.iNet GL-MT3000 / GL-MT6000'},
                       {'openwrt_target':'ath79/generic'},
                       {'tool_python3':'MISSING'},{'python_version':'Python 2.7.18'},
                       {'nft_version':''},{'package_architectures':'arch mips_24kc 10;'},
                       {'bootloader_version':'verified'},{'recovery_backup':'VERIFIED'},
                       {'installation':'AUTHORIZED'},{'native_switch':'ENABLED'},
                       {'sha256:'+module.VENDOR_PATHS[0]:'UNKNOWN'},{'tool_apk':'UNKNOWN'},
                       {'architecture':'aarch64_be'},{'memory_available_kib':'0'}):
            with self.subTest(change=change):self.assertEqual(module.classify(self.report(**change))['result'],'BLOCKED')

    def test_control_characters_and_unexpected_fields_refuse(self):
        for text in (self.report(model='GL.iNet GL-MT3000\x00'),self.report()+'\npassword\tsecret'):
            with self.subTest(text=text[:40]),self.assertRaises(ValueError):module.classify(text)
