import unittest
from fractions import Fraction as F
from unittest.mock import patch
from tests import test_evaluated_program_record as fixture
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.public_convergence import state_key,public_night_observations
from werewolf.calculation_budget import calculation_budget
from werewolf.calculation_tree import CalculationTree
from werewolf.generated_current import GeneratedCurrent

class MaxNightProjectionRecordTests(unittest.TestCase):
 def test_named_pre_post_laws_and_values_for_both_measures(self):
  with calculation_budget(4000000,max_seconds=90):
   c,node=fixture.EvaluatedProgramRecordTests().case('max');e=c._ClosedCalculation__engine;s=node.read();value=node.forecast().village_win
   oracle=InformationSetForecast(e.rules,e.strategy,retire_uninformative_scans=False,exact_renaming=False);oracle.retain_joint_guard_history=True
   snapshots=tuple(e.evaluation_graph.evaluated_program(s,node.groups).program.values)
   with patch.object(e,'solve',side_effect=AssertionError('projection evaluated unseen continuation')):
    selected=e.evaluation_graph.public_projection(s,node.groups)
    counter=e.evaluation_graph.public_projection(s,node.groups,counter=True)
   self.assertEqual(snapshots,tuple(e.evaluation_graph.evaluated_program(s,node.groups).program.values))
   self.assertEqual(selected.value,value)
   self.assertNotEqual({state_key(x.source):x.probability for x in selected.edges},{state_key(x.source):x.probability for x in counter.edges})
   for use_counter,record in ((False,selected),(True,counter)):
    for publish,rows in ((True,record.edges),(False,record.arrivals)):
     named=public_night_observations(oracle,s,node.groups,counter=use_counter,publish=publish)
     self.assertEqual({state_key(x.source):x.probability for x in rows},{state_key(after):mass for mass,after,target in named if publish or not after.public.winner})
    self.assertEqual(sum(x.probability for x in record.edges),1)
    if record.value is not None:self.assertEqual(sum(x.probability*oracle.solve(*x.source,physical=x.source.physical) for x in record.edges),record.value)
    for arrival in record.arrivals:
     self.assertEqual(sum(x.probability for x in arrival.updates),1)
     if arrival.value is not None:self.assertEqual(sum(x.probability*oracle.solve(*x.source,physical=x.source.physical) for x in arrival.updates),arrival.value)
 def test_tree_projection_reuse_cold_Current_and_deferred_counter_values(self):
  with calculation_budget(4000000,max_seconds=90):
   c,node=fixture.EvaluatedProgramRecordTests().case('max');node.forecast();tree=CalculationTree.from_node(node)
   with patch('werewolf.public_convergence.public_night_observations',side_effect=AssertionError('Tree replayed public simulation')):
    data=tree.read('0',True)
   self.assertEqual(data['evaluation_trace']['owner'],'evaluator')
   arrivals=list(tree.nodes['0']['day_arrivals'].values());self.assertTrue(arrivals)
   for arrival in arrivals:
    key=arrival['node'];source=tree.nodes[key]['node'].read()
    self.assertEqual(state_key(GeneratedCurrent(tree,key).source),state_key(source))
    cold=CalculationTree.from_node(node);restored=cold.restore(tree.route(key))
    self.assertEqual(state_key(cold.nodes[restored]['node'].read()),state_key(source))
   for entry in tree.nodes['0']['public_bundles'].values():
    for counter,node_key in entry.get('nodes',{}).items():
     self.assertEqual(state_key(tree.nodes[node_key]['node'].read()),state_key(entry['sources'][counter][1]))
   self.assertTrue(any(row.get('defer_value') for row in tree.nodes.values()))
   for key,row in list(tree.nodes.items()):
    if row.get('defer_value'):
     self.assertIsNone(tree.summary(key)['village_win'])
     shown=tree.read(key)
     self.assertIsNotNone(shown['village_win'])
     break

 def test_linked_multiple_CO_pre_post_and_private_correlations(self):
  from tests import test_public_relation_orbits as linked
  from werewolf.board_flow import BoardData
  from werewolf.closed_calculation import ClosedCalculation
  with calculation_budget(4000000,max_seconds=90):
   c=ClosedCalculation(BoardData.from_game(linked.PublicRelationOrbitTests().game('max')),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
   node=next(o.node for o in c.root.action(3) if not o.node.read().public.winner);e=c._ClosedCalculation__engine;s=node.read();node.forecast()
   oracle=InformationSetForecast(e.rules,e.strategy,retire_uninformative_scans=False,exact_renaming=False);oracle.retain_joint_guard_history=True
   for counter in (False,True):
    projection=e.evaluation_graph.public_projection(s,node.groups,counter=counter);self.assertIsNotNone(projection)
    for publish,rows in ((True,projection.edges),(False,projection.arrivals)):
     named=public_night_observations(oracle,s,node.groups,counter=counter,publish=publish)
     self.assertEqual({state_key(x.source):x.probability for x in rows},{state_key(after):mass for mass,after,target in named if publish or not after.public.winner})
