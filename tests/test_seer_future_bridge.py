import unittest,json,copy
from app import create_app
from werewolf.seer_manual import replay
from werewolf.seer_future_bridge import evaluate_game
from werewolf.exact import Strategy
from werewolf.seer_future_uniform import FuturePending

class FutureBridgeTests(unittest.TestCase):
 def setUp(self):self.app=create_app({'TESTING':True,'SECRET_KEY':'future-bridge','SEER_UNIFORM_FUTURE_PREVIEW':True});self.c=self.app.test_client()
 def g(self):
  with self.c.session_transaction() as s:return copy.deepcopy(s['game'])
 def start(self,n=5,w=2,s=1):self.c.post('/start',data={'citizens':str(n-w-s),'seers':str(s),'wolves':str(w),'day':'max','night':'max'})
 def publish(self,events):return self.c.post('/public-log',data={'revision':str(self.g()['revision']),'operation':'publish','payload':json.dumps({'mode':'simultaneous','events':events})})
 def test_local_preview_reaches_night_day2_and_terminal(self):
  self.start();self.assertEqual(self.publish([{'kind':'co','player':1,'role':'seer'},{'kind':'co','player':2,'role':'seer'},{'kind':'seer','player':1,'day':1,'target':3,'color':'white'},{'kind':'seer','player':2,'day':1,'target':3,'color':'black'}]).status_code,200)
  html=self.c.get('/main').data;self.assertIn(b'data-seer-future="all"',html);self.assertIn(b'id="village-rate"',html)
  for target in (2,3):
   g=self.g();self.assertEqual(self.c.post('/advance',data={'revision':str(g['revision']),'day':'max','night':'max','target':str(target)}).status_code,303)
  html=self.c.get('/main').data;self.assertIn(b'data-seer-pending',html);self.assertNotIn(b'id="village-rate"',html)
  self.assertEqual(self.publish([{'kind':'seer','player':1,'day':2,'target':4,'color':'black'}]).status_code,200)
  self.assertIn(b'id="village-rate"',self.c.get('/main').data)
  g=self.g();self.c.post('/advance',data={'revision':str(g['revision']),'day':'max','night':'max','target':'4'});self.assertEqual(self.c.get('/result').status_code,200)
 def test_developer_preview_flag_does_not_switch_model_a_display(self):
  self.start();g=self.g();self.app.config['SEER_UNIFORM_FUTURE_PREVIEW']=False
  self.assertIn(b'data-seer-future="all"',self.c.get('/main').data);self.assertEqual(self.g(),g)
 def test_current_morning_missing_excludes_truth_and_keeps_dead_truth(self):
  self.start(5,1,1)
  for t in (2,3):
   g=self.g();self.c.post('/advance',data={'revision':str(g['revision']),'day':'max','night':'max','target':str(t)})
  self.assertEqual(self.publish([{'kind':'co','player':1,'role':'seer'}]).status_code,200);g=self.g();rules,p=replay(g);self.assertEqual(p.board.role_probability(1,'seer'),0);self.assertEqual(p.board.wolf_probability(1),1);result=evaluate_game(g,p.board,rules,Strategy());self.assertNotIsInstance(result,FuturePending);self.assertEqual(result.village_win,1)
 def test_incomplete_all_open_day1_is_inconsistent_not_pending(self):
  self.start();old=self.g();r=self.publish([{'kind':'co','player':1,'role':'seer'}]);self.assertEqual(r.status_code,400);self.assertIn('整合',r.get_json()['error']);self.assertEqual(self.g(),old)
 def test_no_initial_rule_allows_no_true_initial_publication(self):
  self.c.post('/start',data={'citizens':'2','seers':'1','wolves':'2','initial_seer':'none','day':'max','night':'max'})
  self.publish([{'kind':'co','player':1,'role':'seer'}]);self.assertIn(b'id="village-rate"',self.c.get('/main').data)

 def test_dead_report_correction_changes_cumulative_not_discarded(self):
  self.start();events=[{'kind':'co','player':1,'role':'seer'},{'kind':'co','player':2,'role':'seer'},{'kind':'seer','player':1,'day':1,'target':3,'color':'white'},{'kind':'seer','player':2,'day':1,'target':3,'color':'black'}];self.publish(events)
  g=self.g();self.c.post('/advance',data={'revision':str(g['revision']),'day':'max','night':'max','target':'2'});old=self.g();self.assertEqual(len(old['seer_inputs']),2)
  self.assertIn(b'id="cumulative-village-rate" class="probability" data-fraction="1/2"',self.c.get('/main').data)
  events[-1]['color']='white'
  rejected=self.c.post('/public-log',data={'revision':str(old['revision']),'operation':'publish','payload':json.dumps({'mode':'simultaneous','events':events,'replace':1})});self.assertEqual(rejected.status_code,400);self.assertEqual(self.g(),old)
  self.c.post('/back',data={'revision':str(old['revision'])});owner=self.g();r=self.c.post('/public-log',data={'revision':str(owner['revision']),'operation':'publish','payload':json.dumps({'mode':'simultaneous','events':events,'replace':1})});self.assertEqual(r.status_code,200,r.data)
  self.assertFalse(self.g()['public_log']['board_graph']['nodes'][old['public_log']['board_id']]['active'])
  owner=self.g();self.c.post('/advance',data={'revision':str(owner['revision']),'day':'max','night':'max','target':'2'})
  html=self.c.get('/main').data;self.assertIn(b'id="village-rate" class="probability" data-fraction="1/2"',html);self.assertIn(b'id="cumulative-village-rate" class="probability" data-fraction="1/4"',html);self.assertEqual(self.g()['seer_inputs'][-1]['reporter'],2)
 def test_seven_player_known_fake_family_evaluates_without_five_player_gate(self):
  self.start(7,2,1);self.publish([{'kind':'co','player':1,'role':'seer'},{'kind':'co','player':2,'role':'seer'},{'kind':'seer','player':1,'day':1,'target':3,'color':'white'},{'kind':'seer','player':2,'day':1,'target':3,'color':'black'}]);g=self.g();rules,p=replay(g);result=evaluate_game(g,p.board,rules,Strategy());self.assertNotIsInstance(result,FuturePending);self.assertEqual(str(result.village_win),'1/2')

 def test_two_surviving_co_unknown_truth_joint_vectors_and_pending(self):
  from fractions import Fraction as F
  from werewolf.seer_acquisition import Hypothesis,Acquisition,SeerReport
  from werewolf.seer_future_uniform import TrueScanState,acquire_uniform
  from werewolf.seer_future_forecast import future_publications,project_private
  self.start();events=[{'kind':'co','player':p,'role':'seer'} for p in (1,2)]+[{'kind':'seer','player':p,'day':1,'target':3,'color':'white'} for p in (1,2)];self.publish(events)
  for target in (4,3):
   g=self.g();self.assertEqual(self.c.post('/advance',data={'revision':str(g['revision']),'target':str(target),'day':'max','night':'max'}).status_code,303)
  g=self.g();rules,progress=replay({**g,'result_disclosure_model':None});morning=progress.board
  self.assertEqual(morning.alive,(1,2,5));self.assertEqual({w[0] for w in morning.worlds},{9,10});self.assertEqual({w[-1] for w in morning.worlds},{F(1,2)})
  prior=TrueScanState(tuple(Hypothesis(w[:-1],(Acquisition(1,1 if w[2]==1 else 2,3,'white'),),w[-1]) for w in morning.worlds),((1,2,3,4,5),))
  generated=acquire_uniform(prior,(1,2,3,5));past=tuple(SeerReport(1,1,p,3,'white') for p in (1,2));branches=future_publications(generated,past,morning.alive,morning.claims)
  # Three legal targets per reporter now include corpse4: 3*3 vectors.
  self.assertEqual(len(branches),9);self.assertEqual(sum(v.probability for v in branches),1);self.assertEqual({v.probability for v in branches},{F(1,9)})
  self.assertTrue(any(r.target==4 and r.color=='black'for v in branches for r in v.reports))
  # Public vector shared by both truth owners is grouped, not selected using secrets.
  common=next(v for v in branches if {(r.player,r.target,r.color) for r in v.reports}=={(1,2,'black'),(2,1,'black')})
  self.assertEqual(common.probability,F(1,9));self.assertEqual({w[0] for w in common.state.public_roles},{9,10});self.assertEqual({w[-1] for w in common.state.public_roles},{F(1,2)})
  # Generated fakes avoid publicly impossible black on citizen5; manual input
  # below deliberately remains free to report such a contradiction.
  self.assertTrue(all(r.color=='white' for v in branches for r in v.reports if r.target==5))
  self.assertTrue(all(len(v.state.public_roles)==2 for v in branches))
  html=self.c.get('/main').data;self.assertIn(b'data-seer-pending',html);self.assertNotIn(b'id="village-rate"',html)
  self.publish([{'kind':'seer','player':1,'day':2,'target':5,'color':'white'}]);self.assertIn(b'id="village-rate"',self.c.get('/main').data);self.assertEqual(replay(self.g())[1].board.role_probability(2,'seer'),0)
  self.publish([{'kind':'seer','player':2,'day':2,'target':5,'color':'black'}]);complete=self.g();rules,p=replay(complete);self.assertEqual({w[0] for w in p.board.worlds},{10});self.assertIn(b'id="village-rate"',self.c.get('/main').data)
  self.app.config['SEER_UNIFORM_FUTURE_PREVIEW']=False;self.assertIn(b'data-seer-future="all"',self.c.get('/main').data);self.assertEqual(self.g(),complete)
