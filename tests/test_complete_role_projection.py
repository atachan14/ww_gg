import unittest
from dataclasses import replace
from fractions import Fraction as F
from werewolf.exact import Board,_validated_complete_roles

class CompleteRoleProjectionTests(unittest.TestCase):
 def board(self,worlds=None,**changes):
  law=((1,2,4,8,F(1,2)),(2,1,8,4,F(1,2))) if worlds is None else worlds
  return Board(4,(1,2,3,4),initial_medium_count=1,initial_seer_count=1,
               initial_hunter_count=1,world_belief=law,**changes)
 def test_joint_projection_and_repeated_complete_inputs_remain_exact(self):
  a=self.board();b=self.board()
  self.assertEqual(a,b);self.assertEqual(a.role_belief,((1,2,F(1,2)),(2,1,F(1,2))))
  self.assertEqual(a.belief,((1,F(1,2)),(2,F(1,2))))
  self.assertEqual(a.role_probability(1,'wolf'),F(1,2))
  self.assertEqual(a.role_probability(1,'medium'),F(1,2))
 def test_invalid_numeric_equal_mask_cannot_hit_a_validated_integer_key(self):
  a=self.board();bad=((1.0,*a.world_belief[0][1:]),a.world_belief[1])
  with self.assertRaisesRegex(ValueError,'Invalid role masks'):self.board(bad)
  bad=((True,*a.world_belief[0][1:]),a.world_belief[1])
  with self.assertRaisesRegex(ValueError,'Invalid role masks'):self.board(bad)
 def test_mutable_and_fraction_subclass_compatibility_never_enter_cache(self):
  a=self.board();before=_validated_complete_roles.cache_info()
  mutable=self.board(list(a.world_belief))
  self.assertEqual(mutable.belief,a.belief);self.assertEqual(mutable.role_belief,a.role_belief)
  class CustomFraction(F):pass
  law=tuple((*row[:4],CustomFraction(row[4])) for row in a.world_belief)
  self.assertEqual(self.board(law),a)
  self.assertEqual(_validated_complete_roles.cache_info(),before)
 def test_same_law_does_not_bypass_board_specific_history_or_count_checks(self):
  a=self.board()
  with self.assertRaisesRegex(ValueError,'History and alive'):replace(a,alive=(1,2,3))
  with self.assertRaisesRegex(ValueError,'Count and joint'):replace(a,wolf_count=2)
  with self.assertRaisesRegex(ValueError,'Role counts disagree'):replace(a,initial_seer_count=0)
 def test_invalid_mass_overlap_duplicate_and_guard_provenance_still_fail(self):
  a=self.board();x,y=a.world_belief
  for law in [(x,x),((*x[:4],F(1,3)),y),((1,1,4,8,F(1,2)),y)]:
   with self.assertRaises(ValueError):self.board(law)
  with self.assertRaisesRegex(ValueError,'guard-history'):replace(a,guard_prior_roster=(1,(1,2,3,4)))

 def test_large_exact_laws_are_validated_without_retention(self):
  from itertools import combinations
  worlds=tuple((sum(1<<i for i in ids),0,0,0,F(1,65)) for ids in tuple(combinations(range(9),3))[:65])
  before=_validated_complete_roles.cache_info()
  a=Board(9,tuple(range(1,10)),wolf_count=3,world_belief=worlds)
  self.assertEqual(sum(q for _,q in a.belief),1)
  self.assertEqual(_validated_complete_roles.cache_info(),before)
