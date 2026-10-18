import unittest
from benchmarks.player_match_groups.cut_out_seven_branch_audit_fixture import audit

class SevenBranchAuditTests(unittest.TestCase):
    def test_selection_already_grouped_but_joint_publication_has_label_orbits(self):
        result=audit()
        self.assertEqual(result['traces'][0]['representatives'],4)
        self.assertEqual(result['night_current_representative_calls'],18)
        self.assertEqual(result['night_joint_info_action_orbits_test_only'],3)
        self.assertEqual(result['raw_complete_report_vectors'],64)
        self.assertEqual(result['report_vector_orbits_test_only'],13)
        self.assertEqual(result['symmetric_pair_unnecessarily_split_vectors'],7)
        self.assertEqual(result['choices_if_only_symmetric_pair_preserved'],269)
        self.assertTrue(all(r['legal_targets']==4 and r['representatives']==3 for r in result['night_actor_choices']))
