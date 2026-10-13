import unittest,copy,json,re
from unittest.mock import patch
from dataclasses import replace
from app import create_app
from werewolf.exact import Strategy,initial_board,condition_claims,ClaimPolicy,build_tree,evaluate_tree,marginal_state,solve,Rules
from werewolf.seer_manual import replay
class DisclosureStrategyTests(unittest.TestCase):
 def setUp(self):
  self.a=create_app({'TESTING':True,'SECRET_KEY':'disclosure','HYBRID_TABLE_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True});self.c=self.a.test_client();self.c.post('/start',data={'citizens':'2','seers':'1','wolves':'2','day':'max','night':'max'})
 def g(self):
  with self.c.session_transaction() as q:return copy.deepcopy(q['game'])
 def settings(self,**fields):
  g=self.g();return self.c.post('/strategy',data={'revision':str(g['revision']),'day':g['policy']['day'],'night':g['policy']['night'],**fields})
 def report(self):
  g=self.g();p={'claims':['seer','seer','latent','latent','latent'],'seers':[{'day':1,'reporter':i,'target':3,'color':'white'} for i in (1,2)],'mediums':[]};self.assertEqual(self.c.post('/table-publish',data={'revision':str(g['revision']),'payload':json.dumps(p)}).status_code,200)
 def rate(self):return re.search(r'id="village-rate"[^>]*data-fraction="([^"]+)"',self.c.get('/main').get_data(as_text=True)).group(1)
 def advance(self,t):
  g=self.g();return self.c.post('/advance',data={'revision':str(g['revision']),'day':'max','night':'max','target':str(t)})
 def test_common_inheritance_and_explicit_role_override(self):
  s=Strategy(disclosure_common='none',seer_disclosure='all');self.assertEqual(s.disclosure_for('seer'),'all');self.assertEqual(s.disclosure_for('medium'),'none');self.assertEqual(s.disclosure_for('hunter'),'none')
  s=replace(s,disclosure_common='all',medium_disclosure='none');self.assertEqual(s.disclosure_for('seer'),'all');self.assertEqual(s.disclosure_for('medium'),'none')
  self.assertEqual(Strategy().disclosure_for('seer'),'all');self.assertEqual(Strategy().disclosure_for('medium'),'all')
 def test_all_none_all_switch_matches_information_fixed_and_keeps_input(self):
  self.report();self.assertEqual(self.rate(),'1/4');before=self.g();self.assertEqual(self.settings(disclosure_common='none',seer_disclosure='inherit',medium_disclosure='inherit').status_code,303)
  g=self.g();rules,p=replay(g);s=Strategy(**g['policy']);expected=evaluate_tree(build_tree(p.board,rules,s),s).board_value(build_tree(p.board,rules,s)).village_win;self.assertEqual(self.rate(),str(expected));self.assertEqual(self.rate(),'1/4');self.assertEqual(g['seer_inputs'],before['seer_inputs']);self.assertEqual(g['public_log']['batches'],before['public_log']['batches'])
  with patch('werewolf.seer_future_bridge.evaluate_game',side_effect=AssertionError('none must not acquire/use future scans')):self.assertEqual(self.c.get('/main').status_code,200)
  self.assertEqual(self.settings(seer_disclosure='all').status_code,303);self.assertEqual(self.rate(),'1/4');self.assertEqual(self.settings(disclosure_common='all',seer_disclosure='inherit').status_code,303);self.assertEqual(self.rate(),'1/4')
 def test_none_does_not_require_future_morning_reports_all_does(self):
  self.report();self.assertEqual(self.advance(4).status_code,303);self.assertEqual(self.advance(3).status_code,303);before=self.g();self.assertEqual(self.advance(2).status_code,400);self.assertEqual(self.g(),before)
  self.assertEqual(self.settings(disclosure_common='none').status_code,303);self.assertNotIn(b'data-seer-pending',self.c.get('/main').data);self.assertEqual(self.advance(2).status_code,303)
 def test_settings_roundtrip_history_back_and_cold_restore(self):
  self.report();self.settings(disclosure_common='none',seer_disclosure='all',medium_disclosure='none',seer_position=json.dumps(['unvisited','uniform']));expected=copy.deepcopy(self.g()['policy']);self.assertEqual(self.advance(4).status_code,303);self.assertEqual(self.g()['history'][0]['policy'],expected);self.settings(seer_disclosure='none');cookie=self.c.get_cookie('session');cold=self.a.test_client();cold.set_cookie('session',cookie.value);self.assertEqual(cold.get('/main').status_code,200)
  with cold.session_transaction() as q:self.assertEqual(q['game']['policy'],self.g()['policy'])
  self.c.post('/back',data={'revision':str(self.g()['revision'])});self.assertEqual(self.g()['policy'],expected)
 def test_invalid_disclosure_filters_and_unsupported_guard_are_atomic(self):
  before=self.g()
  for field,value in [('disclosure_common','white'),('seer_disclosure','secret'),('medium_disclosure','black'),('seer_position','["uniform","unvisited"]'),('seer_position','["nonrole","unvisited","uniform"]'),('hunter_disclosure','all')]:
   self.assertEqual(self.settings(**{field:value}).status_code,400);self.assertEqual(self.g(),before)
 def test_medium_none_skips_future_report_information(self):
  b=condition_claims(initial_board(5,1,1),('medium','medium','latent','latent','latent'),ClaimPolicy());s=Strategy(disclosure_common='none');root=build_tree(b,Rules(),s)
  with patch('werewolf.reports.public_value',side_effect=AssertionError('medium none must stay information fixed')):v=evaluate_tree(root,s).board_value(root)
  self.assertEqual(v,solve(5,'day',marginal_state(b),s))
  s=Strategy(disclosure_common='none',medium_disclosure='all');root=build_tree(b,Rules(),s)
  from werewolf.reports import public_value
  with patch('werewolf.reports.public_value',wraps=public_value) as f:evaluate_tree(root,s);self.assertTrue(f.called)
 def test_medium_none_does_not_generate_reports_inside_seer_forecast(self):
  from werewolf.seer_future_bridge import evaluate_game
  self.c.post('/start',data={'citizens':'1','mediums':'1','seers':'1','wolves':'2','day':'max','night':'max'});g=self.g()
  with patch('werewolf.seer_future_forecast.report_actions',side_effect=AssertionError('medium none must not disclose')):
   rules,p=replay(g);evaluate_game(g,p.board,rules,Strategy(medium_disclosure='none'))
 def test_policy_hashes_distinguish_effective_routes_and_order_is_stable(self):
  self.assertNotEqual(Strategy(),Strategy(seer_disclosure='none'));self.assertEqual(Strategy(seer_position=['unvisited','uniform']),Strategy());self.assertEqual(len({Strategy(),Strategy(disclosure_common='none'),Strategy(medium_disclosure='none')}),3)

 def test_full_co_only_zero_truth_support_is_inconsistent_and_atomic(self):
  g=self.g();p={'claims':['seer','latent','latent','latent','latent'],'seers':[],'mediums':[]};r=self.c.post('/table-publish',data={'revision':str(g['revision']),'payload':json.dumps(p)});self.assertEqual(r.status_code,400);self.assertIn('整合',r.get_json()['error']);self.assertEqual(self.g(),g)
  self.assertEqual(self.settings(disclosure_common='none').status_code,303);g=self.g();self.assertEqual(self.c.post('/table-publish',data={'revision':str(g['revision']),'payload':json.dumps(p)}).status_code,200);self.assertNotIn(b'data-seer-pending',self.c.get('/main').data)
 def test_ordered_position_policy_is_passed_to_future_acquisition_kernel(self):
  from werewolf.seer_future_bridge import evaluate_game
  from werewolf.seer_future_uniform import acquire_uniform
  self.report();g=self.g();rules,p=replay(g)
  with patch('werewolf.seer_future_forecast.acquire_uniform',wraps=acquire_uniform) as calls:
   evaluate_game(g,p.board,rules,Strategy(**g['policy']))
  self.assertTrue(calls.called);self.assertTrue(all(c.kwargs['position']==('unvisited','uniform') for c in calls.call_args_list))
 def test_fake_seer_item_policy_changes_rate_and_roundtrips(self):
  self.report();self.assertEqual(self.rate(),'1/4')
  self.assertEqual(self.settings(fake_seer_policy='["uniform"]').status_code,303);self.assertEqual(self.rate(),'3/8')
  cookie=self.c.get_cookie('session');cold=self.a.test_client();cold.set_cookie('session',cookie.value)
  self.assertIn(b'name="fake_seer_policy"',cold.get('/main').data)
  with cold.session_transaction() as q:self.assertEqual(list(q['game']['policy']['fake_seer_policy']),['uniform'])
  before=self.g();self.assertEqual(self.settings(fake_seer_policy='["uniform","noncontradictory"]').status_code,400);self.assertEqual(self.g(),before)
  self.assertEqual(self.settings(fake_seer_policy='["noncontradictory","uniform"]').status_code,303);self.assertEqual(self.rate(),'1/4')
