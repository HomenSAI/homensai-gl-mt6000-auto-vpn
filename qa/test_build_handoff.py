"""scripts/build-handoff.py names the exact source commit (audit 06.11.2026, F-97): the archive used to send reviewers to
the tag handoff-v<version>, which can point to an older tree than the one the archive was built from."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_handoff', ROOT/'scripts/build-handoff.py')
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)

SOURCE = 'c0ffee'+'1'*34


class HandoffSourceTests(unittest.TestCase):
    def fake_git(self, *args):
        manifest = json.dumps({'handoff': {'version': '1.0.0', 'release_tag': 'handoff-v1.0.0'}}).encode()
        if args[:2] == ('rev-parse', '--verify'):
            return (SOURCE+'\n').encode()
        if args[0] == 'show':
            return manifest if args[1].endswith(':VERSION.json') else b'content\n'
        if args[0] == 'ls-tree':
            return b''
        raise AssertionError(args)

    def test_archive_names_and_points_to_the_exact_source_commit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(handoff, 'ROOT', root), patch.object(handoff, 'git', self.fake_git):
                artifact = handoff.build(SOURCE, root/'private'/'handoff')
            with zipfile.ZipFile(io.BytesIO(artifact.read_bytes())) as archive:
                names = archive.namelist()
                readme = archive.read([n for n in names if n.endswith('BUNDLE-README.md')][0]).decode()
                commit = archive.read([n for n in names if n.endswith('SOURCE-COMMIT')][0]).decode()
        self.assertEqual(commit, SOURCE+'\n')
        self.assertIn('git checkout '+SOURCE, readme)
        self.assertNotIn('at tag handoff-v', readme)

    def test_unknown_or_abbreviated_source_is_refused(self):
        for source in (SOURCE[:12], 'HEAD', 'handoff-v1.0.0'):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError, 'HANDOFF-SOURCE'):
                handoff.build(source, ROOT/'private'/'never-written')
        def other_commit(*args):
            if args[:2] == ('rev-parse', '--verify'):
                return ('d'*40+'\n').encode()
            raise AssertionError(args)
        with patch.object(handoff, 'git', other_commit), self.assertRaisesRegex(ValueError, 'HANDOFF-SOURCE'):
            handoff.build(SOURCE, ROOT/'private'/'never-written')


if __name__ == '__main__':
    unittest.main()
