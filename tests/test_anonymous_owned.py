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
