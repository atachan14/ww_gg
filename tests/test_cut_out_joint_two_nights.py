import unittest
from benchmarks.player_match_groups.cut_out_joint_two_nights_fixture import audit,negatives_and_reachability

class JointTwoNightsTests(unittest.TestCase):
    def test_reachable_six_player_two_nights_and_separate_engine_cold(self):
        r=audit(True)
        self.assertEqual(r['village_win'],'1/4')
        self.assertTrue(r['second_night_independent_cold']['fresh_engine'])
        self.assertEqual(r['second_night_independent_cold']['night_events'],2)
        self.assertGreater(r['second_night_independent_cold']['dead_scan_records'],0)
    def test_small_reachability_and_hidden_history_only_skew_are_checked(self):
        r=negatives_and_reachability()
        self.assertEqual(r['small_max_nights'],{'4/W1':1,'5/W1':1,'5/W2':1})
        self.assertEqual(len(r['rejected']),7)
