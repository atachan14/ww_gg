"""Saved-input correction and demand-only individual correlation regressions."""
import unittest
from benchmarks.player_match_groups.cut_out_six_registry_fixture import edits_case,blocked_case,own_case,initial_case,medium_case,late_co_case


class SixInputRegistryTests(unittest.TestCase):
    def test_current_result_and_root_co_roundtrip_restore_joint_and_invalidate_old_actor(self):
        result=edits_case()
        self.assertTrue(result['old_snapshot_immutable'])
        self.assertTrue(result['unsupported_recipe_invalidated'])
        self.assertTrue(result['root_cancel_redo_exact'])
        self.assertTrue(result['physical_public_separate'])

    def test_late_co_common_pending_preserves_input_and_can_be_undone(self):
        result=blocked_case()
        self.assertEqual(result['reason'],'full_disclosure_truth_not_conditioned')
        self.assertTrue(result['candidate_input_preserved'])
        self.assertTrue(result['delete_withdraw_batch_recovers_exactly'])

    def test_own_complete_table_and_lazy_individual_branch(self):
        from benchmarks.player_match_groups.cut_out_six_registry_fixture import setup
        from benchmarks.player_match_groups.cut_out_six_registry import preview_action
        from benchmarks.player_match_groups.cut_out_uniform_game import OwnView
        from benchmarks.player_match_groups.cut_out_saved_recipes import InvalidatedBranch
        from werewolf.seer_acquisition import Acquisition
        _,registry=setup()
        self.assertIsInstance(preview_action(registry,5,view=OwnView(1,'seer',(Acquisition(1,4,3,'white'),))),InvalidatedBranch)
        result=own_case()['own_screen']
        self.assertTrue(result['joint_table_forecast_pairwise_equal'])
        self.assertFalse(result['terminal_tree_materialized_for_screen'])

    def test_initial_six_registry_can_cancel_and_reenter_co(self):
        result=initial_case()
        self.assertTrue(result['initial_six_registry_corrected'])
        self.assertEqual(result['initial_cancel_support'],6*5*(6-2))

    def test_medium_reports_and_complete_current_table_survive_lazy_detail(self):
        self.assertTrue(medium_case()['medium_reports_preserved'])

    def test_late_owned_co_withdraw_and_reenter_restores_the_original_reference(self):
        result=late_co_case()
        self.assertTrue(result['owned_late_co_cancel_redo_exact'])
        self.assertEqual(result['late_co_wolf1'],'5/8')
        self.assertEqual(result['initial_co_wolf1'],'1/4')
