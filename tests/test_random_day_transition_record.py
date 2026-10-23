import unittest
from fractions import Fraction as F
from unittest.mock import patch
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.actor_information import GuardInformation,PersonalInformation
from werewolf.calculation_tree import CalculationTree
from werewolf.action_flow import resolve_action
from werewolf.evaluation_branch import ActionInputs
from werewolf.root_secret_flow import RootSecretEngine
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.public_convergence import state_key
from werewolf.calculation_budget import calculation_budget

class RandomDayTransitionRecordTests(unittest.TestCase):
 def case(self,hunter=True,personal=False,co=True):
  game=data(5,'random').to_game();game['hunters']=int(hunter)
  if co:game.update(claims=['seer','latent','latent','latent','latent'],seer_inputs=[dict(day=1,reporter=1,target=2,color='white')])
  c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  node=c.root
  if personal:_,node=node.personal(GuardInformation(4) if hunter else PersonalInformation(2,'villager'))
  return c,node
 def oracle(self,c):
  e=c._ClosedCalculation__engine
  other=RootSecretEngine(e.rules,e.strategy,exact_renaming=False) if c.data.game_data.hunters else InformationSetForecast(e.rules,e.strategy,exact_renaming=False,retire_uninformative_scans=False)
  other.retain_joint_guard_history=True;return other
 def test_actual_records_and_named_oracle_for_public_personal_QP(self):
  for hunter in (True,False):
   with self.subTest(hunter=hunter),calculation_budget(4000000,max_seconds=90):
    c,public=self.case(hunter);e=c._ClosedCalculation__engine;oracle=self.oracle(c)
    _,personal=public.personal(GuardInformation(4) if hunter else PersonalInformation(2,'villager'))
    self.assertIs(public.read().public_state,personal.read().public_state)
    for node in (public,personal):
     s=node.read();payload=ActionInputs(s.public_state,s.past,s.private,s.observer,s.physical)
     with e.group_scope(node.groups),node.relation_scope():
      value=e.solve(*s,physical=s.physical)
      self.assertEqual(value,oracle.solve(*s,physical=s.physical))
      for target in s.public.alive:
       record=e.evaluation_graph.refine(s,node.groups,target)
       self.assertIsNotNone(e.evaluation_graph.recorded_action(s.public,payload,target))
       acquired,outcomes=resolve_action(s.public,payload,target,oracle.action_policy)
       expected={state_key(oracle.action_policy.project(s.public,acquired,o,target)):o.probability for o in outcomes}
       actual={state_key(edge.source):edge.probability for edge in record.edges}
       self.assertTrue(actual==expected,'recorded full Q/P/observer children differ')
       self.assertEqual(record.selection_probability,F(1,len(s.public.alive)))
       self.assertEqual(record.value,oracle.act(*s[:3],target,s.private,s.observer,physical=s.physical))
       self.assertEqual(sum(edge.probability for edge in record.edges),1)
       self.assertEqual(sum(edge.probability*oracle.solve(*edge.source,physical=edge.source.physical) for edge in record.edges),record.value)
       self.assertTrue(all(edge.source.observer==s.observer for edge in record.edges))
 def test_tree_consumes_existing_records_without_transition_or_score_replay(self):
  with calculation_budget(4000000,max_seconds=90):
   c,node=self.case(True,True);e=c._ClosedCalculation__engine;s=node.read()
   with e.group_scope(node.groups),node.relation_scope():
    for target in s.public.alive:e.act(*s[:3],target,s.private,s.observer,physical=s.physical)
    e.solve(*s,physical=s.physical)
   self.assertFalse(bool(e.evaluation_graph.refinements))
   tree=CalculationTree.from_node(node)
   with patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('Tree reran transition')),patch.object(e,'solve',side_effect=AssertionError('Tree reran solve')),patch.object(e,'day_scores',side_effect=AssertionError('Random Tree requested Q scores')):
    shown=tree.read(tree.root,True)
   self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
   self.assertEqual(shown['evaluation_trace']['selection'],'fixed-uniform-day')
   self.assertTrue(all(a['evaluation_transition']=='evaluated' for a in shown['actions']))
   self.assertTrue(all(a['q_score'] is None for a in shown['actions']))
 def test_scalar_shortcut_remains_value_only_until_explicit_detail(self):
  c,node=self.case(co=False);e=c._ClosedCalculation__engine;s=node.read();g=e.evaluation_graph
  with patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('scalar shortcut forced detail')):value=e.solve(*s,physical=s.physical)
  self.assertFalse(bool(g.actions));self.assertFalse(bool(g.refinements))
  self.assertIsNone(g.day_refinement(s,node.groups,1,evaluate=False))
  detail=g.refine(s,node.groups,1)
  self.assertEqual(detail.reason,'requested-evaluated-day-detail')
  with patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('repeated detail')):self.assertTrue(g.refine(s,node.groups,1) is detail,'detail cache identity changed')
  self.assertEqual(g.value(s),value)
 def test_terminal_observation_projection_reuses_retained_context(self):
  game=data(3,'random').to_game();game['seers']=0;game['hunters']=1
  c=ClosedCalculation(BoardData.from_game(game),grouped=True,aggregate_reports=True,anonymous=True)
  _,node=c.root.personal(GuardInformation(2));s=node.read();e=c._ClosedCalculation__engine
  e.act(*s[:3],1,s.private,s.observer,physical=s.physical)
  with patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('terminal context replay')):record=e.evaluation_graph.refine(s,node.groups,1)
  self.assertTrue(all(edge.source.public.winner is not None for edge in record.edges))
  self.assertEqual(sum(edge.probability for edge in record.edges),1)

 def test_day_Current_representative_and_cold_routes_preserve_view(self):
  from werewolf.navigation_game import NavigationGame
  from werewolf.navigation_current import NavigationCurrent
  with calculation_budget(4000000,max_seconds=90):
   for hunter in (True,False):
    c,node=self.case(hunter,True);source=node.read();e=c._ClosedCalculation__engine
    tree=CalculationTree.from_node(node);shown=tree.read(tree.root,True)
    self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
    for action in shown['actions']:
     for branch in action['branches']:
      key=branch['node'];child=tree.nodes[key]['node'];cold=CalculationTree.from_node(node)
      restored=cold.restore(tree.route(key))
      self.assertTrue(state_key(cold.nodes[restored]['node'].read())==state_key(child.read()),'cold route differs')
      self.assertEqual(child.read().observer,source.observer)
    game=NavigationGame(node);game.action(5)
    self.assertNotIn(5,NavigationCurrent(game).source.public.alive)
    current=game.node.read()
    self.assertEqual(current.observer,source.observer)
    self.assertTrue(state_key(game.node.export_request().roles())==state_key(current),'cold selected representative differs')
    game.back();self.assertTrue(state_key(game.node.read())==state_key(source),'back lost private view')
    game.forward();self.assertTrue(state_key(game.node.read())==state_key(current),'forward changed view')
