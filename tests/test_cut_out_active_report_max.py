import unittest
from dataclasses import replace
from benchmarks.player_match_groups.cut_out_active_report_max import graph
from benchmarks.player_match_groups.cut_out_active_report_fixture import audit,white_prior_dependency
from benchmarks.player_match_groups.cut_out_model_a import adapt_active_report_max_model_a
from benchmarks.player_match_groups.partitioned_match_groups import UnsupportedPartition

class ActiveReportMaxTests(unittest.TestCase):
    def test_candidate_identity_ties_and_private_posterior_recipes(self):
        result=audit(5,'random_white',True)
        self.assertGreater(result['four_candidate_witnesses'],0)
        self.assertGreater(result['two_candidate_uniform_tie_witnesses'],0)
        self.assertGreater(result['medium_instruction_cold_readbacks'],0)
        self.assertEqual(result['all_candidate_instruction_cold_readbacks'],result['candidate_outcome_joint_checks'])
        self.assertGreater(result['private_report_posterior_witnesses'],0)

    def test_entry_preserves_two_medium_co_and_existing_rules(self):
        spec=graph().engine.baseline.spec
        for changed in (replace(spec,players=6),replace(spec,mediums=0),replace(spec,claims=('latent',)*5)):
            self.assertIsInstance(adapt_active_report_max_model_a(changed),UnsupportedPartition)
        self.assertEqual(audit(4,'none',False)['report_frames'],0)

    def test_M1_white_prior_is_probed_instead_of_assumed_independent(self):
        result=white_prior_dependency()
        self.assertEqual(result['initial_hypotheses'],180)
        self.assertEqual(result['diagnostics']['complete_candidate_scores'],12)
        self.assertEqual(result['diagnostics']['profile_reads'],0)
        self.assertFalse(result['full_entry_expanded'])
