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
