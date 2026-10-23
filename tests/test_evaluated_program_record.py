import unittest
from fractions import Fraction as F
from unittest.mock import patch
from tests.test_joint_action_kernel import fixture
from werewolf.closed_calculation import ClosedCalculation
from werewolf.calculation_tree import CalculationTree
from werewolf.calculation_budget import calculation_budget

class EvaluatedProgramRecordTests(unittest.TestCase):
 def case(self,mode='random'):
  old,unused,client=fixture(mode)
  c=ClosedCalculation(old.data,grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
  node=next(o.node for o in c.root.action(3) if not o.node.read().public.winner)
  return c,node
 def test_record_is_the_actual_completed_evaluator_program(self):
  with calculation_budget(1000000,max_seconds=45):
   c,node=self.case();e=c._ClosedCalculation__engine;s=node.read()
   value=node.forecast().village_win
   record=e.evaluation_graph.evaluated_program(s,node.groups,evaluate=True)
   self.assertIsNotNone(record);self.assertEqual(record.value,value)
   self.assertEqual(sum(leaf.mass for leaf in record.program.leaves),1)
   self.assertEqual(record.evaluated_sources,tuple(record.program.values))
   self.assertTrue(record.evaluated_sources)
   self.assertEqual(sum(branch.probability*branch.state.value(e) for branch in record.program.root.branches()),record.value)
   from werewolf.information_set_forecast import InformationSetForecast
   oracle=InformationSetForecast(e.rules,e.strategy,retire_uninformative_scans=False,exact_renaming=False);oracle.retain_joint_guard_history=True
   self.assertEqual(record.value,oracle.solve(*s,physical=s.physical))
 def test_tree_uses_record_without_recompiling_ability_program(self):
  with calculation_budget(1000000,max_seconds=45):
   c,node=self.case();e=c._ClosedCalculation__engine;node.forecast()
   record=e.evaluation_graph.evaluated_program(node.read(),node.groups,evaluate=True)
   self.assertIsNotNone(record);tree=CalculationTree.from_node(node)
   with patch('werewolf.anonymous_night.shared_night',side_effect=AssertionError('Tree recompiled a completed evaluator program')),patch('werewolf.public_convergence.public_night_observations',side_effect=AssertionError('Tree replayed independent public projection')):
    data=tree.read('0',True)
   self.assertIs(tree._program(node),record.program)
   self.assertEqual(data['evaluation_trace']['owner'],'evaluator')
   self.assertEqual(data['evaluation_trace']['ability_program'],'evaluated')
   self.assertEqual(data['evaluation_trace']['public_projection'],'evaluated')
   self.assertTrue(data['night_stages']['branches'])
 def test_MAX_retains_actual_program_without_claiming_counterfactual_projection(self):
  with calculation_budget(1000000,max_seconds=45):
   c,node=self.case('max');e=c._ClosedCalculation__engine
   self.assertTrue(e.evaluation_graph.program_scope(node.read()))
   value=node.forecast().village_win
   record=e.evaluation_graph.evaluated_program(node.read(),node.groups)
   self.assertIsNotNone(record);self.assertEqual(record.value,value)
   self.assertTrue(any(leaf.mass!=leaf.counter for leaf in record.program.leaves))
   self.assertIsNone(e.evaluation_graph.public_projection(node.read(),node.groups))
 def test_record_identity_includes_the_full_public_source(self):
  # A program is keyed by the full immutable source plus groups, never a label.
  with calculation_budget(1000000,max_seconds=45):
   c,node=self.case();e=c._ClosedCalculation__engine;node.forecast()
   record=e.evaluation_graph.evaluated_program(node.read(),node.groups,evaluate=True)
   from dataclasses import replace
   changed=replace(node.read(),past=())
   if changed!=node.read():self.assertIsNone(e.evaluation_graph.evaluated_program(changed,node.groups))
   self.assertIsNotNone(record)
