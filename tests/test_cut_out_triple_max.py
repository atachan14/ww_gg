import unittest
from benchmarks.player_match_groups.cut_out_triple_max_fixture import audit,active_report_diagnostic
from benchmarks.player_match_groups.cut_out_no_read_night_max import graph,evaluate
from werewolf.exact import Strategy
from fractions import Fraction as F

class TripleMaxTests(unittest.TestCase):
    def test_three_max_settings_are_preserved_without_inventing_fake_seer_max(self):
        source=graph(fake_reports='max')
        self.assertEqual(source.engine.baseline.strategy,Strategy())
        self.assertEqual(source.data.to_game()['policy']['fake_reports'],'max')
        self.assertEqual(source.engine.baseline.strategy.fake_seer_policy,('noncontradictory','uniform'))
        self.assertEqual(evaluate(source)[0].village_win,F(7,15))

    def test_active_report_max_is_defined_in_existing_common_flow_but_not_adopted(self):
        result=active_report_diagnostic()
        self.assertEqual(result['comparison_first_boundary'],'active_medium_report_max_outside_comparison_scope')
        self.assertEqual(result['existing_report_min_value'],'1/2')
        self.assertFalse(result['active_report_entry_adopted'])

    def test_full_initial_cast_stops_at_explicit_no_read_scope(self):
        result=audit('residual')
        self.assertEqual(result['first_boundary'],'five_player_no_read_requires_M0_initial_none_all_latent')
        self.assertFalse(result['approximation_used'])
