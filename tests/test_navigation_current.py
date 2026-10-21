import unittest
from fractions import Fraction as F
from tests import test_manual_public_input as fixtures
from werewolf.navigation_game import NavigationGame
from werewolf.navigation_current import NavigationCurrent

class NavigationCurrentTests(unittest.TestCase):
 def test_projection_matches_chosen_concrete_target_without_reseeding(self):
  root=fixtures.ManualPublicInputTests().root();game=NavigationGame(root)
  game.action(3);current=NavigationCurrent(game)
  self.assertNotIn(3,current.roles.board.alive)
  self.assertEqual(current.roles.progress.settled_village,F(1,5))
  self.assertEqual(current.roles.forecast().village_win,game.node.forecast().village_win)
  self.assertEqual(current.roles.owner.facts.board_id,'navigation-h1')
  self.assertEqual(tuple(current.data.to_game()['claims']),current.source.public.claims)
 def test_terminal_projection_preserves_mixture_and_back_forward(self):
  game=NavigationGame(fixtures.ManualPublicInputTests().root());game.action(3);game.action(2)
  current=NavigationCurrent(game)
  if current.roles.progress.finished:
   self.assertEqual(sum(o.probability for o in current.roles.progress.last_outcomes),1)
  before=current.roles.progress;game.back();game.forward()
  self.assertEqual(NavigationCurrent(game).roles.progress,before)

 def test_tree_continuation_reuses_exact_owner_and_restores_relative_routes(self):
  from werewolf.calculation_tree import CalculationTree
  root=fixtures.ManualPublicInputTests().root();game=NavigationGame(root);game.action(3)
  tree=CalculationTree.from_node(game.node)
  self.assertIs(tree.entry_node,game.node)
  self.assertEqual(tree.nodes[tree.root]['node'].read(),game.node.read())
  self.assertEqual(tree.value(tree.root),game.node.forecast().village_win)
  self.assertEqual(tree.restore([]),tree.root)
  self.assertIsNone(tree.read(tree.root).get('input_timeline'))
  result=tree.read(tree.root,True)
  for row in result['actions'] or ():
   for branch in row['branches']:
    restored=tree.restore(tree.route(branch['node']))
    self.assertEqual(tree.nodes[restored]['node'].read(),tree.nodes[branch['node']]['node'].read())
