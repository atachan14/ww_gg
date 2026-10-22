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

 def test_back_forward_same_action_reuses_occurrence_and_concrete_choice(self):
  game=NavigationGame(self.root());first=game.action(3);game.back();again=game.action(3)
  self.assertEqual(again.key,first.key);self.assertEqual(len(game.history.children('h0')),1)
  self.assertEqual(NavigationGame.restore(self.root(),game.export()).export(),game.export())

 def test_multiple_seers_and_wolves_keep_complete_named_transport(self):
  from app import create_app
  from werewolf.board_flow import BoardData
  from werewolf.closed_calculation import ClosedCalculation
  from werewolf.public_convergence import transport_source
  for citizens,seers,wolves in ((2,2,1),(2,1,2)):
   app=create_app(dict(TESTING=True,SECRET_KEY='multi-navigation'));client=app.test_client()
   client.post('/start',data=dict(citizens=str(citizens),seers=str(seers),wolves=str(wolves),day='random',night='random',fake_reports='random'))
   with client.session_transaction() as session:data=BoardData.from_game(session['game'])
   root=ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True).root
   expected=root.action(3);game=NavigationGame(root);row=game.action(3,outcome=0)
   from dataclasses import replace
   from werewolf.exact import replace_worlds
   moved=transport_source(game.node.read(),row.names.forward);named=expected[0].node.read()
   # Complete-world tuple order is not part of the probability law. Keep every
   # Q/P atom, acquisition and history field; normalize only that row ordering.
   normalize=lambda source:replace(source,public=replace_worlds(source.public,tuple(sorted(source.public.worlds))))
   self.assertEqual(normalize(moved),normalize(named))
   self.assertEqual(sum(h.mass for h in game.node.read().public_state.hypotheses),1)
   self.assertEqual(sum(h.mass for h in game.node.read().private.hypotheses),1)
   self.assertEqual(NavigationGame.restore(root,game.export()).node.read(),game.node.read())

 def test_equal_beliefs_do_not_erase_public_update_timing_or_mutate_old_node_orbits(self):
  root=self.root();whole=NavigationGame(root)
  claims=('seer','seer','latent','latent','latent');r1=SeerReport(1,1,1,3,'white');r2=SeerReport(1,1,2,4,'white')
  whole.public_input(claims,(r1,r2));a=whole.node;identity=a.solver_identity
  separate=NavigationGame(root);separate.public_input(claims,());separate.public_input(claims,(r1,));separate.public_input(claims,(r2,));b=separate.node
  self.assertEqual(a.read(),b.read());self.assertNotEqual(a.solver_identity,b.solver_identity)
  self.assertEqual(a.solver_identity,identity)
  self.assertEqual(a.representative_action(2)[0],1);self.assertEqual(b.representative_action(2)[0],2)
  self.assertEqual(a.representative_action(2)[1].forward,(2,1,4,3,5))
