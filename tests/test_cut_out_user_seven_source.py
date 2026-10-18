import unittest
from benchmarks.player_match_groups.cut_out_user_seven_source_fixture import audit_prefix,audit_endgame,audit_edits,audit_rejections

class UserSevenSourceTests(unittest.TestCase):
    def test_prefix_has_bound_two_wolf_source_without_full_forecast(self):
        self.assertTrue(audit_prefix()['full_forecast_refused'])
    def test_tiny_endgame_matches_exact_public_and_own_values(self):
        self.assertTrue(audit_endgame()['Table_joint_mass_exact'])
    def test_batch_provenance_and_reissued_edit_cancel_redo(self):
        self.assertTrue(audit_edits()['same_batch_redo_preserves_pair'])
    def test_stale_owner_revision_unbound_and_one_carrier_are_rejected(self):
        self.assertGreater(len(audit_rejections()['rejected']),10)
