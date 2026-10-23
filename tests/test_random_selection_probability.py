import unittest
from fractions import Fraction as F
from types import SimpleNamespace
from unittest.mock import patch
from dev_previews.benchmark_player_counts import data
from werewolf.board_flow import BoardData
from werewolf.navigation_store import NavigationDocument
from werewolf.evaluation_graph import DayDecisionRecord

class RandomSelectionProbabilityTests(unittest.TestCase):
 def document(self,n=5,mode='random',hunter=False,wolves=1):
  game=data(n,mode,wolves=wolves).to_game()
  if hunter:game['hunters']=1
  return NavigationDocument(BoardData.from_game(game))
 def test_random_six_guard_selection_never_scores_or_evaluates_future(self):
  doc=self.document(6,hunter=True,wolves=2);node=doc.game.node;e=node._Node__calculation._ClosedCalculation__engine
  with patch.object(e,'day_scores',side_effect=AssertionError('random policy scored')),patch.object(e,'solve',side_effect=AssertionError('random policy solved')),patch.object(e,'act',side_effect=AssertionError('random policy evaluated actions')):
   self.assertEqual(tuple(node.selection_probability(p) for p in range(1,7)),(F(1,6),)*6)
   self.assertEqual(node.selection_probability(99),0)
  self.assertEqual(e.scores,{})
 def test_common_filtered_public_candidates_not_fixed_player_count_or_private_truth(self):
  node=self.document().game.node;e=node._Node__calculation._ClosedCalculation__engine
  with patch('werewolf.closed_calculation.legal_targets',return_value=(2,5)) as legal,patch.object(e,'day_scores',side_effect=AssertionError('filtered random policy scored')):
   self.assertEqual({p:node.selection_probability(p) for p in (1,2,3,5,9)},{1:F(),2:F(1,2),3:F(),5:F(1,2),9:F()})
   self.assertTrue(all(call.args==(node.read().public,e.rules,e.strategy) for call in legal.call_args_list))
  with patch('werewolf.closed_calculation.legal_targets',return_value=()):self.assertEqual(node.selection_probability(2),0)
 def test_private_role_facts_do_not_replace_public_execution_candidates(self):
  from werewolf.actor_information import PersonalInformation
  from werewolf.exact import legal_targets
  doc=self.document(hunter=True);_,node=doc.game.node.personal(PersonalInformation(1,'seer'))
  s=node.read();e=node._Node__calculation._ClosedCalculation__engine
  self.assertEqual(s.physical.role_probability(1,'seer'),1)
  self.assertLess(s.public.role_probability(1,'seer'),1)
  with patch('werewolf.closed_calculation.legal_targets',wraps=legal_targets) as legal,patch.object(e,'day_scores',side_effect=AssertionError('private view scored random policy')),patch.object(e,'solve',side_effect=AssertionError('private view solved random policy')):
   self.assertEqual(tuple(node.selection_probability(p) for p in range(1,6)),(F(1,5),)*5)
   self.assertTrue(all(call.args[0] is s.public for call in legal.call_args_list))

 def test_actual_dead_players_and_terminal_day_excluded(self):
  doc=self.document();doc.game.action(3);doc.game.action(2);node=doc.game.node
  self.assertEqual(node.read().public.phase,'day');alive=node.read().public.alive
  self.assertEqual({p:node.selection_probability(p) for p in range(1,6)},{p:F(1,len(alive)) if p in alive else F() for p in range(1,6)})
  terminal=self.document(4);terminal.game.action(3);terminal.game.action(1);node=terminal.game.node
  self.assertIsNotNone(node.read().public.winner);self.assertEqual(node.selection_probability(2),0)
  from werewolf.exact import initial_board,legal_targets
  ended=initial_board(3,0,experimental_cast=True);e=node._Node__calculation._ClosedCalculation__engine
  self.assertEqual(ended.phase,'day');self.assertIsNotNone(ended.winner)
  # Real terminal-day legality supplies the empty set exercised directly in
  # the selector test above; no unsupported zero-wolf saved game is invented.
  self.assertEqual(legal_targets(ended,e.rules,e.strategy),())
 def test_MAX_retained_policy_and_fallback_ties_zero_inspection_unchanged(self):
  node=self.document(mode='max').game.node;e=node._Node__calculation._ClosedCalculation__engine;g=e.evaluation_graph
  scores=((1,F()),(2,F(3,4)),(3,F(3,4)),(4,F()),(5,F()))
  policy=((1,F()),(2,F(1,2)),(3,F(1,2)),(4,F()),(5,F()))
  with patch.object(g,'day_decision',return_value=DayDecisionRecord(scores,policy)),patch.object(e,'day_scores',side_effect=AssertionError('complete MAX table rescored')):
   self.assertEqual(tuple(node.selection_probability(p) for p in (1,2,3,99)),(F(),F(1,2),F(1,2),F()))
  with patch.object(g,'day_decision',return_value=None),patch.object(e,'day_scores',return_value=scores) as score:
   self.assertEqual(tuple(node.selection_probability(p) for p in (1,2,3,99)),(F(),F(1,2),F(1,2),F()))
   self.assertEqual(score.call_count,4)
 def test_random_night_keeps_actor_conditioned_weighted_policy(self):
  doc=self.document();doc.game.action(3);node=doc.game.node
  rows=(SimpleNamespace(target=2,mass=F(1,5)),SimpleNamespace(target=2,mass=F(3,10)),SimpleNamespace(target=4,mass=F(1,2)))
  with patch.object(type(node),'wolf_choices',return_value=rows):
   self.assertEqual(tuple(node.selection_probability(p) for p in (2,3,4)),(F(1,2),F(),F(1,2)))

if __name__=='__main__':unittest.main()

