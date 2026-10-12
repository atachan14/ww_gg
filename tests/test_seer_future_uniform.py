import unittest
from fractions import Fraction as F
from werewolf.exact import initial_board
from werewolf.seer_acquisition import Hypothesis,Acquisition,SeerReport,from_board
from werewolf.seer_future_uniform import TrueScanState,FuturePending,acquire_uniform,candidates,true_reports,truth_only_publications

class TrueFutureUniformTests(unittest.TestCase):
 def base(self,n=5,w=1,s=1):return TrueScanState(from_board(initial_board(n,w,0,s,experimental_cast=True)))
 def test_initial_joint_draw_preserves_role_marginals_and_is_white(self):
  base=self.base(7,2,2);state=acquire_uniform(base,tuple(range(1,8)))
  self.assertEqual(state.public_roles,base.public_roles)
  self.assertTrue(all(len(h.acquisitions)==2 and all(a.color=='white' and a.target!=a.player for a in h.acquisitions) for h in state.hypotheses))
  for h in state.hypotheses:self.assertEqual(h.mass,F(1,210*16))
 def test_own_history_unvisited_priority_not_other_seer_history(self):
  h=Hypothesis((16,0,3,0),(Acquisition(1,1,3,'white'),Acquisition(1,2,4,'white')),F(1))
  self.assertEqual(candidates(h,1,(1,2,3,4,5)),(2,4,5));self.assertEqual(candidates(h,2,(1,2,3,4,5)),(1,3,5))
 def test_uniform_future_targets_and_exact_truth(self):
  h=Hypothesis((16,0,1,0),(Acquisition(1,1,2,'white'),),F(1));state=TrueScanState((h,),((1,2,3,4,5),))
  result=acquire_uniform(state,(1,2,3,4,5));self.assertEqual(len(result.hypotheses),3)
  self.assertEqual({x.acquisitions[-1].target for x in result.hypotheses},{3,4,5});self.assertEqual({x.mass for x in result.hypotheses},{F(1,3)})
  self.assertTrue(all((a.color=='black')==(a.target==5) for x in result.hypotheses for a in x.acquisitions))
 def test_revisit_fallback_when_all_legal_targets_visited(self):
  h=Hypothesis((4,0,1,0),(Acquisition(1,1,2,'white'),Acquisition(2,1,3,'black')),F(1))
  state=TrueScanState((h,),((1,2,3),(1,2,3)));result=acquire_uniform(state,(1,2,3));self.assertEqual({x.acquisitions[-1].target for x in result.hypotheses},{2,3})
  self.assertEqual({x.mass for x in result.hypotheses},{F(1,2)})
 def test_scan_before_night_casualty_and_only_surviving_co_publication(self):
  state=acquire_uniform(self.base(5,1,2),(1,2,3,4,5))
  h=next(h for h in state.hypotheses if h.roles[2]==3 and any(a.target==3 for a in h.acquisitions))
  rows=true_reports(h,(),(1,4,5),('seer','seer','latent','latent','latent'),1)
  self.assertTrue(all(r.player==1 for r in rows));self.assertEqual(len(rows),1)
  self.assertEqual(true_reports(h,(),(1,4,5),('latent',)*5,1),())
 def test_true_only_public_report_groups_normalize(self):
  h=Hypothesis((16,0,1,0),(),F(1));state=acquire_uniform(TrueScanState((h,)),(1,2,3,4,5))
  outcomes=truth_only_publications(state,(1,2,3,4,5),('seer','latent','latent','latent','latent'))
  self.assertEqual(sum(b.probability for b in outcomes),1);self.assertEqual(len(outcomes),3)
  for b in outcomes:
   self.assertEqual(b.probability,F(1,3));self.assertEqual(sum(x.mass for x in b.state.hypotheses),1)
   self.assertEqual(truth_only_publications(b.state,(1,2,3,4,5),('seer','latent','latent','latent','latent'),b.reports)[0].reports,())
 def test_possible_fake_two_wolves_stays_pending_without_policy_guess(self):
  state=acquire_uniform(self.base(5,2,1),(1,2,3,4,5))
  result=truth_only_publications(state,(1,2,3,4,5),('seer','seer','latent','latent','latent'))
  self.assertIsInstance(result,FuturePending);self.assertIn('unselected',result.reason)
 def test_budget_returns_pending_never_partial_probability(self):
  result=acquire_uniform(self.base(9,2,2),tuple(range(1,10)),max_work=10)
  self.assertIsInstance(result,FuturePending);self.assertIn('budget',result.reason)
 def test_no_seers_and_one_through_nine_rosters(self):
  for n in range(1,10):
   state=acquire_uniform(self.base(n,0,0),tuple(range(1,n+1)));self.assertEqual(len(state.hypotheses),1);self.assertEqual(state.hypotheses[0].acquisitions,())
 def test_missing_history_and_resurrection_are_rejected(self):
  with self.assertRaises(ValueError):TrueScanState((Hypothesis((4,0,1,0),(),F(1)),),((1,2,3),))
  state=acquire_uniform(self.base(5),tuple(range(1,6)))
  state=acquire_uniform(state,(1,2,3,4))
  with self.assertRaises(ValueError):acquire_uniform(state,(1,2,3,4,5))
 def test_no_possible_white_target_is_explicit_pending(self):
  state=TrueScanState((Hypothesis((6,0,1,0),(),F(1)),));self.assertIsInstance(acquire_uniform(state,(1,2,3)),FuturePending)

 def test_past_true_report_requires_conditioned_posterior(self):
  state=acquire_uniform(TrueScanState((Hypothesis((16,0,1,0),(),F(1)),)),(1,2,3,4,5))
  report=SeerReport(1,1,1,2,'white')
  with self.assertRaises(ValueError):truth_only_publications(state,(1,2,3,4,5),('seer','latent','latent','latent','latent'),(report,))
 def test_dead_past_fake_does_not_block_given_conditioned_prior(self):
  h=Hypothesis((6,0,1,0),(Acquisition(1,1,4,'white'),),F(1));state=TrueScanState((h,),((1,2,3,4,5),))
  result=truth_only_publications(state,(1,3,4,5),('seer','seer','latent','latent','latent'),(SeerReport(1,1,2,4,'white'),))
  self.assertEqual(sum(b.probability for b in result),1);self.assertEqual(result[0].reports,(SeerReport(1,1,1,4,'white'),))
 def test_morning_dead_scanned_target_can_still_be_reported(self):
  h=Hypothesis((16,0,1,0),(Acquisition(1,1,2,'white'),),F(1));state=TrueScanState((h,),((1,2,3,4,5),))
  rows=truth_only_publications(state,(1,3,4,5),('seer','latent','latent','latent','latent'))
  self.assertEqual(rows[0].reports,(SeerReport(1,1,1,2,'white'),));self.assertEqual(rows[0].probability,1)
 def test_multiple_wolf_identity_masks_are_retained_without_fake_policy(self):
  base=self.base(7,2,1);state=acquire_uniform(base,(1,2,3,4,5,6,7))
  self.assertEqual({h.roles for h in state.hypotheses},{h.roles for h in base.hypotheses})
  self.assertTrue(all(h.roles[0].bit_count()==2 for h in state.hypotheses))
 def test_truth_publication_budget_exceeded_stays_pending(self):
  h=Hypothesis((16,0,1,0),(Acquisition(1,1,2,'white'),),F(1));state=TrueScanState((h,),((1,2,3,4,5),))
  self.assertIsInstance(truth_only_publications(state,(1,2,3,4,5),('seer','latent','latent','latent','latent'),max_work=1),FuturePending)
