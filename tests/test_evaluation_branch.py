import copy,unittest
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from werewolf.evaluation_branch import ActionInputs,ContinuationInputs,physical_board
from werewolf.exact import initial_board,replace_worlds,Rules,Strategy
from werewolf.public_prior import prepare_public_prior
from werewolf.seer_acquisition import normalize
from werewolf.action_flow import resolve_action
from werewolf.information_set_forecast import InformationSetForecast
from tests import test_guard_history_flow as history_fixture


class EvaluationBranchTests(unittest.TestCase):
    def test_explicit_physical_branch_is_not_rebuilt_from_public_mass(self):
        b=initial_board(5,1,0,0,1);s,_=prepare_public_prior({},b,Rules(),track_live_seers=False)
        own=replace(s,hypotheses=normalize(tuple(h for h in s.hypotheses if h.roles[0]==1)))
        actual=replace_worlds(b,own.public_roles);before=copy.deepcopy((b,s,own,actual))
        with patch('werewolf.evaluation_branch.replace_worlds',side_effect=AssertionError('unexpected rebuild')):
            self.assertIs(physical_board(b,own,actual),actual)
        self.assertNotEqual(actual.worlds,b.worlds)
        self.assertEqual((b,s,own,actual),before)

    def test_divergent_physical_facts_are_rejected_instead_of_silently_replaced(self):
        b=initial_board(5,1,0,0,1);s,_=prepare_public_prior({},b,Rules(),track_live_seers=False)
        with self.assertRaisesRegex(ValueError,'facts disagree'):
            physical_board(b,s,replace(b,day=2))

    def test_gj_actual_world_and_multiple_night_records_reach_next_solver(self):
        fixture=history_fixture.SharedGuardHistoryTests();b,s=fixture.fixture()
        class Traced(InformationSetForecast):
            def solve(self,b,s,past,private,observer,**kwargs):
                self.received=(b,s,private,kwargs.get('physical'))
                return super().solve(b,s,past,private,observer,**kwargs)
        e=Traced(fixture.rules,fixture.strategy)
        acquired,outcomes=resolve_action(b,ActionInputs(s,(),s,None,b),2,e.action_policy)
        success=next(o for o in outcomes if o.board.alive==b.alive)
        context=e.action_policy.project(b,acquired,success,2)
        self.assertIsInstance(context,ContinuationInputs)
        self.assertIs(context.physical,success.board)
        self.assertEqual(context.physical.role_probability(3,'hunter'),1)
        self.assertEqual(context.public.role_probability(2,'hunter'),F(3,4))
        self.assertTrue(all(len(h.guards)==len(h.attacks)==3 for h in context.private.hypotheses))
        self.assertEqual(e.action_policy.day_value(context),1)
        self.assertIs(e.received[3],success.board)
        self.assertEqual(e.received[2],context.private)

    def test_cache_and_uncached_paths_keep_same_physical_measure(self):
        fixture=history_fixture.SharedGuardHistoryTests();b,s=fixture.fixture()
        values=[]
        for memo in (False,True):
            e=InformationSetForecast(fixture.rules,fixture.strategy,memoize_flows=memo)
            values.append(e.solve(b,s,(),s,None,physical=b))
            self.assertEqual(e.solve(b,s,(),s,None,physical=b),values[-1])
        self.assertEqual(values,[F(1,8),F(1,8)])

    def test_mixed_physical_components_rederive_live_count_without_changing_law(self):
        from werewolf.exact import PublicEvent
        from werewolf.public_convergence import mix
        from werewolf.evaluation_branch import ContinuationInputs
        for seers,mediums in ((0,0),(1,0),(1,1)):
            with self.subTest(seers=seers,mediums=mediums):
                b=initial_board(7,2,mediums,seers,0)
                b=replace(b,alive=tuple(range(2,8)),history=(PublicEvent(1,'day',1),),phase='night',wolf_count=None)
                state,_=prepare_public_prior({},b,Rules(),track_live_seers=False)
                components=[]
                for count in (1,2):
                    law=replace(state,hypotheses=normalize(tuple(h for h in state.hypotheses if (h.roles[0]&b.alive_mask).bit_count()==count)))
                    physical=replace_worlds(b,law.public_roles,wolf_count=None)
                    self.assertEqual(physical.wolf_count,count)
                    components.append(ContinuationInputs(b,state,(),law,None,physical))
                for weights in ((F(1,3),F(2,3)),(F(3,4),F(1,4))):
                    expected=normalize(tuple(replace(h,mass=h.mass*w) for w,c in zip(weights,components) for h in c.private.hypotheses))
                    # Reusing the first component's count with this exact law
                    # is the old failure, independently of Tree construction.
                    merged=replace(state,hypotheses=expected)
                    with self.assertRaisesRegex(ValueError,'Count and joint distribution disagree'):
                        replace_worlds(components[0].physical,merged.public_roles)
                    result=mix(tuple(zip(weights,components)))
                    reverse=mix(tuple(reversed(tuple(zip(weights,components)))))
                    self.assertEqual(result.private.hypotheses,expected)
                    self.assertEqual(result.physical.worlds,result.private.public_roles)
                    self.assertEqual(result.physical.wolf_count_distribution,dict(zip((1,2),weights)))
                    self.assertIsNone(result.physical.wolf_count)
                    self.assertEqual(result,reverse)
                    self.assertIs(result.public,b)
                    self.assertIs(result.public_state,state)
                    self.assertEqual([c.physical.wolf_count for c in components],[1,2])
