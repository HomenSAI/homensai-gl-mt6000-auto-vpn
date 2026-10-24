import unittest
from audit_documentation import audit,local_targets,unfenced
class DocumentationCurrentTests(unittest.TestCase):
 def test_local_targets_and_current_version_scopes(self):
  result=audit()
  self.assertEqual(result['result'],'PASS')
  self.assertGreater(result['markdown_files'],100)
 def test_fenced_examples_are_not_document_links(self):
  source='[actual](CURRENT-STATUS.md)\n```text\n[example](not-a-file.md)\n```\n~~~sh\n[placeholder](also-not-a-file)\n~~~\n'
  self.assertEqual(list(local_targets(source)),['CURRENT-STATUS.md'])
 def test_external_fragment_and_root_targets_are_excluded(self):
  self.assertEqual(list(local_targets('[url](https://example.org) [anchor](#part) [root](/route) [file](guide.md#part)')),['guide.md'])
