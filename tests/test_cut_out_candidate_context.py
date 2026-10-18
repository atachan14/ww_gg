import unittest
from benchmarks.player_match_groups.cut_out_candidate_context_fixture import audit,boundary_and_fixed_points

class CandidateContextTests(unittest.TestCase):
    def test_runtime_without_old_matching_preserves_candidate_profiles_and_private_scans(self):
        result=audit('basic5')
        self.assertEqual(result['legacy_canonical_calls_actual'],0)
        self.assertTrue(result['candidate_oracle']['candidate_equivalence_matches_old'])
        self.assertEqual(result['own_scan_targets'],[2,3,4,5])

    def test_medium_report_posteriors_mass_and_ties_do_not_need_canonical(self):
        result=audit('active5')
        self.assertEqual(result['legacy_candidate_constructor_calls_actual'],0)
        self.assertGreater(result['all_candidate_instruction_cold_readbacks'],0)
        self.assertGreater(result['private_report_posterior_witnesses'],0)

    def test_missing_proof_context_is_unsupported_and_future_private_target_stays_fixed(self):
        self.assertTrue(boundary_and_fixed_points()['no_legacy_fallback'])
