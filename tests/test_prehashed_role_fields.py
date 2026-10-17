import unittest
from dataclasses import replace,fields
from fractions import Fraction as F
from werewolf.exact import Board,PublicEvent,MediumReport,initial_board
class PrehashedRoleFieldTests(unittest.TestCase):
 def test_complete_hash_equal_to_generated_hash_before_and_after_reuse(self):
  b=initial_board(5,1,1,1)
  original=Board.__hash__.__wrapped__
  self.assertEqual(hash(b),original(b));self.assertEqual(hash(b),original(b))
  self.assertIsNotNone(b._role_hash_source._parts)
  self.assertNotIn('_verified_board_hash',b.__dict__)
 def test_all_dataclass_hash_fields_remain_in_original_hash(self):
  b=initial_board(5,1,1,1);hash(b)
  values=tuple(getattr(b,f.name) for f in fields(Board) if (f.compare if f.hash is None else f.hash))
  self.assertEqual(hash(b),hash(values))
  for changes in [{'claims':('seer',)+('latent',)*4},{'day':2},{'phase':'night'},
                  {'medium_opportunities':((2,1,5),)},{'reports':(MediumReport(2,1,5,'white'),)},
                  {'report_resolved':((2,1,5),)},
                  {'world_belief':tuple((*row[:4],F(1,2)) for row in b.world_belief[:2]),'wolf_count':None}]:
   edited=replace(b,**changes);self.assertNotIn('_verified_board_hash',edited.__dict__)
   self.assertEqual(hash(edited),Board.__hash__.__wrapped__(edited))
 def test_history_edit_reconstructs_its_hash_and_does_not_reuse_parent_memo(self):
  b=initial_board(5,1,1,1);hash(b)
  edited=replace(b,alive=(1,2,3,4),history=(PublicEvent(1,'day',5),),wolf_count=None)
  self.assertNotIn('_verified_board_hash',edited.__dict__)
  self.assertEqual(hash(edited),Board.__hash__.__wrapped__(edited))
 def test_unknown_hashable_mutable_input_keeps_original_hash_behavior(self):
  class Mutable:
   value=1
   def __hash__(self):return self.value
  item=Mutable();b=replace(initial_board(5,1,1,1),medium_opportunities=((item,),))
  self.assertEqual(hash(b),Board.__hash__.__wrapped__(b));self.assertNotIn('_verified_board_hash',b.__dict__)
  item.value=2;self.assertEqual(hash(b),Board.__hash__.__wrapped__(b));self.assertNotIn('_verified_board_hash',b.__dict__)
 def test_subclass_and_uncertified_laws_keep_original_behavior(self):
  class Other(Board):pass
  b=initial_board(5,1,1,1);other=Other(**{f.name:getattr(b,f.name) for f in fields(Board)})
  self.assertEqual(hash(other),Board.__hash__.__wrapped__(other));self.assertNotIn('_verified_board_hash',other.__dict__)
  plain=initial_board(5,1);hash(plain);self.assertNotIn('_verified_board_hash',plain.__dict__)
  with self.assertRaises(TypeError):hash(replace(b,claims=['latent']*5))
