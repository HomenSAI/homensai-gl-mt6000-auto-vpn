import unittest
from audit_documentation import audit
class DocumentationCurrentTests(unittest.TestCase):
 def test_local_targets_and_current_version_scopes(self):
  result=audit()
  self.assertEqual(result['result'],'PASS')
  self.assertGreater(result['markdown_files'],100)
