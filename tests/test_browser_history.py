import json,re,tempfile,unittest
from unittest.mock import patch
from fractions import Fraction as F
from app import create_app
from itsdangerous import URLSafeSerializer

KEY='browser-history-test-key'
class BrowserHistoryTests(unittest.TestCase):
 def app(self):return create_app(dict(TESTING=True,SECRET_KEY=KEY,BROWSER_HISTORY_PREVIEW=True,GAME_TREE_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,ANONYMOUS_NIGHT_PREVIEW=True,ANONYMOUS_OWNERSHIP_PREVIEW=True))
 def setup_client(self):
  app=self.app();c=app.test_client();c.post('/start',data={'citizens':'4','wolves':'1','day':'max','night':'max'})
  h=c.get('/main',headers={'X-WW-Staged':'1'}).get_data(as_text=True)
  seed=json.loads(re.search(r'id="browser-history-seed">(.*?)</script>',h).group(1));return app,c,seed
 def wire(self,c,token,url='/navigation',method='GET',body='',routes=None,headers=None):
  return c.post('/browser-history/request',json=dict(url=url,method=method,body=body,content_type='application/json' if method=='POST' else '',token=token,routes=routes or {}),headers={'X-WW-Staged':'1',**(headers or {})})
 def test_cold_worker_keeps_Current_and_exact_history(self):
  app,c,seed=self.setup_client();a=self.wire(c,seed['token'],'/navigation/advance','POST',json.dumps(dict(revision=0,target=2))).get_json();self.assertEqual(a['current']['occurrence'],'h1')
  other=self.app().test_client();other.set_cookie('session',c.get_cookie('session').value)
  b=self.wire(other,a['browser_history']).get_json();self.assertEqual(b['current'],a['current']);self.assertEqual(b['occurrences'],a['occurrences'])
  r=self.wire(other,a['browser_history'],'/navigation/calculation?occurrence=h1&revision=1&request_id=1',headers={'Accept':'application/x-ndjson'})
  events=[json.loads(x) for x in r.get_data(as_text=True).splitlines()];complete=next(e for e in events if e['event']=='complete');self.assertTrue(complete['value_complete']);self.assertIn('data-fraction="1/3"',complete['html'])
 def test_tampered_and_replayed_wrong_weights_rejected(self):
  app,c,seed=self.setup_client();prefix,signature=seed['token'].rsplit('.',1);bad=prefix+'.'+('A' if signature[0]!='A' else 'B')+signature[1:];self.assertEqual(self.wire(c,bad).status_code,400)
  signer=URLSafeSerializer(KEY,salt='browser-history-prototype-v1');record=signer.loads(seed['token']);record['history']['rows'][0]['selection_weight']='999'
  self.assertEqual(self.wire(c,signer.dumps(record)).status_code,400)
 def test_duplicate_submission_is_same_recipe_and_invalid_input_not_adopted(self):
  app,c,seed=self.setup_client();body=json.dumps(dict(revision=0,target=2));a=self.wire(c,seed['token'],'/navigation/advance','POST',body).get_json();b=self.wire(c,seed['token'],'/navigation/advance','POST',body).get_json();self.assertEqual(a['browser_history'],b['browser_history'])
  self.assertEqual(self.wire(c,seed['token'],'/navigation/advance','POST',json.dumps(dict(revision=0,target=0))).status_code,400)
  self.assertEqual(self.wire(c,seed['token']).get_json()['current']['occurrence'],'h0')
 def test_cold_tree_routes_and_Current(self):
  app,c,seed=self.setup_client();root=self.wire(c,seed['token'],'/game-tree?expand=1&format=public-tree&defer_analysis=1');self.assertEqual(root.status_code,200);a=root.get_json()
  key=next(k for k in a['browser_routes'] if k!='h0~0');ref=a['browser_routes'][key]
  fresh=self.app().test_client();fresh.set_cookie('session',c.get_cookie('session').value)
  b=self.wire(fresh,a['browser_history'],'/game-tree?node='+key+'&expand=1&format=public-tree&defer_analysis=1',routes={key:ref});self.assertEqual(b.status_code,200);self.assertEqual(b.get_json()['node'],key)
 def test_transport_origin_path_and_size_fail_closed(self):
  app,c,seed=self.setup_client();self.assertEqual(self.wire(c,seed['token'],'https://other.test/navigation').status_code,400)
  self.assertEqual(self.wire(c,seed['token'],headers={'Origin':'https://other.test'}).status_code,403)
  self.assertEqual(c.post('/browser-history/request',data='x'*131073).status_code,413)

 def test_failure_retry_and_budget_have_no_completed_value(self):
  app,c,seed=self.setup_client();url='/navigation/calculation?occurrence=h0&revision=0&request_id=7'
  with patch('werewolf.navigation_evaluation.NavigationEvaluation.forecast',side_effect=ValueError('fixture failure')):
   text=self.wire(c,seed['token'],url,headers={'Accept':'application/x-ndjson'}).get_data(as_text=True)
  events=[json.loads(x) for x in text.splitlines()];self.assertTrue(any(x['event']=='error' for x in events));self.assertFalse(any(x['event']=='complete' for x in events))
  events=[json.loads(x) for x in self.wire(c,seed['token'],url,headers={'Accept':'application/x-ndjson'}).get_data(as_text=True).splitlines()]
  self.assertTrue(any(x['event']=='complete' and x['value_complete'] for x in events))
 def test_stream_disconnect_really_stops_the_CPU_worker(self):
  import http.client,threading,time
  from werkzeug.serving import make_server
  from werewolf.calculation_budget import tick,CalculationCancelled
  app,c,seed=self.setup_client();started=threading.Event();finished=threading.Event();cancelled=threading.Event()
  def expensive(unused):
   started.set();deadline=time.monotonic()+8
   try:
    while time.monotonic()<deadline:tick()
    raise ValueError('fixture did not cancel')
   except CalculationCancelled:cancelled.set();raise
   finally:finished.set()
  server=make_server('127.0.0.1',0,app,threaded=True);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  try:
   with patch('werewolf.navigation_evaluation.NavigationEvaluation.forecast',expensive):
    body=json.dumps(dict(url='/navigation/calculation?occurrence=h0&revision=0&request_id=8',method='GET',body='',content_type='',token=seed['token'],routes={}))
    conn=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=10);conn.request('POST','/browser-history/request',body,{'Content-Type':'application/json','Accept':'application/x-ndjson','Cookie':'session='+c.get_cookie('session').value,'X-WW-Browser-Stream':'1'})
    response=conn.getresponse();first=json.loads(response.readline());self.assertEqual(first['event'],'browser-headers');self.assertTrue(started.wait(2))
    stop=time.monotonic();response.close();conn.close();self.assertTrue(finished.wait(5));elapsed=time.monotonic()-stop
    self.assertTrue(cancelled.is_set());print('browser_disconnect_to_CPU_exit_seconds',round(elapsed,3))
  finally:server.shutdown();server.server_close();thread.join(2)

 def test_hosted_entry_is_optin_and_has_no_filesystem_persistence(self):
  import os
  with patch.dict(os.environ,{'WW_GG_SECRET_KEY':'0123456789abcdef'*4}):
   app=create_app(dict(TESTING=True,BROWSER_HISTORY_PREVIEW=True,GAME_TREE_PREVIEW=True,PERSISTENT_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True),deployment=True)
  from werewolf.browser_history import BrowserStore
  self.assertIsInstance(app.extensions['navigation_store'],BrowserStore)
  self.assertTrue(app.config['SESSION_COOKIE_SECURE'])
  c=app.test_client();self.assertEqual(c.post('/private-view').status_code,422)

 def test_outer_transport_preserves_JSON_and_status(self):
  import base64
  app,c,seed=self.setup_client()
  response=self.wire(c,seed['token'],headers={'X-WW-Browser-Stream':'1'})
  frames=[json.loads(l) for l in response.get_data(as_text=True).splitlines()]
  self.assertEqual(next(f for f in frames if f['event']=='browser-headers')['status'],200)
  data=json.loads(b''.join(base64.b64decode(f['data']) for f in frames if f['event']=='browser-chunk'))
  self.assertEqual(data['current']['occurrence'],'h0')
 def test_new_worker_route_token_cannot_cross_revisions(self):
  app,c,seed=self.setup_client();tree=self.wire(c,seed['token'],'/game-tree?expand=1&format=public-tree&defer_analysis=1').get_json()
  key=next(k for k in tree['browser_routes'] if k!='h0~0');ref=tree['browser_routes'][key]
  advanced=self.wire(c,seed['token'],'/navigation/advance','POST',json.dumps(dict(revision=0,target=2))).get_json()
  self.assertEqual(self.wire(c,advanced['browser_history'],'/game-tree?node='+key,routes={key:ref}).status_code,400)

 def test_budget_stop_does_not_become_a_completed_forecast(self):
  from werewolf.calculation_budget import CalculationBudgetExceeded
  app,c,seed=self.setup_client()
  with patch('werewolf.navigation_evaluation.NavigationEvaluation.forecast',side_effect=CalculationBudgetExceeded(kind='work')):
   text=self.wire(c,seed['token'],'/navigation/calculation?occurrence=h0&revision=0&request_id=9',headers={'Accept':'application/x-ndjson'}).get_data(as_text=True)
  events=[json.loads(x) for x in text.splitlines()]
  self.assertTrue(any(x['event']=='error' and x.get('pending') for x in events));self.assertFalse(any(x['event']=='complete' for x in events))
  self.assertEqual(self.wire(c,seed['token']).get_json()['browser_history'],seed['token'])
 def test_manual_zero_update_keeps_original_history(self):
  app,c,seed=self.setup_client();payload=json.dumps(dict(revision=0,claims=['latent','latent','villager','latent','latent'],reports=[]))
  result=self.wire(c,seed['token'],'/navigation/public-input','POST',payload);self.assertEqual(result.status_code,200);data=result.get_json()
  self.assertEqual(data['occurrences'][-1]['selection_weight'],'0')
  back=self.wire(c,data['browser_history'],'/navigation/move','POST',json.dumps(dict(revision=1,occurrence='h0'))).get_json()
  self.assertEqual(back['current']['occurrence'],'h0');self.assertEqual(len(back['occurrences']),2)

 def test_unavailable_replay_is_explicit_not_partial_or_server_error(self):
  from werewolf.information_set_forecast import Pending
  app,c,seed=self.setup_client()
  with patch('werewolf.browser_history.NavigationDocument.restore',side_effect=Pending('fixture unsupported replay')):
   response=self.wire(c,seed['token'])
  self.assertEqual(response.status_code,422);self.assertTrue(response.get_json()['unsupported']);self.assertNotIn('browser_history',response.get_json())
