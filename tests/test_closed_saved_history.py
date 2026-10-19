import unittest
from fractions import Fraction as F
from dataclasses import replace
from collections import defaultdict
from benchmarks.player_match_groups.closed_saved_history_fixture import case,audit
from benchmarks.player_match_groups.closed_saved_day_fixture import saved_day
from benchmarks.player_match_groups.cut_out_first_cycle_coverage import base
from werewolf.closed_calculation import ClosedCalculation
from werewolf.information_set_forecast import Pending
from werewolf.actor_information import PersonalInformation
from werewolf.calculation_budget import CalculationBudgetExceeded


class ClosedSavedHistoryTests(unittest.TestCase):
    def test_multiple_nights_named_public_owner_and_independent_cold(self):
        from unittest.mock import patch
        from werewolf.acquisition_provenance import AcquisitionLedger,UniformAcquisitionCache
        with patch.object(AcquisitionLedger,'__init__',side_effect=AssertionError('ledger')),patch.object(AcquisitionLedger,'_owner_current',side_effect=AssertionError('owner check')),patch.object(AcquisitionLedger,'_groups_record',side_effect=AssertionError('frame check')),patch.object(UniformAcquisitionCache,'__init__',side_effect=AssertionError('proof cache')):
            result=audit()
        self.assertEqual(result['status'],'verified')
        self.assertEqual([r['prefixes'][-1]['path_probability'] for r in result['cases']],['2/45','1/1750'])
        self.assertFalse(result['state_pruning'])

    def test_observed_wolf_selection_is_weighted_before_physical_outcomes(self):
        graph,targets=case(7);c=ClosedCalculation(saved_day(graph.data,2));night=c.root
        choices=[r for r in night.wolf_choices() if r.target==1]
        self.assertEqual({r.probability for r in choices},{F(1,5),F(1,4)})
        expected=defaultdict(F);total=F()
        for choice in choices:
            for outcome in choice.node.action(1):
                if outcome.node.read().public.winner is not None:continue
                weight=choice.mass*outcome.probability;total+=weight
                for h in outcome.node.read().private.hypotheses:
                    expected[h.roles,h.acquisitions,h.guards,h.attacks]+=weight*h.mass
        mass,node=night.observe(1)
        self.assertEqual(mass,total);self.assertEqual(total,F(23,100))
        actual={(h.roles,h.acquisitions,h.guards,h.attacks):h.mass for h in node.read().private.hypotheses}
        self.assertEqual(actual,{k:v/total for k,v in expected.items()})
        # An intervention omits q_I(target), giving a different P posterior.
        intervention=next(r.node for r in night.action(1) if r.node.read().public.winner is None)
        self.assertNotEqual(node.read().private.hypotheses,intervention.read().private.hypotheses)
        self.assertEqual(node.read().public.worlds,intervention.read().public.worlds)

    def test_edit_cancel_recalculate_and_export_keep_snapshots_isolated(self):
        graph,targets=case(7);data=graph.data
        for t in targets:data=saved_day(data,t)
        c=ClosedCalculation(data);before=c.root.read();want=c.root.forecast()
        edited=data.to_game()['history'];edited[-1]={**edited[-1],'target':5}
        changed=ClosedCalculation(data.updated(history=edited))
        self.assertNotEqual(changed.root.read().public.alive,before.public.alive)
        cancelled=ClosedCalculation(data.updated(history=data.to_game()['history'][:-1]))
        self.assertEqual(cancelled.root.read().public.phase,'night')
        self.assertEqual(changed.stats()['values'],0)
        self.assertEqual(c.root.read(),before);self.assertEqual(c.root.forecast(),want)
        request=c.root.export_request();engine=request.history[0].engine;engine.strategy=replace(engine.strategy,night='max')
        self.assertEqual(c.root.forecast(),want)
        self.assertEqual(c.root.export_request().roles(),before)
        self.assertEqual(c.stats()['saved_sources'],0)

    def test_unsupported_reports_observations_and_zero_support_remain_explicit(self):
        graph,_=case(5)
        with self.assertRaisesRegex(Pending,'new_seer_report'):
            ClosedCalculation(saved_day(saved_day(graph.data,2),4))
        from werewolf.board_flow import BoardData
        game=graph.data.to_game();game.update(players=7,mediums=1,claims=['seer','medium']+['latent']*5);game.pop('public_log',None)
        medium=BoardData.from_game(game)
        with self.assertRaisesRegex(Pending,'new_medium_report'):
            ClosedCalculation(saved_day(saved_day(medium,1),3))
        graph,_=case(5);data=saved_day(saved_day(graph.data,1),2)
        with self.assertRaisesRegex(Pending,'continuation_zero_support'):ClosedCalculation(saved_day(data,3))
        steps=data.to_game()['history'];steps[1].update(observation='death',deaths=[2])
        with self.assertRaisesRegex(Pending,'nonstandard'):ClosedCalculation(data.updated(history=steps))
        c=ClosedCalculation(graph.data);_,own=c.root.personal(PersonalInformation(2,'villager'))
        with self.assertRaises(ValueError):own.observe(1)
        with self.assertRaises((CalculationBudgetExceeded,Pending)):ClosedCalculation(data,max_work=1)
        self.assertEqual(ClosedCalculation(data).root.read().public.day,2)
