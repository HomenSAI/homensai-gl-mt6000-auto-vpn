"""Native PowerShell helper regressions; no actual routes, passwords or requests."""
import shutil,subprocess,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
@unittest.skipUnless(shutil.which('pwsh'),'PowerShell7 unavailable; native Windows evidence is separate')
class PowerShellHelpTests(unittest.TestCase):
 def test_real_helper_refuses_wrong_control_route(self):self.run_script('verify-client-control-path.ps1')
 def test_exact_telegram_recipe_with_mocked_responses(self):self.run_script('verify-help-recipes.ps1')
 def run_script(self,name):
  result=subprocess.run(['pwsh','-NoProfile','-NonInteractive','-File',str(ROOT/'qa'/name)],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',timeout=35)
  self.assertEqual(result.returncode,0,result.stdout+result.stderr);self.assertIn('PASS:',result.stdout)
