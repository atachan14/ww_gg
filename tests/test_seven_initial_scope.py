import unittest
from benchmarks.player_match_groups.closed_full_tree_fixture import case
from werewolf.closed_calculation import ClosedCalculation,_forecast_scope
from werewolf.board_flow import BoardData
from werewolf.information_set_forecast import Pending
from werewolf.actor_information import PersonalInformation


class SevenInitialScopeTests(unittest.TestCase):
    def calc(self,game):return ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_wolf=True,aggregate_reports=True)
    def test_complete_initial_seven_admitted_without_solving(self):
        for kind in ('single','dual','three','medium-pair'):
            c=ClosedCalculation(case(7,kind).data,grouped=True,aggregate_wolf=True,aggregate_reports=True)
            _forecast_scope(c.root.read(),c._ClosedCalculation__engine)
            self.assertEqual(c.stats()['values'],0);self.assertEqual(c.stats()['actions'],0)
    def test_missing_initial_and_two_fakes_stay_public_support_refusals(self):
        g=case(7,'dual').data.to_game();g['seer_inputs']=g['seer_inputs'][:1];c=self.calc(g)
        for n in (c.root,c.root.personal(PersonalInformation(1,'seer'))[1]):
            with self.assertRaises(Pending) as caught:n.forecast()
            self.assertEqual(caught.exception.reason,'closed_forecast_initial_report_pending')
        g=case(7,'single').data.to_game();g.update(wolves=2,claims=['seer']*3+['latent']*4,seer_inputs=[dict(day=1,reporter=p,target=4,color='white') for p in (1,2,3)]);c=self.calc(g)
        for n in (c.root,c.root.personal(PersonalInformation(1,'seer'))[1]):
            with self.assertRaises(Pending) as caught:n.forecast()
            self.assertEqual(caught.exception.reason,'multiple_fake_report_correlation_unselected')
        self.assertEqual(c.stats()['values'],0)
    def test_eight_root_and_seven_night_use_semantic_scope_not_count_gate(self):
        c=ClosedCalculation(case(8,'single').data,grouped=True)
        _forecast_scope(c.root.read(),c._ClosedCalculation__engine)
        child=c.root.observe(2)[1]
        _forecast_scope(child.read(),c._ClosedCalculation__engine)
        self.assertEqual(c.stats()['values'],0)
    def test_seven_self_bite_max_and_guard_are_not_admitted(self):
        g=case(7,'single').data.to_game();g['rules']['allow_self_bite']=True;g['policy']['include_self_bite']=True;c=self.calc(g)
        with self.assertRaises(Pending) as caught:c.root.forecast()
        self.assertEqual(caught.exception.reason,'closed_forecast_self_bite_pending')
        for field in ('day','night','fake_reports'):
            g=case(7,'single').data.to_game();g['policy'][field]='max'
            with self.assertRaises(Pending) as caught:self.calc(g)
            self.assertEqual(caught.exception.reason,'closed_initial_uniform_H0_snapshot_only')
        g=case(7,'single').data.to_game();g['hunters']=2
        with self.assertRaises(Pending) as caught:self.calc(g)
        self.assertEqual(caught.exception.reason,'guard_multiple_hunters_unimplemented')
