import unittest,json,time
from fractions import Fraction as F
from unittest.mock import patch
from tests import test_day_action_quotient as fixture
from werewolf.navigation_store import NavigationDocument
from werewolf.navigation_tree import NavigationTree
from werewolf.navigation_current import NavigationCurrent
from werewolf.calculation_budget import calculation_budget
from werewolf.public_convergence import state_key

class EvaluationGraphTests(unittest.TestCase):
 def doc(self,n=7,m=1,s=1,w=2):return NavigationDocument(fixture.DayActionQuotientTests().data(n,m,0,s,w))
 def test_recorded_seven_player_flow_and_nonrepresentative_current(self):
  with calculation_budget(4000000,max_seconds=60):
   doc=self.doc();node=doc.game.node;e=node._Node__calculation._ClosedCalculation__engine
   self.assertEqual(node.forecast().village_win,F(8,35));self.assertTrue(e.evaluation_graph.values)
   view=NavigationTree(doc);root=view.read(expand=True);self.assertEqual(root['evaluation_trace']['owner'],'evaluator')
   self.assertEqual(len(root['actions']),1);self.assertEqual(len(root['actions'][0]['branches']),1)
   doc.game.action(6);shown=view.read(view.current_key(),True)
   self.assertEqual(shown['stage_roles'],dict(seers=0,mediums=0,hunters=0));self.assertEqual(shown['night_stages']['method'],'evaluation-recorded-v1')
   self.assertNotIn('anonymous_ability_programs',vars(e));self.assertNotIn('night_programs',vars(e))
   stage=shown['night_stages']['branches'];self.assertEqual(sum(F(b['probability']) for b in stage),1)
   attack=stage[0];self.assertNotIn(6,attack['targets']);self.assertIn('人狼',attack['label'])
   target=attack['children']['branches'][0]['children']['leaves'][0]['node'];view.select(target)
   current=NavigationCurrent(doc.game).source;self.assertEqual(current.public.day,2);self.assertNotIn(6,current.public.alive)
   cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())))
   self.assertEqual(state_key(NavigationCurrent(cold.game).source),state_key(current))
   before=len(e.evaluation_graph.refinements);view.read(shown['node'],True);self.assertEqual(len(e.evaluation_graph.refinements),before)
 def test_public_refinement_matches_legacy_full_program_small_case(self):
  with calculation_budget(4000000,max_seconds=60):
   doc=self.doc(5,1,1,1);doc.game.action(1);view=NavigationTree(doc);key=view.current_key();tree=view.view('h1')[0]
   record=doc.game.node._evaluation_refinement()
   expected={state_key(edge.source):edge.probability for edge in record.edges}
   graph=tree.engine.evaluation_graph
   with patch.object(graph,'supports',return_value=False):
    bundles=tree._public_night_bundles('0')
   actual={state_key(entry['sources'][False][1]):entry['sources'][False][0] for entry in bundles.values() if False in entry['sources']}
   self.assertEqual(actual,expected)
 def test_count_independent_even_odd_and_private_history_preservation(self):
  for n in (4,5,6,7,8):
   with self.subTest(n=n),calculation_budget(4000000,max_seconds=60):
    doc=self.doc(n,1,0,1);node=doc.game.node;value=node.forecast().village_win;doc.game.action(n)
    row=doc.game.node._evaluation_refinement();self.assertIsNotNone(row)
    self.assertEqual(sum(edge.probability for edge in row.edges),1)
    self.assertTrue(all(edge.source.public_state and edge.source.private for edge in row.edges))
    self.assertEqual(node.forecast().village_win,value)
 def test_claimed_or_guard_keep_count_fallback_and_record_random_day(self):
  with calculation_budget(4000000,max_seconds=30):
   from tests.test_role_staged_tree import RoleStagedTreeTests
   for doc in (RoleStagedTreeTests().doc('medium'),RoleStagedTreeTests().doc('guard')):
    graph=doc.game.node._Node__calculation._ClosedCalculation__engine.evaluation_graph
    self.assertFalse(graph.supports(doc.game.node.read()))
    self.assertTrue(graph.recorded_day_scope(doc.game.node.read().public,doc.game.node.read()))
    record=doc.game.node._evaluation_refinement(3);self.assertIsNotNone(record)
    self.assertEqual(record.selection_probability,F(1,len(doc.game.node.read().public.alive)))
    self.assertEqual(sum(edge.probability for edge in record.edges),1)
    engine=doc.game.node._Node__calculation._ClosedCalculation__engine
    with patch.object(engine,'solve',side_effect=AssertionError('recorded day solved again')),patch.object(engine,'act',side_effect=AssertionError('recorded day acted again')),patch('werewolf.action_flow.resolve_action',side_effect=AssertionError('recorded day resolved again')):
     self.assertIs(doc.game.node._evaluation_refinement(3),record)

 def test_existing_owned_belief_route_is_preserved_as_explicit_fallback(self):
  with calculation_budget(4000000,max_seconds=20):
   doc=self.doc(5,0,1,1);node=doc.game.node;e=node._Node__calculation._ClosedCalculation__engine
   self.assertIn(node.read(),e.anonymous_beliefs)
   self.assertFalse(e.evaluation_graph.supports(node.read()))
   doc.game.action(1);self.assertIn(doc.game.node.read(),e.anonymous_beliefs)
   view=NavigationTree(doc);self.assertEqual(view.read()['evaluation_trace']['owner'],'legacy-reconstruction')
