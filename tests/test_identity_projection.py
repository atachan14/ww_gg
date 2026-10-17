import unittest
from dataclasses import replace
from fractions import Fraction as F
from types import SimpleNamespace
from werewolf.exact import initial_board,replace_worlds
from werewolf.seer_acquisition import Hypothesis,Acquisition,normalize,from_board
from werewolf.seer_future_uniform import TrueScanState
from werewolf.belief_projection import project_private

def reference(state,board,*,marginalize_private=False):
 old={r[:-1]:r[-1] for r in state.public_roles};new={r[:-1]:r[-1] for r in board.worlds}
 tracked=tuple(p for p in board.alive if board.claims[p-1]=='seer' and (state.tracked is None or p in state.tracked)) if marginalize_private else state.tracked
 entries=tuple(Hypothesis(h.roles,tuple(a for a in h.acquisitions if not marginalize_private or a.player in tracked),h.mass*new[h.roles]/old[h.roles],h.guards,h.attacks) for h in state.hypotheses if h.roles in new)
 return TrueScanState(normalize(entries),state.rosters,state.initial_rule,tracked,state.observed_prefix)

class IdentityProjectionTests(unittest.TestCase):
 def fixture(self):
  b=initial_board(5,1,0,1);s=TrueScanState(normalize(from_board(b)),initial_rule='none')
  return s,b
 def test_normalized_complete_identity_preserves_exact_reference_and_public_cache(self):
  s,b=self.fixture();roles=s.public_roles
  out=project_private(s,b);self.assertIs(out,s);self.assertEqual(out,reference(s,b));self.assertIs(out.public_roles,roles)
 def test_unsorted_and_duplicate_hypotheses_still_normalize(self):
  s,b=self.fixture();h=s.hypotheses[0]
  for entries in [(replace(h,mass=F(1,3)),replace(h,mass=F(2,3))),tuple(replace(h,mass=F(1,2)) for h in s.hypotheses[:2][::-1])]:
   x=replace(s,hypotheses=entries);target=replace_worlds(b,x.public_roles)
   out=project_private(x,target);self.assertIsNot(out,x);self.assertEqual(out,reference(x,target))
 def test_same_role_marginal_keeps_distinct_private_histories(self):
  roles=(1,0,2,0);alive=(1,2,3,4,5)
  hs=tuple(Hypothesis(roles,(Acquisition(2,2,t,'white'),),F(1,2)) for t in (3,4))
  s=TrueScanState(hs,(alive,alive),'none');b=replace_worlds(initial_board(5,1,0,1),s.public_roles)
  out=project_private(s,b);self.assertIs(out,s);self.assertEqual(len(out.hypotheses),2);self.assertEqual(out,reference(s,b))
 def test_changed_role_weights_do_not_return_previous_posterior(self):
  s,b=self.fixture();rows=s.public_roles[:2];law=((*rows[0][:4],F(1,3)),(*rows[1][:4],F(2,3)))
  target=replace_worlds(b,law);out=project_private(s,target)
  self.assertIsNot(out,s);self.assertEqual(out,reference(s,target));self.assertEqual(out.public_roles,tuple(sorted(law)))
 def test_marginalization_and_observed_prefix_keep_original_contract(self):
  roles=(1,0,2,0);alive=(1,2,3,4,5)
  s=TrueScanState((Hypothesis(roles,(Acquisition(2,2,3,'white'),),F(1)),),(alive,alive),'none')
  b=replace_worlds(initial_board(5,1,0,1),s.public_roles)
  out=project_private(s,b,marginalize_private=True);self.assertEqual(out,reference(s,b,marginalize_private=True));self.assertEqual(out.tracked,());self.assertFalse(out.hypotheses[0].acquisitions)
  missing=replace(s,hypotheses=(Hypothesis(roles,(),F(1)),),observed_prefix=2)
  self.assertIs(project_private(missing,b),missing);self.assertEqual(project_private(missing,b),reference(missing,b))
 def test_mutable_metadata_and_subclasses_keep_full_revalidation(self):
  s,b=self.fixture();mutable=replace(s,rosters=[])
  self.assertIsNot(project_private(mutable,b),mutable)
  mutable.rosters.append((1,1))
  with self.assertRaises(ValueError):project_private(mutable,b)
  class Other(TrueScanState):pass
  x=Other(s.hypotheses,initial_rule='none');out=project_private(x,b)
  self.assertIs(type(out),TrueScanState);self.assertEqual(out,reference(x,b))
 def test_numeric_equal_float_target_mass_cannot_bypass_original_error(self):
  s,b=self.fixture();fake=SimpleNamespace(worlds=tuple((*row[:4],float(row[-1])) for row in s.public_roles))
  with self.assertRaises(ValueError):reference(s,fake)
  with self.assertRaises(ValueError):project_private(s,fake)
