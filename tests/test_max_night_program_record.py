import unittest
from fractions import Fraction as F
from unittest.mock import patch
from tests import test_evaluated_program_record as fixture
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.calculation_tree import CalculationTree
from werewolf.calculation_budget import calculation_budget

class MaxNightProgramRecordTests(unittest.TestCase):
 def test_selected_measure_policy_ties_and_independent_value(self):
  with calculation_budget(2000000,max_seconds=60):
   c,node=fixture.EvaluatedProgramRecordTests().case('max');e=c._ClosedCalculation__engine;s=node.read();value=node.forecast().village_win
   record=e.evaluation_graph.evaluated_program(s,node.groups);self.assertIsNotNone(record)
   oracle=InformationSetForecast(e.rules,e.strategy,retire_uninformative_scans=False,exact_renaming=False);oracle.retain_joint_guard_history=True
   self.assertEqual(value,oracle.solve(*s,physical=s.physical));self.assertEqual(sum(leaf.mass for leaf in record.program.leaves),1)
   self.assertEqual(sum(leaf.counter for leaf in record.program.leaves),1)
   self.assertTrue(any(not leaf.mass and leaf.counter for leaf in record.program.leaves))
   for info,policy in record.policies:
    expected=oracle.wolf_policy(s.public,s.public_state,s.past,info.initial_roster,info.attacks)
    self.assertEqual(policy,expected);self.assertEqual(sum(q for target,q in policy),1)
    self.assertEqual(len({q for target,q in policy}),1)
    for target,q in policy:self.assertFalse(info.initial_roster&(1<<(target-1)))
   self.assertEqual(record.evaluated_sources,tuple(record.program.values))
   for leaf in record.program.leaves:
    if leaf.mass:self.assertIn(leaf.source,record.evaluated_sources)
   before=record.evaluated_sources
   zero=next(leaf for leaf in record.program.leaves if not leaf.mass and leaf.counter)
   # Requested counterfactual detail uses this same evaluator continuation; the
   # original record's completed-source snapshot and source value do not change.
   self.assertEqual(record.program.continuation(e,zero),oracle.solve(*zero.source,physical=zero.source.physical))
   self.assertEqual(record.evaluated_sources,before);self.assertEqual(record.value,value)
 def test_tree_reuses_actual_program_and_keeps_projection_fallback(self):
  with calculation_budget(2000000,max_seconds=60):
   c,node=fixture.EvaluatedProgramRecordTests().case('max');e=c._ClosedCalculation__engine;node.forecast()
   record=e.evaluation_graph.evaluated_program(node.read(),node.groups);tree=CalculationTree.from_node(node)
   with patch('werewolf.anonymous_night.shared_night',side_effect=AssertionError('Tree compiled program again')):
    data=tree.read('0',True)
   self.assertIs(tree._program(node),record.program)
   self.assertEqual(data['evaluation_trace']['ability_program'],'evaluated')
   self.assertEqual(data['evaluation_trace']['public_projection'],'legacy-reconstruction')
   self.assertEqual(data['evaluation_trace']['owner'],'mixed-evaluator-program')
   self.assertIsNone(e.evaluation_graph.public_projection(node.read(),node.groups))
   def branches(stage):
    for branch in stage.get('branches',()):
     yield branch;yield from branches(branch['children'])
   self.assertTrue(any(b['policy_probability']=='0' and F(b['counter_probability'])>0 for b in branches(data['night_stages'])))

 def test_physical_conditioning_does_not_recommit_policy_from_P(self):
  with calculation_budget(2000000,max_seconds=60):
   c,node=fixture.EvaluatedProgramRecordTests().case('max');e=c._ClosedCalculation__engine;node.forecast()
   original=e.evaluation_graph.evaluated_program(node.read(),node.groups)
   h=node.read().private.hypotheses[0]
   own=node._select_physical('hypothesis',(h.roles,tuple((a.day,a.player,a.target,a.color) for a in h.acquisitions)))
   own.forecast();record=e.evaluation_graph.evaluated_program(own.read(),own.groups)
   self.assertIsNotNone(record);self.assertNotEqual(own.read().private,node.read().private)
   public=dict(original.policies)
   for info,policy in record.policies:self.assertEqual(policy,public[info])
