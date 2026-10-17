from pathlib import Path
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from package_hooks import scripts,sdk_fragment


class PackageLifecycleTests(unittest.TestCase):
    def test_sdk_and_custom_hooks_share_exact_source(self):
        root=Path(__file__).resolve().parents[1]
        self.assertEqual((root/'package-hooks.mk').read_text(),sdk_fragment())
        self.assertIn('include ./package-hooks.mk',(root/'Makefile').read_text())
        for body in scripts().values():
            self.assertIn('set -eu',body)
            self.assertNotIn('/etc/init.d/network',body)
            self.assertNotIn('/etc/init.d/firewall',body)

    def test_offline_image_install_hooks_have_no_runtime_side_effects(self):
        for name,body in scripts().items():
            result=subprocess.run(['sh','-s'],input=body,text=True,capture_output=True,
                                  env=dict(os.environ,IPKG_INSTROOT='/nonexistent-build-root'),timeout=5)
            self.assertEqual(result.returncode,0,(name,result.stderr))
            self.assertEqual(result.stdout,'')

    def test_failed_stop_aborts_prerm_before_disabling_service(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);trace=root/'trace'
            guard=root/'guard';guard.write_text('#!/bin/sh\ncat >/dev/null\nexit 0\n');guard.chmod(0o755)
            service=root/'service';service.write_text("#!/bin/sh\nprintf '%s\\n' \"$1\" >> "+shlex.quote(str(trace))+"\n[ \"$1\" = stop ] && exit 7\nexit 0\n");service.chmod(0o755)
            body=scripts()['prerm'].replace('/usr/bin/python3','sh '+shlex.quote(str(guard))).replace('/etc/init.d/homensai-vpn','sh '+shlex.quote(str(service)))
            result=subprocess.run(['sh','-s'],input=body,text=True,capture_output=True,
                                  env=dict(os.environ,IPKG_INSTROOT=''),timeout=5)
            self.assertEqual(result.returncode,7)
            self.assertEqual(trace.read_text().splitlines(),['stop'])


if __name__=='__main__':unittest.main()
