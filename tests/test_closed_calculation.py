import unittest
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from benchmarks.player_match_groups.cut_out_publication_orbit_value_fixture import make_role_filter_scope
from benchmarks.player_match_groups.closed_calculation_fixture import worker
from benchmarks.player_match_groups.measure_shared_transition import worker as ordinary
from werewolf.closed_calculation import ClosedCalculation,_Node
from werewolf.actor_information import PersonalInformation,WolfInformation
from werewolf.night_knowledge import WolfAttack
from werewolf.seer_intervention import SeerObserver
from werewolf.information_set_forecast import Pending
from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded


class ClosedCalculationTests(unittest.TestCase):
    def calculation(self,data=None):
        return ClosedCalculation(make_role_filter_scope().graph.data if data is None else data,max_seconds=20)

    def night(self,c):
        root=c.root;h=next(h for h in root.read().private.hypotheses if h.roles[2]&1)
        known=tuple(a for a in h.acquisitions if a.player==1)
        _,node=root.personal(PersonalInformation(1,'seer',known))
        node=next(r.node for r in node.action(2) if r.node.read().public.winner is None)
        return node.personal(SeerObserver(1,known,2,4))[1]

    def test_same_two_named_tasks_and_independent_cold_without_ledger(self):
        for case in ('five-owner-night','seven-owner-three'):
            expected=ordinary(case,False,True);actual=worker(case,True)
            self.assertEqual(actual['semantic_digest'],expected['semantic_digest'])
            self.assertEqual(actual['cold_reads'],expected['cold_reads'])
            self.assertEqual(actual['states']['values'],expected['states']['values'])
            self.assertEqual(actual['states']['actions'],expected['states']['actions'])
            self.assertEqual(actual['states']['saved_sources'],0)
            self.assertGreater(actual['independent_group_generators'],0)
            self.assertNotIn('condition_recipe',actual['instrumented_calls'])

    def test_changed_input_opens_new_snapshot_and_private_cache(self):
        a=self.calculation();node=self.night(a);before=node.forecast()
        b=self.calculation(a.data.updated(revision=12345));other=self.night(b)
        self.assertIsNot(a.data,b.data)
        self.assertGreater(a.stats()['values'],0);self.assertEqual(b.stats()['values'],0)
        self.assertEqual(other.forecast(),before);self.assertEqual(node.forecast(),before)
        self.assertEqual(a.data.to_game().get('revision',0),0)
        with self.assertRaises(AttributeError):a.data=b.data
        with self.assertRaises(AttributeError):node.groups=other.groups
        with self.assertRaises(TypeError):_Node()
        with self.assertRaises(TypeError):ClosedCalculation(other.read())
        with self.assertRaises(ValueError):node.personal(other)
        with self.assertRaises(ValueError):node.action(other)
        with self.assertRaises(TypeError):node.reports(other)
        self.assertFalse(hasattr(a,'_action'))
        self.assertFalse(hasattr(a,'_personal'))

    def test_exported_recipe_cannot_modify_live_engine_or_cache(self):
        c=self.calculation();node=self.night(c);want=node.forecast();states=c.stats()
        request=node.export_request();engine=next(op.engine for op in request.history if hasattr(op,'engine'))
        engine.values['foreign']=0;engine.strategy=replace(engine.strategy,night='max')
        self.assertEqual(node.forecast(),want);self.assertEqual(c.stats(),states)
        fresh=node.export_request();fresh_engine=next(op.engine for op in fresh.history if hasattr(op,'engine'))
        self.assertIsNot(engine,fresh_engine);self.assertEqual(fresh_engine.strategy.night,'random')
        self.assertEqual(fresh.roles(),node.read())
        self.assertEqual(c.stats()['saved_sources'],0)

    def test_input_and_owner_validation_support_errors_and_bounds_remain(self):
        c=self.calculation();root=c.root
        with self.assertRaises(TypeError):ClosedCalculation({})
        with self.assertRaises(Pending):ClosedCalculation(c.data.updated(policy={'day':'random','night':'max','fake_reports':'random'}))
        with self.assertRaises(Pending):
            ClosedCalculation(type(c.data).from_game(c.data.to_game()|dict(players=7,claims=['seer']+['latent']*6))).root.forecast()
        with self.assertRaises(ValueError):root.action(0)
        with self.assertRaises(ValueError):root.personal(PersonalInformation(1,'villager'))
        with self.assertRaises(ValueError):root.personal(lambda h,s:True)
        info=WolfInformation.from_hypothesis(root.read().private.hypotheses[0])
        with self.assertRaises(ValueError):root.personal(replace(info,attacks=(WolfAttack(100,2),)))
        mass,wolf=root.personal(info)
        self.assertGreater(mass,0)
        self.assertIs(wolf.read().public_state,root.read().public_state)
        with self.assertRaises(ValueError):root.personal(SeerObserver(1,(),2,1))
        _,own=root.personal(PersonalInformation(1,'seer'))
        with self.assertRaises(ValueError):own.personal(PersonalInformation(2,'villager'))
        node=self.night(c)
        with self.assertRaises(CalculationBudgetExceeded):
            with calculation_budget(1):node.forecast()
        from werewolf.board_future import _rebuilding
        self.assertFalse(_rebuilding.get())
        self.assertEqual(node.forecast().village_win,F(1,3))
        self.assertFalse(_rebuilding.get())
