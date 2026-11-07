"""Signed test evidence: chain field evidence_sha256, report_manifest.py (build / verify), sign-release --evidence.

Offline. Keys here are throwaway test keys and the store is the reversible test protector; the private\\signing folder and the
real keys are never read. The lab drill 'o' (scripts/signing/lab_drills.py) walks the same tampering through the real tools."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts/signing'))
sys.path.insert(0, str(ROOT/'qa'))
import chain  # noqa: E402
import keytool  # noqa: E402
import report_manifest as rm  # noqa: E402
import test_signing_core as core  # noqa: E402
import usign_format as u  # noqa: E402

MAIN = u.SecretKey(bytes(range(32)), bytes.fromhex('1111111111111111'))
COMMIT = 'a'*40
VERSION = '1.0.0-alpha3-1'
FILES = {
    'docs/TEST-HISTORY.html': b'<html>history</html>\n',
    'docs/test-history/results.json': b'{"passed": 10}\n',
    'qa/ALPHA3-LOCAL-CI.json': b'{"ci": "pass"}\n',
    'private/soak-24h/report-a3/summary.ru.md': b'# soak ok\n',
    'private/soak-24h/report-a3/cycles.json': b'{"cycles": 5}\n',
    'QUEUE-REPORT.md': b'# queue\n',
    'tools/formal/REPORT.ru.md': b'# tlc\n'}


def make_chain(count, evidence=None, origins=None):
    lines, entries = [], []
    for index in range(count):
        entry = chain.next_entry(entries, 'homensai-auto-vpn_1.0.%d-1_all.ipk' % index, '1.0.%d' % index, '1.0.%d-1' % index,
                                 hashlib.sha256(b'%d' % index).hexdigest(), 10+index, COMMIT, '2026-11-04T00:00:00Z', MAIN.key_id.hex(),
                                 origin=(origins or {}).get(index, 'release'), evidence_sha256=(evidence or {}).get(index))
        lines.append(chain.make_line(entry, MAIN))
        entries.append(entry)
    return b'\n'.join(lines)+b'\n'


KEYS = {MAIN.key_id.hex(): u.PublicKey(MAIN.public, MAIN.key_id)}


class ChainEvidenceTests(unittest.TestCase):
    def code(self, data):
        with self.assertRaises(chain.ChainError) as caught:
            chain.verify_chain(data, KEYS)
        return caught.exception.code

    def test_old_entries_are_unchanged_bytes_and_valid(self):
        data = make_chain(3)
        self.assertNotIn(b'evidence', data)
        self.assertEqual(len(chain.verify_chain(data, KEYS)), 3)
        # An entry without the field is byte-identical to what the pre-evidence code wrote: same keys, same order.
        entry = json.loads(data.split(b'\n')[0][len(b'{"entry":'):data.split(b'\n')[0].index(b',"sig"')])
        self.assertEqual(tuple(sorted(entry)), chain.ENTRY_KEYS)

    def test_entry_with_evidence_is_valid_and_sorted_between_date_and_key(self):
        digest = '0123456789abcdef'*4
        data = make_chain(3, evidence={1: digest, 2: 'ab'*32})
        entries = chain.verify_chain(data, KEYS)
        self.assertEqual([entry.get('evidence_sha256') for entry in entries], [None, digest, 'ab'*32])
        line = data.split(b'\n')[1]
        self.assertLess(line.index(b'"date_utc"'), line.index(b'"evidence_sha256"'))
        self.assertLess(line.index(b'"evidence_sha256"'), line.index(b'"key_id"'))
        self.assertEqual(entries[2]['prev'], chain.entry_hash(entries[1]))

    def test_the_link_is_signed_changed_removed_or_added_is_caught(self):
        data = make_chain(3, evidence={1: 'ab'*32})
        lines = data.split(b'\n')
        for label, index, old, new in (('changed', 1, b'ab'*32, b'ab'*31+b'ac'), ('removed', 1, b'"evidence_sha256":"'+b'ab'*32+b'",', b''),
                                       ('added', 2, b'"key_id":', b'"evidence_sha256":"'+b'cd'*32+b'","key_id":')):
            with self.subTest(label):
                edited = list(lines)
                edited[index] = edited[index].replace(old, new, 1)
                self.assertEqual(self.code(b'\n'.join(edited)), 'CHAIN-SIGNATURE-INVALID')

    def test_bad_value_or_place_is_a_format_error(self):
        lines = make_chain(3, evidence={1: 'ab'*32}).split(b'\n')
        field = b'"evidence_sha256":"'+b'ab'*32+b'",'
        for label, line in (('after key_id', lines[1].replace(field, b'').replace(b'"origin":', field+b'"origin":', 1)),
                            ('upper case', lines[1].replace(b'ab'*32, b'AB'*32)), ('short', lines[1].replace(b'ab'*32, b'ab'*31)),
                            ('twice', lines[1].replace(field, field+field)), ('number', lines[1].replace(b'"'+b'ab'*32+b'"', b'12'))):
            with self.subTest(label):
                self.assertEqual(self.code(b'\n'.join([lines[0], line]+lines[2:])), 'CHAIN-FORMAT')

    def test_make_line_refuses_a_malformed_link(self):
        for bad in ('AB'*32, 'ab'*31, 5, '', 'g'*64):
            with self.subTest(bad=bad):
                entry = chain.next_entry([], 'a.ipk', '1.0', '1.0-1', 'f'*64, 1, COMMIT, '2026-11-04T00:00:00Z', MAIN.key_id.hex(), evidence_sha256=bad)
                with self.assertRaises(chain.ChainError):
                    chain.make_line(entry, MAIN)

    def test_imported_history_cannot_carry_evidence(self):
        data = make_chain(2, evidence={1: 'ab'*32}, origins={1: 'imported'})
        self.assertEqual(self.code(data), 'CHAIN-FORMAT')

    def test_chain_extends_with_evidence_lines(self):
        old = make_chain(2, evidence={1: 'ab'*32})
        new = make_chain(3, evidence={1: 'ab'*32, 2: 'cd'*32})
        self.assertEqual(chain.check_extends(old, new), 'extends')


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)/'repo'
        for name, data in FILES.items():
            (self.root/name).parent.mkdir(parents=True, exist_ok=True)
            (self.root/name).write_bytes(data)
        self.out = self.root/'releases/evidence'/VERSION

    def build(self, **extra):
        return rm.build(self.root, self.out, COMMIT, VERSION, now=1_900_000_000, **extra)

    def test_build_lists_every_default_category_with_hashes(self):
        manifest = self.build()
        self.assertEqual([row['path'] for row in manifest['files']], sorted(FILES))
        for row in manifest['files']:
            self.assertEqual(row['sha256'], hashlib.sha256(FILES[row['path']]).hexdigest())
            self.assertEqual(row['size'], len(FILES[row['path']]))
        self.assertEqual({row['category'] for row in manifest['files']}, {'test_history', 'ci_receipts', 'soak', 'queue_report', 'formal'})
        self.assertEqual((manifest['package_version'], manifest['version'], manifest['source_commit'], manifest['base']), (VERSION, '1.0.0-alpha3', COMMIT, '../../..'))
        self.assertEqual(manifest['created_utc'], '2030-03-17T17:46:40Z')
        data = (self.out/rm.MANIFEST).read_bytes()
        self.assertEqual(data, chain.canonical(manifest))
        self.assertFalse(data.endswith(b'\n'))
        self.assertEqual(rm.parse_manifest(data), manifest)

    def test_same_input_gives_the_same_bytes(self):
        self.build()
        first = (self.out/rm.MANIFEST).read_bytes()
        shutil.rmtree(self.out)
        self.build()
        self.assertEqual((self.out/rm.MANIFEST).read_bytes(), first)

    def test_empty_category_is_a_recorded_statement(self):
        (self.root/'QUEUE-REPORT.md').unlink()
        manifest = self.build()
        self.assertEqual(manifest['empty_categories'], ['queue_report'])
        self.assertNotIn('QUEUE-REPORT.md', [row['path'] for row in manifest['files']])

    def test_required_category_must_match_every_pattern(self):
        (self.root/'docs/test-history/results.json').unlink()
        with self.assertRaisesRegex(rm.ReportError, 'EVIDENCE-REQUIRED-MISSING.*results.json'):
            self.build()
        self.assertFalse((self.out/rm.MANIFEST).exists())

    def test_evidence_is_never_overwritten(self):
        self.build()
        with self.assertRaisesRegex(rm.ReportError, 'EVIDENCE-EXISTS'):
            self.build()
        Path(str(self.out/rm.MANIFEST)+'.sig').write_bytes(b'x')
        (self.out/rm.MANIFEST).unlink()
        with self.assertRaisesRegex(rm.ReportError, 'EVIDENCE-EXISTS'):
            self.build()

    def test_inputs_are_checked(self):
        with self.assertRaisesRegex(rm.ReportError, 'EVIDENCE-SOURCE-COMMIT'):
            rm.build(self.root, self.out, 'abc', VERSION)
        with self.assertRaisesRegex(rm.ReportError, 'EVIDENCE-VERSION'):
            rm.build(self.root, self.out, COMMIT, 'bad version')
        for pattern in ('../outside', '/etc/passwd', 'C:/x', 'a\\b', ''):
            with self.subTest(pattern):
                with self.assertRaisesRegex(rm.ReportError, 'EVIDENCE-PATTERN'):
                    self.build(spec={'test_history': [pattern]}, required=())
        with self.assertRaisesRegex(rm.ReportError, 'EVIDENCE-CATEGORY'):
            self.build(spec={'Bad Name': ['QUEUE-REPORT.md']})

    def test_custom_spec_and_duplicate_paths(self):
        manifest = self.build(spec={'one': ['QUEUE-REPORT.md'], 'test_history': ['docs/TEST-HISTORY.html']})
        self.assertEqual([row['path'] for row in manifest['files']], ['QUEUE-REPORT.md', 'docs/TEST-HISTORY.html'])
        shutil.rmtree(self.out)
        with self.assertRaisesRegex(rm.ReportError, 'EVIDENCE-DUPLICATE'):
            self.build(spec={'one': ['QUEUE-REPORT.md'], 'two': ['QUEUE-REPORT.md'], 'test_history': ['docs/TEST-HISTORY.html']})

    def test_symlink_is_refused(self):
        link = self.root/'qa/LINK-CI.json'
        try:
            link.symlink_to(self.root/'QUEUE-REPORT.md')
        except (OSError, NotImplementedError):
            self.skipTest('symbolic links are not available here')
        with self.assertRaisesRegex(rm.ReportError, 'EVIDENCE-SYMLINK'):
            self.build()

    def test_manifest_parser_rejects_every_edit(self):
        good = self.build()
        data = chain.canonical(good)
        cases = {'newline': data+b'\n', 'indent': json.dumps(good, indent=1).encode(), 'spaces': json.dumps(good, sort_keys=True).encode(),
                 'not json': b'{', 'not ascii': 'ä'.encode()}
        for label, bad in cases.items():
            with self.subTest(label):
                with self.assertRaises(rm.ReportError):
                    rm.parse_manifest(bad)

        def edited(change):
            value = json.loads(data)
            change(value)
            return chain.canonical(value)
        rows = lambda v: v['files']   # noqa: E731
        changes = {'extra field': lambda v: v.update(extra=1), 'schema': lambda v: v.update(schema='x'), 'commit': lambda v: v.update(source_commit='z'*40),
                   'date': lambda v: v.update(created_utc='yesterday'), 'base': lambda v: v.update(base='/etc'),
                   'dotdot path': lambda v: rows(v)[0].update(path='../x'), 'abs path': lambda v: rows(v)[0].update(path='/x'),
                   'backslash': lambda v: rows(v)[0].update(path='a\\b'), 'hash': lambda v: rows(v)[0].update(sha256='A'*64),
                   'size': lambda v: rows(v)[0].update(size=-1), 'bool size': lambda v: rows(v)[0].update(size=True),
                   'unsorted': lambda v: rows(v).reverse(), 'duplicate': lambda v: rows(v).append(dict(rows(v)[-1])),
                   'category empty and used': lambda v: v.update(empty_categories=['soak']), 'file row field': lambda v: rows(v)[0].update(x=1)}
        for label, change in changes.items():
            with self.subTest(label):
                with self.assertRaises(rm.ReportError):
                    rm.parse_manifest(edited(change))

    def test_files_changed_missing_and_size_are_named(self):
        manifest = self.build()
        self.assertEqual(rm.check_files(self.out, manifest), [])
        (self.root/'qa/ALPHA3-LOCAL-CI.json').write_bytes(b'{"ci": "fail"}\n')
        (self.root/'QUEUE-REPORT.md').unlink()
        (self.root/'tools/formal/REPORT.ru.md').write_bytes(b'# tlc\n\n')
        found = {(code, name) for code, name, _ in rm.check_files(self.out, manifest)}
        self.assertEqual(found, {('EVIDENCE-FILE-CHANGED', 'qa/ALPHA3-LOCAL-CI.json'), ('EVIDENCE-FILE-MISSING', 'QUEUE-REPORT.md'),
                                 ('EVIDENCE-FILE-CHANGED', 'tools/formal/REPORT.ru.md')})

    def test_bundle_copy_is_self_contained_and_extra_files_are_named(self):
        manifest = self.build(copy=True)
        self.assertEqual(manifest['base'], 'files')
        for name, data in FILES.items():
            self.assertEqual((self.out/'files'/name).read_bytes(), data)
        self.assertEqual(rm.check_files(self.out, manifest), [])
        (self.out/'files/docs/added-later.txt').write_bytes(b'x')
        self.assertEqual([(code, name) for code, name, _ in rm.check_files(self.out, manifest)], [('EVIDENCE-FILE-EXTRA', 'docs/added-later.txt')])
        # a bundle moved elsewhere is checked against the repository files instead
        self.assertEqual([item for item in rm.check_files(self.out, manifest, self.root) if item[0] != 'EVIDENCE-FILE-EXTRA'], [])

    def test_command_line_build_and_unsigned_verify(self):
        with contextlib.redirect_stdout(io.StringIO()):
            code = rm.main(['build', '--out', str(self.out), '--source-commit', COMMIT, '--package-version', VERSION, '--root', str(self.root)])
        self.assertEqual(code, 0)
        self.assertTrue((self.out/rm.MANIFEST).is_file())
        with mock.patch('sys.stderr') as stderr:
            self.assertEqual(rm.main(['build', '--out', str(self.out), '--source-commit', COMMIT, '--package-version', VERSION, '--root', str(self.root)]), 2)
        self.assertIn('EVIDENCE-EXISTS', ''.join(call.args[0] for call in stderr.write.call_args_list))
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            rm.main(['build', '--out', str(self.out)])


@unittest.skipUnless(shutil.which('git'), 'git required')
class SignedEvidenceTests(unittest.TestCase):
    """The whole path: sign-release --evidence with the TOTP gate, then verify against the signed chain."""
    git = core.KeytoolTests.git
    run_tool = core.KeytoolTests.run_tool
    current_code = core.KeytoolTests.current_code
    enrol = core.KeytoolTests.enrol

    def setUp(self):   # noqa: F811
        core.KeytoolTests.setUp(self)
        self.run_tool(['new-keys'], core.Console())
        self.enrol()
        self.name = 'homensai-auto-vpn_%s_all.ipk' % VERSION
        payload = b'package 3\n'
        (self.root/'releases'/self.name).write_bytes(payload)
        (self.root/'VERSION.json').write_text(json.dumps({'application': {'artifact': self.name, 'sha256': hashlib.sha256(payload).hexdigest(),
                                                                             'package_version': VERSION}}))
        for name, data in FILES.items():
            (self.root/name).parent.mkdir(parents=True, exist_ok=True)
            (self.root/name).write_bytes(data)
        self.source = self.git('rev-parse', 'HEAD')
        self.folder = self.root/'releases/evidence'/VERSION
        rm.build(self.root, self.folder, self.source, VERSION)

    def sign(self, extra=(), codes=None):
        self.now[0] += 60
        argv = ['sign-release', '--artifact', 'releases/'+self.name, '--source-commit', self.source, '--no-ots']+list(extra)
        return self.run_tool(argv, core.Console(codes=[self.current_code()] if codes is None else codes))

    def signed(self):
        code, error = self.sign(['--evidence', str(self.folder)])
        self.assertEqual(code, 0, error)

    def problems(self):
        return sorted((item['code'], item['path']) for item in rm.verify_dir(self.folder, self.root)['problems'])

    def test_signed_evidence_verifies_and_is_linked_in_the_chain(self):
        self.signed()
        report = rm.verify_dir(self.folder, self.root)
        self.assertEqual((report['result'], report['problems'], report['files']), ('PASS', [], len(FILES)))
        manifest_hash = hashlib.sha256((self.folder/rm.MANIFEST).read_bytes()).hexdigest()
        entries, _ = keytool.verified_chain(self.root)
        self.assertEqual(entries[-1]['evidence_sha256'], manifest_hash)
        self.assertEqual((report['chain_seq'], report['signer']), (entries[-1]['seq'], entries[-1]['key_id']))
        self.assertEqual(keytool.verify_release(self.root, 'releases/'+self.name)['result'], 'PASS')
        self.assertTrue((self.folder/(rm.MANIFEST+'.sig')).is_file())

    def test_release_without_evidence_has_no_field_and_old_flow_is_unchanged(self):
        code, error = self.sign()
        self.assertEqual(code, 0, error)
        entries, _ = keytool.verified_chain(self.root)
        self.assertNotIn('evidence_sha256', entries[-1])
        self.assertFalse((self.folder/(rm.MANIFEST+'.sig')).exists())
        self.assertIn('EVIDENCE-NOT-IN-CHAIN', [item[0] for item in self.problems()])

    def test_unsigned_manifest_is_not_accepted(self):
        self.assertEqual(self.problems(), [('EVIDENCE-NOT-IN-CHAIN', rm.MANIFEST), ('EVIDENCE-SIGNATURE-MISSING', rm.MANIFEST+'.sig')])

    def test_one_edited_file_is_named_and_only_it(self):
        self.signed()
        (self.root/'qa/ALPHA3-LOCAL-CI.json').write_bytes(b'{"ci": "pass", "x": 1}\n')
        self.assertEqual(self.problems(), [('EVIDENCE-FILE-CHANGED', 'qa/ALPHA3-LOCAL-CI.json')])
        (self.root/'qa/ALPHA3-LOCAL-CI.json').write_bytes(FILES['qa/ALPHA3-LOCAL-CI.json'])
        self.assertEqual(self.problems(), [])

    def test_deleted_file_is_named(self):
        self.signed()
        (self.root/'private/soak-24h/report-a3/cycles.json').unlink()
        self.assertEqual(self.problems(), [('EVIDENCE-FILE-MISSING', 'private/soak-24h/report-a3/cycles.json')])

    def test_manifest_fitted_to_a_forged_file_breaks_signature_and_link(self):
        self.signed()
        forged = b'{"passed": 99}\n'
        (self.root/'docs/test-history/results.json').write_bytes(forged)
        value = json.loads((self.folder/rm.MANIFEST).read_bytes())
        for row in value['files']:
            if row['path'] == 'docs/test-history/results.json':
                row.update(sha256=hashlib.sha256(forged).hexdigest(), size=len(forged))
        (self.folder/rm.MANIFEST).write_bytes(chain.canonical(value))
        self.assertEqual(self.problems(), [('EVIDENCE-NOT-IN-CHAIN', rm.MANIFEST), ('EVIDENCE-SIGNATURE-INVALID', rm.MANIFEST+'.sig')])

    def test_hand_edited_manifest_and_missing_signature(self):
        self.signed()
        original = (self.folder/rm.MANIFEST).read_bytes()
        (self.folder/rm.MANIFEST).write_bytes(original+b'\n')
        self.assertEqual([item[0] for item in self.problems()], ['EVIDENCE-MANIFEST-FORMAT'])
        (self.folder/rm.MANIFEST).write_bytes(original)
        (self.folder/(rm.MANIFEST+'.sig')).unlink()
        self.assertEqual(self.problems(), [('EVIDENCE-SIGNATURE-MISSING', rm.MANIFEST+'.sig')])
        (self.folder/rm.MANIFEST).unlink()
        self.assertEqual(self.problems(), [('EVIDENCE-MANIFEST-MISSING', rm.MANIFEST)])

    def test_signature_by_another_trusted_key_is_not_the_release_signer(self):
        self.signed()
        reserve = u.SecretKey.from_file(self.store.read_secret('reserve.key.dpapi'))
        (self.folder/(rm.MANIFEST+'.sig')).write_bytes(reserve.sign_file((self.folder/rm.MANIFEST).read_bytes()))
        self.assertEqual(self.problems(), [('EVIDENCE-SIGNER-MISMATCH', rm.MANIFEST+'.sig')])
        stranger = u.SecretKey.generate()
        (self.folder/(rm.MANIFEST+'.sig')).write_bytes(stranger.sign_file((self.folder/rm.MANIFEST).read_bytes()))
        self.assertEqual(self.problems(), [('EVIDENCE-SIGNATURE-INVALID', rm.MANIFEST+'.sig')])
        # the other trusted key, revoked from this entry on, signs no evidence of this release either
        (self.folder/(rm.MANIFEST+'.sig')).write_bytes(reserve.sign_file((self.folder/rm.MANIFEST).read_bytes()))
        entries, _ = keytool.verified_chain(self.root)
        keytool.write_revocations(self.root, {(reserve.key_id.hex(), entries[-1]['seq'])})
        self.assertEqual(self.problems(), [('EVIDENCE-SIGNATURE-INVALID', rm.MANIFEST+'.sig')])

    def test_signature_of_a_revoked_key_is_refused(self):
        self.signed()
        entries, _ = keytool.verified_chain(self.root)
        keytool.write_revocations(self.root, {(entries[-1]['key_id'], entries[-1]['seq'])})
        codes = [code for code, _ in self.problems()]
        self.assertIn('EVIDENCE-CHAIN-INVALID', codes)   # the entry itself was signed by a key that is revoked from its seq
        self.assertNotIn('EVIDENCE-FILE-CHANGED', codes)

    def test_chain_without_the_release_entry_does_not_link_the_manifest(self):
        self.signed()
        path = keytool.chain_path(self.root)
        lines = path.read_bytes().split(b'\n')
        path.write_bytes(b'\n'.join(lines[:-2])+b'\n')
        self.assertEqual(self.problems(), [('EVIDENCE-NOT-IN-CHAIN', rm.MANIFEST)])

    def test_manifest_of_another_release_or_commit_in_the_chain_is_a_mismatch(self):
        # A correctly signed entry carries the hash, but it is the entry of another commit: not this release's evidence.
        data = (self.folder/rm.MANIFEST).read_bytes()
        entries, _ = keytool.verified_chain(self.root)
        key = keytool.load_secret(self.root, self.store, 'main')
        package = (self.root/'releases'/self.name).read_bytes()
        entry = chain.next_entry(entries, self.name, '1.0.0-alpha3', VERSION, hashlib.sha256(package).hexdigest(), len(package), 'b'*40,
                                 keytool.utc(), key.key_id.hex(), evidence_sha256=hashlib.sha256(data).hexdigest())
        keytool.chain_path(self.root).write_bytes(keytool.read_chain(self.root)+chain.make_line(entry, key)+b'\n')
        (self.folder/(rm.MANIFEST+'.sig')).write_bytes(key.sign_file(data))
        self.assertEqual(self.problems(), [('EVIDENCE-CHAIN-MISMATCH', rm.MANIFEST)])

    def test_sign_release_refuses_bad_evidence_before_asking_for_a_code(self):
        # No code is supplied: a refusal that needs one would raise IndexError instead of printing the stop line.
        code, error = self.sign(['--evidence', str(self.root/'nowhere')], codes=[])
        self.assertIn('EVIDENCE-MANIFEST-MISSING', error)
        (self.root/'qa/ALPHA3-LOCAL-CI.json').write_bytes(b'changed after the manifest\n')
        code, error = self.sign(['--evidence', str(self.folder)], codes=[])
        self.assertIn('EVIDENCE-FILE-CHANGED', error)
        self.assertIn('qa/ALPHA3-LOCAL-CI.json', error)
        (self.root/'qa/ALPHA3-LOCAL-CI.json').write_bytes(FILES['qa/ALPHA3-LOCAL-CI.json'])
        other = self.root/'releases/evidence/other'
        rm.build(self.root, other, 'b'*40, VERSION)
        code, error = self.sign(['--evidence', str(other)], codes=[])
        self.assertIn('EVIDENCE-RELEASE-MISMATCH', error)
        rm.build(self.root, self.root/'releases/evidence/v2', self.source, '1.0.0-alpha9-1')
        code, error = self.sign(['--evidence', str(self.root/'releases/evidence/v2')], codes=[])
        self.assertIn('EVIDENCE-RELEASE-MISMATCH', error)
        self.assertEqual(len(keytool.verified_chain(self.root)[0]), 2, 'nothing was signed')
        self.assertFalse(Path(str(self.root/'releases'/self.name)+'.sig').exists())

    def test_a_manifest_with_a_signature_is_never_signed_again(self):
        (self.folder/(rm.MANIFEST+'.sig')).write_bytes(b'someone was here first\n')
        code, error = self.sign(['--evidence', str(self.folder)], codes=[])
        self.assertIn('EVIDENCE-ALREADY-SIGNED', error)
        self.assertEqual(len(keytool.verified_chain(self.root)[0]), 2)

    def test_evidence_cannot_be_signed_twice(self):
        self.signed()
        self.assertEqual(len(keytool.verified_chain(self.root)[0]), 3)
        code, error = self.sign(['--evidence', str(self.folder)], codes=[])
        self.assertTrue('EVIDENCE-ALREADY-SIGNED' in error or 'SIGN-ALREADY-IN-CHAIN' in error)

    def test_command_line_verify_prints_the_names(self):
        self.signed()
        self.assertEqual(rm.main(['verify', str(self.folder), '--root', str(self.root)], console=core.Console()), 0)
        (self.root/'QUEUE-REPORT.md').write_bytes(b'# queue, quietly improved\n')
        console = core.Console()
        with mock.patch('sys.stderr') as stderr:
            self.assertEqual(rm.main(['verify', str(self.folder), '--root', str(self.root)], console=console), 1)
        text = ''.join(call.args[0] for call in stderr.write.call_args_list)
        self.assertIn('EVIDENCE-FILE-CHANGED: QUEUE-REPORT.md', text)
        self.assertIn('STOP: EVIDENCE-VERIFY-FAILED: 1 problem(s)', text)
        self.assertEqual(json.loads(console.lines[-1])['result'], 'FAIL')


if __name__ == '__main__':
    unittest.main()
