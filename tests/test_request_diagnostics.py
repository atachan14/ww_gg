import json,time,unittest
from unittest.mock import patch
from app import create_app
from werewolf.calculation_budget import tick
from werewolf.board_flow import RoleState
from werewolf.request_diagnostics import RequestTrace

class RequestDiagnosticsTests(unittest.TestCase):
    def app(self,enabled=True):
        return create_app({'TESTING':True,'SECRET_KEY':'diagnostic-fixture','REQUEST_LIFECYCLE_DIAGNOSTICS':enabled,'HYBRID_TABLE_PREVIEW':True})
    def test_disabled_has_no_header_or_lifecycle_logs(self):
        c=self.app(False).test_client()
        with patch('werewolf.request_diagnostics.logging.getLogger') as log:
            r=c.post('/start',data={'citizens':4,'wolves':1,'day':'max','night':'max'})
        self.assertNotIn('X-WW-Diagnostic-Request',r.headers);log.assert_not_called()
    def test_complete_correlates_without_recording_inputs(self):
        c=self.app().test_client()
        c.post('/start',data={'citizens':4,'wolves':1,'day':'max','night':'max'})
        with self.assertLogs('wwgg.lifecycle',level='WARNING') as logs:
            r=c.get('/main',headers={'Accept':'application/x-ndjson','X-Private-Fixture':'DO-NOT-LOG-SECRET'})
            events=[json.loads(chunk) for chunk in r.response];r.close()
        data=[json.loads(line.split('wwgg_lifecycle ',1)[1]) for line in logs.output]
        self.assertEqual(events[-1]['event'],'complete')
        self.assertEqual({d['request'] for d in data},{r.headers['X-WW-Diagnostic-Request']})
        self.assertNotIn('DO-NOT-LOG-SECRET',str(data))
        names=[d['event'] for d in data]
        for before,after in [('request_enter','stream_wait'),('stream_acquired','stream_released'),('stream_released','worker_exit'),('cancel_set','join_done')]:self.assertLess(names.index(before),names.index(after))
        self.assertLessEqual(len(data),12)
        self.assertTrue(all(set(d)<=set(('event','at','elapsed_ms','request','process','endpoint','reason','pending')) for d in data))
    def test_close_traces_cancel_and_releases_slot(self):
        c=self.app().test_client();c.post('/start',data={'citizens':4,'wolves':1,'day':'max','night':'max'})
        def slow(owner,**kwargs):
            while True:tick();time.sleep(.005)
        with patch.object(RoleState,'forecast',slow),self.assertLogs('wwgg.lifecycle',level='WARNING') as logs:
            r=c.get('/main',headers={'Accept':'application/x-ndjson'},buffered=False)
            self.assertEqual(json.loads(next(iter(r.response)))['event'],'roles');r.close()
        data=[json.loads(line.split('wwgg_lifecycle ',1)[1]) for line in logs.output]
        self.assertTrue(any(d['event']=='iterator_exit' and d['reason']=='closed' for d in data))
        self.assertTrue(any(d['event']=='worker_exit' and d['reason']=='cancelled' for d in data))
        self.assertTrue(any(d['event']=='join_done' and d['pending'] is False for d in data))
        self.assertEqual(c.post('/start',data={'citizens':4,'wolves':1,'day':'max','night':'max'}).status_code,303)
    def test_logging_failure_does_not_raise(self):
        with patch('werewolf.request_diagnostics.logging.getLogger',side_effect=RuntimeError('secret')):
            RequestTrace('main').emit('request_enter')
