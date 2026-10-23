import unittest,json,tempfile
from fractions import Fraction as F
from unittest.mock import patch
from tests import test_public_relation_orbits as relation_tests
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.calculation_tree import CalculationTree
from werewolf.calculation_budget import calculation_budget
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.navigation_store import NavigationDocument
from werewolf.navigation_current import NavigationCurrent
from werewolf.public_convergence import state_key

class MaxDayDecisionRecordTests(unittest.TestCase):
 def data(self):return BoardData.from_game(relation_tests.PublicRelationOrbitTests().game('max'))
 def closed(self):return ClosedCalculation(self.data(),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
 def test_complete_public_scores_ties_and_named_oracle(self):
  with calculation_budget(2000000,max_seconds=60):
   c=self.closed();node=c.root;s=node.read();e=c._ClosedCalculation__engine
   with e.group_scope(node.groups),node.relation_scope():record=e.evaluation_graph.day_decision(s,evaluate=True)
   self.assertTrue(record.complete);self.assertEqual(record.information,'public-Q')
   oracle=InformationSetForecast(e.rules,e.strategy,retire_uninformative_scans=False,exact_renaming=False);oracle.retain_joint_guard_history=True
   self.assertEqual(dict(record.scores),dict(oracle.day_scores(s.public,s.public_state,s.past)))
   policy=dict(record.policy);self.assertEqual(policy[1],F(1,2));self.assertEqual(policy[2],F(1,2))
   self.assertEqual({p for p,q in policy.items() if q==0},{3,4,5});self.assertEqual(sum(policy.values()),1)
   h=s.private.hypotheses[0]
   private=node._select_physical('hypothesis',(h.roles,tuple((a.day,a.player,a.target,a.color) for a in h.acquisitions)))
   self.assertIs(e.evaluation_graph.day_decision(private.read(),evaluate=True),record)
 def test_early_win_bound_does_not_fabricate_ties(self):
  with calculation_budget(2000000,max_seconds=60):
   c=self.closed();node=c.root;s=node.read();e=c._ClosedCalculation__engine;key=(s.public,s.public_state,s.past)
   with e.group_scope(node.groups),node.relation_scope():self.assertEqual(e.public_day_max(*key),1)
   self.assertNotIn(key,e.scores);self.assertIsNone(e.evaluation_graph.day_decision(s))
   with e.group_scope(node.groups),node.relation_scope():record=e.evaluation_graph.day_decision(s,evaluate=True)
   self.assertEqual(len(record.scores),5);self.assertEqual(dict(record.policy)[2],F(1,2))
 def test_tree_reuses_decision_and_preserves_zero_policy_branches(self):
  with calculation_budget(2000000,max_seconds=60):
   c=self.closed();node=c.root;e=c._ClosedCalculation__engine
   with e.group_scope(node.groups),node.relation_scope():record=e.evaluation_graph.day_decision(node.read(),evaluate=True)
   tree=CalculationTree.from_node(node)
   with patch.object(e,'score_day_targets',side_effect=AssertionError('complete MAX scores re-evaluated')):tree.expand('0')
   shown=tree.summary('0',True);self.assertEqual(shown['evaluation_trace']['selection'],'evaluated-public-MAX')
   self.assertEqual(shown['evaluation_trace']['transition'],'evaluated')
   self.assertEqual(sum(F(a['policy_probability']) for a in shown['actions']),1)
   self.assertTrue(any(a['policy_probability']=='0' and a['branches'] for a in shown['actions']))
   for action in shown['actions']:self.assertEqual(F(action['policy_probability']),sum(dict(record.policy)[p] for p in action['targets']))
 def test_concrete_tied_and_nonchosen_history_replay(self):
  with calculation_budget(2000000,max_seconds=60):
   doc=NavigationDocument(self.data());anchor=doc.game.current;source=doc.game.node;value=source.forecast().village_win
   tied=doc.game.action(2);self.assertEqual(tied.selection_weight,F(1,2));self.assertNotIn(2,NavigationCurrent(doc.game).source.public.alive)
   doc.game.move(anchor);zero=doc.game.action(4);self.assertEqual(zero.selection_weight,0);self.assertNotIn(4,NavigationCurrent(doc.game).source.public.alive)
   cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())))
   self.assertEqual(state_key(NavigationCurrent(cold.game).source),state_key(NavigationCurrent(doc.game).source))
   doc.game.move(anchor);self.assertEqual(doc.game.node.forecast().village_win,value)
