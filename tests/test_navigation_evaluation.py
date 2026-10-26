import json,tempfile,unittest
from unittest.mock import patch
from app import create_app
from werewolf.closed_calculation import _Node
from werewolf.navigation_evaluation import capture

class NavigationEvaluationTests(unittest.TestCase):
 def setUp(self):
  self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
  self.app=create_app(dict(TESTING=True,SECRET_KEY='staged-navigation',PERSISTENT_TREE_PREVIEW=True,GAME_TREE_PREVIEW=True,HYBRID_TABLE_PREVIEW=True,CALCULATION_POSITION_ENABLED=False,NAVIGATION_DIRECTORY=self.directory.name))
  self.client=self.app.test_client();self.client.post('/start',data=dict(citizens=3,seers=1,wolves=1,day='random',night='random',fake_reports='random',win_cutoff=0))
 def document(self):return next(iter(self.app.extensions['navigation_store']._documents.values()))
 def test_document_shell_and_adoption_do_not_run_future_forecast(self):
  with patch.object(_Node,'forecast',side_effect=AssertionError('no future solve during adoption')):
   page=self.client.get('/main',headers={'Sec-Fetch-Dest':'document'})
   self.assertEqual(page.status_code,200);self.assertIn('data-navigation-calculation="pending"',page.text)
   response=self.client.post('/navigation/public-input',json=dict(revision=0,claims=['seer','latent','latent','latent','latent'],reports=[]),headers={'X-WW-Staged':'1'})
   self.assertEqual(response.status_code,200,response.json);self.assertEqual(response.json['current']['occurrence'],'h1');self.assertIsNone(response.json['village_win'])
  self.assertEqual(self.document().revision,1)
 def test_stream_roles_before_win_same_snapshot_and_cached_result(self):
  self.client.get('/main',headers={'Sec-Fetch-Dest':'document'});doc=self.document();original=_Node.forecast;calls=[]
  def spy(node):calls.append(node);return original(node)
  with patch.object(_Node,'forecast',spy):
   response=self.client.get('/navigation/calculation?occurrence=h0&revision=0&request_id=1',headers={'Accept':'application/x-ndjson'},buffered=False)
   roles=json.loads(next(response.response));self.assertEqual(roles['event'],'roles');self.assertEqual(calls,[])
   complete=json.loads(next(response.response));self.assertEqual(complete['event'],'complete');self.assertEqual(complete['occurrence'],roles['occurrence']);self.assertEqual(complete['revision'],roles['revision']);self.assertEqual(len(calls),1)
   response.close();self.client.get('/navigation');self.assertEqual(len(calls),1)
  self.assertEqual(doc.revision,0)
 def test_old_snapshot_cannot_be_current_and_new_posterior_has_own_cache(self):
  self.client.get('/main',headers={'Sec-Fetch-Dest':'document'});doc=self.document();before=capture(doc);old_value=before.forecast()
  doc.game.public_input(('seer','latent','latent','latent','latent'));doc.revision+=1
  self.assertFalse(before.is_current());after=capture(doc);self.assertIsNot(before.current.navigation.node,after.current.navigation.node);self.assertIs(before.forecast(),old_value)
  stale=self.client.get('/navigation/calculation?occurrence=h0&revision=0',headers={'Accept':'application/x-ndjson'});self.assertEqual(stale.status_code,409)
 def test_legacy_summary_and_html_share_one_forecast(self):
  original=_Node.forecast;calls=[]
  def spy(node):calls.append(node);return original(node)
  with patch.object(_Node,'forecast',spy):
   result=self.client.get('/navigation');self.assertEqual(result.status_code,200);self.assertEqual(len(calls),1)

 def test_failed_calculation_is_not_failed_adoption_and_retry_matches_cold_owner(self):
  from werewolf.navigation_store import NavigationDocument
  self.client.get('/main',headers={'Sec-Fetch-Dest':'document'})
  result=self.client.post('/navigation/public-input',json=dict(revision=0,claims=['seer','seer','latent','latent','latent'],reports=[dict(acquired_day=1,published_day=1,player=1,target=3,color='white'),dict(acquired_day=1,published_day=1,player=2,target=3,color='white')]),headers={'X-WW-Staged':'1'})
  self.assertEqual(result.status_code,200);doc=self.document()
  with patch.object(_Node,'forecast',side_effect=ValueError('test calculation failure')):
   failure=self.client.get('/navigation/calculation?occurrence=h1&revision=1',headers={'Accept':'application/x-ndjson'})
   rows=[json.loads(row) for row in failure.data.splitlines()];self.assertEqual(rows[-1]['event'],'error')
  self.assertEqual(doc.game.current,'h1');self.assertEqual(doc.revision,1)
  actual=capture(doc).forecast();cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())))
  self.assertEqual(doc.game.node.read(),cold.game.node.read())
  self.assertEqual(actual,cold.game.node.forecast())
  self.assertEqual(doc.revision,1)
 def test_terminal_does_not_forecast_and_partial_certificate_is_not_full_details(self):
  self.client.post('/start',data=dict(citizens=2,seers=0,wolves=1,day='random',night='random',fake_reports='random',win_cutoff=0))
  self.client.get('/main',headers={'Sec-Fetch-Dest':'document'});doc=self.document();doc.game.action(1,outcome=0);doc.revision=1
  with patch.object(_Node,'forecast',side_effect=AssertionError('terminal must not forecast')):
   self.assertIsNone(capture(doc).forecast())
  self.client.post('/start',data=dict(citizens=3,seers=1,wolves=1,day='max',night='max',fake_reports='max',win_cutoff=1))
  self.client.get('/main',headers={'Sec-Fetch-Dest':'document'});doc=list(self.app.extensions['navigation_store']._documents.values())[-1]
  from werewolf.seer_acquisition import SeerReport
  doc.game.public_input(('seer','seer','latent','latent','latent'),(SeerReport(1,1,1,3,'white'),SeerReport(1,1,2,3,'white')));doc.revision+=1
  partial=capture(doc).forecast();self.assertIn('win_cutoff_details',partial.pending_metrics)
  full=capture(doc,details=True).forecast();self.assertEqual(full,doc.game.node.forecast());self.assertTrue(full.action_values);self.assertNotIn('win_cutoff_details',full.pending_metrics)

 def test_snapshot_fork_reuses_only_same_node_and_names_projection(self):
  from werewolf import navigation_current
  self.client.get('/main',headers={'Sec-Fetch-Dest':'document'});doc=self.document()
  if hasattr(doc.game,'_current_projection'):del doc.game._current_projection
  original=navigation_current._current_source
  with patch.object(navigation_current,'_current_source',wraps=original) as projected:
   first=capture(doc);again=capture(doc);self.assertIs(first.current.source,again.current.source);self.assertEqual(projected.call_count,1)
   doc.game.public_input(('seer','latent','latent','latent','latent'));doc.revision+=1
   changed=capture(doc);self.assertIsNot(changed.current.source,first.current.source);self.assertEqual(projected.call_count,2)
