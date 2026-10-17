import json,time,threading,unittest
from types import SimpleNamespace
from unittest.mock import patch
from werewolf.exploration_position import current_path,position_stream
from werewolf.calculation_budget import calculation_budget,tick

class ExplorationPositionStreamTests(unittest.TestCase):
    def threads(self):return [t for t in threading.enumerate() if t.name=='ww-calculation-stream']
    def test_sampler_filters_secrets_and_other_threads(self):
        board=SimpleNamespace(day=2,phase='night',worlds='SECRET-WORLD',roles='SECRET-ROLE',history='SECRET-HISTORY')
        frame=SimpleNamespace(f_globals={'__name__':'werewolf.root_secret_flow'},f_code=SimpleNamespace(co_name='solve'),f_locals={'b':board,'secret':'SECRET-LOCAL'},f_back=None)
        with patch('sys._current_frames',return_value={1:frame,2:SimpleNamespace()}):depth,path=current_path(1)
        self.assertEqual(depth,1);self.assertEqual(path,[{'day':2,'phase':'night'}]);self.assertNotIn('SECRET',json.dumps(path))
    def test_long_request_has_scoped_position_then_stops(self):
        finish=threading.Event();closed=threading.Event()
        def produce(send):
            try:
                with calculation_budget(10000,max_seconds=3):
                    send(json.dumps({'event':'roles','board_id':'b1','revision':4,'request_id':'draft9'}))
                    while not finish.wait(.01):tick()
                    send(json.dumps({'event':'complete','answer':'7/15'}))
            finally:closed.set()
        with patch('werewolf.exploration_position.current_path',return_value=(14,[{'day':3,'phase':'night'}]*12)):
            stream=position_stream(produce,view='seer')
            roles=json.loads(next(stream));position=json.loads(next(stream))
            self.assertEqual(position['event'],'position');self.assertEqual(position['view'],'seer')
            for key in ('board_id','revision','request_id','run_id'):self.assertEqual(position[key],roles[key])
            self.assertTrue(position['truncated']);finish.set()
            final=[json.loads(item) for item in stream]
        self.assertEqual([e['event'] for e in final],['complete']);self.assertTrue(closed.is_set());self.assertFalse(self.threads())
    def test_disconnect_cancels_work_and_waits_for_cleanup(self):
        closed=threading.Event()
        def produce(send):
            try:
                with calculation_budget(10000,max_seconds=5):
                    send(json.dumps({'event':'roles','board_id':'b','revision':1}))
                    while True:tick();time.sleep(.01)
            finally:closed.set()
        stream=position_stream(produce);next(stream);stream.close()
        self.assertTrue(closed.is_set());self.assertFalse(self.threads())
    def test_exception_stops_worker_without_retaining_slot_or_timer(self):
        def produce(send):
            send(json.dumps({'event':'roles','board_id':'b','revision':1}));raise ValueError('fixture')
        stream=position_stream(produce);next(stream)
        with self.assertRaises(ValueError):list(stream)
        self.assertFalse(self.threads())
    def test_no_sampling_faster_than_one_hz(self):
        with self.assertRaises(ValueError):next(position_stream(lambda send:None,interval=.1))

    def test_request_deadline_in_worker_leaves_roles_and_releases_slot(self):
        from app import create_app
        from werewolf.board_flow import RoleState
        app=create_app({'TESTING':True,'SECRET_KEY':'position-deadline','HYBRID_TABLE_PREVIEW':True,'MANUAL_CALC_MAX_SECONDS':1.2})
        c=app.test_client();c.post('/start',data={'citizens':'4','wolves':'1','day':'max','night':'max'})
        def slow(owner,**kwargs):
            while True:tick();time.sleep(.01)
        with patch.object(RoleState,'forecast',slow):
            response=c.get('/main',headers={'Accept':'application/x-ndjson'})
            events=[json.loads(chunk) for chunk in response.response];response.close()
        self.assertEqual(events[0]['event'],'roles');self.assertEqual(events[-1]['event'],'complete')
        self.assertIn('Pending',events[-1]['html']);self.assertFalse(self.threads())
        self.assertEqual(c.get('/main').status_code,200)

    def test_sampling_unavailable_does_not_change_calculation(self):
        def produce(send):
            send(json.dumps({'event':'roles','board_id':'b','revision':1}));time.sleep(1.05)
            send(json.dumps({'event':'complete','answer':'7/15'}))
        with patch('werewolf.exploration_position.current_path',side_effect=RuntimeError('private runtime detail')) as collect:
            events=[json.loads(chunk) for chunk in position_stream(produce)]
        self.assertEqual(events[-1]['answer'],'7/15');self.assertEqual(collect.call_count,1)
        self.assertIn('position-unavailable',[e['event'] for e in events])
        self.assertNotIn('private runtime detail',json.dumps(events));self.assertFalse(self.threads())

    def test_queue_still_has_finite_cap_if_optional_math_time_is_none(self):
        from app import create_app
        app=create_app({'TESTING':True,'SECRET_KEY':'queue-cap','HYBRID_TABLE_PREVIEW':True,'MANUAL_CALC_MAX_SECONDS':None})
        c=app.test_client();c.post('/start',data={'citizens':'4','wolves':'1','day':'max','night':'max'})
        with patch('app.monotonic',side_effect=[0,271]):
            response=c.get('/main',headers={'Accept':'application/x-ndjson'})
            events=[json.loads(chunk) for chunk in response.response];response.close()
        self.assertEqual(events[-1]['event'],'error');self.assertEqual(events[-1]['budget_kind'],'time')
        self.assertFalse(self.threads())
