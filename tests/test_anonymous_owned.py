import unittest
from unittest.mock import patch
from fractions import Fraction as F
from dataclasses import FrozenInstanceError
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.anonymous_owned import AnonymousCalculation
from werewolf.navigation_history import NavigationHistory
from werewolf.calculation_budget import calculation_budget

class AnonymousOwnedTests(unittest.TestCase):
 def document(self):return BoardData.from_game(data(5,'random').to_game())
 def test_initial_and_day_night_history_do_not_materialize(self):
  prepared=self.document()
  with calculation_budget(4000000,max_seconds=45),patch('werewolf.anonymous_materialization.expand',side_effect=AssertionError('expanded names')),patch('werewolf.anonymous_materialization.expand_laws',side_effect=AssertionError('expanded laws')),patch('werewolf.board_future.SavedOrigin.__call__',side_effect=AssertionError('named prior')):
   c=AnonymousCalculation(prepared);root=c.root
   value=root.forecast();self.assertEqual(value.village_win,F(7,15))
   history=NavigationHistory(root);representative,lift=root.representative_action(4);self.assertEqual(representative,1);self.assertEqual(lift.display(1),4)
   branches=root.action(representative);self.assertEqual(sum(r.probability for r in branches),1)
   ongoing=next(r.node for r in branches if not r.node.read().public.winner)
   with patch('werewolf.public_convergence.state_key',side_effect=AssertionError('named history identity')):
    added=history.append(history.root,ongoing,dict(kind='action',target=1),names=lift)
   self.assertEqual(history.state(added.key).source,ongoing.owned)
   rows=ongoing.night();self.assertEqual(sum(r.probability for r in rows),1)
   child=next(r.node for r in rows if not r.node.read().public.winner)
   self.assertEqual(child.read().public.day,2);self.assertEqual(len(child.read().public.alive),3)
   self.assertFalse(any(a.population.scans for mass,a in child.owned.belief.p.rows))
   self.assertTrue(any(a.population.scans for mass,a in child.full_belief().p.rows))
   with self.assertRaises(FrozenInstanceError):child.owned=ongoing.owned
 def test_deferred_histories_match_existing_named_cycle(self):
  from werewolf.closed_calculation import ClosedCalculation
  from werewolf.anonymous_materialization import expand
  from werewolf.public_convergence import public_observation_orbits
  with calculation_budget(4000000,max_seconds=45):
   data=self.document();c=AnonymousCalculation(data);old=ClosedCalculation(data,grouped=True,aggregate_wolf=True,aggregate_reports=True,anonymous=True)
   self.assertEqual(expand(c.root.full_belief().q,c.root.groups),old.root.read().public_state.hypotheses)
   night=next(r.node for r in c.root.action(1) if not r.node.read().public.winner)
   named=next(r.node for r in old.root.action(1) if not r.node.read().public.winner);e=old._ClosedCalculation__engine
   for row in night.night():
    child=row.node;victim,result=child.owned.recipe.steps[-1][2];full=child.full_belief()
    with old._ClosedCalculation__kernel(),e.group_scope(named.groups):
     expected=next(s for q,s in public_observation_orbits(e,named.read(),victim,named.groups) if s.public.winner==result)
    self.assertEqual(expand(full.q,full.groups),expected.public_state.hypotheses)
    self.assertEqual(expand(full.p,full.groups),expected.private.hypotheses)
 def test_retained_transitions_are_read_without_generating_again(self):
  c=AnonymousCalculation(self.document());c.root.forecast();night=next(r.node for r in c.root.action(1) if not r.node.read().public.winner)
  night.forecast();night.night()
  with patch('werewolf.anonymous_belief.Belief.execute',side_effect=AssertionError('day rerun')),patch.object(c.evaluator,'night_flow',side_effect=AssertionError('night rerun')):
   c.root.action(1);night.night()

 def test_record_tree_navigation_and_cold_restore_without_names(self):
  import json
  from werewolf.anonymous_record_tree import AnonymousRecordTree
  from werewolf.navigation_game import NavigationGame
  prepared=self.document()
  with calculation_budget(4000000,max_seconds=45),patch('werewolf.anonymous_materialization.expand_laws',side_effect=AssertionError('ordinary Tree expanded names')),patch('werewolf.board_future.SavedOrigin.__call__',side_effect=AssertionError('ordinary history named prior')):
   c=AnonymousCalculation(prepared);tree=AnonymousRecordTree(c.root);shown=tree.read(expand=True)
   self.assertEqual(shown['evaluation_trace']['representation'],'anonymous-owned')
   game=NavigationGame(c.root);game.action(4);self.assertEqual(game.occurrence.names.display(1),4)
   game.action(3);saved=json.loads(json.dumps(game.export()));current=game.node.state_identity
   cold=NavigationGame.restore(AnonymousCalculation(prepared).root,saved)
   self.assertEqual(cold.node.state_identity,current);game.back();game.forward();self.assertEqual(game.node.state_identity,current)
   for edge in shown['edges']:
    if not tree.nodes[edge['node']].read().public.winner:tree.read(edge['node'],True)
 def test_explicit_Current_projection_and_manual_exit_preserve_original(self):
  import json
  from werewolf.navigation_game import NavigationGame
  from werewolf.public_convergence import state_key
  from werewolf.seer_acquisition import SeerReport
  with calculation_budget(4000000,max_seconds=45):
   prepared=self.document();c=AnonymousCalculation(prepared);game=NavigationGame(c.root)
   game.action(1);game.action(2);original=game.node;before=original.forecast();source=original.project_named().read()
   cold=original.export_request()._reconstruct();self.assertTrue(state_key(source)==state_key(cold),'explicit Current cold projection differs')
   self.assertEqual(source.public.day,2);self.assertEqual(source.public.alive,(3,4,5))
   game.public_input(['latent','latent','seer','latent','latent'],(SeerReport(1,2,3,4,'white'),SeerReport(2,2,3,5,'black')))
   self.assertEqual(game.occurrence.selection_weight,0);self.assertEqual(game.occurrence.edge_kind,'manual_public')
   self.assertFalse(hasattr(game.node,'owned'));self.assertEqual(original.forecast(),before)
   saved=json.loads(json.dumps(game.export()));restored=NavigationGame.restore(AnonymousCalculation(prepared).root,saved)
   self.assertTrue(state_key(restored.node.read())==state_key(game.node.read()),'manual compatibility cold state differs')
   game.back();self.assertIs(game.node,original);self.assertEqual(game.node.forecast(),before)

 def test_actual_Current_preserves_reselected_names_and_first_day_manual_exit(self):
  from werewolf.navigation_game import NavigationGame
  from werewolf.navigation_current import NavigationCurrent
  from werewolf.seer_acquisition import SeerReport
  from werewolf.public_convergence import state_key
  prepared=self.document();c=AnonymousCalculation(prepared);game=NavigationGame(c.root)
  initial=NavigationCurrent(game);self.assertEqual(initial.source.public.day,1)
  game.public_input(['seer','latent','latent','latent','latent'],(SeerReport(1,1,1,2,'white'),))
  self.assertEqual(game.occurrence.selection_weight,0);self.assertFalse(hasattr(game.node,'owned'))
  self.assertTrue(state_key(game.node.export_request()._reconstruct())==state_key(game.node.read()),'Day1 manual named cold replay differs')
  game.back();game.action(4);current=NavigationCurrent(game)
  self.assertNotIn(4,current.source.public.alive);self.assertIsNotNone(game.node.owned)
  self.assertEqual(current.public_log,[]);self.assertEqual(current.roles.forecast().village_win,game.node.forecast().village_win)

 def test_full_six_person_two_seer_path_keeps_correlations_at_Current(self):
  from werewolf.navigation_game import NavigationGame
  from werewolf.navigation_current import NavigationCurrent
  from werewolf.information_set_forecast import InformationSetForecast
  from werewolf.anonymous_materialization import expand
  from werewolf.public_convergence import state_key
  prepared=BoardData.from_game(data(6,'random',seers=2).to_game());c=AnonymousCalculation(prepared);game=NavigationGame(c.root)
  with calculation_budget(4000000,max_seconds=45),patch('werewolf.anonymous_materialization.expand_laws',side_effect=AssertionError('full path materialized')):
   game.action(6);game.action(5);game.action(4);game.action(3)
   saved=game.export();cold=NavigationGame.restore(AnonymousCalculation(prepared).root,saved)
   self.assertTrue(cold.node.state_identity==game.node.state_identity,'full path cold ownership differs')
  current=NavigationCurrent(game);source=current.source
  self.assertEqual(len(source.public.alive),2);self.assertEqual(source.public.day,3)
  self.assertTrue(all(a.player!=a.target for h in source.private.hypotheses for a in h.acquisitions))
  from werewolf.phase_updates import acquisition_roster
  self.assertTrue(all(a.target in acquisition_roster(6,source.public.history,a.day) and a.player in acquisition_roster(6,source.public.history,a.day) for h in source.private.hypotheses for a in h.acquisitions),'deferred scan used post-death roster')
  self.assertTrue(any(len(h.acquisitions)>2 for h in source.private.hypotheses),'deferred scans lost relational history')
  projected=game.node.project_named();self.assertTrue(state_key(projected.export_request()._reconstruct())==state_key(projected.read()),'full path cold Current law differs')
 def test_full_anonymous_tree_recursion_conserves_value_without_names(self):
  prepared=self.document();c=AnonymousCalculation(prepared);visited=set()
  with calculation_budget(4000000,max_seconds=45),patch('werewolf.anonymous_materialization.expand_laws',side_effect=AssertionError('recursive Tree named expansion')):
   def walk(node):
    b=node.read().public;value=node.forecast().village_win
    if node.state_identity in visited:return value
    visited.add(node.state_identity)
    if b.winner:return value
    if b.phase=='night':rows=node.night();expected=sum(row.probability*walk(row.node) for row in rows)
    else:
     expected=F()
     for group in node.groups:
      living=[p for p in group if p in b.alive]
      if living:expected+=F(len(living),len(b.alive))*sum(row.probability*walk(row.node) for row in node.action(living[0]))
    self.assertEqual(value,expected);return value
   self.assertEqual(walk(c.root),F(7,15));self.assertGreater(len(visited),3)
