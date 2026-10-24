import unittest
from collections import defaultdict
from dataclasses import replace
from fractions import Fraction as F
from itertools import product
from benchmarks.player_match_groups.tracking_comparison import complete_tracking,comparison_source
from werewolf.seer_acquisition import Hypothesis,Acquisition
from werewolf.seer_future_uniform import TrueScanState,acquire_uniform,true_reports
from werewolf.exact import initial_board,replace_worlds,Rules,Strategy,PublicEvent
from werewolf.evaluation_branch import ContinuationInputs,physical_board
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.calculation_budget import calculation_budget

class TrackingComparisonTests(unittest.TestCase):
 def law(self,owners=(1,),tracked=None):
  mask=sum(1<<(p-1) for p in owners)
  return TrueScanState((Hypothesis((16,0,mask,0),(),F(1)),),((1,2,3,4,5),),'none',tracked)
 def independent(self,owners):
  alive=(1,2,3,5);choices=[tuple(p for p in alive if p!=actor)for actor in owners];rows={}
  for targets in product(*choices):
   records=tuple((2,p,t,'black' if t==5 else 'white')for p,t in zip(owners,targets))
   for bite in (1,2,3):
    reports=tuple((2,2,p,t,color)for _,p,t,color in records if p!=bite)
    rows[(records,bite,reports)]=F(1,3)*F(1,len(tuple(product(*choices))))
  return rows
 def actual(self,law):
  acquired=acquire_uniform(law,(1,2,3,5));out={}
  claims=tuple('seer' if law.hypotheses[0].roles[2]&(1<<(p-1)) else 'latent' for p in range(1,6))
  for h in acquired.hypotheses:
   records=tuple((a.day,a.player,a.target,a.color)for a in h.acquisitions)
   for bite in (1,2,3):
    reports=true_reports(h,(),tuple(p for p in (1,2,3,5)if p!=bite),claims,2)
    out[(records,bite,tuple((r.acquired_day,r.published_day,r.player,r.target,r.color)for r in reports))]=h.mass/F(3)
  return acquired,out
 def test_complete_known_owner_matches_independent_full_private_and_public_law(self):
  all_=self.law();explicit=self.law(tracked=(1,));self.assertNotEqual(all_,explicit)
  left,lrows=self.actual(all_);right,rrows=self.actual(explicit)
  self.assertEqual(lrows,self.independent((1,)));self.assertEqual(rrows,lrows)
  self.assertEqual(complete_tracking(left),complete_tracking(right));self.assertEqual(sum(lrows.values()),1)
  # Simultaneous victim obtains the scan but does not publish after death.
  killed=[(records,reports)for (records,bite,reports)in lrows if bite==1]
  self.assertTrue(all(records and not reports for records,reports in killed))
  self.assertTrue(all(target!=4 for records,_,_ in lrows for _,_,target,_ in records))
 def test_partial_tracking_with_two_true_seers_is_not_equivalent(self):
  all_=self.law((1,2));partial=self.law((1,2),tracked=(1,))
  self.assertEqual(all_.hypotheses,partial.hypotheses)
  left,lrows=self.actual(all_);right,rrows=self.actual(partial)
  self.assertEqual(lrows,self.independent((1,2)));self.assertNotEqual(lrows,rrows)
  self.assertEqual(len(left.hypotheses),9);self.assertEqual(len(right.hypotheses),3)
  self.assertIs(complete_tracking(partial),partial);self.assertNotEqual(complete_tracking(all_),complete_tracking(partial))
 def test_values_and_complete_sources_preserve_Q_P_and_every_other_field(self):
  with calculation_budget(250000,max_seconds=15):
   law=self.law();explicit=replace(law,tracked=(1,));board=replace_worlds(initial_board(5,1,0,1),law.public_roles,alive=(1,2,3,5),phase='night',history=(PublicEvent(1,'day',4),),claims=('seer','latent','latent','latent','latent'))
   left=ContinuationInputs(board,law,(),law,None,board);right=replace(left,public_state=explicit,private=explicit)
   self.assertEqual(comparison_source(left),comparison_source(right))
   rules=Rules(initial_seer='none');strategy=Strategy(day='random',night='random',fake_reports='random')
   values=[]
   for state in (left,right):
    engine=InformationSetForecast(rules,strategy,exact_renaming=False,retire_uninformative_scans=False);engine.retain_joint_guard_history=True
    values.append(engine.solve(*state,physical=state.physical))
   self.assertEqual(values,[F(1,3),F(1,3)]) # Three survivors, one wolf, uniform execution.
   variant=replace(right,past=('different-public-history',))
   self.assertNotEqual(comparison_source(left),comparison_source(variant))
 def test_private_conditioning_is_not_replaced_with_public_weights(self):
  q=TrueScanState((Hypothesis((8,0,1,0),(),F(1,2)),Hypothesis((16,0,1,0),(),F(1,2))),((1,2,3,4,5),),'none',(1,))
  own=replace(q,hypotheses=(replace(q.hypotheses[0],mass=F(1)),))
  board=replace_worlds(initial_board(5,1,0,1),q.public_roles)
  source=ContinuationInputs(board,q,(),own,None,physical_board(board,own))
  result=comparison_source(source)
  self.assertEqual(result.public_state.hypotheses,q.hypotheses);self.assertEqual(result.private.hypotheses,own.hypotheses)
  self.assertNotEqual(result.public_state,result.private);self.assertEqual(result.physical,source.physical)
