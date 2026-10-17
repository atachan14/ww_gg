import unittest,concurrent.futures,threading
from unittest.mock import patch
from werewolf.calculation_budget import calculation_budget,tick,CalculationBudgetExceeded,budget_stop,reset_diagnostics,DEFAULT_MAX_SECONDS,DEFAULT_MAX_WORK
from app import create_app

class ExtendedBudgetTests(unittest.TestCase):
 def setUp(self):reset_diagnostics()
 def test_nested_work_cannot_reset_parent_and_kind_is_recorded(self):
  with calculation_budget(3):
   tick(2)
   with calculation_budget(100):
    with self.assertRaises(CalculationBudgetExceeded) as raised:tick(2)
  self.assertEqual(raised.exception.kind,'work');self.assertEqual(budget_stop()['work'],4)
 def test_nested_time_uses_earliest_deadline(self):
  with patch('werewolf.calculation_budget.monotonic',side_effect=[10,10.5,11.1]):
   with calculation_budget(100,max_seconds=1):
    with calculation_budget(100,max_seconds=100):
     with self.assertRaises(CalculationBudgetExceeded) as raised:tick()
  self.assertEqual(raised.exception.kind,'time')
 def test_independent_thread_budgets_do_not_share_counts(self):
  def run(limit):
   reset_diagnostics()
   with calculation_budget(limit):
    tick(limit)
    self.assertIsNone(budget_stop())
   return limit
  with concurrent.futures.ThreadPoolExecutor(2) as pool:self.assertEqual(list(pool.map(run,(2,5))),[2,5])
 def client(self,**config):
  app=create_app({'TESTING':True,'SECRET_KEY':'budget-fixture',**config});c=app.test_client();c.post('/start',data={'citizens':'4','wolves':'1','day':'max','night':'max'});return app,c
 def test_work_stop_display_and_no_secret_log(self):
  app,c=self.client(MANUAL_CALC_MAX_WORK=1)
  with self.assertLogs('wwgg.budget',level='WARNING') as logs:r=c.get('/main')
  self.assertIn('作業量',r.get_data(as_text=True));self.assertNotIn('id="village-rate"',r.get_data(as_text=True));self.assertTrue(any('kind=work' in x for x in logs.output));self.assertFalse(any('session=' in x or 'hypotheses' in x for x in logs.output))
 def test_time_stop_display(self):
  app,c=self.client(MANUAL_CALC_MAX_SECONDS=1)
  with patch('werewolf.calculation_budget.monotonic',side_effect=lambda: self.clock()):
   self.now=0;r=c.get('/main')
  self.assertIn('計算時間',r.get_data(as_text=True));self.assertNotIn('id="village-rate"',r.get_data(as_text=True))
 def clock(self):self.now+=2;return self.now
 def test_defaults_and_forecast_still_exact(self):
  self.assertEqual((DEFAULT_MAX_WORK,DEFAULT_MAX_SECONDS),(4000000,270));app,c=self.client();r=c.get('/main');self.assertIn('data-fraction="7/15"',r.get_data(as_text=True));self.assertIn('最大約5分',r.get_data(as_text=True));self.assertIn('最大約5分',c.get('/').get_data(as_text=True))

 def test_concurrent_requests_use_one_slot_and_release_after_error(self):
  import time
  app=create_app({'TESTING':True,'SECRET_KEY':'concurrency-fixture'});active=0;peak=0;guard=threading.Lock()
  def view():
   nonlocal active,peak
   with guard:active+=1;peak=max(peak,active)
   time.sleep(0.02)
   with guard:active-=1
   return 'ok'
  app.view_functions['main']=view
  def request(_):
   with app.test_client() as client:return client.get('/main').status_code
  with concurrent.futures.ThreadPoolExecutor(2) as pool:self.assertEqual(list(pool.map(request,range(2))),[200,200])
  self.assertEqual(peak,1)
  def stopped():
   with calculation_budget(1):tick(2)
  app.view_functions['main']=stopped
  self.assertEqual(app.test_client().get('/main').status_code,503)
  app.view_functions['main']=view;self.assertEqual(app.test_client().get('/main').status_code,200)

 def test_failed_post_retains_previous_saved_game(self):
  from flask import session
  app,c=self.client()
  with c.session_transaction() as saved:before=dict(saved)
  def failed():
   session['game']={'invalid':'partial write'}
   with calculation_budget(1):tick(2)
  app.view_functions['start']=failed
  self.assertEqual(c.post('/start').status_code,503)
  with c.session_transaction() as saved:self.assertEqual(dict(saved),before)
