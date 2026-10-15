import copy,json,unittest,os,importlib,sys
from unittest.mock import patch
from app import create_app
class FutureReleaseTests(unittest.TestCase):
 def test_production_entrypoint_enables_both_features_without_changing_secret_contract(self):
  with patch.dict(os.environ,{'WW_GG_SECRET_KEY':'0123456789abcdef'*4}):
   sys.modules.pop('wsgi',None);a=importlib.import_module('wsgi').app
  self.assertTrue(a.config['HYBRID_TABLE_PREVIEW']);self.assertTrue(a.config['SEER_UNIFORM_FUTURE_PREVIEW']);self.assertTrue(a.config['SESSION_COOKIE_SECURE'])
 def test_multiple_fake_preview_is_pending_not_false_win_and_does_not_commit(self):
  a=create_app({'TESTING':True,'SECRET_KEY':'release-multiple','HYBRID_TABLE_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True});c=a.test_client();c.post('/start',data={'citizens':'4','seers':'1','wolves':'2','day':'max','night':'max'})
  with c.session_transaction() as q:before=copy.deepcopy(q['game'])
  p={'claims':['seer']*3+['latent']*4,'seers':[{'day':1,'reporter':i,'target':6,'color':'white'} for i in (1,2,3)],'mediums':[]};r=c.post('/table-preview',data={'revision':str(before['revision']),'board_id':before['public_log']['board_id'],'payload':json.dumps(p)})
  self.assertEqual(r.status_code,200);h=r.get_json()['html'];self.assertIn('data-seer-pending',h);self.assertIn('共同報告は未対応',h);self.assertNotIn('id="village-rate"',h)
  with c.session_transaction() as q:self.assertEqual(q['game'],before)
 def test_limits_fixed_co_and_supported_guard_scope_are_visible(self):
  a=create_app({'TESTING':True,'SECRET_KEY':'release-scope','HYBRID_TABLE_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True});c=a.test_client();c.post('/start',data={'citizens':'3','seers':'1','mediums':'1','hunters':'1','wolves':'1','day':'max','night':'max'});h=c.get('/help/specs').get_data(as_text=True);self.assertIn('COは現在の宣言に固定',h);self.assertIn('狩人1人が公開情報で確定',h);self.assertIn('狩人未確定でも昼均等・護衛均等・狼襲撃最大化に対応',h);self.assertIn('占霊・公開報告を含む新経路maxや同時複数maxの一般化は別途未対応',h);self.assertIn('計算予算・期限到達はPending',h)

 def test_nested_future_work_budgets_cannot_reset_parent_time_deadline(self):
  from werewolf.calculation_budget import calculation_budget,tick,CalculationBudgetExceeded
  with patch('werewolf.calculation_budget.monotonic',side_effect=[10,10.5,11.1]):
   with calculation_budget(100,max_seconds=1):
    tick()
    with calculation_budget(250000):
     with self.assertRaises(CalculationBudgetExceeded):tick()
 def test_deadline_reached_returns_pending_not_partial_zero(self):
  a=create_app({'TESTING':True,'SECRET_KEY':'release-deadline','HYBRID_TABLE_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True});c=a.test_client();c.post('/start',data={'citizens':'2','seers':'1','wolves':'2','day':'max','night':'max'})
  with patch('werewolf.calculation_budget.monotonic',side_effect=lambda: self._clock_tick()):
   self.clock=0;h=c.get('/main').get_data(as_text=True)
  self.assertIn('data-seer-pending',h);self.assertNotIn('id="village-rate"',h)
 def _clock_tick(self):
  self.clock+=21;return self.clock
