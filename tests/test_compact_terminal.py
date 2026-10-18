import unittest
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch
from werewolf.exact import Board,Rules,Strategy,initial_board,action_outcomes,replace_worlds
from werewolf.action_flow import resolve_action,action_flow
from werewolf.terminal_outcome import terminal_death_outcomes,TerminalOutcome
from werewolf.information_set_forecast import InformationSetForecast,InformationSetActionPolicy,Pending
from werewolf.seer_acquisition import from_board
from werewolf.seer_future_uniform import TrueScanState
from werewolf.actor_information import condition_actor_state
from werewolf.evaluation_branch import ActionInputs,physical_board
from werewolf.board_future import evidence_reconstruction,outcome_key
from benchmarks.player_match_groups.cut_out_compact_terminal import TerminalPolicy
from benchmarks.player_match_groups.cut_out_deferred_diagnostics import DeferredLedger


def fixture(n=3,phase='day',wolves=1,hunters=0):
    b=replace(initial_board(n,wolves,0,1,hunters),phase=phase)
    s=TrueScanState(from_board(b),(b.alive,),initial_rule='none')
    e=InformationSetForecast(Rules(initial_seer='none'),Strategy(day='random',night='random',fake_reports='random'))
    e.deferred_ledger=DeferredLedger(e);e.terminal_compact_actions=0;e.action_policy=TerminalPolicy(e)
    return b,ActionInputs(s,(),s,None,b),e


class CompactTerminalTests(unittest.TestCase):
    def test_scalar_day_and_night_construct_no_child_Board_but_full_details_are_exact(self):
        for phase in ('day','night'):
            b,p,e=fixture(phase=phase)
            with patch.object(Board,'__post_init__',side_effect=AssertionError('scalar child Board constructed')):
                acquired,rows=resolve_action(b,p,2,e.action_policy,terminal_payoffs=True)
                value=sum((o.probability*F(o.board.winner=='village') for o in rows),F())
            self.assertTrue(all(isinstance(o,TerminalOutcome) for o in rows))
            self.assertTrue(all(o.board.details.rows is None for o in rows))
            if phase=='night':
                self.assertEqual(len(acquired.public_state.rosters),2)
                self.assertTrue(any(h.acquisitions for h in acquired.private.hypotheses))
            full=InformationSetActionPolicy.outcomes(e.action_policy,b,acquired,2)
            self.assertEqual(value,sum((o.probability*F(o.board.winner=='village') for o in full),F()))
            for row in rows:
                expected=next(o for o in full if o.board.winner==row.board.winner)
                self.assertEqual(outcome_key(row),outcome_key(expected))
                self.assertEqual(row.materialize(),expected)
                self.assertIs(row.materialize(),row.materialize())
                self.assertEqual(row.board.worlds,expected.board.worlds)
            self.assertEqual(e.terminal_compact_actions,1)

    def test_physical_weights_are_not_replaced_by_public_Q(self):
        b,p,e=fixture()
        own=condition_actor_state(p.private,lambda h:h.roles[0]==1)
        p=replace(p,private=own,physical=physical_board(b,own))
        rows=terminal_death_outcomes(b,p,1,e)
        self.assertEqual([(o.probability,o.board.winner) for o in rows],[(F(1),'village')])
        public=terminal_death_outcomes(b,replace(p,private=p.public_state,physical=b),1,e)
        self.assertEqual(sum((o.probability for o in public if o.board.winner=='village'),F()),F(1,3))

    def test_full_history_contract_never_uses_compact_outcomes(self):
        b,p,e=fixture()
        acquired,rows=resolve_action(b,p,1,e.action_policy,terminal_payoffs=False)
        self.assertTrue(all(type(o.board)is Board for o in rows))
        self.assertEqual(e.terminal_compact_actions,0)
        self.assertEqual(rows,InformationSetActionPolicy.outcomes(e.action_policy,b,acquired,1))

    def test_any_continuation_hunter_or_custom_physics_declines_without_pruning(self):
        for phase in ('day','night'):
            b,p,e=fixture(n=4,phase=phase)
            self.assertIsNone(terminal_death_outcomes(b,p,2,e))
            acquired,rows=resolve_action(b,p,2,e.action_policy,terminal_payoffs=True)
            self.assertTrue(any(o.board.winner is None for o in rows))
            self.assertTrue(all(type(o.board)is Board for o in rows))
        b,p,e=fixture(hunters=1)
        self.assertIsNone(terminal_death_outcomes(b,p,2,e))
        b,p,e=fixture();e.physical_children=lambda *args:()
        self.assertIsNone(terminal_death_outcomes(b,p,2,e))
        b,p,e=fixture();e.strategy=replace(e.strategy,night='max')
        self.assertIsNone(terminal_death_outcomes(b,p,2,e))

    def test_existing_parity_can_end_a_larger_P_branch_without_changing_public_Q(self):
        b,p,e=fixture(n=5,wolves=2)
        own=condition_actor_state(p.private,lambda h:h.roles[0]==3)
        p=replace(p,private=own,physical=physical_board(b,own))
        rows=terminal_death_outcomes(b,p,3,e)
        self.assertEqual([(o.probability,o.board.winner,len(o.board.alive)) for o in rows],[(F(1),'wolf',4)])
        self.assertEqual(rows[0].materialize(),InformationSetActionPolicy.outcomes(e.action_policy,b,p,3)[0])

    def test_unsupported_public_corpse_and_observer_acquisition_still_fail(self):
        b,p,e=fixture(phase='night')
        q=condition_actor_state(p.public_state,lambda h:h.roles[0]==1)
        board=replace_worlds(b,q.public_roles)
        own=condition_actor_state(p.private,lambda h:h.roles[0]==2)
        payload=replace(p,public_state=q,private=own,physical=physical_board(board,own))
        for callback in (lambda:terminal_death_outcomes(board,payload,1,e),lambda:InformationSetActionPolicy.outcomes(e.action_policy,board,payload,1)):
            with self.assertRaises(Pending) as error:callback()
            self.assertEqual(error.exception.reason,'information_set_public_corpse_inconsistent')
        bad=replace(p,observer=lambda h,state:False)
        with self.assertRaises(Pending) as error:resolve_action(b,bad,2,e.action_policy,terminal_payoffs=True)
        self.assertIn('scan_outside_public_support',error.exception.reason)
        self.assertEqual(e.terminal_compact_actions,0)

    def test_counterfactual_terminal_payoff_does_not_invent_public_history_support(self):
        b,p,e=fixture();q=condition_actor_state(p.public_state,lambda h:h.roles[0]==1)
        b=replace_worlds(b,q.public_roles);own=condition_actor_state(p.private,lambda h:h.roles[0]==2)
        p=replace(p,public_state=q,private=own,physical=physical_board(b,own))
        row=terminal_death_outcomes(b,p,2,e)[0]
        self.assertEqual((row.probability,row.board.winner),(F(1),'village'))
        self.assertIsNone(row.context)
        with self.assertRaises(Pending):e.action_policy.project(b,p,row,2)

    def test_terminal_hook_change_invalidates_resolution_reuse(self):
        b,p,e=fixture()
        class Counting(TerminalPolicy):
            def outcomes(self,*args):self.calls+=1;return super().outcomes(*args)
        policy=Counting(e);policy.calls=0;e.action_policy=policy
        with evidence_reconstruction():
            resolve_action(b,p,2,policy,terminal_payoffs=True)
            self.assertEqual(policy.calls,0)
            policy.terminal_outcomes=lambda *args:None
            _,rows=resolve_action(b,p,2,policy,terminal_payoffs=True)
        self.assertEqual(policy.calls,1)
        self.assertTrue(all(type(o.board)is Board for o in rows))

    def test_illegal_self_bite_terminal_input_and_strategy_still_rejected(self):
        b,p,e=fixture(phase='night')
        own=condition_actor_state(p.private,lambda h:h.roles[0]==1)
        p=replace(p,private=own,physical=physical_board(b,own))
        with self.assertRaises(ValueError):terminal_death_outcomes(b,p,1,e)
        b,p,e=fixture();e.strategy=replace(e.strategy,include_self_bite=True)
        with self.assertRaises(ValueError):terminal_death_outcomes(b,p,2,e)
        b,p,e=fixture(n=2)
        with self.assertRaises(ValueError):terminal_death_outcomes(b,p,1,e)
        b,p,e=fixture(n=2,phase='night')
        for callback in (lambda:terminal_death_outcomes(b,p,1,e),lambda:InformationSetActionPolicy.outcomes(e.action_policy,b,p,1)):
            with self.assertRaises(Pending) as error:callback()
            self.assertEqual(error.exception.reason,'information_set_public_corpse_inconsistent')

    def test_observed_roster_filter_preserves_mass_and_custom_night_resolver_declines(self):
        b,p,e=fixture()
        _,rows=resolve_action(b,p,2,e.action_policy,terminal_payoffs=True,observed_alive=(1,2))
        self.assertEqual(rows,())
        b,p,e=fixture(phase='night')
        e.action_policy.night_outcomes=lambda *args:()
        self.assertIsNone(e.action_policy.terminal_outcomes(b,p,2))

    def test_complete_finite_case_and_actual_saved_day3_without_initial_search(self):
        from benchmarks.player_match_groups.cut_out_compact_terminal_fixture import audit
        from benchmarks.player_match_groups.cut_out_compact_terminal import CompactTerminalInitialEngine
        from benchmarks.player_match_groups.cut_out_separate_publications_fixture import reproduce
        from benchmarks.player_match_groups.cut_out_initial_publications import InitialPublicationEngine
        from werewolf.calculation_budget import calculation_budget
        from werewolf.board_future import calculation_origin,remember
        with calculation_budget(4000000,max_seconds=30):
            self.assertEqual(audit('four')['status'],'verified')
            graph,seed,request,source,saved=reproduce();outputs=[]
            for cls in (InitialPublicationEngine,CompactTerminalInitialEngine):
                engine=cls(graph,witness=seed.source_witness);engine.inherited_groups=seed.inherited_groups
                with calculation_origin(graph.data):
                    remember(engine,request,source)
                    value=engine.solve(*source,physical=source.physical)
                    actions=tuple((p,engine.act(*source[:3],p,source.private,source.observer,physical=source.physical)) for p in source.public.alive)
                outputs.append((value,actions))
            self.assertEqual(outputs[0],outputs[1])
            self.assertGreater(engine.terminal_compact_actions,0)

    def test_configured_self_bite_permission_and_exact_forced_weights_match_full(self):
        b,p,e=fixture(phase='night')
        e.rules=replace(e.rules,allow_self_bite=True)
        e.strategy=replace(e.strategy,include_self_bite=True)
        rows=terminal_death_outcomes(b,p,2,e)
        self.assertEqual(sum((o.probability for o in rows if o.board.winner=='village'),F()),F(1,3))
        self.assertEqual(tuple(o.materialize() for o in rows),InformationSetActionPolicy.outcomes(e.action_policy,b,p,2))
        e.strategy=replace(e.strategy,include_self_bite=False)
        rows=terminal_death_outcomes(b,p,2,e)
        self.assertEqual([(o.probability,o.board.winner) for o in rows],[(F(1),'wolf')])
        self.assertEqual(tuple(o.materialize() for o in rows),InformationSetActionPolicy.outcomes(e.action_policy,b,p,2))
