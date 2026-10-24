import unittest
from collections import defaultdict
from fractions import Fraction as F
from unittest.mock import patch
from tests.test_joint_value_sharing import hypothesis,law
from werewolf.seer_acquisition import normalize,Hypothesis,Acquisition

class NormalizationRecordReuseTests(unittest.TestCase):
 def independent(self,entries):
  weights=defaultdict(F)
  for h in entries:weights[h.roles,h.acquisitions,h.guards,h.attacks]+=h.mass
  total=sum(weights.values(),F())
  return tuple(Hypothesis(roles,scans,q/total,guards,attacks) for (roles,scans,guards,attacks),q in sorted(weights.items()))

 def test_mass_only_change_reuses_records_without_revalidating_them(self):
  entries=(hypothesis(mass=F(1),target=3),hypothesis(mass=F(2),target=4))
  expected=self.independent(entries)
  with patch.object(Hypothesis,'__post_init__',side_effect=AssertionError('immutable history revalidated')):
   actual=normalize(entries)
  self.assertEqual(actual,expected);self.assertEqual(tuple(h.mass for h in actual),(F(1,3),F(2,3)))
  for out,original in zip(actual,entries):
   self.assertIsNot(out,original);self.assertIs(out.roles,original.roles);self.assertIs(out.acquisitions,original.acquisitions);self.assertIs(out.attacks,original.attacks)
  self.assertEqual(tuple(h.mass for h in entries),(F(1),F(2)))

 def test_duplicate_entries_and_correlated_histories_keep_exact_joint_weights(self):
  entries=(hypothesis(mass=F(2),target=3,attack=3),hypothesis(mass=F(3),target=3,attack=3),hypothesis(mass=F(7),target=4,attack=3),hypothesis(mass=F(11),target=3,attack=4))
  actual=normalize(iter(entries));self.assertEqual(actual,self.independent(entries));self.assertEqual(len(actual),3);self.assertEqual(sum(h.mass for h in actual),1)
  self.assertEqual(sorted(h.mass for h in actual),[F(5,23),F(7,23),F(11,23)])

 def test_unchanged_normalization_retains_original_objects(self):
  entries=(hypothesis(mass=F(1,3),target=3),hypothesis(mass=F(2,3),target=4))
  self.assertTrue(all(a is b for a,b in zip(normalize(entries),entries)))

 def test_noncanonical_subclasses_keep_complete_constructor_validation(self):
  class Derived(Hypothesis):pass
  plain=hypothesis();derived=Derived(plain.roles,plain.acquisitions,F(2),plain.guards,plain.attacks)
  original=Hypothesis.__post_init__;calls=[]
  def validate(h):calls.append(h);return original(h)
  with patch.object(Hypothesis,'__post_init__',validate):actual=normalize((derived,))
  self.assertEqual(len(calls),1);self.assertIs(type(actual[0]),Hypothesis);self.assertEqual(actual[0].mass,1)
  class Masks(tuple):pass
  custom=hypothesis(roles=Masks((1,0,2,0)),mass=F(2));calls.clear()
  with patch.object(Hypothesis,'__post_init__',validate):normalize((custom,))
  # Custom role tuple is currently immutable but not an exact supported tuple.
  self.assertEqual(len(calls),1)

 def test_invalid_external_input_still_rejected_and_pool_owner_checks_remain(self):
  from types import SimpleNamespace
  from werewolf.joint_value_sharing import share_joint_values,JointPoolOwnerChanged
  bad=SimpleNamespace(roles=(1,0,2,0),acquisitions=(Acquisition(2,2,1,'white'),),mass=F(2),guards=(),attacks=())
  with self.assertRaises(ValueError):normalize((bad,))
  good=hypothesis(mass=F(2));owner=SimpleNamespace(data=object())
  with share_joint_values(owner):
   owner.data=object()
   with self.assertRaises(JointPoolOwnerChanged):normalize((good,))

 def test_equal_marginals_do_not_erase_role_history_correlations(self):
  left=(hypothesis(mass=F(2),roles=(1,0,2,0)),hypothesis(mass=F(2),roles=(4,0,8,0),target=2))
  right=(hypothesis(mass=F(2),roles=(1,0,8,0),target=2),hypothesis(mass=F(2),roles=(4,0,2,0)))
  a,b=normalize(left),normalize(right)
  for role in (0,2):
   marginal=lambda entries:{mask:sum(h.mass for h in entries if h.roles[role]==mask) for mask in {h.roles[role] for h in entries}}
   self.assertEqual(marginal(a),marginal(b))
  self.assertNotEqual(a,b);self.assertEqual(a,self.independent(left));self.assertEqual(b,self.independent(right))
