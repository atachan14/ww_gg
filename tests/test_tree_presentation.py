import unittest
from types import SimpleNamespace
from app import create_app
from werewolf.calculation_tree import composition_label

class TreePresentationTests(unittest.TestCase):
 def test_composition_follows_supplied_role_table_order_and_retains_zero_survivors(self):
  game=SimpleNamespace(players=9,wolves=2,mediums=1,seers=1,hunters=1)
  counts=(1,0,1,1,3)
  self.assertEqual(composition_label(counts,game,('villager','medium','seer','hunter','wolf')),'\u5e02\u6c113\u970a\u80fd0\u5360\u30441\u72e9\u4eba1\u72fc1')
  self.assertEqual(composition_label(counts,game,('wolf','hunter','seer','medium','villager')),'\u72fc1\u72e9\u4eba1\u5360\u30441\u970a\u80fd0\u5e02\u6c113')
 def test_API_uses_current_configured_table_order_even_for_same_saved_inputs(self):
  app=create_app({'TESTING':True,'SECRET_KEY':'tree-presentation','GAME_TREE_PREVIEW':True});client=app.test_client()
  client.post('/start',data={'citizens':'3','seers':'1','wolves':'1','day':'max','night':'max'})
  first=client.get('/game-tree?expand=1').json
  self.assertEqual(first['compositions'][0]['label'],'\u5e02\u6c113\u5360\u30441\u72fc1')
  app.jinja_env.globals['role_order']=('seer','hunter','medium','villager','wolf')
  top=client.get('/').data.decode()
  self.assertLess(top.index('id="seer-count"'),top.index('id="citizen-count"'))
  second=client.get('/game-tree?expand=1').json
  self.assertEqual(second['compositions'][0]['label'],'\u5360\u30441\u5e02\u6c113\u72fc1')
  self.assertEqual(first['village_win'],second['village_win']);self.assertEqual(first['snapshot'],second['snapshot'])
  html=client.get('/main').data.decode()
  self.assertNotIn('class="site-foot"',html);self.assertNotIn('tree-conditions',html);self.assertNotIn('data-tree-inspector',html)
  self.assertIn('data-tree-status',html);self.assertIn('tree-flow-frame',html);self.assertIn('data-tree-navigation="1"',html)
