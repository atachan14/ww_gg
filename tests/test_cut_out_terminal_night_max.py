import unittest
from dataclasses import replace
from benchmarks.player_match_groups.cut_out_terminal_night_max import graph
from benchmarks.player_match_groups.cut_out_terminal_night_fixture import audit
from benchmarks.player_match_groups.cut_out_model_a import adapt_terminal_night_max_model_a,adapt_latent_max_model_a
from benchmarks.player_match_groups.partitioned_match_groups import UnsupportedPartition

class TerminalNightMaxTests(unittest.TestCase):
    def test_four_player_terminal_scope_is_explicit(self):
        spec=graph().engine.baseline.spec
        self.assertIsInstance(adapt_latent_max_model_a(spec),UnsupportedPartition)
        for changed in (replace(spec,players=5),replace(spec,seers=2),replace(spec,mediums=1,claims=('medium',)+('latent',)*3)):
            self.assertIsInstance(adapt_terminal_night_max_model_a(changed),UnsupportedPartition)

    def test_old_unique_certificate_matches_private_complete_joint_and_scan(self):
        result=audit('[1,"random_white","white"]')
        self.assertTrue(result['old_night_max_exact_policy_equal'])
        self.assertTrue(result['independently_generated_initial_and_terminal_joint_equal'])

    def test_five_player_feedback_remains_unfinished_without_policy(self):
        result=audit('five-feedback')
        self.assertEqual(result['theoretical_profiles'],2401)
        self.assertFalse(result['numeric_policy_installed'])
        self.assertEqual(result['guarded_common_flow_profile_reads'],0)
        self.assertEqual(sum(len(r['scores']) for r in result['guarded_candidate_rows']),12)
