import unittest
from fractions import Fraction as F
from tests import test_manual_public_input as fixtures
from werewolf.navigation_game import NavigationGame
from werewolf.seer_acquisition import SeerReport

class NavigationGameTests(unittest.TestCase):
 def root(self):return fixtures.ManualPublicInputTests().root()
 def test_footer_preserves_settled_mass_and_round_trip_cursor(self):
  root=self.root();game=NavigationGame(root);before=root.forecast().village_win
  child=game.action(3)
  self.assertEqual(child.settled_village,F(1,5));self.assertEqual(child.active_mass,F(4,5))
  value=child.settled_village+child.active_mass*game.node.forecast().village_win
  self.assertEqual(value,dict(root.forecast().action_values)[3])
  self.assertEqual(game.back().key,game.history.root);self.assertEqual(game.forward().key,child.key)
  rebuilt=NavigationGame.restore(self.root(),game.export());self.assertEqual(rebuilt.export(),game.export());self.assertEqual(rebuilt.node.read(),game.node.read())
  self.assertEqual(root.forecast().village_win,before)
 def test_repeated_updates_keep_old_futures_and_cold_reconstruct(self):
  root=self.root();game=NavigationGame(root);before=root.forecast()
  old=game.action(3);game.back()
  first=game.public_input(('seer','latent','latent','latent','latent'),(SeerReport(1,1,1,3,'white'),))
  second=game.public_input(('seer','seer','latent','latent','latent'),(SeerReport(1,1,2,4,'white'),))
  self.assertEqual((first.selection_weight,second.selection_weight),(0,0));self.assertEqual(root.forecast(),before)
  self.assertEqual(game.history.children(game.history.root),(old,first));self.assertEqual(game.back(),first);self.assertEqual(game.forward(),second)
  rebuilt=NavigationGame.restore(self.root(),game.export());self.assertEqual(rebuilt.export(),game.export());self.assertEqual(rebuilt.node.read(),game.node.read())

 def test_selected_representative_transports_complete_private_and_public_state(self):
  from werewolf.public_convergence import transport_source
  for target in (2,3,4,5):
   root=self.root();game=NavigationGame(root);direct=root.action(target)
   chosen=game.action(target,outcome=1)
   self.assertEqual(chosen.names.display(1),target)
   self.assertEqual(transport_source(game.node.read(),chosen.names.forward),direct[1].node.read())
   rebuilt=NavigationGame.restore(self.root(),game.export())
   self.assertEqual(rebuilt.export(),game.export())
   self.assertEqual(rebuilt.node.read(),game.node.read())
 def test_coupled_report_transport_keeps_reporter_target_pairs(self):
  from tests.test_public_relation_orbits import PublicRelationOrbitTests
  from werewolf.board_flow import BoardData
  from werewolf.closed_calculation import ClosedCalculation
  from werewolf.public_convergence import transport_source
  root=ClosedCalculation(BoardData.from_game(PublicRelationOrbitTests().game()),grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True).root
  game=NavigationGame(root);chosen=game.action(2,outcome=0)
  self.assertEqual(chosen.names.forward,(2,1,4,3,5))
  self.assertEqual(transport_source(game.node.read(),chosen.names.forward),root.action(2)[0].node.read())
  restored=NavigationGame.restore(root,game.export());self.assertEqual(restored.export(),game.export())

 def test_restore_rejects_injected_weights_and_unrelated_forward_path(self):
  from copy import deepcopy
  root=self.root();game=NavigationGame(root);game.action(3)
  record=deepcopy(game.export());record['rows'][1]['selection_weight']='0'
  with self.assertRaises(ValueError):NavigationGame.restore(root,record)
  record=deepcopy(game.export());record['forward']={'h1':'h0'}
  with self.assertRaises(ValueError):NavigationGame.restore(root,record)
