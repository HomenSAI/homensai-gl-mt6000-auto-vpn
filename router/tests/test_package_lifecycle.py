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

    def run_prerm(self,argument,guard_exit_codes):
        """prerm with stubbed guard and service; the guard answers with the given exit codes, one per call."""
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        root=Path(directory.name);trace=root/'trace';codes=root/'codes';codes.write_text(' '.join(map(str,guard_exit_codes)))
        guard=root/'guard';guard.write_text('#!/bin/sh\ncat >/dev/null\nset -- $(cat '+shlex.quote(str(codes))+')\ncode=$1; shift\n'
                                            'echo "$*" > '+shlex.quote(str(codes))+'\nprintf "guard %s\\n" "$code" >> '+shlex.quote(str(trace))+'\nexit $code\n')
        service=root/'service';service.write_text("#!/bin/sh\nprintf '%s\\n' \"$1\" >> "+shlex.quote(str(trace))+"\nexit 0\n")
        body=scripts()['prerm'].replace('/usr/bin/python3','sh '+shlex.quote(str(guard))).replace('/etc/init.d/homensai-vpn','sh '+shlex.quote(str(service)))
        result=subprocess.run(['sh','-s','--',argument],input=body,text=True,capture_output=True,env=dict(os.environ,IPKG_INSTROOT=''),timeout=10)
        return result.returncode,trace.read_text().splitlines()

    def test_prerm_assesses_again_after_the_stop_before_disabling(self):
        # F-16/F-17 (audit 06.11.2026): a Start accepted between the first assessment and the stop, or a shutdown whose
        # recovery did not finish, refuses the removal while the recovery code is still installed.
        for argument in ('remove','upgrade'):
            with self.subTest(argument=argument):
                code,trace=self.run_prerm(argument,[0,0])
                self.assertEqual(code,0);self.assertEqual(trace,['guard 0','stop','guard 0','disable'])
                # R4-07a (night2 N3-lifecycle 1): the refusal after the stop starts the still-installed service again, so the
                # recovery supervisor is running when the package operation aborts; nothing is disabled
                code,trace=self.run_prerm(argument,[0,1])
                self.assertNotEqual(code,0);self.assertEqual(trace,['guard 0','stop','guard 1','start'],'never disabled; the service runs again')
                for refusal in (2,7,126,127):
                    code,trace=self.run_prerm(argument,[0,refusal])
                    self.assertNotEqual(code,0);self.assertEqual(trace,['guard 0','stop','guard %d'%refusal,'start'])

    def run_preinst(self,guard_exit,service_present=True):
        """preinst of an upgrade (settings present) with stubbed guard and service; the persist paths in a temp dir."""
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        root=Path(directory.name);trace=root/'trace';persist=root/'persist';persist.mkdir()
        guard=root/'guard';guard.write_text('#!/bin/sh\ncat >/dev/null\nprintf "guard %s\\n" "$2" >> '+shlex.quote(str(trace))+'\nexit '+str(guard_exit)+'\n')
        service=root/'service';service.write_text("#!/bin/sh\nprintf '%s\\n' \"$1\" >> "+shlex.quote(str(trace))+"\nexit 0\n");service.chmod(0o755)
        body=scripts()['preinst']
        # [ -f ] instead of [ -x ]: CI mounts /tmp noexec, where access(X_OK) fails although the stub is run through sh
        body=body.replace('[ -x /etc/init.d/homensai-vpn ]','[ -f '+shlex.quote(str(service if service_present else root/'absent'))+' ]')
        body=(body.replace('/etc/init.d/homensai-vpn','sh '+shlex.quote(str(service))).replace('[ -x /usr/bin/python3 ]','[ -x /bin/sh ]')
              .replace('/usr/bin/python3','sh '+shlex.quote(str(guard))).replace('/etc/homensai-vpn',str(persist))
              .replace('/usr/lib/homensai-vpn/integrity.sha256',str(root/'manifest')))
        result=subprocess.run(['sh','-s','--','upgrade','2.1.0-alpha9-1'],input=body,text=True,capture_output=True,env=dict(os.environ,IPKG_INSTROOT=''),timeout=10)
        return result.returncode,(trace.read_text().splitlines() if trace.exists() else []),result.stderr

    def test_refused_preinst_starts_the_stopped_service_again(self):
        # IR-08 (integration review 07.11.2026): the old prerm stopped the service; a refusal of the new preinst's guard
        # aborts opkg, so the refusal starts the installed version again (monitoring always runs; R4-07a for preinst)
        code,trace,_=self.run_preinst(0)
        self.assertEqual(code,0);self.assertEqual(trace,['guard prepare'],'an accepted preinst never touches the service')
        for refusal in (1,2,126,127):
            with self.subTest(refusal=refusal):
                code,trace,stderr=self.run_preinst(refusal)
                self.assertEqual(code,refusal);self.assertEqual(trace,['guard prepare','start'])
                self.assertIn('LIFECYCLE-REFUSED-PREINST',stderr)
        # a first install over leftover settings: no init script, nothing to start, still refused
        code,trace,stderr=self.run_preinst(1,service_present=False)
        self.assertEqual(code,1);self.assertEqual(trace,['guard prepare']);self.assertIn('LIFECYCLE-REFUSED-PREINST',stderr)


if __name__=='__main__':unittest.main()
