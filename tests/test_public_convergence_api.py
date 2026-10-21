import unittest
from fractions import Fraction as F
from collections import defaultdict
from tests import test_anonymous_night as native_tests
from werewolf.calculation_tree import CalculationTree
from werewolf.generated_current import GeneratedCurrent
from werewolf.physical_selection import counts

class PublicConvergenceAPITests(unittest.TestCase):
 def tree(self,seers=1):
  c,node=native_tests.AnonymousNightTests().case(seers=seers,citizens=4-seers)
  roles=c.data.roles();forecast=roles.forecast()
  return CalculationTree(c.data,roles.board,forecast,anonymous=True)
 def night(self,tree):
  root=tree.read(tree.root,True)
  self.assertEqual(len(root['actions']),1)
  self.assertEqual(len(root['actions'][0]['branches']),2)
  self.assertEqual(sum(F(b['probability']) for b in root['actions'][0]['branches']),1)
  key=next(branch['node'] for action in root['actions'] for branch in action['branches'] if not root['items'][branch['node']]['winner'])
  return key,tree.read(key,True)
 def leaves(self,stage):
  return stage.get('leaves',[])+[leaf for b in stage.get('branches',[]) for leaf in self.leaves(b['children'])]
 def test_true_graph_convergence_has_full_hidden_distribution_and_contexts(self):
  tree=self.tree();night,data=self.night(tree);leaves=self.leaves(data['night_stages'])
  self.assertTrue(leaves);self.assertEqual(len({leaf['node'] for leaf in leaves}),1)
  key=leaves[0]['node'];summary=tree.summary(key);self.assertTrue(summary['public_bundle'])
  self.assertEqual({row['counts']['seers']:F(row['probability']) for row in summary['compositions']},{0:F(1,2),1:F(1,2)})
  self.assertGreater(len({leaf['context_node'] for leaf in leaves}),1)
  self.assertTrue(summary['hidden_contexts'])
  source=tree.nodes[key]['node'].read()
  for leaf in leaves:
   context=tree.nodes[leaf['context_node']]['node'].read();self.assertEqual(context.public_state,source.public_state);self.assertEqual(context.public,source.public)
 def test_public_and_private_path_Current_cold_restore(self):
  tree=self.tree();night,data=self.night(tree);leaves=self.leaves(data['night_stages'])
  for key in (leaves[0]['node'],leaves[0]['context_node'],leaves[-1]['context_node']):
   source=tree.nodes[key]['node'].read();current=GeneratedCurrent(tree,key)
   self.assertEqual(tuple(current.source),tuple(source));self.assertEqual(current.source.physical,source.physical)
   cold=self.tree();restored=cold.restore(tree.route(key));self.assertEqual(tuple(cold.nodes[restored]['node'].read()),tuple(source))
 def test_multiple_seers_converge_without_discarding_actor_histories(self):
  tree=self.tree(2);night,data=self.night(tree);leaves=self.leaves(data['night_stages'])
  self.assertEqual(len({leaf['node'] for leaf in leaves}),1)
  source=tree.nodes[leaves[0]['node']]['node'].read()
  self.assertTrue(any(len({a.player for a in h.acquisitions if a.day==2})==2 for h in source.private.hypotheses))
  self.assertEqual(sum(h.mass for h in source.private.hypotheses),1)

 def test_MAX_publications_and_zero_policy_contexts_reconstruct(self):
  from tests.test_joint_action_kernel import fixture
  c,unused,client=fixture('max');roles=c.data.roles();tree=CalculationTree(c.data,roles.board,roles.forecast(),anonymous=True)
  root=tree.read(tree.root,True);action=next(a for a in root['actions'] if 3 in a['targets'])
  key=next(b['node'] for b in action['branches'] if not root['items'][b['node']]['winner'])
  data=tree.read(key,True);leaves=self.leaves(data['night_stages']);self.assertTrue(leaves)
  contexts=[leaf['context_node'] for leaf in leaves if tree.nodes[leaf['context_node']].get('counterfactual')]
  self.assertTrue(contexts)
  for context in contexts[:3]:
   source=tree.nodes[context]['node'].read();current=GeneratedCurrent(tree,context);self.assertEqual(tuple(current.source),tuple(source))
  for bundle in tree.nodes[key]['public_bundles'].values():
   self.assertGreaterEqual(sum(weight for weight,source in bundle['sources'].values()),0)
