import unittest,json
from fractions import Fraction as F
from app import create_app
from werewolf.seer_acquisition import Hypothesis,Acquisition
from werewolf.seer_future_uniform import TrueScanState,acquire_uniform
class ActiveInputLedgerTests(unittest.TestCase):
 def test_active_input_target_only_then_generated_true_history_is_preserved(self):
  # Retired input target2 is deliberately absent; current declaration target3
  # defines the user Board. Actual future acquisitions are not reset later.
  s=TrueScanState((Hypothesis((16,0,1,0),(Acquisition(1,1,3,'white'),),F(1)),),((1,2,3,4,5),),'random_white',(1,),1)
  next_state=acquire_uniform(s,(1,2,3,4,5));self.assertEqual({h.acquisitions[-1].target for h in next_state.hypotheses},{2,4,5});self.assertTrue(all(h.acquisitions[0].target==3 for h in next_state.hypotheses))
  future=acquire_uniform(next_state,(1,2,3,4,5));self.assertTrue(all(len(h.acquisitions)==3 for h in future.hypotheses));self.assertEqual(future.observed_prefix,1)
  with self.assertRaises(ValueError):TrueScanState((Hypothesis((16,0,1,0),(Acquisition(1,1,3,'white'),),F(1)),),((1,2,3,4,5),(1,2,3,4,5)),'random_white',(1,),1)
 def test_retired_report_alone_does_not_force_future_pending(self):
  a=create_app({'TESTING':True,'SECRET_KEY':'active-input-future','HYBRID_TABLE_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True});c=a.test_client();c.post('/start',data={'citizens':'2','seers':'1','wolves':'2','day':'max','night':'max'})
  def g():
   with c.session_transaction() as q:return q['game'].copy()
  def send(p):return c.post('/table-publish',data={'revision':str(g()['revision']),'payload':json.dumps(p)})
  p={'claims':['seer','seer','latent','latent','latent'],'seers':[{'day':1,'reporter':1,'target':3,'color':'white'},{'day':1,'reporter':2,'target':3,'color':'black'}],'mediums':[]};self.assertEqual(send(p).status_code,200);p['seers'][0]['target']=4;self.assertEqual(send(p).status_code,200);h=c.get('/main').data;self.assertIn(b'data-seer-future="all"',h);self.assertIn(b'id="village-rate"',h);self.assertTrue(g()['public_log']['retired_input_reports']);self.assertEqual(g()['seer_inputs'][0]['target'],4)
