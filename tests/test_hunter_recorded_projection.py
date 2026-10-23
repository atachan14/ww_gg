import unittest
from fractions import Fraction as F
from unittest.mock import patch
from tests import test_hunter_evaluated_flow_record as fixture
from werewolf.root_secret_flow import RootSecretEngine
from werewolf.public_convergence import public_night_observations,state_key
from werewolf.calculation_tree import CalculationTree
from werewolf.generated_current import GeneratedCurrent
from werewolf.calculation_budget import calculation_budget

class HunterRecordedProjectionTests(unittest.TestCase):
 def test_recorded_full_death_no_death_and_report_laws_equal_named(self):
  for repeat in (True,False):
   with self.subTest(repeat=repeat),calculation_budget(4000000,max_seconds=60):
    c,node=fixture.HunterEvaluatedFlowRecordTests().case(repeat=repeat);e=c._ClosedCalculation__engine;s=node.read();value=node.forecast().village_win
    with patch.object(e,'solve',side_effect=AssertionError('projection solved again')),patch.object(e,'report_children',side_effect=AssertionError('projection regenerated reports')),patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('projection resolved again')):
     projection=e.evaluation_graph.public_projection(s,node.groups)
     self.assertIsNotNone(projection)
     self.assertIs(e.evaluation_graph.public_projection(s,node.groups,counter=True),projection)
    oracle=RootSecretEngine(e.rules,e.strategy,exact_renaming=False)
    for publish,rows in ((True,projection.edges),(False,projection.arrivals)):
     named=public_night_observations(oracle,s,node.groups,publish=publish)
     self.assertTrue({state_key(r.source):r.probability for r in rows}=={state_key(after):q for q,after,t in named if publish or not after.public.winner},'full Q/P observation law differs')
    self.assertEqual(projection.value,value);self.assertEqual(sum(r.probability for r in projection.edges),1)
    self.assertTrue(any(len(r.source.public.alive)==len(s.public.alive) for r in projection.edges))
    self.assertTrue(any(len(r.source.public.alive)<len(s.public.alive) for r in projection.edges))
    for arrival in projection.arrivals:
     self.assertEqual(sum(r.probability for r in arrival.updates),1)
     self.assertEqual(sum(r.probability*oracle.solve(*r.source,physical=r.source.physical) for r in arrival.updates),arrival.value)
 def test_tree_reuses_public_records_and_cold_Current(self):
  with calculation_budget(4000000,max_seconds=60):
   c,node=fixture.HunterEvaluatedFlowRecordTests().case();node.forecast();tree=CalculationTree.from_node(node)
   with patch('werewolf.public_convergence.public_night_observations',side_effect=AssertionError('Tree resimulated public transitions')),patch('werewolf.anonymous_night.shared_night',side_effect=AssertionError('Tree regenerated guard actions')):
    shown=tree.read('0',True)
   self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
   self.assertEqual(shown['evaluation_trace']['public_projection'],'evaluated')
   self.assertEqual(shown['evaluation_trace']['ability_program'],'factored-evaluated-flow')
   for key,row in list(tree.nodes.items()):
    if not row.get('public_bundle'):continue
    source=row['node'].read();self.assertTrue(state_key(GeneratedCurrent(tree,key).source)==state_key(source),'Current source differs')
    cold=CalculationTree.from_node(node);restored=cold.restore(tree.route(key))
    self.assertTrue(state_key(cold.nodes[restored]['node'].read())==state_key(source),'cold source differs')

 def test_guard_detail_factor_uses_only_recorded_joint_histories(self):
  from collections import defaultdict
  from werewolf.public_convergence import public_key
  with calculation_budget(4000000,max_seconds=60):
   c,node=fixture.HunterEvaluatedFlowRecordTests().case(repeat=False);e=c._ClosedCalculation__engine;s=node.read();value=node.forecast().village_win;graph=e.evaluation_graph
   with patch.object(e,'solve',side_effect=AssertionError('factor evaluated unseen state')),patch.object(e,'wolf_policy',side_effect=AssertionError('factor recomputed actor policy')),patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('factor resolved game again')):
    record=graph.evaluated_program(s,node.groups)
   self.assertIsNotNone(record);program=record.program;self.assertEqual(record.reason,'factored-evaluated-action-flow');self.assertEqual(program.stats['generated_actions'],0)
   expected=defaultdict(F);actual=defaultdict(F)
   identity=lambda after,h:(public_key(after),h.roles,h.acquisitions,h.guards,h.attacks)
   for row in graph.hunter_rows(s)[0]:
    mass,before,after=row[:3]
    for h in after.private.hypotheses:expected[identity(after,h)]+=mass*h.mass
   for leaf in program.leaves:
    self.assertEqual(len(leaf.source.private.hypotheses),1);h=leaf.source.private.hypotheses[0];actual[identity(leaf.source,h)]+=leaf.mass
    names=dict(leaf.correspondence)
    for step in leaf.steps:
     if step.kind=='guard_target':
      actor,target=names[step.actor.index],names[step.target.index]
      self.assertIn((actor,target),{(g.actor,g.target) for g in h.guards if g.night==s.public.day})
      self.assertNotEqual(actor,target)
     if step.kind=='wolf_target':self.assertNotIn(names[step.target.index],{names[a.index] for a in step.actors})
   self.assertTrue(dict(actual)==dict(expected),'recorded joint identity/memory masses differ')
   def check(stage):
    self.assertIs(stage.public,s.public_state)
    if stage.terminal:return
    self.assertEqual(sum(b.probability for b in stage.branches()),1)
    for branch in stage.branches():check(branch.state)
   check(program.root);self.assertEqual(program.root.value(e),value)

 def test_owned_anonymous_source_retains_explicit_fallback(self):
  c,node=fixture.HunterEvaluatedFlowRecordTests().case();node.forecast();e=c._ClosedCalculation__engine;s=node.read()
  e.anonymous_beliefs[s]=object()
  self.assertIsNone(e.evaluation_graph.hunter_rows(s));self.assertIsNone(e.evaluation_graph.evaluated_program(s,node.groups))

 def test_guard_success_publication_Current_preserves_empty_night(self):
  from werewolf.navigation_store import NavigationDocument
  from werewolf.navigation_tree import NavigationTree
  from werewolf.navigation_current import NavigationCurrent
  import json
  with calculation_budget(4000000,max_seconds=60):
   c,_=fixture.HunterEvaluatedFlowRecordTests().case();doc=NavigationDocument(c.data);doc.game.action(3);view=NavigationTree(doc);shown=view.read(view.current_key(),True)
   before_key,arrival=next((key,row) for key,row in shown['items'].items() if row.get('day_start') and len(row['alive'])==4 and any(len(shown['items'][u['node']]['reports'])>len(row['reports']) for u in row.get('public_updates') or ()))
   view.select(before_key);current=NavigationCurrent(doc.game)
   self.assertEqual(current.data.facts.day,2);self.assertEqual(current.data.facts.phase,'day')
   update=next(u['node'] for u in arrival['public_updates'] if len(shown['items'][u['node']]['reports'])>len(arrival['reports']))
   view.select(update);current=NavigationCurrent(doc.game)
   self.assertEqual(current.data.facts.day,2);self.assertEqual(current.data.facts.phase,'day')
   self.assertTrue(any(r.acquired_day==2 for r in current.source.past))
   cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())))
   self.assertTrue(state_key(NavigationCurrent(cold.game).source)==state_key(current.source),'empty-night cold Current differs')
