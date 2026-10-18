import unittest
from benchmarks.player_match_groups.cut_out_inherited_groups_fixture import audit,boundary_checks

class InheritedGroupTests(unittest.TestCase):
    def test_recursive_medium_reports_and_private_history_preserve_full_groups(self):
        r=audit('active5')
        self.assertGreaterEqual(r['max_depth'],4)
        self.assertGreater(r['event_counts']['publication-medium'],0)
        self.assertGreater(r['private_groups_equal_old_root_oracle'],0)
        self.assertEqual(r['legacy_root_rebuilds_all_children'],0)

    def test_sealed_initial_CO_and_public_seer_report_children(self):
        r=audit('seer5')
        self.assertGreater(r['recursive_contexts'],0)
        self.assertGreater(r['event_counts']['publication-seer'],0)
        self.assertEqual(r['canonical_calls_all_recursive_children'],0)

    def test_unproved_new_CO_and_private_observer_are_not_silently_accepted(self):
        self.assertTrue(all(boundary_checks().values()))
