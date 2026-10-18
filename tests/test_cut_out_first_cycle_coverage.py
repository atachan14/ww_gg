import unittest
from dataclasses import replace
from fractions import Fraction as F
from benchmarks.player_match_groups.cut_out_first_cycle_coverage import (
    census,make_prefix,check,observed_choice,Pending)
from werewolf.calculation_budget import calculation_budget
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.board_future import GeneratedBoard
from benchmarks.player_match_groups.cut_out_live_medium_forecast import cold


class FirstCycleCoverageTests(unittest.TestCase):
    def test_all_first_day_night_branches_and_explicit_coverage_layers(self):
        with calculation_budget(4000000,max_seconds=30):row=census()
        self.assertEqual(row['legal_labelled_histories'],42)
        self.assertEqual(row['legal_information_action_branches'],180)
        self.assertEqual(row['illegal_wolf_self_bite_branches'],72)
        self.assertEqual(row['unknown_corpse_physical_mass'],'3/5')
        self.assertEqual(row['report_aggregation_classification'],{'supported':40,'structure_unproved':0,'legitimate_exclusion':2})
        self.assertEqual(row['observed_mixture_certificate_after'],42)
        self.assertFalse(row['automatic_initial_solver_fast_dispatch'])

    def test_observed_corpse_can_remove_an_entire_count_class(self):
        cap=make_prefix(1,2)
        self.assertEqual(set(cap.source.public.wolf_count_distribution),{1})
        self.assertEqual(cap.choice.likelihood(cap.before),F(1,10))
        self.assertTrue(all(any(a.player==2 and a.day==2 for a in h.acquisitions) for h in cap.source.private.hypotheses))
        self.assertEqual(cold(cap,cap.request),cap.source)
        self.assertEqual(cap.engine.values,{})

    def test_count_choice_likelihood_updates_P_without_weighting_Q(self):
        cap=make_prefix(5,1);b=cap.source.public
        marginal=lambda law:sum((h.mass for h in law.hypotheses if (h.roles[0]&b.alive_mask).bit_count()==1),F())
        self.assertEqual(marginal(cap.source.public_state),F(1,3))
        self.assertEqual(marginal(cap.source.private),F(2,7))
        self.assertEqual(cap.physical_mass,F(1,60))
        self.assertEqual(cold(cap,cap.request),cap.source)

    def test_invalid_history_owner_and_policy_refuse_without_bypasses(self):
        for player in range(1,8):
            with self.assertRaises(Pending):make_prefix(player,player)
        cap=make_prefix(3,6)
        with self.assertRaises(Pending):check(replace(cap))
        with self.assertRaises(Pending):observed_choice(cap.registry,cap.witness,cap.before,cap.request,4,cap.choice.engine)
        other=InformationSetForecast(cap.engine.rules,replace(cap.engine.strategy,night='max'),exact_renaming=False)
        parent=GeneratedBoard(cap.request.origin,cap.request.history[:1])
        with self.assertRaises(Pending):observed_choice(cap.registry,cap.witness,cap.before,parent,4,other)
        r=cap.registry;data=r.data;r.data=data.updated(revision=data.to_game().get('revision',0)+1)
        try:
            with self.assertRaises(Pending):check(cap)
        finally:r.data=data