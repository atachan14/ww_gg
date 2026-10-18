import unittest
from benchmarks.player_match_groups.cut_out_joint_night_forecast_fixture import audit,negatives

class JointNightForecastTests(unittest.TestCase):
    def test_four_player_full_forecast_and_saved_origin_branches(self):
        r=audit(4)
        self.assertTrue(r['complete_Forecast_action_horizon_Table_joint_equal'])
        self.assertEqual(r['fully_cold_samples'],1)
    def test_private_wolf_view_preserves_legal_joint_mass_and_all_labels(self):
        r=audit(5,'wolf')
        self.assertTrue(r['full_joint_selection_mass_equal'])
        self.assertTrue(r['all_terminal_sources_equal'])
    def test_bias_one_carrier_stale_owner_and_future_scope_are_refused(self):
        self.assertEqual(len(negatives()['rejected']),17)
