import unittest
from fractions import Fraction as F
from werewolf.seer_acquisition import SeerReport,Hypothesis
from werewolf.seer_fake_uniform import fake_uniform_options,fake_joint_options
from werewolf.seer_future_uniform import FuturePending,TrueScanState,acquire_uniform

class FakeUniformTests(unittest.TestCase):
 def test_unreported_priority_target_then_color_equal_probability(self):
  past=(SeerReport(1,1,1,2,'white'),)
  options=fake_uniform_options((1,2,3,4),1,past)
  self.assertEqual({t for (t,c),q in options},{3,4});self.assertEqual({q for action,q in options},{F(1,4)});self.assertEqual(sum(q for a,q in options),1)
 def test_only_own_public_history_affects_target_priority(self):
  past=(SeerReport(1,1,2,3,'white'),)
  self.assertEqual({t for (t,c),q in fake_uniform_options((1,2,3,4),1,past)},{2,3,4})
 def test_revisit_fallback_retains_literal_uniform_colors(self):
  past=(SeerReport(1,1,1,2,'white'),SeerReport(2,2,1,3,'black'))
  options=fake_uniform_options((1,2,3),1,past);self.assertEqual(options,(((2,'white'),F(1,4)),((2,'black'),F(1,4)),((3,'white'),F(1,4)),((3,'black'),F(1,4))))
 def test_single_fake_and_no_fake_joint_law_complete(self):
  self.assertEqual(fake_joint_options((1,2,3),(),()),(((),F(1)),));self.assertEqual(sum(q for a,q in fake_joint_options((1,2,3),(1,),())),1)
 def test_multiple_fake_joint_correlation_not_assumed(self):
  result=fake_joint_options((1,2,3,4),(1,2),());self.assertIsInstance(result,FuturePending);self.assertEqual(result.reason,'multiple_fake_report_correlation_unselected')
 def test_first_none_has_no_true_initial_scan_but_next_night_scans(self):
  h=Hypothesis((4,0,1,0),(),F(1));s=acquire_uniform(TrueScanState((h,),initial_rule='none'),(1,2,3));self.assertEqual(s.hypotheses[0].acquisitions,())
  s=acquire_uniform(s,(1,2,3));self.assertEqual({h.acquisitions[0].color for h in s.hypotheses},{'white','black'})
 def test_initial_normal_uniform_truth_can_be_black(self):
  h=Hypothesis((4,0,1,0),(),F(1));s=acquire_uniform(TrueScanState((h,),initial_rule='normal'),(1,2,3));self.assertEqual({h.acquisitions[0].color for h in s.hypotheses},{'white','black'});self.assertEqual({h.mass for h in s.hypotheses},{F(1,2)})
