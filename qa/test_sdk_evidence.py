import hashlib
import gzip
import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('sdk_evidence',Path(__file__).resolve().parents[1]/'scripts/check-sdk-evidence.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def archive(entries):
    output=io.BytesIO()
    with tarfile.open(fileobj=output,mode='w') as tar:
        for name,data,mode in entries:
            item=tarfile.TarInfo(name);item.mode=mode;item.size=len(data)
            tar.addfile(item,io.BytesIO(data))
    return gzip.compress(output.getvalue(),mtime=0)


def ipk(payload=b'payload',mode=0o644,depends='python3, lua',hook=b'exit 0\n',architecture='all'):
    control=b'Package: homensai-auto-vpn\nVersion: test-1\nArchitecture: '+architecture.encode()+b'\nDepends: '+depends.encode()+b'\n'
    return archive([('./debian-binary',b'2.0\n',0o644),
                    ('./control.tar.gz',archive([('control',control,0o644),('postinst',hook,0o755)]),0o644),
                    ('./data.tar.gz',archive([('./usr/lib/test.py',payload,mode)]),0o644)])


class SDKEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
        sdk=b'local SDK archive fixture';sdk_name='openwrt-sdk-21.02.7-x86-64_gcc-8.4.0_musl.Linux-x86_64.tar.xz'
        payload={role:('evidence '+role).encode() for role in m.ROLES}
        payload.update(sdk_archive=sdk,supplier_checksums=(hashlib.sha256(sdk).hexdigest()+' *'+sdk_name+'\n').encode(),
                       config=b'CONFIG_TARGET_x86=y\nCONFIG_PACKAGE_homensai-auto-vpn=m\n',
                       feeds=('src-git packages https://git.openwrt.org/feed/packages.git;'+'a'*40+'\n').encode(),
                       package_first=ipk(),package_second=ipk(),reference_package=ipk(depends='lua, python3'))
        self.data={'schema':1,'sdk_scope':'upstream','source_commit':'b'*40,
                   'supplier_url':'https://downloads.openwrt.org/releases/21.02.7/targets/x86/64/'+sdk_name,'files':{}}
        for role,value in payload.items():self.change(role,value)

    def change(self,role,value):
        (self.base/role).write_bytes(value)
        self.data['files'][role]={'path':role,'sha256':hashlib.sha256(value).hexdigest()}

    def check(self):return m.verify(self.data,self.base)

    def test_consistency_never_grants_vendor_hardware_or_install_acceptance(self):
        result=self.check();self.assertEqual(result['result'],'EVIDENCE-CONSISTENT')
        self.assertEqual(result['payload_files_compared'],1)
        for field in ('vendor_firmware_match','device_acceptance','installation_authorized','native_adapter_certified'):
            self.assertIs(result[field],False)

    def test_generic_evidence_cannot_be_relabelled_as_vendor_acceptance(self):
        for scope in ('vendor','gl-inet-4.11.0','vendor-certified',None):
            self.data['sdk_scope']=scope
            with self.subTest(scope=scope),self.assertRaisesRegex(ValueError,'VENDOR-CLAIM-REFUSED'):self.check()

    def test_coherently_rehashed_payload_mode_dependency_and_hook_tampering_refuse(self):
        for candidate in (ipk(payload=b'changed'),ipk(mode=0o777),ipk(depends='python3'),ipk(hook=b'unsafe change')):
            self.change('package_first',candidate);self.change('package_second',candidate)
            with self.subTest(candidate=hashlib.sha256(candidate).hexdigest()),self.assertRaisesRegex(ValueError,'SDK-PACKAGE-'):
                self.check()

    def test_nondeterministic_sdk_builds_refuse_even_with_individual_hashes(self):
        self.change('package_second',ipk(payload=b'another build'))
        with self.assertRaisesRegex(ValueError,'NOT-REPRODUCIBLE'):self.check()

    def test_target_specific_architecture_cannot_pass_all_package_parity(self):
        for role in ('package_first','package_second'):self.change(role,ipk(architecture='x86_64'))
        with self.assertRaisesRegex(ValueError,'METADATA:Architecture'):self.check()

    def test_mutated_input_after_manifest_refuses(self):
        (self.base/'config').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'HASH-MISMATCH'):self.check()

    def test_missing_or_unpinned_inputs_refuse(self):
        entry=self.data['files'].pop('toolchain')
        with self.assertRaisesRegex(ValueError,'INCOMPLETE'):self.check()
        self.data['files']['toolchain']=entry
        self.change('feeds',b'src-git packages https://git.openwrt.org/feed/packages.git;openwrt-21.02\n')
        with self.assertRaisesRegex(ValueError,'FEEDS-NOT-IMMUTABLE'):self.check()

    def test_forged_supplier_checksum_and_other_host_refuse(self):
        self.change('supplier_checksums',b'not a verified checksum')
        with self.assertRaisesRegex(ValueError,'CHECKSUM-MISMATCH'):self.check()
        self.data['supplier_url']=self.data['supplier_url'].replace('downloads.openwrt.org','example.invalid')
        with self.assertRaisesRegex(ValueError,'UPSTREAM-SUPPLIER'):self.check()

    def test_path_escape_and_reused_evidence_refuse(self):
        for path in ('../secret','/etc/passwd','C:/secret','..\\secret'):
            self.data['files']['licence']['path']=path
            with self.subTest(path=path),self.assertRaisesRegex(ValueError,'PATH'):self.check()
        self.data['files']['licence']=dict(self.data['files']['toolchain'])
        with self.assertRaisesRegex(ValueError,'REUSED-FILE'):self.check()

    def test_archive_traversal_duplicate_and_symlink_refuse(self):
        for entries in ([('../outside',b'x',0o644)],[('/absolute',b'x',0o644)],
                        [('file',b'x',0o644),('./file',b'x',0o644)]):
            with self.subTest(entries=entries),self.assertRaisesRegex(ValueError,'PATH-OR-DUPLICATE'):
                m.tar_files(archive(entries))
        output=io.BytesIO()
        with tarfile.open(fileobj=output,mode='w:gz') as tar:
            item=tarfile.TarInfo('link');item.type=tarfile.SYMTYPE;item.linkname='/outside';tar.addfile(item)
        with self.assertRaisesRegex(ValueError,'LINK-OR-SPECIAL'):m.tar_files(output.getvalue())

    def test_only_exact_pinned_sdk_wrapper_and_libc_difference_are_accepted(self):
        control=b'Package: homensai-auto-vpn\nVersion: test-1\nArchitecture: all\nDepends: libc, python3, lua\n'
        reference=archive([('debian-binary',b'2.0\n',0o644),
                           ('control.tar.gz',archive([('control',control,0o644),('postinst',b'post hook',0o755),('prerm',b'pre hook',0o755)]),0o644),
                           ('data.tar.gz',archive([('usr/lib/test.py',b'payload',0o644)]),0o644)])
        self.change('reference_package',reference)
        def sdk(wrapper):return archive([('debian-binary',b'2.0\n',0o644),
            ('control.tar.gz',archive([('control',control,0o644),('postinst',wrapper,0o755),('prerm',m.SDK_WRAPPERS['prerm'],0o755),
                                      ('postinst-pkg',b'post hook',0o755),('prerm-pkg',b'pre hook',0o755)]),0o644),
            ('data.tar.gz',archive([('usr/lib/test.py',b'payload',0o644)]),0o644)])
        for role in ('package_first','package_second'):self.change(role,sdk(m.SDK_WRAPPERS['postinst']))
        self.assertEqual(self.check()['result'],'EVIDENCE-CONSISTENT')
        for role in ('package_first','package_second'):self.change(role,sdk(m.SDK_WRAPPERS['postinst']+b'unsafe appended command\n'))
        with self.assertRaisesRegex(ValueError,'UNKNOWN-WRAPPER'):self.check()


if __name__=='__main__':unittest.main()
