"""BH2-01/02 (bug hunt 07.11.2026): malformed numeric UCI options take the documented default on every reader.

inventory.lua read numbers with Lua 5.1 tonumber (strtod), which also accepts 'nan', 'inf', '1e999', hex and exponent
spellings: a non-finite channel priority made cjson.encode raise (the whole inventory failed: Auto NATIVE-SYSTEM-001, no
settings page), and math.max(lo,math.min(hi,NaN)) is hi, so recovery_failures 'nan' meant 10 instead of the default 3.
Now one strict finite parser (the F-46/R2-03 grammar of recovery_settings.normalized / pair.recovery_normalized) is used
for every numeric option. The real helpers run under Lua 5.1 with a fake UCI; their output is compared with the Python
readers of the same raw strings: recovery_settings.normalized (the supervisor reads the raw options through
native_policy.lua), priority_config (1..1000, else 100), native_policy.lua for the detector options, and the stats_until
twins stats_mode.until / lua/accounting.lua stats.until_time.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
LIB=HERE.parent/'files/usr/lib/homensai-vpn'
sys.path.insert(0,str(LIB))
import recovery_settings  # noqa: E402
import stats_mode  # noqa: E402

LUA=shutil.which('lua5.1')
INVENTORY=LIB/'inventory.lua'
POLICY=LIB/'native_policy.lua'

MALFORMED=('nan','NaN','-nan','inf','-inf','Infinity','1e999','1e1','0x3c','0X10','2.5','3.0','','  ','1_0','abc','5x',
           '0000000003','1234567890','++3','.5','5.')
WELL_FORMED=('3',' 5 ','\t4\n','+7','-3','0','2','10','11','100','900','1800','4000','123456789','000000004')
RECOVERY=('failures','successes','cooldown','min_dwell','primary_successes','primary_stable','rescue_stable',
          'flap_halflife','flap_suppress','flap_reuse')
# every other numeric option of inventory.lua with its documented default (absent = this value)
DEFAULTS={'interval':10,'checkpoint':900,'probe_limit':16,'live_log_limit':2000,'history_days':7,'onboarding_version':0,
          'speed_budget_mib':8,'speed_duration':5,'speed_streams':2,'speed_daily_mib':128,'speed_busy_mbps':2,'native_duration':10,
          'telegram_interval':60,'telegram_hour':7,'reserve_probe_interval':0,'probe_level':0,'wan_recover_grace':30,
          'measure_interval':0,'ping_interval':60,'advisor_window':7}
DETECTOR=('hmm_theta','hmm_dur_b','return_pg','hmm_or_failures','turbo_beats')


def lua_string(value):return '"'+''.join('\\%d'%b for b in value.encode('utf-8'))+'"'


def lua_table(values):return '{'+','.join('[%s]=%s'%(lua_string(k),lua_string(v)) for k,v in sorted(values.items()))+'}'


def run_helper(helper,main,servers=()):
    rows=[dict(main,**{'.name':'main','.type':'main'})]+[dict(row,**{'.type':'server'}) for row in servers]
    text=("local rows={%s}\n"
          "package.preload['uci']=function() return {cursor=function() return {\n"
          " foreach=function(_,pkg,typ,fn) if pkg~='homensai_vpn' then return end\n"
          "  for _,s in ipairs(rows) do if typ==nil or s['.type']==typ then fn(s) end end end,\n"
          " get_all=function(_,pkg,section) if pkg=='homensai_vpn' and section=='main' then return rows[1] end end,\n"
          " get=function() return nil end} end} end\n"
          "local helper=arg[1];arg={[0]=helper};dofile(helper)\n")%','.join(lua_table(r) for r in rows)
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'run.lua';path.write_text(text,encoding='utf-8')
        out=subprocess.run([LUA,str(path),str(helper)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
    if out.returncode:raise AssertionError(out.stderr.decode())
    return json.loads(out.stdout.decode().strip().splitlines()[-1])


def strict_int(raw):
    """The F-46/R2-03 grammar (recovery_settings.normalized): the integer, or None when malformed."""
    return int(raw) if re.fullmatch(r'\s*[+-]?[0-9]{1,9}\s*',raw) else None


@unittest.skipUnless(LUA,'Lua 5.1 runtime absent; use homensai-vpn-python39:night')
class InventoryStrictNumbers(unittest.TestCase):
    def test_finding_vectors(self):
        for main,expected in (({'recovery_failures':'nan','recovery_cooldown':'nan','interval':'nan'},(3,60,10)),
                              ({'recovery_failures':'-inf','recovery_cooldown':'0x3c','interval':'1e1'},(3,60,10)),
                              ({'recovery_failures':'1','recovery_cooldown':'61','interval':'15'},(2,61,15))):
            s=run_helper(INVENTORY,main)['settings']
            self.assertEqual((s['recovery_failures'],s['recovery_cooldown'],s['interval']),expected,main)

    def test_non_finite_priority_no_longer_breaks_the_inventory(self):
        for raw in MALFORMED+WELL_FORMED+('0','1001','-5','1000','1'):
            servers=[{'.name':'srv_a','profile':'openvpn:1_1','name':'A','channel':'Main','priority':raw,'enabled':'1'}]
            data=run_helper(INVENTORY,{'enabled':'1','onboarding_version':raw},servers)
            n=strict_int(raw)
            # priority_config.py: anything but a whole number 1..1000 is 100
            self.assertEqual(data['servers'][0]['priority'],n if n is not None and 1<=n<=1000 else 100,repr(raw))
            self.assertEqual(data['settings']['onboarding_version'],max(0,n) if n is not None else 0,repr(raw))

    def test_recovery_options_match_the_python_reader(self):
        for raw in MALFORMED+WELL_FORMED:
            main={'recovery_'+k:raw for k in RECOVERY}
            got=run_helper(INVENTORY,main)['settings']
            want=recovery_settings.normalized(main)
            for k in RECOVERY:
                self.assertEqual(got['recovery_'+k],want[k],'%s=%r'%(k,raw))
                self.assertIs(type(got['recovery_'+k]),int,'%s=%r'%(k,raw))

    def test_every_numeric_option_takes_its_default_when_malformed(self):
        for raw in MALFORMED:
            got=run_helper(INVENTORY,{k:raw for k in DEFAULTS})['settings']
            for k,default in DEFAULTS.items():self.assertEqual(got[k],default,'%s=%r'%(k,raw))

    def test_detector_options_read_the_same_by_inventory_and_native_policy(self):
        for raw in ('0.9',' .9 ','0.90','9e-1','0x1','nan','inf','-inf','1e999','+0.75','5','5.','0.990000000000001','1234567890123456'):
            main={k:raw for k in DETECTOR}
            inv=run_helper(INVENTORY,main)['settings'];pol=run_helper(POLICY,main)['settings']
            for k,(lo,hi) in (('hmm_theta',(0.5,0.99)),('return_pg',(0.5,0.99)),('hmm_dur_b',(1,15))):
                self.assertEqual(inv.get(k),pol.get(k) if pol.get(k) is not None and lo<=pol[k]<=hi else None,'%s=%r'%(k,raw))
            spelled=re.fullmatch(r'\s*[+-]?([0-9]*)\.?([0-9]*)\s*',raw)
            if not spelled or not 1<=len(spelled.group(1)+spelled.group(2))<=15:
                for k in DETECTOR:self.assertIsNone(pol.get(k),'%s=%r'%(k,raw));self.assertIsNone(inv.get(k),'%s=%r'%(k,raw))


@unittest.skipUnless(LUA,'Lua 5.1 runtime absent; use homensai-vpn-python39:night')
class StatsUntilTwins(unittest.TestCase):
    VECTORS=('0','1794056641','1794056641.5','5.','inf','nan','Infinity','0x10','1_0','1e9','-5','12345678901234',
             '123456789012','1.1234567','','abc')

    def lua_until(self,raw):
        code=("package.path=%s..'/?.lua;'..package.path\n"
              "local a=require('accounting')\n"
              "local R={config_mtime=function() return 1 end,config_text=function() return %s end}\n"
              "io.write(string.format('%%.6f',a.stats.until_time(R)))")%(lua_string(str(LIB/'lua')),lua_string("config main 'main'\n\toption stats_until '%s'\n"%raw))
        out=subprocess.run([LUA,'-e',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        if out.returncode:raise AssertionError(out.stderr.decode())
        return float(out.stdout.decode())

    def test_the_twins_read_stats_until_the_same(self):
        with tempfile.TemporaryDirectory() as folder:
            for i,raw in enumerate(self.VECTORS):
                path=Path(folder)/('c%d'%i);path.write_text("config main 'main'\n\toption stats_until '%s'\n"%raw)
                py=stats_mode.until(path)
                self.assertEqual(round(py,6),self.lua_until(raw),repr(raw))
                # inventory.lua shows the same value in whole seconds
                self.assertEqual(run_helper(INVENTORY,{'stats_until':raw})['settings']['stats_until'],int(py),repr(raw))
                if raw in ('inf','nan','Infinity','0x10','1_0','1e9','-5','12345678901234'):self.assertEqual(py,0.0,repr(raw))
            self.assertEqual(stats_mode.until(Path(folder)/'c1'),1794056641.0)


if __name__=='__main__':
    unittest.main()
