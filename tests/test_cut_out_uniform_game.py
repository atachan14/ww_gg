"""Finite full-game equality checks, each worker bounded externally."""
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from benchmarks.player_match_groups.cut_out_model_a import adapt_model_a
from benchmarks.player_match_groups.cut_out_saved_recipes import SavedCutOutGraph
from benchmarks.player_match_groups.cut_out_uniform_game import evaluate,OwnView
from benchmarks.player_match_groups.partitioned_match_groups import UnsupportedPartition
from werewolf.board_future import same_role_board,SavedOrigin
from werewolf.player_view import build_public_view,ViewScope,ResultFrame,private_api_rows
import test_cut_out_model_a as initial
import test_cut_out_morning as morning


def table(graph,forecast,view):
    root=graph.origin();law=root.public_state
    if view is not None:
        from werewolf.actor_information import condition_actor_state
        law=condition_actor_state(law,view.accepts)
    from werewolf.exact import replace_worlds
    board=replace_worlds(root.public,law.public_roles)
    marginals=[{r:board.role_probability(p,r) for r in ('wolf','medium','seer','hunter','villager')} for p in range(1,board.player_count+1)]
    if view is not None:
        return private_api_rows(marginals,targets=dict(forecast.action_values),final_values=dict(forecast.action_values),dawn_for=dict(forecast.by_dawn_values).get)
    roles=SimpleNamespace(probabilities=lambda p:marginals[p-1])
    frame=ResultFrame(ViewScope.public(graph.data),'complete','comparison')
    return build_public_view(graph.data,roles,board,frame,state=graph.data.to_game(),event_history=board.history,
        alive=board.alive,action_values=dict(forecast.action_values),by_dawn_values=dict(forecast.by_dawn_values),manual=True)


def audit(spec,view=None):
    graph=SavedCutOutGraph(adapt_model_a(spec));original=graph.data.inputs
    with (patch('werewolf.exact_renaming.canonical_key',side_effect=AssertionError('old permutation search')),
          patch('benchmarks.player_match_groups.cut_out_model_a.reconstruct_saved',side_effect=AssertionError('child reallocation'))):
        result,grouped=evaluate(graph,view=view)
        expected,full=evaluate(graph,view=view,official_reference=True)
    assert result==expected,(result,expected)
    assert table(graph,result,view)==table(graph,expected,view)
    assert grouped.costs['saved_origins']==full.costs['saved_origins']==1
    assert all(type(request.origin) is SavedOrigin for request in grouped.board_sources.values())
    assert graph.data.inputs==original
    # Every calculated representative's physical branch probabilities and
    # Boards match an actually evaluated individual in the OLD recursion.
    reference={(b,s,own,observer,target):outcomes for b,s,own,observer,target,outcomes in full.branch_records}
    for b,s,own,observer,target,outcomes in grouped.branch_records:
        assert reference[(b,s,own,observer,target)]==outcomes
        assert sum((q for q,_ in outcomes),F())==1
    reference_contexts={(c.public_state,c.past,c.private,c.observer,c.physical.day,c.physical.phase,c.physical.history):c for c in full.projected}
    for context in grouped.projected:
        counterpart=reference_contexts[(context.public_state,context.past,context.private,context.observer,context.physical.day,context.physical.phase,context.physical.history)]
        assert same_role_board(context.public,counterpart.public)
        assert same_role_board(context.physical,counterpart.physical)
        if context.board_data is not None:
            replay=context.board_data.roles()
            assert replay.public_state==context.public_state
            assert replay.private==context.private
            assert replay.past==context.past
            assert replay.observer==context.observer
            assert same_role_board(replay.physical,context.physical)
    return result,grouped,full


class CutOutUniformGameTests(unittest.TestCase):
    def test_four_player_complete_public_table(self):
        audit(initial.cases(4)['single'])

    def test_five_player_complete_public_table(self):
        audit(initial.cases()['single'])
        audit(morning.medium_spec())

    def test_cancelled_latent_root_reaches_decision(self):
        spec=replace(initial.cases()['single'],claims=('latent',)*5,reports=())
        audit(spec)

    def test_own_seer_and_wolf_conditions_preserve_public_policy(self):
        spec=initial.cases()['single']
        acquisition=adapt_model_a(spec).baseline.state.hypotheses[0].acquisitions[0]
        audit(spec,OwnView(1,'seer',(acquisition,)))
        audit(spec,OwnView(2,'wolf'))

    def test_unsupported_view_is_explicit(self):
        graph=SavedCutOutGraph(adapt_model_a(initial.cases(4)['single']))
        self.assertIsInstance(evaluate(graph,view=OwnView(1,'hunter')),UnsupportedPartition)
