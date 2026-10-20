import unittest
from dataclasses import replace
from fractions import Fraction as F
from itertools import combinations
from werewolf.exact import initial_board,replace_worlds,PublicEvent
from werewolf.seer_acquisition import Hypothesis
from werewolf.seer_future_uniform import TrueScanState
from werewolf.evaluation_branch import ContinuationInputs,physical_board
from werewolf.night_program import NightProgram,NightLeaf
from werewolf.night_abilities import AbilityStep
from werewolf.actor_information import WolfInformation
from werewolf.ability_labels import stage_label
from tests import test_night_program as stage_tests

class ActorLabelTests(unittest.TestCase):
 def source(self,rosters,groups,dead=3):
  base=initial_board(7,len(rosters[0]),0,0,0,experimental_cast=True)
  q=F(1,len(rosters));entries=tuple(Hypothesis((sum(1<<(p-1) for p in roster),0,0,0),(),q) for roster in rosters)
  b=replace_worlds(base,tuple((*h.roles,h.mass) for h in entries));b=replace(b,alive=tuple(p for p in b.alive if p!=dead),phase='night',history=(PublicEvent(1,'day',dead),))
  law=TrueScanState(entries,rosters=(tuple(range(1,8)),),initial_rule='none');source=ContinuationInputs(b,law,(),law,None,physical_board(b,law));leaves=[]
  for roster,h in zip(rosters,entries):
   own=replace(law,hypotheses=(replace(h,mass=F(1)),));s=replace(source,private=own,physical=physical_board(b,own));legal=[p for p in b.alive if p not in roster]
   for target in legal:
    mass=q/F(len(legal));step=AbilityStep('wolf_target',None,target,(),tuple(roster))
    leaves.append(NightLeaf(mass,mass,s,(step,),WolfInformation(h.roles[0],()),0,target,0,None,None,tuple(roster),(),groups))
  return NightProgram(None,source,groups,leaves)
 def test_split_wolf_actor_groups_and_residual_target_orbit(self):
  p=self.source(tuple((a,b) for a in (1,2) for b in (5,6,7)),((1,2),(3,),(4,),(5,6,7)))
  labels=[stage_label(b)[0] for b in p.root.branches()]
  self.assertIn('[(1),2]\u3068[(5),6,7]\u304c[(6),7]\u3092\u8972\u6483',labels)
  self.assertEqual(sum(b.probability for b in p.root.branches()),1)
  for branch in p.root.branches():
   label,groups,choices=stage_label(branch)
   for choice in choices:self.assertNotIn(choice['target'],choice['actors'])
   for t in branch.targets:self.assertNotIn(t,branch.step.actors)
 def test_multiple_wolves_in_one_group_are_explicit_alternate_allocations(self):
  p=self.source(tuple(combinations((1,2,3),2)),((1,2,3),(4,5,6),(7,)),dead=7)
  label,groups,choices=next(stage_label(b) for b in p.root.branches() if b.targets==(4,5,6))
  self.assertEqual(label,'[(1),(2),3]\uff082\u4eba\uff09\u304c[(4),5,6]\u3092\u8972\u6483')
  self.assertEqual(groups,[dict(members=[1,2,3],representatives=[1,2],count=2)])
  self.assertEqual({tuple(c['actors']) for c in choices},{(1,2),(1,3),(2,3)})
 def test_real_latent_seer_and_wolf_labels_preserve_correlated_legality(self):
  c,node,client=stage_tests.NightProgramTests().case();program=node._night_program();scan=program.root.branches()[0]
  for choice in stage_label(scan)[2]:self.assertNotIn(choice['target'],choice['actors'])
  self.assertEqual(stage_label(scan)[0],'[(2),3,4,5]\u304c[(3),4,5]\u304b\u3089\u5360\u3044')
  white=next(b for b in scan.state.branches() if b.step.value=='white')
  attack=next(b for b in white.state.branches() if b.step.actors==(4,) and b.targets==(5,))
  self.assertEqual(stage_label(attack)[0],'[(4),5]\u304c5\u3092\u8972\u6483')
  for branch in white.state.branches():
   for choice in stage_label(branch)[2]:self.assertNotIn(choice['target'],choice['actors'])
 def test_known_actor_stays_single_and_second_seer_is_not_first(self):
  c,node,client=stage_tests.NightProgramTests().case(2,'random');p=node._night_program()
  for first in p.root.branches():
   for result in first.state.branches():
    for second in result.state.branches():
     self.assertNotEqual(first.step.actor,second.step.actor)
     self.assertTrue(all(named.actor!=first.step.actor for named,leaves,mapping in second.images))

 def test_single_known_actor_stays_natural(self):
  from tests.test_joint_action_kernel import fixture
  c,node,client=fixture();branch=node._night_program().root.branches()[0]
  self.assertEqual(stage_label(branch)[0],'1\u304c[(4),5]\u304b\u3089\u5360\u3044')
