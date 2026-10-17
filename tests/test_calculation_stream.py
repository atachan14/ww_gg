import copy,json,unittest
from unittest.mock import patch
from app import create_app
from werewolf.board_flow import RoleState,BoardData

ACCEPT={'Accept':'application/x-ndjson'}
class CalculationStreamTests(unittest.TestCase):
    def setUp(self):
        self.app=create_app({'TESTING':True,'SECRET_KEY':'stream-fixture','HYBRID_TABLE_PREVIEW':True,'DAWN_BOARD_PREVIEW':True,'SEER_UNIFORM_FUTURE_PREVIEW':True})
        self.c=self.app.test_client()
        self.c.post('/start',data={'citizens':'4','wolves':'1','day':'max','night':'max'})
    def state(self):
        with self.c.session_transaction() as s:return copy.deepcopy(s['game'])
    def test_roles_are_sent_before_forecast_with_one_reconstruction(self):
        self.app.config['CALCULATION_POSITION_ENABLED']=False
        expected=self.c.get('/main').get_data(as_text=True)
        original_forecast=RoleState.forecast
        original=BoardData.roles
        with patch.object(BoardData,'roles',autospec=True,side_effect=original) as roles, patch.object(RoleState,'forecast',autospec=True,wraps=RoleState.forecast) as forecast:
            forecast.side_effect=original_forecast
            r=self.c.get('/main',headers=ACCEPT,buffered=False)
            first=json.loads(next(iter(r.response)))
            self.assertEqual(first['event'],'roles');self.assertEqual(forecast.call_count,0)
            self.assertIn('勝率を計算中',first['html']);self.assertNotIn('id="village-rate" data-fraction="7/15"',first['html'])
            final=json.loads(next(iter(r.response)))
            self.assertEqual(final['event'],'complete');self.assertEqual(final['html'],expected)
            self.assertEqual(roles.call_count,1);self.assertEqual(forecast.call_count,1)
            r.close()
    def test_failure_after_roles_keeps_session_and_releases_slot(self):
        before=self.state()
        with patch.object(RoleState,'forecast',side_effect=ValueError('fixture continuation failure')):
            r=self.c.get('/main',headers=ACCEPT,buffered=False)
            events=[json.loads(chunk) for chunk in r.response];r.close()
        self.assertEqual([e['event'] for e in events],['roles','error'])
        self.assertEqual(self.state(),before)
        self.assertEqual(self.c.get('/main').status_code,200)
    def test_private_roles_and_values_match_and_public_is_unchanged(self):
        state=self.state()
        self.c.post('/advance',data={'revision':state['revision'],'target':'1','day':'max','night':'max'})
        state=self.state();before=self.state()
        form={'revision':state['revision'],'board_id':state['public_log']['board_id'],
              'payload':json.dumps({'role':'wolf','players':[2],'results':[]})}
        legacy=self.c.post('/private-view',data=form).get_json()
        response=self.c.post('/private-view',data=form,headers=ACCEPT,buffered=False)
        events=[json.loads(chunk) for chunk in response.response];response.close()
        self.assertEqual([e['event'] for e in events],['roles','complete'])
        self.assertEqual([p['probabilities'] for p in events[0]['players']],
                         [p['probabilities'] for p in legacy['players']])
        self.assertEqual({k:v for k,v in events[1].items() if k not in ('event','run_id','view')},legacy)
        self.assertEqual(self.state(),before)
    def test_stream_keeps_budget_active_while_forecast_runs(self):
        from werewolf.calculation_budget import budget_usage
        original=RoleState.forecast;seen=[]
        def forecast(owner,**kwargs):
            seen.append(budget_usage())
            return original(owner,**kwargs)
        with patch.object(RoleState,'forecast',forecast):
            r=self.c.get('/main',headers=ACCEPT);list(r.response);r.close()
        self.assertTrue(seen[0]);self.assertIsNotNone(seen[0])

    def test_shell_does_not_reconstruct_before_single_stream(self):
        with patch.object(BoardData,'roles',side_effect=AssertionError('shell must not calculate')):
            response=self.c.get('/main',headers={'Sec-Fetch-Dest':'document'})
            self.assertIn('data-calculation-start',response.get_data(as_text=True))
    def test_close_after_roles_releases_slot(self):
        response=self.c.get('/main',headers=ACCEPT,buffered=False)
        self.assertEqual(json.loads(next(iter(response.response)))['event'],'roles')
        response.close()
        self.assertEqual(self.c.get('/main').status_code,200)
    def test_own_history_roles_survive_pending_continuation(self):
        from pathlib import Path
        from werewolf.seer_future_uniform import FuturePending
        fixture=json.loads(Path('benchmarks/board_b_extended_cases.json').read_text())['private-history']
        with self.c.session_transaction() as session:session['game']=fixture['game']
        state=self.state()
        # game() migrates the public identity without starting a win forecast.
        self.c.get('/main',headers={'Sec-Fetch-Dest':'document'})
        state=self.state();own=fixture['private']
        with patch('werewolf.root_secret_flow.root_seer_forecast',return_value=FuturePending('root_secret_budget_exceeded')),patch('werewolf.seer_view_forecast.seer_forecast',return_value=FuturePending('information_set_budget_exceeded')):
            response=self.c.post('/private-view',headers=ACCEPT,data={'revision':state['revision'],'board_id':state['public_log']['board_id'],'payload':json.dumps(own)})
            events=[json.loads(chunk) for chunk in response.response];response.close()
        self.assertEqual([e['event'] for e in events],['roles','complete'])
        self.assertTrue(events[0]['players'])
        self.assertEqual([p['probabilities'] for p in events[0]['players']],[p['probabilities'] for p in events[1]['players']])
        self.assertTrue(all(p['final'] is None for p in events[1]['players']))

    def test_table_preview_validation_is_inside_stream_budget(self):
        from werewolf.calculation_budget import budget_usage
        state=self.state();observed=[];original=BoardData.roles
        def roles(owner):
            observed.append(budget_usage())
            return original(owner)
        payload={'claims':['villager']+['latent']*4,'seers':[],'mediums':[]}
        with patch.object(BoardData,'roles',roles):
            response=self.c.post('/table-preview',headers=ACCEPT,data={'revision':state['revision'],'board_id':state['public_log']['board_id'],'request_id':'41','payload':json.dumps(payload)})
            events=[json.loads(chunk) for chunk in response.response];response.close()
        self.assertEqual([e['event'] for e in events],['roles','complete'])
        self.assertTrue(observed);self.assertTrue(all(observed))
        self.assertTrue(all(e['request_id']=='41' for e in events))
    def test_stream_works_without_hybrid_public_log(self):
        c=create_app({'TESTING':True,'SECRET_KEY':'plain-stream'}).test_client()
        c.post('/start',data={'citizens':'4','wolves':'1','day':'max','night':'max'})
        response=c.get('/main',headers=ACCEPT)
        events=[json.loads(chunk) for chunk in response.response];response.close()
        self.assertEqual([e['event'] for e in events],['roles','complete'])
    def test_joint_actor_conditioning_is_shared_before_seer_forecast(self):
        from werewolf.root_secret_flow import root_actor_view
        self.c.post('/start',data={'citizens':'2','mediums':'1','seers':'1','wolves':'1','day':'random','night':'random','initial_seer':'random_white'})
        state=self.state();self.c.post('/advance',data={'revision':state['revision'],'target':'1','day':'random','night':'random'})
        state=self.state()
        own={'role':'seer','players':[2],'results':[{'day':1,'target':3,'color':'white'}]}
        with patch('werewolf.root_secret_flow.root_actor_view',wraps=root_actor_view) as condition:
            response=self.c.post('/private-view',headers=ACCEPT,data={'revision':state['revision'],'board_id':state['public_log']['board_id'],'payload':json.dumps(own)})
            events=[json.loads(chunk) for chunk in response.response];response.close()
        self.assertEqual([e['event'] for e in events],['roles','complete'])
        self.assertEqual(condition.call_count,1)
        self.assertEqual([p['probabilities'] for p in events[0]['players']],[p['probabilities'] for p in events[1]['players']])
