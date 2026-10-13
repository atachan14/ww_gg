import unittest,copy,json
from fractions import Fraction as F
from app import create_app
from werewolf.exact import Strategy,ClaimPolicy,initial_board,replace_worlds
from werewolf.seer_manual import replay
from werewolf.result_disclosure import condition_observed,MODEL,DisclosureInconsistent
from werewolf.seer_acquisition import from_board,Hypothesis
from werewolf.seer_future_uniform import TrueScanState,acquire_uniform
from werewolf.seer_future_forecast import future_publications,fake_backlog_options
class FullDisclosureObservedTests(unittest.TestCase):
 def setUp(self):
  self.a=create_app({'TESTING':True,'SECRET_KEY':'full-observed','HYBRID_TABLE_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True});self.c=self.a.test_client()
 def start(self,n=5,w=2,initial='random_white',cp='filled'):
  self.assertEqual(self.c.post('/start',data={'citizens':str(n-w-1),'seers':'1','wolves':str(w),'initial_seer':initial,'cco_seer':cp,'day':'max','night':'max'}).status_code,303)
 def g(self):
  with self.c.session_transaction() as q:return copy.deepcopy(q['game'])
 def table(self,p,preview=False):
  g=self.g();return self.c.post('/table-preview' if preview else '/table-publish',data={'revision':str(g['revision']),'board_id':g['public_log']['board_id'],'payload':json.dumps(p)})
 def co_only(self,p=1):
  g=self.g();return {'claims':['seer' if i==p else 'latent' for i in range(1,g['players']+1)],'seers':[],'mediums':[]}
 def advance(self,t):
  g=self.g();r=self.c.post('/advance',data={'revision':str(g['revision']),'target':str(t),'day':'max','night':'max'});self.assertEqual(r.status_code,303,r.data)
 def setting(self,**fields):
  g=self.g();return self.c.post('/strategy',data={'revision':str(g['revision']),'day':'max','night':'max',**fields})
 def test_day1_co_only_false_when_latent_truth_allowed_without_private_rescue(self):
  self.start(cp='none');self.assertEqual(self.table(self.co_only()).status_code,200);g=self.g();b=replay(g)[1].board;self.assertEqual(b.role_probability(1,'seer'),0);self.assertEqual(b.wolf_probability(1),1);h=self.c.get('/main').get_data(as_text=True);self.assertIn('id="village-rate" class="probability" data-fraction="1/3"',h);self.assertEqual(g['seer_inputs'],[])
 def test_all_worlds_removed_is_atomic_inconsistency(self):
  self.start();before=self.g();r=self.table(self.co_only());self.assertEqual(r.status_code,400);self.assertIn('整合する配役がありません',r.get_json()['error']);self.assertEqual(self.g(),before)
 def test_initial_none_day1_has_no_obligation(self):
  self.start(initial='none');self.assertEqual(self.table(self.co_only()).status_code,200);b=replay(self.g())[1].board;self.assertEqual(b.role_probability(1,'seer'),1);self.assertIn(b'id="village-rate"',self.c.get('/main').data)
 def test_none_override_retains_information_fixed_and_latent_truth(self):
  self.start(cp='none');self.assertEqual(self.setting(seer_disclosure='none').status_code,303);self.table(self.co_only());b=replay(self.g())[1].board;self.assertGreater(b.role_probability(1,'seer'),0)
  self.assertEqual(self.setting(seer_disclosure='inherit').status_code,303);self.assertEqual(replay(self.g())[1].board.role_probability(1,'seer'),0)
 def test_day2_late_co_unpublished_excludes_live_truth_but_keeps_dead_true(self):
  self.start();self.advance(1);self.advance(2);self.assertEqual(self.table(self.co_only(3)).status_code,200);b=replay(self.g())[1].board;self.assertEqual(b.role_probability(2,'seer'),1);self.assertEqual(b.role_probability(3,'seer'),0);self.assertEqual(b.wolf_probability(3),1);self.assertIn(b'id="village-rate" class="probability" data-fraction="1"',self.c.get('/main').data)
 def test_late_co_requires_initial_backlog_even_if_current_report_present(self):
  self.start();self.advance(1);self.advance(2);p=self.co_only(3);p['seers']=[{'day':2,'reporter':3,'target':5,'color':'black'}];self.assertEqual(self.table(p).status_code,200);self.assertEqual(replay(self.g())[1].board.role_probability(3,'seer'),0)
 def test_true_co_dead_before_morning_is_not_required_to_report_after_death(self):
  self.start(7,1);p=self.co_only();p['seers']=[{'day':1,'reporter':1,'target':4,'color':'white'}];self.table(p);self.advance(2);self.advance(1);b=replay(self.g())[1].board;self.assertNotIn(1,b.alive);self.assertEqual(b.role_probability(1,'seer'),1);self.assertIn(b'id="village-rate"',self.c.get('/main').data)
 def test_arrival_zero_support_is_editable_without_any_probability_numbers(self):
  self.start();p={'claims':['seer','seer','latent','latent','latent'],'seers':[{'day':1,'reporter':i,'target':3,'color':'white'} for i in (1,2)],'mediums':[]};self.table(p);self.advance(4);self.advance(3);h=self.c.get('/main').get_data(as_text=True);self.assertIn('不整合',h);self.assertNotIn('data-fraction=',h);g=self.g();p['seers'].append({'day':2,'reporter':1,'target':5,'color':'white'});self.assertEqual(self.table(p).status_code,200);b=replay(self.g())[1].board;self.assertEqual(b.role_probability(2,'seer'),0);self.assertIn(b'id="village-rate"',self.c.get('/main').data)
 def test_nonuniform_compatible_prior_preserved(self):
  b=replace_worlds(initial_board(5,2,0,1,experimental_cast=True),((5,0,2,0,F(3,4)),(17,0,4,0,F(1,4))));claims=('latent','latent','seer','latent','latent');g={'players':5,'rules':{'initial_seer':'random_white'},'history':[],'seer_inputs':[{'day':1,'reporter':3,'target':4,'color':'white'}],'result_disclosure_model':MODEL};r=condition_observed(g,b,claims,ClaimPolicy(seer='none'),{});self.assertEqual(r.worlds,b.worlds)
 def test_true_fake_backlog_same_days_and_no_report_count_truth_leak(self):
  b=replace_worlds(initial_board(5,2,0,1,experimental_cast=True),((9,0,2,0,F(3,4)),(10,0,1,0,F(1,4))));s=acquire_uniform(TrueScanState(from_board(b),initial_rule='random_white',tracked=(1,2)),b.alive);self.assertEqual(s.public_roles,tuple(sorted(b.worlds)));s=acquire_uniform(s,(1,2,3,5));branches=future_publications(s,(),(1,2,5),('seer','seer','latent','latent','latent'));self.assertEqual(sum(v.probability for v in branches),1);self.assertTrue(all({(r.player,r.acquired_day) for r in v.reports}=={(1,1),(1,2),(2,1),(2,2)} for v in branches));self.assertTrue(any(len(v.state.public_roles)>1 for v in branches))
  for v in branches:
   for r in v.reports:self.assertNotEqual(r.target,r.player);self.assertIn(r.target,s.rosters[r.acquired_day-1])
 def test_initial_none_fake_does_not_invent_day1_and_world_plan_mass_one(self):
  s=acquire_uniform(TrueScanState((Hypothesis((9,0,2,0),(),F(1)),),initial_rule='none',tracked=(1,2)),(1,2,3,4,5));s=acquire_uniform(s,(1,2,3,5));options=fake_backlog_options(s,(1,),());self.assertEqual(sum(q for _,q in options),1);self.assertTrue(all(all(r.acquired_day==2 for r in rs) for rs,q in options))
 def test_full_medium_current_missing_excludes_true_medium(self):
  self.c.post('/start',data={'citizens':'4','mediums':'1','wolves':'1','cco_medium':'none','day':'max','night':'max'});g=self.g();p={'claims':['medium','latent','latent','latent','latent','latent'],'seers':[],'mediums':[]};self.assertEqual(self.table(p).status_code,200);self.advance(2);self.advance(3);h=self.c.get('/main').get_data(as_text=True);self.assertIn('id="village-rate" class="probability" data-fraction="1"',h)

 def test_closed_full_co_omission_survives_later_withdrawal(self):
  self.start(cp='none');self.table(self.co_only());self.advance(3);g=self.g();p={'claims':['latent']*5,'seers':[],'mediums':[]};self.assertEqual(self.table(p).status_code,200);b=replay(self.g())[1].board;self.assertEqual(b.wolf_probability(1),1);self.assertEqual(b.claims[0],'latent')
 def test_medium_dead_before_first_report_has_no_posthumous_obligation(self):
  self.c.post('/start',data={'citizens':'4','mediums':'1','wolves':'1','day':'max','night':'max'});p={'claims':['medium','latent','latent','latent','latent','latent'],'seers':[],'mediums':[]};self.table(p);self.advance(2);self.advance(1);h=self.c.get('/main').get_data(as_text=True);self.assertIn(b'id="village-rate"',h.encode());self.assertNotIn('不整合:',h)

 def test_direct_unfiltered_truth_cannot_be_rescued_with_private_initialization(self):
  from werewolf.seer_future_bridge import evaluate_game
  from werewolf.seer_future_uniform import FuturePending
  from werewolf.exact import condition_claims,Rules
  b=condition_claims(initial_board(5,2,0,1,experimental_cast=True),('seer','latent','latent','latent','latent'),ClaimPolicy(seer='none'));g={'players':5,'rules':{'initial_seer':'random_white'},'seer_options':{'initial_rule':'random_white'},'seer_inputs':[]};r=evaluate_game(g,b,Rules(),Strategy());self.assertIsInstance(r,FuturePending);self.assertEqual(r.reason,'full_disclosure_truth_not_conditioned')

 def test_legacy_history_is_not_assigned_unrecorded_full_obligation(self):
  old=create_app({'TESTING':True,'SECRET_KEY':'full-observed','HYBRID_TABLE_PREVIEW':True}).test_client();old.post('/start',data={'citizens':'5','seers':'1','wolves':'1','day':'max','night':'max'})
  with old.session_transaction() as q:g=copy.deepcopy(q['game'])
  old.post('/table-publish',data={'revision':str(g['revision']),'payload':json.dumps({'claims':['seer']+['latent']*6,'seers':[],'mediums':[]})})
  for t in (2,1):
   with old.session_transaction() as q:g=copy.deepcopy(q['game'])
   old.post('/advance',data={'revision':str(g['revision']),'target':str(t),'day':'max','night':'max'})
  cookie=old.get_cookie('session');self.c.set_cookie('session',cookie.value);h=self.c.get('/main');self.assertEqual(h.status_code,200);b=replay(self.g())[1].board;self.assertEqual(b.role_probability(1,'seer'),1);self.assertNotIn('不整合:'.encode(),h.data)
 def test_observation_model_in_history_and_branch_identity(self):
  from werewolf.board_owned_log import signature
  self.start(cp='none');self.table(self.co_only());self.advance(3);step=self.g()['history'][0];self.assertEqual(step['result_disclosure_model'],MODEL);old=copy.deepcopy(step);old.pop('result_disclosure_model');self.assertNotEqual(signature(step),signature(old))
