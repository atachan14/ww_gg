import unittest,json,copy,re
from app import create_app

class BoardLogUITests(unittest.TestCase):
 def setUp(self):
  self.app=create_app({'TESTING':True,'SECRET_KEY':'boardlog-ui-only'});self.c=self.app.test_client()
  self.c.post('/start',data={'citizens':'2','seers':'1','wolves':'2','day':'max','night':'max'})
 def g(self):
  with self.c.session_transaction() as s:return copy.deepcopy(s['game'])
 def publish(self,events):return self.c.post('/public-log',data={'revision':str(self.g()['revision']),'operation':'publish','payload':json.dumps({'mode':'simultaneous','events':events})})
 def events(self):return [{'kind':'co','player':1,'role':'seer'},{'kind':'seer','player':1,'day':1,'target':3,'color':'white'},{'kind':'co','player':2,'role':'seer'},{'kind':'seer','player':2,'day':1,'target':3,'color':'black'}]
 def test_permanent_boardlog_has_no_forms_or_instructions(self):
  html=self.c.get('/main').get_data(as_text=True);section=html.split('<section id="system-log"')[1].split('<dialog')[0]
  self.assertIn('>BoardLog</h3>',section);self.assertNotIn('<select',section);self.assertNotIn('<input',section);self.assertNotIn('<p',section);self.assertIn('data-public-open',section)
 def test_one_simultaneous_item_two_player_lines_with_combined_tokens(self):
  self.assertEqual(self.publish(self.events()).status_code,200)
  html=self.c.get('/main').get_data(as_text=True);self.assertEqual(html.count('data-public-batch="1"'),1)
  for p in (1,2):
   line=re.search(r'<div class="board-log-line" data-log-player="'+str(p)+r'">(.*?)</div>',html,re.S).group(1)
   self.assertIn('CO:占い師',line);self.assertIn('占い結果:Player3=',line);self.assertIn('を公開',line)
  self.assertNotIn('LogItem',html)
 def test_distinct_timing_items_and_edit_keep_id_order(self):
  self.publish(self.events());self.publish([{'kind':'co','player':1,'role':'seer'}])
  old=self.g();data={'mode':'simultaneous','events':self.events(),'replace':1}
  self.assertEqual(self.c.post('/public-log',data={'revision':str(old['revision']),'operation':'publish','payload':json.dumps(data)}).status_code,200)
  self.assertEqual([b['id'] for b in self.g()['public_log']['batches']],[1,2]);html=self.c.get('/main').get_data(as_text=True);self.assertLess(html.index('data-public-batch="1"'),html.index('data-public-batch="2"'))
 def test_legacy_baseline_is_not_labeled_simultaneous(self):
  self.publish(self.events());g=self.g();g.pop('public_log')
  with self.c.session_transaction() as s:s['game']=g
  html=self.c.get('/main').get_data(as_text=True);section=html.split('<section id="system-log"')[1].split('<dialog')[0]
  self.assertIn('旧保存：順序不明',section);self.assertNotIn('data-public-batch=',section);self.assertIn('data-legacy-open',section)
 def test_old_flat_draft_preserved_and_duplicate_publish_rejected(self):
  old=self.g();payload={'mode':'simultaneous','events':self.events()}
  self.assertEqual(self.c.post('/public-log',data={'revision':str(old['revision']),'operation':'draft','payload':json.dumps(payload)}).status_code,200)
  self.assertEqual(self.g()['public_draft']['payload'],payload);self.assertEqual(self.g()['revision'],old['revision'])
  invalid={'mode':'simultaneous','events':[self.events()[0],self.events()[0]]};before=self.g()
  self.assertEqual(self.c.post('/public-log',data={'revision':str(before['revision']),'operation':'publish','payload':json.dumps(invalid)}).status_code,400);self.assertEqual(self.g(),before)
