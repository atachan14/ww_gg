import unittest
from collections import Counter
from types import SimpleNamespace
from unittest.mock import patch
from werewolf.calculation_tree import CalculationTree
from werewolf.navigation_tree import NavigationTree
from werewolf.navigation_store import NavigationDocument
from tests.test_manual_public_input import ManualPublicInputTests

class PublicTreeResponseTests(unittest.TestCase):
 def test_converged_references_summarized_once_per_response_without_stale_cache(self):
  tree=CalculationTree.__new__(CalculationTree)
  from threading import RLock
  tree.lock=RLock();tree.root='0';tree.input_updates=[]
  tree.nodes={'0':dict(actions=[dict(branches=[dict(node='1'),dict(node='1')])]),'1':dict(actions=[])}
  calls=Counter();revision=[0]
  def summary(key,actions=False):
   calls[key]+=1
   return dict(node=key,revision=revision[0],actions=tree.nodes[key]['actions'])
  tree.summary=summary;tree._composition_rows=lambda key:[]
  first=tree.read('0')
  self.assertEqual(calls,{'0':1,'1':1})
  self.assertEqual(first,dict(node='0',revision=0,actions=tree.nodes['0']['actions'],items={'1':dict(node='1',revision=0,actions=[])},input_timeline=[]))
  revision[0]=1;second=tree.read('0')
  self.assertEqual(second['items']['1']['revision'],1)
  self.assertEqual(first['items']['1']['revision'],0)
  self.assertEqual(calls,{'0':2,'1':2})

 def test_navigation_metadata_is_shared_only_within_request(self):
  doc=NavigationDocument(ManualPublicInputTests().root().data);view=NavigationTree(doc)
  view.read(expand=True)
  with patch.object(view,'phase_updates',wraps=view.phase_updates) as phases:
   before=view.read()
  self.assertEqual(phases.call_count,1)
  for item in [before,*before['items'].values()]:
   self.assertEqual(item['navigation_depth'],view.depth(item['navigation_owner'],item['column_day'],item['column_phase']))
   self.assertEqual(item['navigation_phase_updates'],view.phase_updates())
  doc.game.public_input(('seer','latent','latent','latent','latent'),())
  after=view.read()
  current=after['items'][view.current_key()]
  self.assertEqual(current['navigation_depth'],1)
  self.assertNotEqual(before['navigation_phase_updates'],after['navigation_phase_updates'])

 def test_navigation_does_not_copy_discarded_descendant_payload(self):
  class Uncopyable:
   def __deepcopy__(self,memo):raise AssertionError('discarded items were copied')
  doc=NavigationDocument(ManualPublicInputTests().root().data);view=NavigationTree(doc)
  owner,local,tree,names=view.parse(view.current_key())
  raw=tree.summary(local,True);raw['items']=Uncopyable()
  out=view._summary(owner,local,raw)
  self.assertNotIn('items',out)
  self.assertEqual(out['village_win'],raw['village_win'])

 def assert_compact(self,view,key=None):
  from werewolf.tree_payload import public_tree_payload,DETAIL_FIELDS
  full=view.read(key,True,analysis=True)
  compact=view.read(key,True,analysis=True,compact=True)
  expected=public_tree_payload(full)
  expected['items']={k:public_tree_payload(row) for k,row in full['items'].items()}
  self.assertEqual(compact,expected)
  for row in [compact,*compact['items'].values()]:self.assertFalse(DETAIL_FIELDS.intersection(row))
  self.assertIn('players',view.read(key))
  return full,compact

 def test_compact_keeps_manual_zero_edges_representatives_and_restore(self):
  import json
  doc=NavigationDocument(ManualPublicInputTests().root().data);view=NavigationTree(doc)
  self.assert_compact(view)
  doc.game.action(3);self.assert_compact(view)
  doc.game.back();doc.game.public_input(('seer','latent','latent','latent','latent'),())
  full,compact=self.assert_compact(view)
  self.assertEqual(compact['manual_updates'][-1]['probability'],'0')
  cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())))
  self.assert_compact(NavigationTree(cold))

 def test_compact_anonymous_owned_and_mixed_manual_exit(self):
  from tests.test_anonymous_owned import AnonymousOwnedTests
  doc=NavigationDocument(AnonymousOwnedTests().document(),anonymous_owned=True);view=NavigationTree(doc)
  self.assert_compact(view)
  doc.game.action(4);self.assert_compact(view)
  doc.game.back();doc.game.public_input(('seer','latent','latent','latent','latent'),())
  self.assert_compact(view)

 def test_compact_skips_unused_named_player_probabilities(self):
  doc=NavigationDocument(ManualPublicInputTests().root().data);view=NavigationTree(doc)
  owner,local,tree,names=view.parse(view.current_key())
  tree.summary(local,True)
  board=tree.nodes[local]['node'].read().public
  with patch.object(type(board),'role_probability',side_effect=AssertionError('unused player marginal')):
   compact=tree.summary(local,True,compact=True)
  self.assertNotIn('players',compact)

 def test_http_compact_is_opt_in_and_analysis_still_available(self):
  import tempfile
  from app import create_app
  from werewolf.tree_payload import public_tree_payload
  with tempfile.TemporaryDirectory() as directory:
   app=create_app(dict(TESTING=True,SECRET_KEY='compact-response-test',PERSISTENT_TREE_PREVIEW=True,GAME_TREE_PREVIEW=True,NAVIGATION_DIRECTORY=directory))
   client=app.test_client();client.post('/start',data=dict(citizens=3,seers=1,wolves=1,day='max',night='max',fake_reports='max',win_cutoff=0))
   full=client.get('/game-tree?expand=1').json
   response=client.get('/game-tree?expand=1&format=public-tree')
   self.assertEqual(response.status_code,200)
   expected=public_tree_payload(full);expected['items']={k:public_tree_payload(v) for k,v in full['items'].items()}
   self.assertEqual(response.json,expected)
   self.assertIn('players',client.get('/game-tree').json)
   analysis=client.get('/game-tree?format=public-tree&analysis=1')
   self.assertEqual(analysis.status_code,200);self.assertIn('distribution',analysis.json)
