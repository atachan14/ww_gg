import unittest
from fractions import Fraction as F
from dataclasses import replace
from werewolf.exact import initial_board,replace_worlds,Rules,Strategy,build_tree,evaluate_tree,condition_claims,ClaimPolicy
from werewolf.seer_acquisition import Hypothesis,Acquisition,SeerReport,from_board
from werewolf.seer_future_uniform import TrueScanState,acquire_uniform,FuturePending
from werewolf.seer_future_forecast import future_publications,forecast

class SeerFutureForecastTests(unittest.TestCase):
 def test_complete_true_single_fake_vectors_use_generation_likelihood(self):
  h=Hypothesis((12,0,1,0),(Acquisition(1,1,2,'white'),Acquisition(2,1,3,'black')),F(1))
  s=TrueScanState((h,),((1,2,3,4,5),(1,2,3,4,5)))
  past=(SeerReport(1,1,1,2,'white'),SeerReport(1,1,3,2,'white'))
  branches=future_publications(s,past,(1,2,3,4,5),('seer','latent','seer','latent','latent'))
  self.assertEqual(len(branches),6);self.assertEqual(sum(b.probability for b in branches),1)
  self.assertEqual({b.probability for b in branches},{F(1,6)})
  self.assertTrue(all(len(b.reports)==2 for b in branches))
 def test_multiple_fake_pending_no_partial_outcomes(self):
  h=Hypothesis((12,0,1,0),(Acquisition(1,1,2,'white'),Acquisition(2,1,3,'black')),F(1));s=TrueScanState((h,),((1,2,3,4,5),(1,2,3,4,5)))
  result=future_publications(s,(),(1,2,3,4,5),('seer','latent','seer','seer','latent'));self.assertIsInstance(result,FuturePending)
 def test_no_seer_co_matches_existing_solver_for_broad_casts(self):
  for n in range(3,8):
   b=initial_board(n,1,0,1);s=acquire_uniform(TrueScanState(from_board(b)),tuple(range(1,n+1)))
   value=forecast(b,s,(),Rules(),Strategy());self.assertEqual(value.village_win,evaluate_tree(build_tree(b,Rules(),Strategy()),Strategy()).board_value(build_tree(b,Rules(),Strategy())).village_win)
 def test_known_true_scan_forecast_reaches_terminal_exactly(self):
  b=initial_board(5,1,0,1);b=replace_worlds(b,((16,0,1,0,F(1)),));b=replace(b,claims=('seer','latent','latent','latent','latent'))
  s=acquire_uniform(TrueScanState(from_board(b)),(1,2,3,4,5));result=forecast(b,s,(),Rules(),Strategy());self.assertNotIsInstance(result,FuturePending);self.assertEqual(result.village_win,1);self.assertEqual(dict(result.action_values)[5],1)
 def test_random_public_actions_do_not_optimize_inside_truth_worlds(self):
  b=initial_board(3,1,0,1);b=condition_claims(b,('seer','latent','latent'),ClaimPolicy());s=acquire_uniform(TrueScanState(from_board(b)),(1,2,3))
  result=forecast(b,s,(),Rules(),Strategy('random','random'));self.assertEqual(result.village_win,F(1,3))
 def test_budget_returns_pending_and_never_cache_partial_zero(self):
  b=initial_board(5,1,0,1);b=condition_claims(b,('seer','latent','latent','latent','latent'),ClaimPolicy());s=acquire_uniform(TrueScanState(from_board(b)),(1,2,3,4,5))
  self.assertIsInstance(forecast(b,s,(),Rules(),Strategy(),max_work=1),FuturePending)
 def test_mixed_medium_scope_preserves_existing_model_without_seer_co(self):
  b=initial_board(5,1,1,1);b=condition_claims(b,('medium','latent','latent','latent','latent'),ClaimPolicy());s=acquire_uniform(TrueScanState(from_board(b)),(1,2,3,4,5))
  result=forecast(b,s,(),Rules(),Strategy());root=build_tree(b,Rules(),Strategy());self.assertEqual(result.village_win,evaluate_tree(root,Strategy()).board_value(root).village_win)

 def test_five_player_manual_prior_future_terminal_values_literal(self):
  # Three equally weighted legal worlds after normal initial reports:
  # seer1/wolves2+4, seer1/wolves2+5, seer2/wolves1+3.
  worlds=((10,0,1,0,F(1,3)),(18,0,1,0,F(1,3)),(5,0,2,0,F(1,3)))
  b=replace_worlds(initial_board(5,2,0,1),worlds);b=replace(b,claims=('seer','seer','latent','latent','latent'))
  hs=tuple(Hypothesis(r[:-1],(Acquisition(1,1,3,'white'),) if r[2]==1 else (Acquisition(1,2,3,'black'),),r[-1]) for r in worlds)
  s=TrueScanState(hs,((1,2,3,4,5),),initial_rule='normal');past=(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,3,'black'))
  result=forecast(b,s,past,Rules(initial_seer='normal'),Strategy())
  self.assertNotIsInstance(result,FuturePending);self.assertEqual(result.village_win,F(1,3));self.assertEqual(set(dict(result.action_values).values()),{F(1,3)})

 def test_night_future_truth_signal_changes_action_three_from_half_to_one(self):
  from werewolf.exact import Progress,advance,value_for_action
  from werewolf.seer_future_forecast import project_private
  worlds=((10,0,1,0,F(1,2)),(18,0,1,0,F(1,2)))
  b=replace(replace_worlds(initial_board(5,2,0,1),worlds),claims=('seer','seer','latent','latent','latent'))
  s=TrueScanState(tuple(Hypothesis(r[:-1],(Acquisition(1,1,3,'white'),),r[-1]) for r in worlds),((1,2,3,4,5),))
  p=advance(Progress.initial(b),2,Rules(),Strategy());s=project_private(s,p.board)
  result=forecast(p.board,s,(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,3,'black')),Rules(),Strategy())
  self.assertEqual(dict(result.action_values)[3],1)
  self.assertEqual(value_for_action(p.board,3,Rules(),Strategy()).village_win,F(1,2))
  self.assertEqual(result.village_win,F(1,2))

 def test_medium_max_and_random_law_preserved_after_seer_death(self):
  from werewolf.exact import Progress,advance
  from werewolf.seer_future_forecast import project_private
  worlds=((2,4,1,0,F(1,2)),(4,2,1,0,F(1,2)))
  b=replace(replace_worlds(initial_board(5,1,1,1),worlds),claims=('seer','medium','medium','latent','latent'))
  s=TrueScanState(tuple(Hypothesis(r[:-1],(Acquisition(1,1,4,'white'),),r[-1]) for r in worlds),((1,2,3,4,5),))
  p=advance(Progress.initial(b),4,Rules(),Strategy());s=project_private(s,p.board);past=(SeerReport(1,1,1,4,'white'),)
  maximum=forecast(p.board,s,past,Rules(),Strategy(fake_reports='max'))
  random=forecast(p.board,s,past,Rules(),Strategy(fake_reports='random'))
  self.assertEqual(dict(maximum.action_values)[1],F(1,2));self.assertEqual(dict(random.action_values)[1],F(3,4))

 def test_known_single_fake_noise_marginalization_matches_full_vectors(self):
  worlds=((10,0,1,0,F(1,2)),(18,0,1,0,F(1,2)))
  b=replace(replace_worlds(initial_board(5,2,0,1),worlds),claims=('seer','seer','latent','latent','latent'))
  s=TrueScanState(tuple(Hypothesis(r[:-1],(Acquisition(1,1,3,'white'),),r[-1]) for r in worlds),((1,2,3,4,5),))
  past=(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,3,'black'))
  full=forecast(b,s,past,Rules(),Strategy(),marginalize_known_fake=False)
  fast=forecast(b,s,past,Rules(),Strategy(),marginalize_known_fake=True)
  self.assertEqual(fast,full)

 def test_known_fake_noise_equivalence_through_multiple_mornings(self):
  b=replace(replace_worlds(initial_board(7,1,0,1),((2,0,1,0,F(1)),)),claims=('seer','seer','latent','latent','latent','latent','latent'))
  s=TrueScanState((Hypothesis((2,0,1,0),(Acquisition(1,1,3,'white'),),F(1)),),((1,2,3,4,5,6,7),))
  past=(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,3,'black'))
  fast=forecast(b,s,past,Rules(),Strategy(),marginalize_known_fake=True)
  full=forecast(b,s,past,Rules(),Strategy(),max_work=1000000,marginalize_known_fake=False)
  self.assertNotIsInstance(full,FuturePending);self.assertEqual(fast,full)

 def test_initial_terminal_one_and_two_players_need_no_private_acquisition(self):
  for n,w,s,value in ((1,0,1,1),(2,2,0,0),(2,0,2,1)):
   b=initial_board(n,w,0,s,experimental_cast=True);private=TrueScanState(from_board(b));result=forecast(b,private,(),Rules(),Strategy());self.assertEqual(result.village_win,value);self.assertEqual(result.action_values,())

 def test_dead_private_history_marginalization_matches_full_ledger(self):
  worlds=((10,0,1,0,F(1,2)),(18,0,1,0,F(1,2)))
  b=replace(replace_worlds(initial_board(5,2,0,1),worlds),claims=('seer','seer','latent','latent','latent'))
  s=TrueScanState(tuple(Hypothesis(r[:-1],(Acquisition(1,1,3,'white'),),r[-1]) for r in worlds),((1,2,3,4,5),))
  past=(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,3,'black'))
  self.assertEqual(forecast(b,s,past,Rules(),Strategy(),marginalize_private=True),forecast(b,s,past,Rules(),Strategy(),marginalize_private=False))
 def test_private_projection_keeps_joint_role_masks_and_living_own_history(self):
  from werewolf.exact import Progress,advance
  from werewolf.seer_future_forecast import project_private
  b=replace(replace_worlds(initial_board(5,1,0,2),((16,0,3,0,F(1)),)),claims=('seer','seer','latent','latent','latent'))
  s=acquire_uniform(TrueScanState(from_board(b)),(1,2,3,4,5));next_board=advance(Progress.initial(b),1,Rules(),Strategy()).board
  reduced=project_private(s,next_board,marginalize_private=True)
  self.assertEqual(reduced.public_roles,tuple(sorted(next_board.worlds)));self.assertEqual(reduced.tracked,(2,));self.assertTrue(all(a.player==2 for h in reduced.hypotheses for a in h.acquisitions))

 def test_generated_morning_four_vectors_each_quarter_then_known_wolf(self):
  from werewolf.exact import Progress,advance
  from werewolf.seer_future_forecast import project_private
  worlds=((10,0,1,0,F(1,2)),(18,0,1,0,F(1,2)))
  b=replace(replace_worlds(initial_board(5,2,0,1),worlds),claims=('seer','seer','latent','latent','latent'))
  s=TrueScanState(tuple(Hypothesis(r[:-1],(Acquisition(1,1,3,'white'),),r[-1]) for r in worlds),((1,2,3,4,5),))
  p=advance(Progress.initial(b),2,Rules(),Strategy());s=project_private(s,p.board,marginalize_private=True);s=acquire_uniform(s,p.board.alive);morning=advance(p,3,Rules(),Strategy()).board;s=project_private(s,morning,marginalize_private=True)
  past=(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,3,'black'));branches=future_publications(s,past,morning.alive,morning.claims)
  self.assertEqual(len(branches),4);self.assertEqual({v.probability for v in branches},{F(1,4)})
  for v in branches:
   self.assertEqual(len(v.reports),1);self.assertEqual(v.reports[0].player,1);self.assertEqual(v.reports[0].acquired_day,2)
   self.assertEqual(len(v.state.public_roles),1);self.assertTrue(v.state.public_roles[0][0]&2)
