import copy,unittest
from dataclasses import replace
from fractions import Fraction as F
from threading import Event
from unittest.mock import patch
from werewolf.exact import initial_board,replace_worlds,action_outcomes,Rules,Strategy,legal_targets
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.phase_updates import night_observation_outcomes
from werewolf.transition_cache import cacheable_transition

class DeathTransitionMemoTests(unittest.TestCase):
    def test_exact_rows_for_role_mixes_day_night_and_shared_public_physical(self):
        for cast in ((4,1,0,1,0),(5,1,1,1,0),(5,1,0,0,1),(5,1,0,1,1)):
            root=initial_board(*cast);e=InformationSetForecast(Rules(),Strategy())
            for phase in ('day','night'):
                b=replace(root,phase=phase)
                for target in legal_targets(b,e.rules,e.strategy):
                    self.assertEqual(e.physical_children(b,target),action_outcomes(b,target,e.rules,e.strategy))
                    expected=(action_outcomes(b,target,e.rules,e.strategy) if phase=='day' else night_observation_outcomes(b,target,e.rules,e.strategy))
                    self.assertEqual(e.public_children(b,target),expected)
            self.assertLessEqual(len(e.death_transitions.entries),256)
        b=initial_board(5,1,0,1);e=InformationSetForecast(Rules(),Strategy())
        with patch('werewolf.information_set_forecast.action_outcomes',wraps=action_outcomes) as calls:
            q=e.public_children(b,2);p=e.physical_children(b,2)
            self.assertIs(q,p);self.assertEqual(calls.call_count,1)

    def test_key_keeps_target_role_mass_rules_strategy_and_history(self):
        b=initial_board(5,1,0,1);e=InformationSetForecast(Rules(),Strategy())
        variants=[(b,1,Rules(),Strategy()),(b,2,Rules(),Strategy()),
                  (b,1,Rules(initial_seer='none'),Strategy()),(b,1,Rules(),Strategy('random','random')),
                  (replace_worlds(b,(b.worlds[0][:-1]+(F(1),),),wolf_count=None),1,Rules(),Strategy()),
                  (next(o.board for o in action_outcomes(b,5,Rules(),Strategy()) if o.board.winner is None),1,Rules(),Strategy())]
        with patch('werewolf.information_set_forecast.action_outcomes',wraps=action_outcomes) as calls:
            for board,target,rules,strategy in variants:
                self.assertEqual(e.transition_children(board,target,rules,strategy),action_outcomes(board,target,rules,strategy))
            self.assertEqual(calls.call_count,len(variants))

    def test_role_carrier_reuse_preserves_two_private_histories(self):
        from werewolf.seer_acquisition import Hypothesis,Acquisition
        from werewolf.seer_future_uniform import TrueScanState
        from werewolf.belief_projection import project_private
        b=replace_worlds(initial_board(5,1,0,1),((2,0,1,0,F(1)),))
        states=[TrueScanState((Hypothesis((2,0,1,0),(Acquisition(1,1,t,'white'),),F(1)),),(b.alive,),initial_rule='normal',tracked=(1,)) for t in (3,4)]
        e=InformationSetForecast(Rules(initial_seer='normal'),Strategy());before=copy.deepcopy(states)
        rows=e.physical_children(b,5);again=e.physical_children(b,5);self.assertIs(rows,again)
        child=next(o.board for o in rows if o.board.winner is None)
        a,c=(project_private(s,child) for s in states)
        self.assertNotEqual(a,c);self.assertEqual(a.public_roles,c.public_roles)
        self.assertEqual(a.hypotheses[0].acquisitions[0].target,3);self.assertEqual(c.hypotheses[0].acquisitions[0].target,4)
        self.assertEqual(states,before)

    def test_errors_and_cache_hits_observe_cancel_time_and_manual_zero_choice(self):
        from werewolf.calculation_budget import cancellation_scope,calculation_budget,CalculationCancelled,CalculationBudgetExceeded
        b=replace_worlds(initial_board(3),((1,0,0,0,F(1)),));e=InformationSetForecast(Rules(),Strategy())
        self.assertEqual(e.physical_children(b,1)[0].board.winner,'village')
        self.assertEqual(e.physical_children(b,2)[0].board.winner,'wolf') # legal forced non-selected action
        size=len(e.death_transitions.entries)
        with self.assertRaises(ValueError):e.physical_children(b,9)
        self.assertEqual(len(e.death_transitions.entries),size)
        stop=Event();stop.set()
        with cancellation_scope(stop),self.assertRaises(CalculationCancelled):e.physical_children(b,1)
        with patch('werewolf.calculation_budget.monotonic',side_effect=(0.,1.)),calculation_budget(max_seconds=.001),self.assertRaises(CalculationBudgetExceeded):
            e.physical_children(b,1)
        self.assertEqual(e.physical_children(b,1),action_outcomes(b,1,e.rules,e.strategy))

    def test_bounds_and_mutable_subclass_compatibility(self):
        root=initial_board(3);e=InformationSetForecast(Rules(),Strategy())
        for i in range(300):
            b=replace_worlds(root,((1,0,0,0,F(1,i+2)),(2,0,0,0,F(i+1,i+2))),wolf_count=None)
            e.physical_children(b,3)
        self.assertEqual(len(e.death_transitions.entries),256);self.assertEqual(e.board_key_hashes,{})
        big=initial_board(6,1,1,1,1);fresh=InformationSetForecast(Rules(),Strategy())
        fresh.physical_children(big,1);self.assertEqual(len(fresh.death_transitions.entries),0)
        mutable=replace(root,claims=list(root.claims));self.assertFalse(cacheable_transition(mutable,e.rules,e.strategy))
        self.assertEqual(e.physical_children(mutable,1),action_outcomes(mutable,1,e.rules,e.strategy))
        class ChildRules(Rules):pass
        self.assertFalse(cacheable_transition(root,ChildRules(),e.strategy))
        no=InformationSetForecast(Rules(),Strategy(),memoize_flows=False);no.physical_children(root,1);self.assertEqual(len(no.death_transitions.entries),0)

    def test_equal_structural_hashes_never_merge_different_probabilities(self):
        import sys
        root=initial_board(3);small=F(1,sys.hash_info.modulus+2)
        laws=[((1,0,0,0,q),(2,0,0,0,1-q)) for q in (F(1,2),small)]
        a,b=(replace_worlds(root,law,wolf_count=None) for law in laws)
        self.assertEqual(hash(a),hash(b));self.assertNotEqual(a,b)
        e=InformationSetForecast(Rules(),Strategy())
        x=e.physical_children(a,3);y=e.physical_children(b,3)
        self.assertEqual(x,action_outcomes(a,3,e.rules,e.strategy));self.assertEqual(y,action_outcomes(b,3,e.rules,e.strategy))
        self.assertNotEqual(x,y);self.assertEqual(len(e.death_transitions.entries),2)

    def test_observed_self_bite_rule_and_configured_action_policy_stay_separate(self):
        b=replace(initial_board(5),phase='night')
        rules=Rules(allow_self_bite=True);policy=Strategy('random','random',include_self_bite=False)
        e=InformationSetForecast(rules,policy)
        public=e.public_children(b,1);physical=e.physical_children(b,1)
        self.assertEqual(public,night_observation_outcomes(b,1,rules,policy))
        self.assertEqual(physical,action_outcomes(b,1,rules,policy))
        self.assertNotEqual(public,physical)
        self.assertTrue(any(o.board.winner=='village' for o in public))
        self.assertFalse(any(o.board.winner=='village' for o in physical))

    def test_numeric_aliases_cannot_bypass_target_validation_or_rewrite_history(self):
        from werewolf.exact import PublicEvent
        class Target(int):pass
        e=InformationSetForecast(Rules(),Strategy());root=initial_board(5)
        e.physical_children(root,1)
        for target in (True,1.,F(1),Target(1)):
            with self.subTest(target_type=type(target)):
                with self.assertRaises(ValueError):e.physical_children(root,target)
        known=replace_worlds(root,((2,0,0,0,F(1)),))
        b=replace(known,alive=(2,3,4,5),history=(PublicEvent(1,'day',1),),phase='night',wolf_count=None)
        odd=replace(b,history=(PublicEvent(1.,'day',True),))
        self.assertEqual(b,odd);self.assertFalse(cacheable_transition(odd,e.rules,e.strategy))
        e.physical_children(b,3);rows=e.physical_children(odd,3)
        self.assertEqual(rows,action_outcomes(odd,3,e.rules,e.strategy))
        self.assertIs(type(rows[0].board.history[0].target),bool)
        self.assertIs(type(rows[0].board.history[0].day),float)
