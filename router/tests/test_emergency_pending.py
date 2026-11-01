"""Regression: emergency Stop must not commit another operator's pending edits."""
import os,shutil,subprocess,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
@unittest.skipUnless(os.name=='posix' and shutil.which('sh'),'POSIX platform and shell required')
class EmergencyPendingEdits(unittest.TestCase):
 def run_case(self,source,pending,stop_failure=False):
  with tempfile.TemporaryDirectory() as directory:
   root=Path(directory);log=root/'calls';init=root/'own-init';init.write_text('#!/bin/sh\necho "service:$1" >> "$AUDIT_LOG"\nexit '+('1' if stop_failure else '0')+'\n');init.chmod(0o755)
   uci=root/'uci';uci.write_text('#!/bin/sh\nif [ "$1 $2" = "-q changes" ]; then printf "%s" "$AUDIT_PENDING"; exit 0; fi\necho "uci:$*" >> "$AUDIT_LOG"\n');uci.chmod(0o755)
   # CI tmpfs is noexec: call mock programs through sh, preserving the real
   # command/control flow without requiring an executable temporary mount.
   script=root/'emergency.sh';body=source.read_text().replace('/etc/init.d/homensai-vpn','sh '+str(init))
   script.write_text('uci() { sh '+str(uci)+' "$@"; }\n'+body)
   env=dict(os.environ,PATH=str(root)+os.pathsep+os.environ['PATH'],AUDIT_LOG=str(log),AUDIT_PENDING=pending)
   result=subprocess.run(['sh',str(script),'stop-auto'],env=env,capture_output=True,text=True,timeout=8)
   self.assertTrue(log.exists(),result.stderr or result.stdout)
   return result,log.read_text().splitlines()
 def test_pending_edits_stop_services_but_are_not_committed(self):
  for name in ['router/files/usr/sbin/homensai-vpn-emergency','router-test-kit/05-emergency.sh']:
   with self.subTest(source=name):
    result,calls=self.run_case(ROOT/name,"homensai_vpn.main.example='operator-edit'\n")
    self.assertNotEqual(result.returncode,0);self.assertEqual(calls,['service:stop']);self.assertIn('remain uncommitted',result.stdout)
 def test_clean_stop_disables_only_saved_auto_flag(self):
  for name in ['router/files/usr/sbin/homensai-vpn-emergency','router-test-kit/05-emergency.sh']:
   with self.subTest(source=name):
    result,calls=self.run_case(ROOT/name,'');self.assertEqual(result.returncode,0);self.assertEqual(calls,['service:stop','uci:set homensai_vpn.main.native_enabled=0','uci:commit homensai_vpn','service:stop'])
 def test_failed_service_stop_never_commits(self):
  for name in ['router/files/usr/sbin/homensai-vpn-emergency','router-test-kit/05-emergency.sh']:
   with self.subTest(source=name):
    result,calls=self.run_case(ROOT/name,'',True);self.assertNotEqual(result.returncode,0);self.assertEqual(calls,['service:stop']);self.assertIn('service stop failed',result.stdout)
if __name__=='__main__':unittest.main()
