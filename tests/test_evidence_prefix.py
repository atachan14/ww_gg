import unittest,weakref
from dataclasses import replace
from unittest.mock import patch
from fractions import Fraction as F
from werewolf import board_future as flow
from werewolf.board_flow import BoardData
from tests.test_board_flow import game
from werewolf.evaluation_branch import ContinuationInputs,physical_board
from werewolf.exact import initial_board,Rules,Strategy
from werewolf.seer_acquisition import from_board
from werewolf.seer_future_uniform import TrueScanState
from werewolf.actor_information import condition_actor_state
from werewolf.information_set_forecast import InformationSetForecast

class EvidencePrefixTests(unittest.TestCase):
 def fixture(self):
  data=BoardData.from_game(game())
  board=initial_board(5,1);law=TrueScanState(from_board(board),initial_rule='none',tracked=())
  state=ContinuationInputs(board,law,(),law,None,board)
  root=flow.GeneratedBoard(flow.KernelOrigin(state,data.game_data))
  return root,state
 def test_verified_prefix_runs_only_new_recipe_and_reference_replays_all(self):
  root,state=self.fixture();a=root.child(flow.PublicViewEvidence(),None);b=a.child(flow.PublicViewEvidence(),None)
  original=flow.GeneratedBoard.replay_operation
  with patch.object(flow.GeneratedBoard,'replay_operation',side_effect=original) as replay:
   self.assertEqual(a.roles(),state);self.assertEqual(replay.call_count,1)
   self.assertEqual(b.roles(),state);self.assertEqual(replay.call_count,2)
   self.assertEqual(b.roles(),state);self.assertEqual(replay.call_count,2)
   with flow.reconstruction_kernel_reuse(False):self.assertEqual(b.roles(),state)
   self.assertEqual(replay.call_count,4)
  self.assertIs(b.game_data,root.game_data)
 def test_private_siblings_and_public_view_keep_full_public_support(self):
  root,state=self.fixture();left=condition_actor_state(state.public_state,lambda h:h.roles[0]==1)
  right=condition_actor_state(state.public_state,lambda h:h.roles[0]==2)
  def own(law):return replace(state,private=law,physical=physical_board(state.public,law))
  a=root.child(flow.condition_recipe(state,own(left)),None)
  b=root.child(flow.condition_recipe(state,own(right)),None)
  self.assertEqual(a.roles().private,left);self.assertEqual(b.roles().private,right)
  public=a.child(flow.PublicViewEvidence(),None).roles()
  self.assertEqual(public.private,state.public_state)
  self.assertGreater(len(public.private.hypotheses),len(left.hypotheses))
  with flow.reconstruction_kernel_reuse(False):self.assertEqual(b.roles(),own(right))
 def test_replace_history_and_origin_clear_prefix_and_completed_values(self):
  root,state=self.fixture();a=root.child(flow.PublicViewEvidence(),None);a.roles()
  changed=replace(a,history=())
  self.assertIsNone(changed._parent);self.assertFalse(changed._completed)
  own=condition_actor_state(state.public_state,lambda h:h.roles[0]==1)
  target=replace(state,private=own,physical=physical_board(state.public,own))
  changed=replace(a,history=(flow.condition_recipe(state,target),))
  self.assertEqual(changed.roles(),target)
  replaced=replace(a,origin=flow.KernelOrigin(target,root.game_data),history=())
  self.assertEqual(replaced.roles(),target)
 def test_unknown_or_mutable_inputs_never_install_prefix_results(self):
  root,state=self.fixture()
  class MutableOrigin:
   game_data=root.game_data
   def __init__(self):self.calls=0
   def __call__(self):self.calls+=1;return state
  origin=MutableOrigin();request=flow.GeneratedBoard(origin)
  request.roles();request.roles();self.assertEqual(origin.calls,2);self.assertFalse(request._completed)
  from types import SimpleNamespace
  unknown=flow.GeneratedBoard(flow.KernelOrigin(SimpleNamespace(value=1),root.game_data))
  unknown.roles();self.assertFalse(unknown._completed)
  mutable=flow.GeneratedBoard(root.origin,[flow.PublicViewEvidence()])
  mutable.roles();self.assertFalse(mutable._completed)
  engine=InformationSetForecast(Rules(),Strategy())
  unsnapshotted=root.child(flow.ContextEvidence(engine),None)
  unsnapshotted.roles();self.assertFalse(unsnapshotted._completed)
 def test_failed_step_is_not_cached_and_hit_still_enforces_deadline(self):
  root,state=self.fixture();a=root.child(flow.PublicViewEvidence(),None)
  with patch.object(flow.PublicViewEvidence,'__call__',side_effect=ValueError('no support')):
   with self.assertRaisesRegex(ValueError,'no support'):a.roles()
  self.assertFalse(a._completed)
  from werewolf.seer_future_uniform import FuturePending
  with patch.object(flow.PublicViewEvidence,'__call__',return_value=FuturePending('not complete')):
   self.assertIsInstance(a.roles(),FuturePending)
  self.assertFalse(a._completed);self.assertEqual(a.roles(),state)
  from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded
  with calculation_budget(10,max_seconds=20),patch('werewolf.calculation_budget.monotonic',return_value=float('inf')):
   with self.assertRaises(CalculationBudgetExceeded):a.roles()
 def test_replace_recipe_and_saved_origin_never_copy_derived_memos(self):
  root,state=self.fixture();step=flow.PublicViewEvidence();step(state)
  self.assertTrue(step._completed);self.assertFalse(replace(step)._completed)
  engine=InformationSetForecast(Rules(),Strategy())
  a=next(o for o in engine.physical_children(state.public,5) if o.board.winner is None)
  b=next(o for o in engine.physical_children(state.public,4) if o.board.winner is None)
  action=flow.ActionEvidence(flow.kernel_snapshot(engine),5,flow.outcome_key(a))
  self.assertEqual(root.child(action,None).roles().physical.history[-1].target,5)
  edited=replace(action,target=4,observation=flow.outcome_key(b))
  result=root.child(edited,None).roles()
  self.assertEqual(result.physical.history[-1].target,4)
  with flow.reconstruction_kernel_reuse(False):self.assertEqual(root.child(edited,None).roles(),result)
  data=BoardData.from_game(game(mediums=1,claims=['medium']+['latent']*4));origin=flow.SavedOrigin(data,data.game_data.rules,Strategy())
  origin();changed=replace(origin,board_data=data.updated(claims=['latent']*5))
  self.assertFalse(changed._completed)
  self.assertNotEqual(origin().public.claims,changed().public.claims)
  self.assertEqual(changed(),flow.SavedOrigin(changed.board_data,changed.rules,changed.strategy)())
 def test_prefix_ownership_has_no_completed_result_cycle(self):
  root,state=self.fixture();child=root.child(flow.PublicViewEvidence(),None);child.roles()
  a=weakref.ref(root);b=weakref.ref(child);del root
  self.assertIsNotNone(a());del child
  self.assertIsNone(a());self.assertIsNone(b())

 def test_long_prefix_branch_edit_and_full_reference_keep_the_same_evidence(self):
  root,state=self.fixture();nodes=[root]
  for _ in range(64):nodes.append(nodes[-1].child(flow.PublicViewEvidence(),None))
  original=flow.GeneratedBoard.replay_operation
  with patch.object(flow.GeneratedBoard,'replay_operation',side_effect=original) as replay:
   self.assertEqual(nodes[-1].roles(),state)
   self.assertEqual(replay.call_count,64)
   branch=nodes[32].child(flow.PublicViewEvidence(),None)
   self.assertEqual(branch.roles(),state);self.assertEqual(replay.call_count,65)
   edited=replace(nodes[-1],history=nodes[-1].history[:17])
   self.assertIsNone(edited._parent);self.assertFalse(edited._completed)
   self.assertEqual(edited.roles(),state);self.assertEqual(replay.call_count,82)
   with flow.reconstruction_kernel_reuse(False):self.assertEqual(nodes[-1].roles(),state)
   self.assertEqual(replay.call_count,146)
  self.assertEqual(len(nodes[-1].history),64)
  self.assertEqual(len(edited.history),17)
