import unittest
from git_reconciliation_plan import collision_plan


class ReconciliationTests(unittest.TestCase):
    def test_collision_preserves_both_original_objects_and_names(self):
        refs={'refs/homensai-canonical/tags/v1':'a'*40,'refs/tags/v1':'b'*40}
        row=collision_plan(refs)[0]
        self.assertTrue(row['collision'])
        self.assertEqual(row['canonical_object'],'a'*40)
        self.assertEqual(row['existing_tag_object'],'b'*40)
        self.assertEqual(row['proposed_distinct_public_tag'],'native/v1')
        self.assertEqual(len(refs),2)

    def test_same_or_absent_tags_need_no_collision_alias(self):
        for other in (None,'a'*40):
            refs={'refs/homensai-canonical/tags/v1':'a'*40}
            if other:refs['refs/tags/v1']=other
            row=collision_plan(refs)[0]
            self.assertFalse(row['collision'])
            self.assertEqual(row['proposed_distinct_public_tag'],'v1')


if __name__=='__main__':unittest.main()
