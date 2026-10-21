import unittest
from fractions import Fraction as F
from dataclasses import replace
from collections import defaultdict
from tests import test_anonymous_night as native_tests
from werewolf.anonymous_night import compile_anonymous
from werewolf.public_convergence import public_transport,transport_source,public_key,digest,mix,observation_branches,prefix_likelihood,condition_prefix
from werewolf.physical_selection import counts

class PublicConvergenceTests(unittest.TestCase):
 def case(self,seers=1):return native_tests.AnonymousNightTests().case(seers=seers,citizens=4-seers)
 def test_public_observation_retains_both_living_and_dead_seer_components(self):
  c,node=self.case();e=c._ClosedCalculation__engine
  with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
   rows=observation_branches(e,node.read(),2);self.assertEqual(len(rows),1);mass,source=rows[0]
   self.assertEqual(mass,F(1,4));distribution=defaultdict(F)
   for h in source.private.hypotheses:distribution[counts(h,source.public.alive)[2]]+=h.mass
   self.assertEqual(dict(distribution),{0:F(1,2),1:F(1,2)})
   self.assertTrue(any(any(a.player==2 and a.day==2 for a in h.acquisitions) for h in source.private.hypotheses))
 def test_transport_roundtrip_preserves_every_public_private_coordinate(self):
  c,node=self.case();e=c._ClosedCalculation__engine
  with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
   source=observation_branches(e,node.read(),4)[0][1];mapping=public_transport(node.read(),source,node.groups)
   moved=transport_source(source,mapping);inverse=tuple(mapping.index(p)+1 for p in range(1,len(mapping)+1))
   self.assertEqual(transport_source(moved,inverse),source)
   self.assertEqual(moved.public.history[-1].target,2)
 def test_same_public_picture_with_different_Q_cannot_be_mixed(self):
  c,node=self.case();e=c._ClosedCalculation__engine
  with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
   source=observation_branches(e,node.read(),2)[0][1]
   altered=replace(source,public_state=replace(source.public_state,observed_prefix=source.public_state.observed_prefix+1))
   with self.assertRaises(ValueError):mix(((F(1,2),source),(F(1,2),altered)))
 def test_prefix_joint_masses_match_native_program_for_one_and_two_seers(self):
  for seers in (1,2):
   c,node=self.case(seers);e=c._ClosedCalculation__engine
   with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
    before=node.read();program=compile_anonymous(e,before,node.groups);source=observation_branches(e,before,2)[0][1]
    pending=[program.root]
    while pending:
     stage=pending.pop();native=stage.mass
     measured=sum((h.mass*prefix_likelihood(h,before,source,node.groups,stage.prefix) for h in source.private.hypotheses),F())
     self.assertEqual(measured,native,repr(stage.prefix))
     if not stage.terminal:pending.extend(branch.state for branch in stage.branches())
 def test_conditioning_a_hidden_path_does_not_change_Q(self):
  c,node=self.case();e=c._ClosedCalculation__engine
  with c._ClosedCalculation__kernel(),e.group_scope(node.groups):
   before=node.read();program=compile_anonymous(e,before,node.groups);source=observation_branches(e,before,2)[0][1]
   first=next(b for b in program.root.branches() if b.step.kind=='seer_target');black=next(b for b in first.state.branches() if b.step.target=='black')
   mass,selected=condition_prefix(source,before,node.groups,black.state.prefix)
   self.assertEqual(mass,black.state.mass);self.assertIs(selected.public_state,source.public_state);self.assertEqual(selected.public,source.public)
