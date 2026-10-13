from test_board_owned_log import BoardOwnedLogTests as _Base
from app import create_app
class BoardOwnedFutureTests(_Base):
 def setUp(self):
  self.a=create_app({'TESTING':True,'SECRET_KEY':'board-owned-future','HYBRID_TABLE_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True});self.c=self.a.test_client();self.c.post('/start',data={'citizens':'5','seers':'1','wolves':'1','day':'max','night':'max'})
 def test_late_report_bridge_preserves_publication_day_and_uses_only_active_input(self):
  from unittest.mock import patch
  from werewolf.seer_manual import replay
  from werewolf.seer_future_bridge import evaluate_game
  from werewolf.seer_future_forecast import Forecast
  from werewolf.exact import Strategy
  from fractions import Fraction
  self.advance(2);self.advance(3);owner=self.bid();p=self.payload();p['claims'][0]='seer';p['seers']=[{'day':1,'reporter':1,'target':3,'color':'white'},{'day':2,'reporter':1,'target':4,'color':'white'}];self.assertEqual(self.table(p).status_code,200)
  p['seers'][0]['target']=5;self.assertEqual(self.table(p).status_code,200);g=self.g();rules,progress=replay(g)
  with patch('werewolf.seer_future_bridge.forecast',return_value=Forecast(Fraction(1,2),())) as forecast:
   evaluate_game(g,progress.board,rules,Strategy())
  private,past=forecast.call_args.args[1:3];self.assertEqual(private.observed_prefix,2);self.assertTrue(all(a.target!=3 for h in private.hypotheses for a in h.acquisitions));self.assertEqual({(r.acquired_day,r.published_day) for r in past},{(1,2),(2,2)});self.assertEqual(g['public_log']['report_publications']['seer:1:1']['board_id'],owner)
  p['seers']=[p['seers'][1]];self.assertEqual(self.table(p).status_code,200);g=self.g();rules,progress=replay(g)
  with patch('werewolf.seer_future_bridge.forecast',return_value=Forecast(Fraction(1,2),())) as forecast:
   evaluate_game(g,progress.board,rules,Strategy())
  private,past=forecast.call_args.args[1:3];self.assertTrue(all(a.day!=1 for h in private.hypotheses for a in h.acquisitions));self.assertEqual({r.acquired_day for r in past},{2})
 def test_budget_preview_is_pending_and_keeps_confirmed_state(self):
  self.root_report();before=self.g();p=self.payload();p['seers'][0]['target']=5;self.a.config['MANUAL_CALC_MAX_WORK']=1;r=self.table(p,True);self.assertEqual(r.status_code,200);h=r.get_json()['html'];self.assertIn('data-seer-pending',h);self.assertNotIn('id="village-rate"',h);self.assertEqual(self.g(),before)
 def test_published_day2_half_example_also_with_future_enabled(self):
  from unittest.mock import patch
  from test_seer_manual_compatibility import HandCompatibilityTests
  from app import create_app as factory
  def future_factory(config):return factory({**config,'SEER_UNIFORM_FUTURE_PREVIEW':True})
  with patch('test_seer_manual_compatibility.create_app',side_effect=future_factory):
   HandCompatibilityTests().test_day2_dead_and_live_seer_candidates_half_with_preview_and_co_table()
 def test_parent_commit_retires_descendants_and_forward_regenerates_without_old_input(self):
  g=self.g();self.c.post('/strategy',data={'revision':str(g['revision']),'day':'max','night':'max','disclosure_common':'none'})
  super().test_parent_commit_retires_descendants_and_forward_regenerates_without_old_input()
del _Base
