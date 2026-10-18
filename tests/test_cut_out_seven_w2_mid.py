import unittest
from fractions import Fraction as F
from benchmarks.player_match_groups.cut_out_seven_w2_mid import make_mid
from benchmarks.player_match_groups.cut_out_seven_w2_mid_fixture import audit,negatives,raw_cold_request,first_team_proof

class SevenW2MidTests(unittest.TestCase):
    def test_agree_full_forecast_joint_labels_and_independent_cold(self):
        result=audit('agree')
        self.assertEqual(result['village_win'],'2/15')
        self.assertTrue(result['future_independent_cold']['QP_different'])
        self.assertEqual(result['first_night']['observed_choice_mass'],'1/4')
    def test_count_change_policy_density_and_report_vector_boundaries(self):
        cap=make_mid('count-change')
        self.assertEqual(first_team_proof(cap)['observed_choice_mass'],'9/40')
        self.assertEqual(raw_cold_request(cap,cap.request),cap.source)
        self.assertNotEqual(cap.source.private,cap.source.public_state)
        disagree=make_mid('disagree')
        self.assertNotIn((1,2),disagree.groups)
        self.assertEqual(len(negatives()['rejected']),10)
