import unittest
from fractions import Fraction as F
from unittest.mock import patch
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.root_secret_flow import RootSecretEngine
from werewolf.action_flow import resolve_action
from werewolf.public_convergence import state_key
from werewolf.calculation_budget import calculation_budget

class HunterEvaluatedFlowRecordTests(unittest.TestCase):
 def case(self,repeat=True,co=True):
  g=data(5,'random').to_game();g['hunters']=1;g['rules']['allow_repeat_guard']=repeat
  if co:g.update(claims=['seer','latent','latent','latent','latent'],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
  c=ClosedCalculation(BoardData.from_game(g),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  n=next(o.node for o in c.root.action(3) if not o.node.read().public.winner)
  return c,n
 def test_actual_outcomes_guard_memory_reports_and_named_values(self):
  with calculation_budget(4000000,max_seconds=60):
   c,node=self.case();e=c._ClosedCalculation__engine;source=node.read();value=node.forecast().village_win;graph=e.evaluation_graph
   oracle=RootSecretEngine(e.rules,e.strategy,exact_renaming=False)
   self.assertEqual(value,F(53,162));self.assertEqual(value,oracle.solve(*source,physical=source.physical))
   records=[(b,p,t,r) for (b,p,t),r in graph.actions.items() if b==source.public]
   self.assertTrue(records);self.assertTrue(graph.mornings);saw_success=saw_death=saw_guard=saw_report=False
   for b,p,target,record in records:
    self.assertEqual(record.value,oracle.act(b,p.public_state,p.past,target,p.private,p.observer,physical=p.physical))
    acquired,outcomes=resolve_action(b,p,target,oracle.action_policy,terminal_payoffs=True)
    self.assertTrue(record.acquired==acquired,'acquired Q/P laws differ');self.assertTrue(tuple(x.outcome for x in record.outcomes)==outcomes,'physical outcomes differ')
    self.assertEqual(sum(x.outcome.probability for x in record.outcomes),1)
    self.assertEqual(sum(x.outcome.probability*x.value for x in record.outcomes),record.value)
    for row in record.outcomes:
     saw_success|=len(row.outcome.board.alive)==len(b.alive);saw_death|=len(row.outcome.board.alive)<len(b.alive)
     if row.source is None:
      self.assertIsNotNone(row.outcome.board.winner);continue
     expected=oracle.action_policy.project(b,acquired,row.outcome,target)
     self.assertTrue(state_key(row.source)==state_key(expected),'projected full source differs')
     saw_guard|=any(h.guards for h in row.source.private.hypotheses)
     morning=graph.mornings[row.source];self.assertEqual(morning.value,row.value)
     self.assertEqual(sum(q for q,s,v in morning.branches),1)
     self.assertEqual(sum(q*v for q,s,v in morning.branches),morning.value)
     for q,child,v in morning.branches:
      self.assertEqual(v,oracle.solve(*child,physical=child.physical))
      saw_report|=child.past!=row.source.past
      for report in child.past[len(row.source.past):]:self.assertIn(report.player,child.public.alive)
    for info,policy in record.policies:
     if policy is not None:self.assertEqual(policy,oracle.wolf_policy(b,p.public_state,p.past,info.initial_roster,info.attacks))
    with patch.object(e,'solve',side_effect=AssertionError('trace consumer recalculated')),patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('trace consumer resolved again')):
     self.assertIs(graph.recorded_action(b,p,target),record)
   self.assertTrue(saw_success and saw_death and saw_guard and saw_report)
 def test_no_repeat_memories_and_shortcut_remain_explicit(self):
  with calculation_budget(4000000,max_seconds=60):
   c,node=self.case(repeat=False);node.forecast();e=c._ClosedCalculation__engine;saw_repeat_history=False
   for record in e.evaluation_graph.actions.values():
    for row in record.outcomes:
     if row.source is None:continue
     for h in row.source.private.hypotheses:
      for actor in {g.actor for g in h.guards}:
       guards=[g for g in h.guards if g.actor==actor]
       for before,after in zip(guards,guards[1:]):
        if before.night+1==after.night:
         saw_repeat_history=True;self.assertNotEqual(before.target,after.target)
   self.assertTrue(saw_repeat_history)
 def test_value_only_reduction_does_not_request_action_detail(self):
  from tests import test_uniform_fixed_backup as backup
  from werewolf.fixed_actor_continuation import fixed_uniform_action_value
  from werewolf.evaluation_graph import EvaluationGraph
  rules,strategy,source=backup.UniformFixedBackupTests().fixture(True)
  engine=RootSecretEngine(rules,strategy);engine.evaluation_graph=EvaluationGraph(engine)
  expected=fixed_uniform_action_value(source.public,source.public_law,source.physical_law,engine,None,physical=source.physical,past=source.past)
  self.assertIsNotNone(expected)
  with patch('werewolf.information_set_forecast.action_flow',side_effect=AssertionError('value-only shortcut expanded actions')):
   value=engine.solve(source.public,source.public_law,source.past,source.physical_law,None,physical=source.physical)
  self.assertEqual(value,expected)
  self.assertEqual(len(engine.evaluation_graph.actions),0);self.assertEqual(len(engine.evaluation_graph.mornings),0)


 def test_configuration_identity_keeps_cutoff_option(self):
  from dataclasses import replace
  from werewolf.exact_renaming import configuration
  c,node=self.case();strategy=replace(c._ClosedCalculation__engine.strategy,day='max')
  self.assertNotEqual(configuration(replace(strategy,win_cutoff=False)),configuration(replace(strategy,win_cutoff=True)))
