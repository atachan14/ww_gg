import unittest
from copy import deepcopy
from fractions import Fraction as F
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import make_role_filter_scope,forecast,tables
from benchmarks.player_match_groups.cut_out_first_cycle_coverage import base
from benchmarks.player_match_groups.cut_out_compact_terminal_fixture import independent_cold
from werewolf.closed_calculation import ClosedCalculation
from werewolf.board_future import SavedOrigin,GeneratedBoard,remember,calculation_origin
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.exact import Strategy


from benchmarks.player_match_groups.closed_saved_day_fixture import saved_day


class ClosedSavedDayTests(unittest.TestCase):
    def test_saved_day_matches_initial_generation_full_state_and_cold(self):
        for graph,target,probability in ((make_role_filter_scope().graph,2,F(2,15)),(base()[0],1,F(1,7))):
            initial=ClosedCalculation(graph.data)
            live=next(r.node for r in initial.root.action(target) if r.node.read().public.winner is None)
            current=saved_day(graph.data,target);reopened=ClosedCalculation(current)
            self.assertIs(reopened.data,current)
            self.assertEqual(reopened.entry_probability,probability)
            self.assertEqual(reopened.root.read(),live.read())
            self.assertEqual(reopened.root.groups,live.groups)
            self.assertGreater(max(map(len,reopened.root.groups)),1)
            self.assertEqual(independent_cold(graph,reopened.root.export_request()),live.read())
            self.assertEqual(reopened.stats()['saved_sources'],0)
            # The ordinary saved path has the same complete hypotheses but a
            # different acquisition/declaration configuration. Do not overwrite
            # either representation just to make whole objects compare equal.
            baseline=SavedOrigin(current,current.game_data.rules,Strategy(**current.to_game()['policy']),False)()
            for attr in ('public_state','private'):
                self.assertEqual(getattr(baseline,attr).hypotheses,getattr(live.read(),attr).hypotheses)
                self.assertEqual(getattr(baseline,attr).rosters,getattr(live.read(),attr).rosters)
            if current.game_data.players==5:
                e=InformationSetForecast(current.game_data.rules,Strategy(**current.to_game()['policy']),exact_renaming=False,retire_uninformative_scans=False)
                e.retain_joint_guard_history=True
                request=GeneratedBoard(SavedOrigin(current,e.rules,e.strategy,False))
                with calculation_origin(current):
                    remember(e,request,baseline);want=forecast(e,baseline)
                got=reopened.root.forecast()
                self.assertEqual(got,want);self.assertEqual(tables(reopened.root.read(),got),tables(baseline,want))

    def test_edit_cancel_and_recalculate_are_new_snapshots(self):
        data=make_role_filter_scope().graph.data
        first=ClosedCalculation(saved_day(data,2));old=first.root.read()
        edited=ClosedCalculation(saved_day(data,3))
        self.assertEqual(first.root.read(),old)
        self.assertNotEqual(edited.root.read().public.alive,old.public.alive)
        self.assertEqual(edited.entry_probability,F(1,5))
        self.assertEqual(max(map(len,edited.root.groups)),3)
        cancelled=ClosedCalculation(first.data.updated(history=[]))
        self.assertEqual(cancelled.root.read(),ClosedCalculation(data).root.read())
        self.assertEqual(cancelled.entry_probability,1)
        self.assertEqual(edited.stats()['values'],0)

    def test_other_saved_conditions_decline_and_night_weights_are_not_constant(self):
        data=make_role_filter_scope().graph.data;mid=saved_day(data,2)
        with self.assertRaises(Pending):ClosedCalculation(mid.child(mid.to_game()['history'][0]))
        game=mid.to_game();game['history'][0]['policy']['day']='max'
        with self.assertRaises(Pending):ClosedCalculation(mid.updated(history=game['history']))
        with self.assertRaises(Pending):ClosedCalculation(mid.updated(claims=['latent']*5))
        with self.assertRaises(Pending):ClosedCalculation(mid.updated(seer_inputs=[]))
        graph=base()[0];night=ClosedCalculation(saved_day(graph.data,1)).root
        choices=[c for c in night.wolf_choices() if c.target==4]
        self.assertEqual({c.probability for c in choices},{F(1,5),F(1,4)})
        total=sum((c.mass for c in choices),F())
        prior=sum((c.information_mass for c in choices if (c.information.initial_roster&night.read().public.alive_mask).bit_count()==2),F())
        posterior=sum((c.mass for c in choices if (c.information.initial_roster&night.read().public.alive_mask).bit_count()==2),F())/total
        self.assertNotEqual(prior,posterior)
