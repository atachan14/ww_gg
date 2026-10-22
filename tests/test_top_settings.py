import unittest,json,re,html
from copy import deepcopy
from app import create_app
from werewolf.strategy_ui import co_editor

class TopSettingsTests(unittest.TestCase):
 def setUp(self):self.client=create_app(dict(TESTING=True,SECRET_KEY='top-settings')).test_client()
 def state(self):
  with self.client.session_transaction() as s:return deepcopy(s.get('game'))
 def seed(self,response):
  text=response.get_data(as_text=True);return json.loads(html.unescape(text.split("data-seed="+chr(39),1)[1].split(chr(39),1)[0]))
 def form(self):
  return dict(citizens='3',seers='1',wolves='1',day='random',night='random',fake_reports='random',win_cutoff='0',include_self_bite='0',initial_seer='random_white',allow_repeat_guard='0',allow_self_bite='0',model='group',strategy_ui=json.dumps(co_editor({})),seer_position=json.dumps(['unvisited','uniform']),guard_position=json.dumps(['uniform']),fake_seer_policy=json.dumps(['uniform']),disclosure_common='all',seer_disclosure='inherit',medium_disclosure='inherit')
 def test_same_order_shared_markup_default_and_external_display_form(self):
  response=self.client.get('/');text=response.get_data(as_text=True);seed=self.seed(response)
  self.assertEqual(re.findall(r'data-settings-pane="([^"]+)"',text),['display','rules','strategy'])
  self.assertTrue(seed['setup']);self.assertTrue(seed['policy']['win_cutoff']);self.assertFalse(seed['finished'])
  self.assertIn('form="display-options-form"',text);self.assertEqual(text.count('id="display-options-form"'),1)
  self.assertEqual(text.count('name="day"'),1);self.assertEqual(text.count('name="win_cutoff"'),1)
  self.assertIsNone(self.state())
 def test_transfer_and_restore_without_modifying_current_game(self):
  data=self.form();editor=co_editor({});editor['common']=['filled','counter'];data['strategy_ui']=json.dumps(editor)
  self.assertEqual(self.client.post('/start',data=data).status_code,303)
  saved=self.state();self.assertEqual(saved['policy']['day'],'random');self.assertFalse(saved['policy']['win_cutoff'])
  self.assertEqual(saved['strategy_ui']['common'],['counter','filled']);self.assertEqual(saved['rules']['allow_repeat_guard'],False)
  top=self.client.get('/');seed=self.seed(top)
  self.assertEqual(seed['policy']['fake_seer_policy'],['uniform']);self.assertEqual(seed['policy']['night'],'random')
  self.assertEqual(seed['co'],saved['strategy_ui']);self.assertFalse(seed['policy']['win_cutoff']);self.assertEqual(seed['roles'],['villager','seer','wolf'])
  self.assertEqual(self.state(),saved)
  main=self.client.get('/main');self.assertEqual(main.status_code,200)
  self.assertEqual(re.findall(r'data-settings-pane="([^"]+)"',main.get_data(as_text=True)),['display','rules','strategy'])
 def test_invalid_cast_preserves_valid_strategy_draft_and_game_atomically(self):
  self.client.post('/start',data=self.form());saved=self.state();bad=self.form();bad['citizens']='20'
  response=self.client.post('/start',data=bad);self.assertEqual(response.status_code,400)
  self.assertEqual(self.seed(response)['policy']['day'],'random');self.assertFalse(self.seed(response)['policy']['win_cutoff'])
  self.assertIn('value="20"',response.get_data(as_text=True));self.assertEqual(self.state(),saved)
 def test_reject_duplicate_or_ambiguous_CO_payload_without_mutating_game(self):
  self.client.post('/start',data=self.form());saved=self.state()
  for change in [dict(strategy_ui='{}'),dict(cco_villager='none')]:
   bad={**self.form(),**change};self.assertEqual(self.client.post('/start',data=bad).status_code,400);self.assertEqual(self.state(),saved)
