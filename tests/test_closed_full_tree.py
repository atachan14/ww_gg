import unittest
from dataclasses import replace
from unittest.mock import patch
from benchmarks.player_match_groups.closed_full_tree_fixture import case,run
from werewolf.closed_calculation import ClosedCalculation
from werewolf.actor_information import PersonalInformation
from werewolf.information_set_forecast import Pending
from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded


class ClosedFullTreeTests(unittest.TestCase):
    def checked(self,n,kind,view='public'):
        result=run(n,kind,view)
        self.assertIsNone(result['termination'],result);self.assertEqual(result['returncode'],0,result)
        worker=result['worker'];self.assertEqual(worker['status'],'verified',result)
        self.assertLessEqual(worker['budget']['work'],250000)
        self.assertLess(worker['seconds'],30);self.assertLess(result['observed_peak_working_set_bytes'],384*1024*1024)
        for row in worker['views']:
            self.assertTrue(row['expanded_cold_Forecast_Table_equal']);self.assertGreater(row['counts']['action_edges'],0)
            self.assertGreater(row['counts']['cold_joint_sources'],0);self.assertGreater(row['mass_checks'],0)
        return worker

    def test_five_small_public_and_complete_owner_trees(self):
        for view in ('public','seer','wolf'):
            result=self.checked(5,'single',view);self.assertEqual(result['views'][0]['village_win'],'7/15')

    def test_five_correlated_true_fake_complete_owner_trees(self):
        for view in ('public','seer','wolf'):
            result=self.checked(5,'dual',view);self.assertEqual(result['views'][0]['village_win'],'7/15')

    def test_five_night_and_joint_medium_public_trees(self):
        self.assertEqual(self.checked(5,'night')['entry']['phase'],'night')
        self.assertGreater(self.checked(5,'medium-pair')['views'][0]['counts']['report_edges'],0)

    def test_undefined_multiple_fake_joint_kernel_is_rejected_before_recursion(self):
        g=case(5,'single').data.to_game();g.update(wolves=2,claims=['seer']*3+['latent']*2,seer_inputs=[dict(day=1,reporter=p,target=4,color='white') for p in (1,2,3)])
        from werewolf.board_flow import BoardData
        c=ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_wolf=True,aggregate_reports=True)
        for node in (c.root,c.root.personal(PersonalInformation(1,'seer'))[1]):
            with self.assertRaises(Pending) as caught:node.forecast()
            self.assertEqual(caught.exception.reason,'multiple_fake_report_correlation_unselected')
        self.assertEqual(c.stats()['values'],0);self.assertEqual(c.stats()['actions'],0)
        self.assertEqual(c._ClosedCalculation__engine.groups,())

    def test_budget_separate_scope_limit_and_no_ledger(self):
        data=case(5,'single').data;c=ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True)
        with self.assertRaises(CalculationBudgetExceeded):
            with calculation_budget(1):c.root.forecast()
        self.assertEqual(c._ClosedCalculation__engine.groups,());self.assertEqual(c.stats()['values'],0)
        from werewolf.acquisition_provenance import AcquisitionLedger,UniformAcquisitionCache
        with patch.object(AcquisitionLedger,'__init__',side_effect=AssertionError('ledger')),patch.object(UniformAcquisitionCache,'__init__',side_effect=AssertionError('proof cache')):
            self.assertEqual(str(c.root.forecast().village_win),'7/15')
        seven=ClosedCalculation(case(7,'single').data)
        with self.assertRaises(Pending):seven.root.forecast()
        self.assertEqual(seven.stats()['values'],0)

    def test_missing_initial_declaration_is_not_synthesized_as_future_policy(self):
        data=case(5,'dual').data;g=data.to_game();g['seer_inputs']=g['seer_inputs'][:1]
        from werewolf.board_flow import BoardData
        c=ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_reports=True)
        with self.assertRaises(Pending) as caught:c.root.forecast()
        self.assertEqual(caught.exception.reason,'closed_forecast_initial_report_pending')
        self.assertEqual(c.stats()['values'],0)
