import unittest
from benchmarks.player_match_groups.cut_out_six_inherited_fixture import audit,scope_checks

class SixInheritedTests(unittest.TestCase):
    def test_two_night_joint_and_attacks_keep_parent_group_witness(self):
        r=audit('public')
        self.assertEqual(r['village_win'],'3/8')
        self.assertGreaterEqual(r['inheritance_stats']['max_depth'],6)
        self.assertGreater(r['second_night_terminal_counts']['second_night_terminal_recipes'],0)
        self.assertEqual(r['actual_initial_group_rebuild_calls'],0)

    def test_new_entry_rejects_max_seven_and_current_registry_without_witness(self):
        r=scope_checks()
        self.assertTrue(r['six_max_refused'])
        self.assertTrue(r['four_and_seven_refused'])
