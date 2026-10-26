import unittest
from dataclasses import replace
from fractions import Fraction as F
from itertools import permutations
from types import SimpleNamespace
from unittest.mock import patch
from werewolf.exact import initial_board,replace_worlds,action_outcomes,Rules,Strategy,MediumReport
from werewolf.seer_acquisition import Acquisition,Hypothesis,SeerReport
from werewolf.seer_future_uniform import TrueScanState
from werewolf.evaluation_branch import ContinuationInputs
from werewolf.public_convergence import transport_source
from werewolf.tree_public_updates import publication_label,_publication_facts
from dev_previews.publication_label_reference import legacy_label


class PublicationLabelProjectionTests(unittest.TestCase):
 def sources(self):
  root=replace_worlds(initial_board(6,1,1,1),((32,2,1,0,F(1)),))
  root=replace(root,claims=('seer','latent','latent','latent','latent','latent'))
  night=action_outcomes(root,4,Rules(),Strategy('random','random'))[0].board
  day=action_outcomes(night,5,Rules(),Strategy('random','random'))[0].board
  scans=(Acquisition(1,1,3,'white'),Acquisition(2,1,6,'black'))
  state=TrueScanState((Hypothesis((32,2,1,0),scans,F(1)),),(root.alive,night.alive),initial_rule='normal')
  first=SeerReport(1,1,1,3,'white');second=SeerReport(2,2,1,6,'black')
  before=ContinuationInputs(day,state,(first,),state,None,day)
  after_board=replace(day,claims=('seer','medium','latent','latent','latent','latent'),reports=(MediumReport(2,2,4,'white'),))
  after=ContinuationInputs(after_board,state,(first,second),state,None,after_board)
  return before,after

 def test_all_bijections_match_full_joint_transport_reference(self):
  before,after=self.sources()
  for mapping in permutations(range(1,7)):
   a,b=transport_source(before,mapping),transport_source(after,mapping)
   expected=legacy_label(a,b)
   self.assertEqual(publication_label(before,after,mapping=mapping),expected,mapping)
   self.assertEqual(_publication_facts(after,mapping),(b.past,b.public.reports,b.public.claims),mapping)

 def test_simultaneous_true_and_fake_reporters_keep_mapped_group_order(self):
  before,after=self.sources()
  old_fake=SeerReport(1,1,6,3,'white');new_fake=SeerReport(2,2,6,2,'black')
  old_board=replace(before.public,claims=('seer','latent','latent','latent','latent','seer'))
  new_board=replace(after.public,claims=('seer','medium','latent','latent','latent','seer'))
  before=replace(before,public=old_board,physical=old_board,past=before.past+(old_fake,))
  after=replace(after,public=new_board,physical=new_board,past=after.past+(old_fake,new_fake))
  for mapping in permutations(range(1,7)):
   self.assertEqual(publication_label(before,after,mapping=mapping),legacy_label(transport_source(before,mapping),transport_source(after,mapping)),mapping)

 def test_identity_keeps_original_order_and_delayed_report_timing(self):
  before,after=self.sources();before=replace(before,past=())
  after=replace(after,past=(after.past[1],SeerReport(1,2,1,3,'white')))
  for mapping in (tuple(range(1,7)),(6,5,4,3,2,1)):
   expected=legacy_label(transport_source(before,mapping),transport_source(after,mapping))
   actual=publication_label(before,after,mapping=mapping)
   self.assertEqual(actual,expected);self.assertIn('Day1',actual)
  self.assertEqual(publication_label(before,after),legacy_label(before,after))

 def test_unchanged_publication_and_withdrawal_match_reference(self):
  before,after=self.sources()
  for first,last in ((before,before),(after,before)):
   for mapping in ((1,2,3,4,5,6),(3,2,1,6,5,4)):
    self.assertEqual(publication_label(first,last,mapping=mapping),legacy_label(transport_source(first,mapping),transport_source(last,mapping)))

 def test_label_reads_no_Q_P_law_or_navigation_metadata(self):
  before,after=self.sources();mapping=(2,3,4,5,6,1)
  expected=legacy_label(transport_source(before,mapping),transport_source(after,mapping))
  class VisibleOnly:
   def __init__(self,source):self.public=SimpleNamespace(player_count=source.public.player_count,reports=source.public.reports,claims=source.public.claims);self.past=source.past
   def __getattr__(self,name):raise AssertionError('unnecessary calculation field '+name)
  with patch('werewolf.public_convergence.transport_source',side_effect=AssertionError('full state transport')),patch('werewolf.seer_acquisition.normalize',side_effect=AssertionError('secret normalization')),patch('werewolf.exact.replace_worlds',side_effect=AssertionError('Board rebuild')):
   self.assertEqual(publication_label(VisibleOnly(before),VisibleOnly(after),mapping=mapping),expected)

 def test_actual_ability_program_keeps_complete_leaves_without_label_transport(self):
  from tests.test_joint_action_kernel import fixture
  from werewolf.anonymous_role_night import compile_abilities
  calculation,node,_=fixture('random');engine=calculation._ClosedCalculation__engine;source=node.read()
  def reference(before,after,*,mapping=None):
   if mapping is None:return legacy_label(before,after)
   return legacy_label(transport_source(before,mapping),transport_source(after,mapping))
  with calculation._ClosedCalculation__kernel(),engine.group_scope(node.groups):
   engine.anonymous_ability_programs={}
   with patch('werewolf.tree_public_updates.publication_label',side_effect=reference):expected=compile_abilities(engine,source,node.groups)
   engine.anonymous_ability_programs={}
   with patch('werewolf.public_convergence.transport_source',side_effect=AssertionError('label must not rebuild full state')):actual=compile_abilities(engine,source,node.groups)
  self.assertIsNotNone(actual);self.assertEqual(len(actual.leaves),len(expected.leaves))
  self.assertTrue(any(step.kind=='publication' for leaf in actual.leaves for step in leaf.steps))
  for i,(left,right) in enumerate(zip(actual.leaves,expected.leaves)):
   self.assertTrue(left==right,'complete leaf differs at '+str(i))
  self.assertEqual(actual.stats,expected.stats)
