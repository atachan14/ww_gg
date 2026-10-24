import copy,json,time,unittest
from threading import Event,Thread
from unittest.mock import patch
from app import create_app
from werewolf.board_flow import RoleState
from werewolf.calculation_budget import tick
from werewolf.calculation_jobs import CalculationJobs

class CalculationCancellationTests(unittest.TestCase):
 def test_owner_isolation_early_cancel_repeat_and_cleanup(self):
  jobs=CalculationJobs();token='a'*32
  first=jobs.begin('one',token)
  self.assertFalse(jobs.cancel('two',token));self.assertFalse(first.is_set())
  self.assertTrue(jobs.cancel('one',token));self.assertTrue(first.is_set())
  self.assertTrue(jobs.cancel('one',token));jobs.finish('one',token,first)
  self.assertFalse(jobs.active)
  self.assertTrue(jobs.begin('one',token).is_set())
  fresh=jobs.begin('one','b'*32);self.assertFalse(fresh.is_set())
  jobs.finish('one','b'*32,fresh)
 def run_cancel(self,streaming,path="/main"):
  app=create_app({'TESTING':True,'SECRET_KEY':'cancel-test-only'})
  client=app.test_client();client.post('/start',data={'citizens':'4','wolves':'1','day':'max','night':'max'})
  client.get('/main',headers={'Sec-Fetch-Dest':'document'})
  with client.session_transaction() as s:before=copy.deepcopy(s['game'])
  cookie=client.get_cookie('session').value
  started=Event();stopped=Event();outcome={};original=RoleState.forecast
  def heavy(owner,**kw):
   started.set()
   try:
    deadline=time.monotonic()+4
    while time.monotonic()<deadline:tick(0);time.sleep(.001)
    return original(owner,**kw)
   finally:stopped.set()
  def request():
   c=app.test_client();c.set_cookie('session',cookie)
   headers={'X-WW-Calculation-ID':'c'*32}
   if streaming:headers['Accept']='application/x-ndjson'
   with c.get(path,headers=headers,buffered=False) as r:
    outcome['status']=r.status_code;outcome['body']=b''.join(r.response)
  if path=='/game-tree':
   endpoint=next(rule.endpoint for rule in app.url_map.iter_rules() if rule.rule=='/game-tree')
   app.view_functions[endpoint]=lambda:heavy(None)
  with patch.object(RoleState,'forecast',heavy):
   worker=Thread(target=request);worker.start();self.assertTrue(started.wait(3))
   now=time.monotonic()
   self.assertEqual(client.post('/calculation-cancel',data={'calculation_id':'c'*32}).status_code,200)
   self.assertTrue(stopped.wait(1));worker.join(2);self.assertFalse(worker.is_alive())
   self.assertLess(time.monotonic()-now,1)
  if not streaming:self.assertEqual(outcome['status'],499)
  else:self.assertNotIn(b'"event":"complete"',outcome['body'])
  self.assertFalse(app.extensions['calculation_jobs'].active)
  self.assertEqual(client.post('/calculation-cancel',data={'calculation_id':'c'*32}).status_code,200)
  # A new exact calculation still completes with the unchanged result, after
  # worker termination, not merely after the old browser stopped reading.
  with client.get('/main',headers={'X-WW-Calculation-ID':'d'*32}) as response:
   self.assertEqual(response.status_code,200);self.assertIn(b'data-fraction="7/15"',response.data)
  with client.session_transaction() as s:self.assertEqual(s['game'],before)
  self.assertFalse(app.extensions['calculation_jobs'].active)
 def test_cancel_nonstream_releases_actual_worker_and_next_exact_result(self):self.run_cancel(False)
 def test_cancel_stream_releases_actual_worker_and_next_exact_result(self):self.run_cancel(True)
 def test_cancel_is_not_cross_origin_or_a_state_mutation(self):
  app=create_app({'TESTING':True,'SECRET_KEY':'cancel-test-only'});c=app.test_client()
  self.assertEqual(c.post('/calculation-cancel',data={'calculation_id':'a'*32},headers={'Origin':'https://other.test'}).status_code,403)
  self.assertEqual(c.post('/calculation-cancel',data={'calculation_id':'bad'}).status_code,400)

 def test_cancelled_hypothesis_construction_has_no_partial_result(self):
  from werewolf.calculation_budget import cancellation_scope,CalculationCancelled
  from werewolf.seer_acquisition import normalize,Hypothesis
  from fractions import Fraction
  event=Event();seen=[]
  def entries():
   for i in range(300):
    seen.append(i)
    if i==1:event.set()
    yield Hypothesis((1,0,0,0),(),Fraction(1,300))
  with cancellation_scope(event),self.assertRaises(CalculationCancelled):normalize(entries())
  self.assertLess(len(seen),300)
  event.clear()
  with cancellation_scope(event):self.assertEqual(normalize([Hypothesis((1,0,0,0),(),Fraction(1))])[0].mass,1)

 def test_cancel_public_tree_read_uses_same_worker_scope(self):self.run_cancel(False,'/game-tree')

 def test_cancelled_real_solver_can_resume_with_identical_complete_probabilities(self):
  import re
  from werewolf import calculation_budget as budget
  def fixture():
   app=create_app({'TESTING':True,'SECRET_KEY':'real-cancel-parity','SEER_UNIFORM_FUTURE_PREVIEW':True,'MANUAL_CALC_MAX_SECONDS':5})
   c=app.test_client();c.post('/start',data={'citizens':'3','seers':'1','wolves':'1','day':'max','night':'max','win_cutoff':'0'})
   with c.session_transaction() as session:revision=session['game']['revision']
   result=c.post('/public-log',data={'revision':revision,'operation':'publish','payload':json.dumps({'mode':'simultaneous','events':[{'kind':'co','player':1,'role':'seer'},{'kind':'seer','player':1,'day':1,'target':2,'color':'white'}]})})
   self.assertEqual(result.status_code,200)
   return app,c
  baseline,reference=fixture()
  with reference.get('/main') as r:
   self.assertEqual(r.status_code,200);expected=re.findall(rb'data-fraction="([^"]+)"',r.data)
  self.assertTrue(expected)
  app,c=fixture();event=Event();count=0;original=budget.check_cancelled
  def stop_inside_real_kernel():
   nonlocal count
   count+=1
   if count==8:
    for active in app.extensions['calculation_jobs'].active.values():active.set()
   original()
  from werewolf.calculation_budget import cancellation_scope
  with cancellation_scope(event),patch.object(budget,'check_cancelled',stop_inside_real_kernel):
   with c.get('/main',headers={'X-WW-Calculation-ID':'f'*32}) as r:self.assertEqual(r.status_code,499)
  self.assertGreaterEqual(count,8);event.clear()
  with c.get('/main',headers={'X-WW-Calculation-ID':'0'*32}) as r:
   self.assertEqual(r.status_code,200);self.assertEqual(re.findall(rb'data-fraction="([^"]+)"',r.data),expected)
  self.assertFalse(app.extensions['calculation_jobs'].active)
