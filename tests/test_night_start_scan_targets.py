import unittest
from dataclasses import replace
from fractions import Fraction as F
from werewolf.exact import PublicEvent
from werewolf.phase_updates import acquisition_roster
from werewolf.seer_acquisition import Hypothesis,Acquisition,SeerReport
from werewolf.seer_future_uniform import TrueScanState,acquire_uniform,truth_only_publications
from werewolf.morning_publications import fake_backlog_options

class NightStartScanTargets(unittest.TestCase):
 def seed(self):
  return TrueScanState((Hypothesis((16,0,1,0),(),F(1)),),((1,2,3,4,5),),'none',(1,))
 def test_execution_and_earlier_night_death_excluded(self):
  history=(PublicEvent(1,'day',3),PublicEvent(1,'night',2),PublicEvent(2,'day',4))
  self.assertEqual(acquisition_roster(5,history,2),(1,2,4,5))
  self.assertEqual(acquisition_roster(5,history,3),(1,5))
  first=acquire_uniform(self.seed(),(1,2,4,5))
  self.assertEqual({a.target for h in first.hypotheses for a in h.acquisitions if a.day==2},{2,4,5})
  later=acquire_uniform(first,(1,5))
  self.assertEqual({a.target for h in later.hypotheses for a in h.acquisitions if a.day==3},{5})
  self.assertEqual(sum(h.mass for h in later.hypotheses),1)
 def test_same_night_bitten_target_reported_but_dead_seer_not_published(self):
  state=acquire_uniform(self.seed(),(1,2,4,5))
  h=next(h for h in state.hypotheses if h.acquisitions[-1].target==2)
  conditioned=replace(state,hypotheses=(replace(h,mass=F(1)),))
  alive=(1,4,5)
  reports=truth_only_publications(conditioned,alive,('seer',)+('latent',)*4)
  self.assertEqual(reports[0].reports,(SeerReport(2,2,1,2,'white'),))
  dead=truth_only_publications(conditioned,(2,4,5),('seer',)+('latent',)*4)
  self.assertEqual(dead[0].reports,())
  self.assertEqual(dead[0].state.hypotheses[0].acquisitions,(Acquisition(2,1,2,'white'),))
  self.assertEqual(sum(b.probability for b in reports),1)
  self.assertEqual(sum(b.probability for b in dead),1)
 def test_invalid_historical_record_rejected_and_fake_domain_matches_night(self):
  with self.assertRaises(ValueError):
   TrueScanState((Hypothesis((16,0,1,0),(Acquisition(2,1,3,'white'),),F(1)),),((1,2,3,4,5),(1,2,4,5)),'none',(1,))
  state=acquire_uniform(self.seed(),(1,2,4,5))
  options=fake_backlog_options(state,(2,),())
  self.assertEqual({r.target for reports,q in options for r in reports},{1,4,5})
  self.assertEqual(sum(q for reports,q in options),1)
