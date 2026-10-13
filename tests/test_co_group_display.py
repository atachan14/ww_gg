import re
import unittest
from flask import render_template
from app import create_app
from werewolf.exact import initial_board,co_group_compositions,ROLE_LABELS

class COGroupDisplayTests(unittest.TestCase):
 def test_four_columns_and_only_nonzero_role_counts(self):
  app=create_app({'TESTING':True,'SECRET_KEY':'groups'})
  board=initial_board(5,1,0,1)
  before=board.worlds
  with app.test_request_context('/'):
   h=render_template('co_groups.html',co_groups=co_group_compositions(board),role_labels=ROLE_LABELS,co_display_main=True)
  self.assertIn('COグループ内訳',h)
  self.assertEqual(re.findall(r'<th>(.*?)</th>',h),['CO','生存位置','内訳','確率'])
  self.assertIn('市民3，占い師1，狼1',h)
  self.assertNotIn('霊能0',h);self.assertNotIn('手動のみ',h)
  self.assertIn('data-fraction="1"',h)
  self.assertEqual(board.worlds,before)
 def test_zero_in_a_composition_is_hidden_even_if_role_exists_in_game(self):
  from fractions import Fraction as F
  app=create_app({'TESTING':True,'SECRET_KEY':'groups'})
  groups=[dict(claim='seer',ids=(1,2),roles=('villager','medium','seer','wolf'),visible_roles=('villager','seer','wolf'),compositions=((0,0,1,1,F(1)),))]
  with app.test_request_context('/'):
   h=render_template('co_groups.html',co_groups=groups,role_labels=ROLE_LABELS,co_display_main=True)
  self.assertIn('占い師1，狼1',h);self.assertNotIn('市民0',h)
