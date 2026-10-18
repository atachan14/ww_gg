"""Public-only interim fake report policy; not expected-win maximization."""
import unittest
from dataclasses import replace
from fractions import Fraction as F
from werewolf.exact import initial_board,replace_worlds,Rules,Strategy,action_outcomes
from werewolf.seer_acquisition import Hypothesis,Acquisition,SeerReport,normalize
from werewolf.seer_future_uniform import TrueScanState,acquire_uniform,FuturePending
from werewolf.seer_future_forecast import forecast,project_private,future_publications,plausible_fake_options,fake_backlog_options

class NoncontradictoryFakeTests(unittest.TestCase):
 def fixture(self):
  worlds=((10,0,1,0,F(1,4)),(18,0,1,0,F(1,4)),(9,0,2,0,F(1,4)),(17,0,2,0,F(1,4)))
  b=replace(replace_worlds(initial_board(5,2,0,1),worlds),claims=('seer','seer','latent','latent','latent'))
  s=TrueScanState(tuple(Hypothesis(r[:-1],(Acquisition(1,1 if r[2]==1 else 2,3,'white'),),r[-1]) for r in worlds),((1,2,3,4,5),))
  past=tuple(SeerReport(1,1,p,3,'white') for p in (1,2))
  return b,s,past
 def morning(self):
  b,s,past=self.fixture();night=next(o.board for o in action_outcomes(b,4,Rules(),Strategy()) if o.board.winner is None)
  s=project_private(s,night);s=acquire_uniform(s,night.alive)
  morning=action_outcomes(night,3,Rules(),Strategy())[0].board
  return morning,project_private(s,morning),past
 def test_same_white_example_all_four_uncertain_executions_are_quarter(self):
  b,s,past=self.fixture();result=forecast(b,s,past,Rules(),Strategy())
  self.assertEqual(dict(result.action_values),{1:F(1,4),2:F(1,4),3:F(),4:F(1,4),5:F(1,4)})
  self.assertEqual(dict(result.by_dawn_values)[4].wolf_win,F(1,2))
 def test_morning_vectors_keep_both_true_owners_and_total_mass(self):
  b,s,past=self.morning();branches=future_publications(s,past,b.alive,b.claims)
  # Three legal targets per reporter include corpse4: 3x3 public vectors.
  self.assertEqual(len(branches),9);self.assertEqual({v.probability for v in branches},{F(1,9)})
  for branch in branches:
   self.assertEqual(len(branch.state.public_roles),2)
   self.assertEqual({r.color for r in branch.reports if r.target==5},{'white'} if any(r.target==5 for r in branch.reports) else set())
   self.assertTrue(all(r.color=='black' for r in branch.reports if r.target in (1,2,4)))
 def test_candidate_support_does_not_weight_by_true_history_mass(self):
  b,s,past=self.morning()
  entries=[]
  for h in s.hypotheses:
   mass=F(3) if h.acquisitions[-1].target==5 else F(1)
   entries.append(replace(h,mass=mass))
  uneven=replace(s,hypotheses=normalize(entries))
  self.assertEqual(plausible_fake_options(s,(1,),past),plausible_fake_options(uneven,(1,),past))
  self.assertEqual({q for _,q in plausible_fake_options(uneven,(1,),past)},{F(1,3)})
 def test_already_exposed_fake_retains_complete_noise_not_pending(self):
  b,s,past=self.morning();entries=tuple(h for h in s.hypotheses if h.roles[2]==2)
  exposed=replace(s,hypotheses=tuple(replace(h,mass=h.mass*2) for h in entries))
  self.assertEqual(plausible_fake_options(exposed,(1,),past),fake_backlog_options(exposed,(1,),past))
 def test_multiple_fake_policy_still_unselected(self):
  _,s,past=self.morning();self.assertIsInstance(plausible_fake_options(s,(1,2),past),FuturePending)
 def test_uniform_only_restores_old_three_eighths(self):
  b,s,past=self.fixture();result=forecast(b,s,past,Rules(),Strategy(fake_seer_policy=['uniform']))
  self.assertEqual(dict(result.action_values)[4],F(3,8))
  for values in ([],['noncontradictory'],['uniform','noncontradictory'],['max'],['uniform','uniform']):
   with self.assertRaises(ValueError):Strategy(fake_seer_policy=values)
  self.assertNotEqual(Strategy(),Strategy(fake_seer_policy=['uniform']))
