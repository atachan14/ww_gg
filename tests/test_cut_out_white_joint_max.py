import unittest
from fractions import Fraction as F
from benchmarks.player_match_groups.cut_out_white_joint_fixture import audit,support_refusals
from benchmarks.player_match_groups.cut_out_white_joint_max import graph,scan_values,evaluate
from benchmarks.player_match_groups.cut_out_uniform_game import OwnView
from werewolf.seer_acquisition import Acquisition
from benchmarks.player_match_groups.partitioned_match_groups import UnsupportedPartition

class WhiteJointMaxTests(unittest.TestCase):
    def test_complete_private_white_contexts_and_current_scan_match(self):
        result=audit('white',3,True)
        self.assertTrue(result['all_root_labels_verified'])
        self.assertEqual(result['own_scan_targets'],[2,4,5])
        self.assertEqual(result['village_win'],'7/15')

    def test_public_CO_and_secret_support_neighbors_are_refused(self):
        result=support_refusals()
        self.assertEqual(len(result['refusals']),4)
        self.assertTrue(result['no_partial_certificate_installed'])
        self.assertEqual(result['public_seer_CO_legacy_value'],'2/3')

    def test_unknown_or_impossible_own_initial_white_is_not_filled(self):
        source=graph()
        self.assertEqual(scan_values(source,OwnView(1,'seer')).reason,'seer_view_past_private_history_unresolved')
        self.assertIsInstance(evaluate(source,view=OwnView(1,'seer',(Acquisition(1,1,2,'black'),))),UnsupportedPartition)
