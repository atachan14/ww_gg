"""Full six-player scalar coverage without irrelevant initial score-table solves."""
import unittest
from fractions import Fraction as F
from collections import defaultdict
from unittest.mock import patch
from tests.random_guard_count_oracle import value
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.actor_information import WolfObserver,condition_personal
from werewolf.evaluation_branch import ActionInputs,physical_board
from werewolf.action_flow import resolve_action
from werewolf.calculation_budget import calculation_budget

class SixPlayerGuardOracleTests(unittest.TestCase):
 def test_independent_complete_recursion_phase_and_small_named_checks(self):
  self.assertEqual(value(3,1,0,'day'),F(1,3))
  self.assertEqual(value(4,1,1,'day'),F(7,24))
  self.assertEqual(value(4,1,1,'night'),F(35,108))
  self.assertEqual(F(4,27)*value(4,1,1,'day')+F(23,27)*value(3,1,0,'day'),F(53,162))
  self.assertEqual(F(2,3)*value(5,2,1,'night')+F(1,3)*value(5,2,0,'night'),F(7,486))

 def test_full_six_named_night_and_reports_match_complete_scalar_oracle(self):
  with calculation_budget(4000000,max_seconds=45):
   game=data(6,'random',wolves=2).to_game();game['hunters']=1
   game.update(claims=['seer',*['latent']*5],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
   calc=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
   e=calc._ClosedCalculation__engine;root=calc.root.read()
   self.assertTrue(e.rules.allow_repeat_guard);self.assertFalse(e.rules.allow_self_bite)
   self.assertEqual((e.strategy.day,e.strategy.night,e.strategy.fake_reports),('random',)*3)
   self.assertEqual(e.strategy.guard_position,('uniform',))
   with patch.object(e,'solve',side_effect=AssertionError('oracle setup/factorization requested a continuation solve')):
    acquired,outcomes=resolve_action(root.public,ActionInputs(root.public_state,root.past,root.private,None,root.physical),3,e.action_policy,terminal_payoffs=False)
    outcome=next(row for row in outcomes if row.board.winner is None)
    source=e.action_policy.project(root.public,acquired,outcome,3)
    _,own=condition_personal(source.private,WolfObserver((1<<3)|(1<<4)))
    self.assertEqual({h.roles[0] for h in own.hypotheses},{24})
    self.assertEqual({h.roles[2] for h in own.hypotheses},{1})
    guards=defaultdict(F)
    for h in own.hypotheses:guards[h.roles[3]]+=h.mass
    self.assertEqual(dict(guards),{2:F(1,3),4:F(1,3),32:F(1,3)})
    actual={};successes={}
    for target in (1,2,6):
     payload=ActionInputs(source.public_state,source.past,own,WolfObserver(24),physical_board(source.public,own,source.physical))
     acquired,outcomes=resolve_action(source.public,payload,target,e.action_policy,terminal_payoffs=False)
     self.assertEqual(sum(row.probability for row in outcomes),1)
     total=success=F()
     for outcome in outcomes:
      before=e.action_policy.project(source.public,acquired,outcome,target)
      if len(before.physical.alive)==5:success+=outcome.probability
      reports=((None,F(1),before),) if before.public.winner else tuple(e.report_children(before))
      self.assertEqual(sum(p for _,p,_ in reports),1)
      for _,p,after in reports:
       n=len(after.physical.alive);living=after.physical.alive_mask
       conditional=sum((h.mass*value(n,(h.roles[0]&living).bit_count(),int(bool(h.roles[3]&living)),'day') for h in after.private.hypotheses),F())
       total+=outcome.probability*p*conditional
     actual[target]=total;successes[target]=success
    self.assertEqual(successes,{1:F(1,6),2:F(1,12),6:F(1,12)})
    self.assertEqual(actual,{1:F(7,324),2:F(7,648),6:F(7,648)})
    self.assertEqual(sum(actual.values(),F())/3,F(7,486))

 def test_full_six_conditional_evaluator_values_and_recorded_Tree(self):
  from werewolf.actor_information import WolfInformation
  from werewolf.board_future import outcome_key
  from werewolf.group_partition import _fix
  from werewolf.calculation_tree import CalculationTree
  from werewolf.public_convergence import state_key,transport_view_source
  with calculation_budget(4000000,max_seconds=45):
   game=data(6,'random',wolves=2).to_game();game['hunters']=1
   game.update(claims=['seer',*['latent']*5],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
   calc=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
   e=calc._ClosedCalculation__engine;root=calc.root.read()
   # Same generator/projection as Node.action(3), without first calculating
   # values for unrelated executions merely to learn a uniform policy weight.
   acquired,rows=resolve_action(root.public,ActionInputs(root.public_state,root.past,root.private,None,root.physical),3,e.action_policy,terminal_payoffs=False)
   outcome=next(row for row in rows if row.board.winner is None)
   source=e.action_policy.project(root.public,acquired,outcome,3)
   night=calc._ClosedCalculation__node(source,_fix(calc.root.groups,(3,)),(('action',3,outcome_key(outcome)),))
   nodes={}
   for pack,targets in ((24,(1,2,6)),(40,(1,2,5))):
    _,node=night.personal(WolfObserver(pack));nodes[pack]=node;s=node.read()
    with e.actor_scope(WolfInformation(pack)):
     actual={target:e.act(s.public,s.public_state,s.past,target,s.private,s.observer,physical=s.physical) for target in targets}
     self.assertEqual(actual,{targets[0]:F(7,324),targets[1]:F(7,648),targets[2]:F(7,648)})
     self.assertEqual(node.forecast().village_win,F(7,486))
    # A completed scalar may deliberately omit detailed terminal contexts.
    # Request them through the SAME evaluator before testing trace consumption.
    record=e.evaluation_graph.personal_program(s,node.groups,evaluate=True);self.assertIsNotNone(record)
    self.assertEqual(record.value,F(7,486))
    with patch.object(e,'solve',side_effect=AssertionError('six Tree reran solve')),patch.object(e,'wolf_policy',side_effect=AssertionError('six Tree reselected policy')),patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('six Tree repeated transition')):
     projection=e.evaluation_graph.personal_projection(s,node.groups)
     shown=CalculationTree.from_node(node).read('0',True)
    self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
    self.assertEqual(sum(r.probability for r in projection.edges),1)
    self.assertTrue(all(len(h.attacks)==1 for r in projection.edges for h in r.source.private.hypotheses))
   # This is a valid full six-person renaming, not a smaller game: public
   # CO1/white2/execution3 stay fixed; exchange5/6 maps the entire pack/law.
   mapping=(1,2,3,4,6,5)
   self.assertTrue(state_key(transport_view_source(nodes[24].read(),mapping))==state_key(nodes[40].read()),'complete six-person symmetry failed')

if __name__=='__main__':unittest.main()
