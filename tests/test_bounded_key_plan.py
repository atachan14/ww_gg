import unittest,threading
from fractions import Fraction as F
from dataclasses import replace
from werewolf.exact import initial_board,Rules,Strategy
from werewolf.seer_acquisition import from_board,normalize
from werewolf.seer_future_uniform import TrueScanState
from werewolf.exact_renaming import canonical_key
from werewolf.night_knowledge import WolfAttack
from werewolf.actor_information import WolfInformation
from werewolf.policy_choice import uniform_policy
from werewolf.calculation_budget import cancellation_scope,calculation_budget,CalculationCancelled,CalculationBudgetExceeded
from benchmarks.player_match_groups.bounded_key_plan import planned_key,KeyReusePlan

class BoundedKeyPlanTests(unittest.TestCase):
    def fixture(self,n=6):
        b=initial_board(n,1);s=TrueScanState(from_board(b),(b.alive,),initial_rule='none')
        return b,s,Rules(initial_seer='none'),Strategy()

    def test_complete_symmetry_proof_matches_full_keys_for_five_and_six(self):
        for n in(5,6):
            b,s,rules,strategy=self.fixture(n);plan=KeyReusePlan(max_seconds=1)
            expected=canonical_key(b,s,(),s,None,rules,strategy,max_mappings=1000,prune_automorphisms=False)
            self.assertEqual(planned_key(b,s,(),s,None,rules,strategy,plan=plan,max_mappings=120),expected)
            self.assertEqual(plan.certified_blocks,[tuple(range(1,n+1))]);self.assertEqual(plan.residual_count,1)
            if n==6:self.assertIsNone(canonical_key(b,s,(),s,None,rules,strategy,max_mappings=120))
            self.assertEqual(plan.reason,'complete')

    def test_equal_marginals_do_not_prove_cyclic_private_history_symmetry(self):
        b,s,rules,strategy=self.fixture();rosters=(b.alive,b.alive)
        hs=normalize(tuple(replace(h,attacks=(WolfAttack(1,t),),mass=F(1,30))for h in s.hypotheses for t in b.alive if not h.roles[0]&(1<<(t-1))))
        public=replace(s,hypotheses=hs,rosters=rosters)
        private=replace(public,hypotheses=normalize(tuple(h for h in hs if h.attacks[0].target==(h.roles[0].bit_length()%6)+1)))
        self.assertEqual(public.public_roles,private.public_roles)
        plan=KeyReusePlan(max_seconds=1)
        self.assertIsNone(planned_key(b,public,(),private,None,rules,strategy,plan=plan,max_mappings=120))
        self.assertEqual(plan.reason,'residual_mapping_limit');self.assertEqual(plan.certified_blocks,[])

    def test_root_policy_context_and_actor_mask_match_original(self):
        b,s,rules,strategy=self.fixture(5)
        profile=tuple((WolfInformation(h.roles[0]),uniform_policy(tuple(t for t in b.alive if not h.roles[0]&(1<<(t-1)))))for h in s.hypotheses)
        contexts=((b,s,(),profile),);keys=[]
        for actor in(1,2):
            kwargs=dict(target=1,wolf_profiles=contexts,actor_mask=actor,max_mappings=120)
            plan=KeyReusePlan(max_snapshots=64,max_serialized_cells=200000,max_seconds=1)
            expected=canonical_key(b,s,(),s,None,rules,strategy,**kwargs)
            actual=planned_key(b,s,(),s,None,rules,strategy,plan=plan,**kwargs)
            self.assertIsNotNone(actual);self.assertEqual(actual,expected);keys.append(actual)
        self.assertNotEqual(*keys)

    def test_local_plan_limits_return_missing_key_and_do_not_modify_sources(self):
        b,s,rules,strategy=self.fixture();before=(b,s)
        for options,reason in((dict(max_source_cells=1),'source_cell_limit'),(dict(max_snapshots=1),'snapshot_limit'),(dict(max_swaps=1),'swap_limit'),(dict(max_serialized_cells=1),'serialized_cell_limit')):
            plan=KeyReusePlan(max_seconds=1,**options)
            self.assertIsNone(planned_key(b,s,(),s,None,rules,strategy,plan=plan,max_mappings=120));self.assertEqual(plan.reason,reason)
        self.assertEqual((b,s),before)
        plan=KeyReusePlan(max_seconds=1);planned_key(b,s,(),s,None,rules,strategy,plan=plan)
        with self.assertRaises(ValueError):planned_key(b,s,(),s,None,rules,strategy,plan=plan)

    def test_request_cancel_and_work_limit_propagate_instead_of_fallback(self):
        b,s,rules,strategy=self.fixture();event=threading.Event();event.set()
        cancelled=KeyReusePlan()
        with cancellation_scope(event),self.assertRaises(CalculationCancelled):planned_key(b,s,(),s,None,rules,strategy,plan=cancelled)
        with self.assertRaises(ValueError):planned_key(b,s,(),s,None,rules,strategy,plan=cancelled)
        spent=KeyReusePlan()
        with calculation_budget(1),self.assertRaises(CalculationBudgetExceeded):planned_key(b,s,(),s,None,rules,strategy,plan=spent)
        with self.assertRaises(ValueError):planned_key(b,s,(),s,None,rules,strategy,plan=spent)
    def test_physical_law_is_not_replaced_by_public_projection(self):
        from werewolf.exact import replace_worlds
        b,s,rules,strategy=self.fixture(5)
        physical=replace_worlds(b,tuple((*w[:-1],F(1,2)if w[0]==1 else F(1,8))for w in b.worlds))
        plan=KeyReusePlan(max_snapshots=128,max_serialized_cells=200000,max_seconds=1)
        expected=canonical_key(b,s,(),s,None,rules,strategy,physical=physical,max_mappings=120)
        actual=planned_key(b,s,(),s,None,rules,strategy,plan=plan,physical=physical,max_mappings=120)
        self.assertIsNotNone(actual);self.assertEqual(actual,expected)
        self.assertNotEqual(actual,canonical_key(b,s,(),s,None,rules,strategy,max_mappings=120))

    def test_local_time_and_unsupported_shapes_fail_closed(self):
        from unittest.mock import patch
        b,s,rules,strategy=self.fixture()
        plan=KeyReusePlan()
        with patch('benchmarks.player_match_groups.bounded_key_plan.monotonic',side_effect=(0,1)):
            self.assertIsNone(planned_key(b,s,(),s,None,rules,strategy,plan=plan))
        self.assertEqual(plan.reason,'plan_time_limit')
        for kwargs,reason in((dict(wolf_profiles=((b,s),)),'profile_context_shape'),(dict(observer=lambda h,s:True),'unsupported_observer')):
            plan=KeyReusePlan(max_seconds=1);observer=kwargs.pop('observer',None)
            self.assertIsNone(planned_key(b,s,(),s,observer,rules,strategy,plan=plan,**kwargs));self.assertEqual(plan.reason,reason)
    def test_typed_observers_are_bounded_and_preserved(self):
        from werewolf.seer_intervention import SeerObserver
        from werewolf.guard_model import GuardObserver
        from werewolf.seer_acquisition import Acquisition
        b,s,rules,strategy=self.fixture(5)
        for observer in(SeerObserver(1,(),2,3),GuardObserver(b,1,3,tuple(h.roles for h in s.hypotheses))):
            plan=KeyReusePlan(max_snapshots=128,max_serialized_cells=200000,max_seconds=1)
            expected=canonical_key(b,s,(),s,observer,rules,strategy,max_mappings=120)
            actual=planned_key(b,s,(),s,observer,rules,strategy,plan=plan,max_mappings=120)
            self.assertIsNotNone(actual);self.assertEqual(actual,expected)
        oversized=SeerObserver(1,(Acquisition(2,1,2,'white'),)*33,2,3)
        plan=KeyReusePlan()
        self.assertIsNone(planned_key(b,s,(),s,oversized,rules,strategy,plan=plan));self.assertEqual(plan.reason,'observer_limit')