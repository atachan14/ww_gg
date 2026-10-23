import unittest,json
from fractions import Fraction as F
from unittest.mock import patch
from tests import test_evaluated_program_record as record_tests
from werewolf.public_convergence import state_key,public_night_observations,digest
from werewolf.calculation_budget import calculation_budget
from werewolf.calculation_tree import CalculationTree
from werewolf.generated_current import GeneratedCurrent
from werewolf.information_set_forecast import InformationSetForecast

class RecordedPublicProjectionTests(unittest.TestCase):
 def case(self):return record_tests.EvaluatedProgramRecordTests().case()
 def test_full_post_and_pre_report_laws_equal_existing_exact_projection(self):
  with calculation_budget(2000000,max_seconds=60):
   c,node=self.case();e=c._ClosedCalculation__engine;s=node.read();node.forecast()
   with e.group_scope(node.groups),node.relation_scope():
    projection=e.evaluation_graph.public_projection(s,node.groups,evaluate=True)
    self.assertIsNotNone(projection)
    old=public_night_observations(e,s,node.groups)
    before=public_night_observations(e,s,node.groups,publish=False)
   self.assertEqual({state_key(x.source):x.probability for x in projection.edges},{state_key(x):mass for mass,x,target in old})
   self.assertEqual({state_key(x.source):x.probability for x in projection.arrivals},{state_key(x):mass for mass,x,target in before if not x.public.winner})
   self.assertEqual(sum(x.probability for x in projection.edges),1)
   oracle=InformationSetForecast(e.rules,e.strategy,retire_uninformative_scans=False,exact_renaming=False);oracle.retain_joint_guard_history=True
   self.assertEqual(sum(x.probability*oracle.solve(*x.source,physical=x.source.physical) for x in projection.edges),projection.value)
   for arrival in projection.arrivals:
    self.assertEqual(arrival.source.past,s.past)
    self.assertEqual(sum(x.probability for x in arrival.updates),1)
    self.assertEqual(sum(x.probability*oracle.solve(*x.source,physical=x.source.physical) for x in arrival.updates),arrival.value)
 def test_tree_arrival_updates_and_cold_Current_use_evaluated_records(self):
  with calculation_budget(2000000,max_seconds=60):
   c,node=self.case();node.forecast();tree=CalculationTree.from_node(node)
   with patch('werewolf.public_convergence.public_night_observations',side_effect=AssertionError('independent projection called')):
    data=tree.read('0',True)
   arrivals=list(tree.nodes['0']['day_arrivals'].values());self.assertTrue(arrivals)
   for arrival in arrivals:
    key=arrival['node'];shown=tree.summary(key,True)
    self.assertEqual(shown['evaluation_trace']['owner'],'evaluator')
    self.assertTrue(shown['day_start']);self.assertTrue(shown['public_updates'])
    current=GeneratedCurrent(tree,key)
    self.assertEqual(state_key(current.source),state_key(tree.nodes[key]['node'].read()))
    cold=CalculationTree.from_node(node);restored=cold.restore(tree.route(key))
    self.assertEqual(state_key(cold.nodes[restored]['node'].read()),state_key(current.source))
   self.assertEqual(data['evaluation_trace']['public_projection'],'evaluated')

 def test_multiple_CO_and_medium_keep_full_joint_history_laws(self):
  from tests.test_role_staged_tree import RoleStagedTreeTests
  from tests.test_public_relation_orbits import PublicRelationOrbitTests
  from werewolf.board_flow import BoardData
  from werewolf.navigation_store import NavigationDocument
  for kind in ('linked-seers','seer-and-medium'):
   with self.subTest(kind=kind),calculation_budget(4000000,max_seconds=60):
    if kind=='linked-seers':
     doc=NavigationDocument(BoardData.from_game(PublicRelationOrbitTests().game('random')))
    else:doc=RoleStagedTreeTests().doc('medium')
    doc.game.action(3);node=doc.game.node;e=node._Node__calculation._ClosedCalculation__engine;s=node.read();node.forecast()
    with e.group_scope(node.groups),node.relation_scope():
     projection=e.evaluation_graph.public_projection(s,node.groups,evaluate=True)
     self.assertIsNotNone(projection)
     for published in (True,False):
      rows=projection.edges if published else projection.arrivals
      old=public_night_observations(e,s,node.groups,publish=published)
      self.assertEqual({state_key(x.source):x.probability for x in rows},{state_key(x):mass for mass,x,target in old if published or not x.public.winner})
 def test_manual_zero_update_representative_and_cold_history(self):
  from tests import test_day_action_quotient as fixture
  from werewolf.navigation_store import NavigationDocument
  from werewolf.navigation_tree import NavigationTree
  from werewolf.navigation_current import NavigationCurrent
  from werewolf.seer_acquisition import SeerReport
  with calculation_budget(4000000,max_seconds=60):
   doc=NavigationDocument(fixture.DayActionQuotientTests().data(5,0,0,1,1));original=doc.game.node.forecast().village_win
   update=doc.game.public_input(('seer','latent','latent','latent','latent'),(SeerReport(1,1,1,2,'white'),))
   self.assertEqual(update.selection_weight,0)
   doc.game.action(5);node=doc.game.node;node.forecast();view=NavigationTree(doc);shown=view.read(view.current_key(),True)
   self.assertEqual(shown['evaluation_trace']['public_projection'],'evaluated')
   tree=view.view(doc.game.current)[0];arrival=next(iter(tree.nodes['0']['day_arrivals'].values()))
   view.select(view.key(doc.game.current,arrival['node']))
   before=NavigationCurrent(doc.game).source
   self.assertNotIn(5,before.public.alive);self.assertEqual(before.public.day,2)
   self.assertEqual(len(before.past),1)
   cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())))
   self.assertEqual(state_key(NavigationCurrent(cold.game).source),state_key(before))
   doc.game.move('h0');self.assertEqual(doc.game.node.forecast().village_win,original)
