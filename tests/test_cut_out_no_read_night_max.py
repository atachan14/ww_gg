import unittest
from dataclasses import replace
from benchmarks.player_match_groups.cut_out_no_read_night_max import graph
from benchmarks.player_match_groups.cut_out_no_read_night_fixture import audit,read_control
from benchmarks.player_match_groups.cut_out_model_a import adapt_no_read_night_max_model_a,adapt_latent_max_model_a
from benchmarks.player_match_groups.partitioned_match_groups import UnsupportedPartition
from werewolf.exact import Rules

class NoReadNightMaxTests(unittest.TestCase):
    def test_proof_scope_is_five_player_none_no_public_abilities(self):
        spec=graph().engine.baseline.spec
        self.assertIsInstance(adapt_latent_max_model_a(spec),UnsupportedPartition)
        for changed in (replace(spec,players=4),replace(spec,mediums=1),replace(spec,rules=Rules(initial_seer='random_white')),
                        replace(spec,claims=('seer',)+('latent',)*4)):
            self.assertIsInstance(adapt_no_read_night_max_model_a(changed),UnsupportedPartition)

    def test_actual_profile_read_is_never_an_independence_certificate(self):
        result=read_control()
        self.assertEqual(result['diagnostics']['profile_reads'],1)
        self.assertFalse(result['numeric_certificate'])

    def test_private_complete_table_joint_and_scans_match_exact(self):
        result=audit('role')
        self.assertEqual(result['village_win'],'7/15')
        self.assertEqual(result['own_scan_targets'],[2,3,4,5])
        self.assertTrue(result['certified_policy_matches_existing_exact'])
