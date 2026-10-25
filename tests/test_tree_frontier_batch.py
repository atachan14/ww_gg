import tempfile
import unittest
from app import create_app

class TreeFrontierBatchTests(unittest.TestCase):
 def client(self,directory):
  app=create_app(dict(TESTING=True,SECRET_KEY='batch-test',PERSISTENT_TREE_PREVIEW=True,GAME_TREE_PREVIEW=True,NAVIGATION_DIRECTORY=directory))
  client=app.test_client();client.post('/start',data=dict(citizens=2,seers=1,wolves=1,day='random',night='random',fake_reports='random',win_cutoff=0))
  return client
 def test_ordered_batch_matches_complete_single_responses(self):
  with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
   serial=self.client(a);batch=self.client(b)
   query=dict(expand=1,format='public-tree',defer_analysis=1)
   first=serial.get('/game-tree',query_string=query).json
   self.assertEqual(first,batch.get('/game-tree',query_string=query).json)
   keys=[key for key in first['items'] if key!=first['node']][:4]
   self.assertGreater(len(keys),1)
   expected=[serial.get('/game-tree',query_string=dict(query,node=key)).json for key in keys]
   response=batch.get('/game-tree',query_string=[*query.items(),*[('node',key) for key in keys]])
   self.assertEqual(response.status_code,200)
   self.assertEqual(response.json['batch'],expected)
   # Full compatibility reads and subsequent reads still expose identical exact state.
   self.assertEqual(serial.get('/game-tree').json,batch.get('/game-tree').json)
 def test_batch_bound_and_analysis_validation_do_not_hide_bad_nodes(self):
  with tempfile.TemporaryDirectory() as directory:
   client=self.client(directory);root=client.get('/game-tree?expand=1').json['node']
   self.assertEqual(client.get('/game-tree',query_string=[('node',root)]*9).status_code,409)
   self.assertEqual(client.get('/game-tree',query_string=[('node',root),('node',root),('analysis','1')]).status_code,409)
   self.assertEqual(client.get('/game-tree',query_string=[('node',root),('node','unknown')]).status_code,409)
   self.assertEqual(client.get('/game-tree?analysis=1').status_code,200)
