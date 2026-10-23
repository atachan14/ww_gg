import unittest
from fractions import Fraction as F
from tests import test_max_day_decision_record as fixture
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.action_flow import resolve_action
from werewolf.evaluation_branch import ActionInputs
from werewolf.public_convergence import state_key
from werewolf.calculation_budget import calculation_budget

class MaxDayTransitionRecordTests(unittest.TestCase):
 def test_exact_children_and_same_Q_different_P(self):
  with calculation_budget(4000000,max_seconds=90):
   c=fixture.MaxDayDecisionRecordTests().closed();node=c.root;e=c._ClosedCalculation__engine;s=node.read()
   oracle=InformationSetForecast(e.rules,e.strategy,retire_uninformative_scans=False,exact_renaming=False);oracle.retain_joint_guard_history=True
   with e.group_scope(node.groups),node.relation_scope():decision=e.evaluation_graph.day_decision(s,evaluate=True)
   h=s.private.hypotheses[0]
   private=node._select_physical('hypothesis',(h.roles,tuple((a.day,a.player,a.target,a.color) for a in h.acquisitions)))
   self.assertIs(e.evaluation_graph.day_decision(private.read()),decision)
   for current in (node,private):
    source=current.read()
    for target in source.public.alive:
     with self.subTest(private=current is private,target=target),e.group_scope(current.groups),current.relation_scope():
      record=e.evaluation_graph.refine(source,current.groups,target)
      acquired,outcomes=resolve_action(source.public,ActionInputs(source.public_state,source.past,source.private,source.observer,source.physical),target,oracle.action_policy)
      expected={state_key(oracle.action_policy.project(source.public,acquired,o,target)):o.probability for o in outcomes}
      self.assertEqual({state_key(edge.source):edge.probability for edge in record.edges},expected)
      self.assertEqual(sum(edge.probability for edge in record.edges),1)
      value=oracle.act(*source[:3],target,source.private,source.observer,physical=source.physical)
      self.assertEqual(record.value,value)
      self.assertEqual(sum(edge.probability*oracle.solve(*edge.source,physical=edge.source.physical) for edge in record.edges),value)
      self.assertEqual(record.selection_probability,dict(decision.policy)[target])
      self.assertIs(e.evaluation_graph.refine(source,current.groups,target),record)
 def test_value_only_does_not_force_selection_or_refinement(self):
  c=fixture.MaxDayDecisionRecordTests().closed();node=c.root;e=c._ClosedCalculation__engine;s=node.read()
  with e.group_scope(node.groups),node.relation_scope():
   e.public_day_max(s.public,s.public_state,s.past)
   self.assertIsNone(e.evaluation_graph.refine(s,node.groups,1))
  self.assertIsNone(e.evaluation_graph.day_decision(s))
  self.assertFalse(e.evaluation_graph.refinements)
