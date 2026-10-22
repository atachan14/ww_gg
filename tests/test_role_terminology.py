import unittest
from app import create_app
from werewolf.exact import ROLES,ROLE_LABELS
from werewolf.co_ui import CO_LABELS

class RoleTerminologyTests(unittest.TestCase):
 def test_role_labels_change_but_serialized_role_keys_and_faction_do_not(self):
  self.assertEqual(ROLE_LABELS['wolf'],'人狼');self.assertEqual(CO_LABELS['wolf'],'人狼')
  self.assertEqual(ROLES,('villager','medium','seer','hunter','wolf'))
  app=create_app(dict(TESTING=True,SECRET_KEY='role-terminology',GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True))
  client=app.test_client();setup=client.get('/').get_data(as_text=True)
  self.assertIn('<span>人狼</span>',setup);self.assertIn('狼陣営',setup);self.assertNotIn('人狼陣営',setup)
  client.post('/start',data=dict(citizens='3',seers='1',wolves='1',day='max',night='max',fake_reports='max'))
  main=client.get('/main').get_data(as_text=True)
  self.assertIn('人狼1',main);self.assertIn('<th>人狼<small>狼陣営</small>',main)
  self.assertIn('村 / 狼',main);self.assertNotIn('人狼陣営',main)
  with client.session_transaction() as session:
   self.assertEqual(session['game']['wolves'],1);self.assertEqual(session['game']['claims'],['latent']*5)
  root=client.get('/game-tree?expand=1').json
  self.assertEqual(root['compositions'][0]['label'],'市民3占い1人狼1')
  self.assertEqual(root['village_win'],'7/15')
