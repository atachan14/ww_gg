import copy,json,re,unittest
from fractions import Fraction as F
from app import create_app
from werewolf.exact import initial_board,replace_worlds
from werewolf.seer_manual import condition,replay
class HandCompatibilityTests(unittest.TestCase):
 def test_day2_dead_and_live_seer_candidates_half_with_preview_and_co_table(self):
  a=create_app({'TESTING':True,'SECRET_KEY':'manual-compatibility','HYBRID_TABLE_PREVIEW':True});c=a.test_client();self.assertEqual(c.post('/start',data={'citizens':'2','seers':'1','wolves':'2','day':'max','night':'max'}).status_code,303)
  def game():
   with c.session_transaction() as q:return copy.deepcopy(q['game'])
  for target in (1,2):
   g=game();self.assertEqual(c.post('/advance',data={'revision':str(g['revision']),'day':'max','night':'max','target':str(target)}).status_code,303)
  g=game();payload={'claims':['latent','latent','seer','latent','latent'],'seers':[{'day':1,'reporter':3,'target':4,'color':'white'},{'day':2,'reporter':3,'target':5,'color':'black'}],'mediums':[]};data={'revision':str(g['revision']),'board_id':g['public_log']['board_id'],'request_id':'1','payload':json.dumps(payload)}
  preview=c.post('/table-preview',data=data);self.assertEqual(preview.status_code,200);self.assertEqual(game(),g);self.assertIn('data-fraction="1/2"',preview.get_json()['html']);self.assertEqual(c.post('/table-publish',data=data).status_code,200)
  b=replay(game())[1].board
  for player in (2,3):self.assertEqual(b.role_probability(player,'seer'),F(1,2))
  for player in (2,5):self.assertEqual(b.role_probability(player,'villager'),F(1,2))
  self.assertEqual(b.wolf_probability(1),1);self.assertEqual(b.role_probability(4,'villager'),1);self.assertEqual({w[-1] for w in b.worlds},{F(1,2)});self.assertEqual(len(b.worlds),2)
  html=c.get('/main').get_data(as_text=True);self.assertIn('id="village-rate" class="probability" data-fraction="1/2"',html);self.assertNotIn('<th>霊能</th>',html);self.assertIn('<th>占い師</th>',html);self.assertIn('<td>占い師</td>',html)
 def test_nonuniform_prior_is_preserved_without_true_fake_asymmetry(self):
  b=replace_worlds(initial_board(5,2,0,1,experimental_cast=True),((5,0,2,0,F(3,4)),(17,0,4,0,F(1,4))))
  rows=({'day':1,'reporter':3,'target':4,'color':'white'},)
  result=condition(b,rows,{'initial_rule':'random_white','likelihood':'compatibility'},b.alive);self.assertEqual(result.worlds,b.worlds)
 def test_random_white_true_black_and_illegal_white_still_excluded(self):
  b=replace_worlds(initial_board(5,2,0,1,experimental_cast=True),((5,0,2,0,F(3,4)),(17,0,4,0,F(1,4))))
  for row in ({'day':1,'reporter':3,'target':5,'color':'black'},{'day':1,'reporter':3,'target':3,'color':'white'}):
   result=condition(b,(row,),{'initial_rule':'random_white','likelihood':'compatibility'},b.alive);self.assertEqual(result.worlds,((5,0,2,0,F(1)),))
