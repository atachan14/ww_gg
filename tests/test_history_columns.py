import json,unittest
from collections import Counter
from types import SimpleNamespace as S
from unittest.mock import patch
from werewolf.navigation_tree import NavigationTree
from werewolf.navigation_store import NavigationDocument
from tests.test_manual_public_input import ManualPublicInputTests

class HistoryColumnTests(unittest.TestCase):
 def naive(self,rows,boards):
  by_key={r['key']:r for r in rows};totals={}
  for row in rows:
   phase=boards[row['key']];key=row['key'];depth=0
   while key is not None:
    old=by_key[key];step=old['selector']
    if boards[key]==phase and (old['edge_kind'] in ('manual_public','recorded_input') or step is not None and step.get('kind')=='published'):depth+=1
    key=old['parent']
   column=str((phase[0]-1)*2+(phase[1]=='night'));totals[column]=max(totals.get(column,0),depth)
  return totals

 def test_branching_publication_and_noncontiguous_phase_counts(self):
  rows=[];boards={}
  def add(key,parent,phase,edge='strategy',kind='generated'):
   rows.append(dict(key=key,parent=parent,edge_kind=edge,selector=None if kind is None else dict(kind=kind)));boards[key]=phase
  add('0',None,(1,'day'),'root',None);add('1','0',(1,'day'),'manual_public')
  add('2','1',(1,'night'));add('3','2',(2,'day'));add('4','3',(2,'day'),kind='published')
  add('5','3',(1,'day'),'recorded_input');add('6','0',(1,'day'),'manual_public');add('7','4',(2,'day'),kind='published')
  visits=Counter()
  def state(key):visits[key]+=1;day,phase=boards[key];return S(source=S(public=S(day=day,phase=phase)))
  history=S(export=lambda:rows,state=state);view=NavigationTree.__new__(NavigationTree);view.document=S(game=S(history=history))
  self.assertEqual(view.phase_updates(),self.naive(rows,boards));self.assertEqual(view.phase_updates(),{'0':2,'1':0,'2':2})
  self.assertEqual(visits,{key:2 for key in boards})

 def test_actual_manual_branches_and_cold_restore_keep_full_response(self):
  doc=NavigationDocument(ManualPublicInputTests().root().data)
  for _ in range(8):doc.game.public_input(('latent',)*5,())
  for _ in range(4):doc.game.back()
  for _ in range(2):doc.game.public_input(('latent',)*5,())
  view=NavigationTree(doc);root=doc.game.history.state(doc.game.history.root).source
  rows=doc.game.history.export();boards={r['key']:(doc.game.history.state(r['key']).source.public.day,doc.game.history.state(r['key']).source.public.phase) for r in rows}
  self.assertEqual(view.phase_updates(),self.naive(rows,boards));self.assertEqual(view.phase_updates(),{'0':8})
  with patch.object(doc.game.history,'state',wraps=doc.game.history.state) as state:
   self.assertEqual(view.phase_updates(),{'0':8})
  self.assertEqual(state.call_count,len(rows))
  sources={r['key']:doc.game.history.state(r['key']).source for r in rows}
  before=view.read(expand=True,compact=True)
  self.assertEqual({r['key']:doc.game.history.state(r['key']).source for r in rows},sources)
  self.assertEqual(before['village_win'],'7/15');self.assertEqual(doc.game.history.state(doc.game.history.root).source,root)
  cold=NavigationDocument.restore(json.loads(json.dumps(doc.export())))
  self.assertEqual({r['key']:cold.game.history.state(r['key']).source for r in rows},sources)
  after=NavigationTree(cold).read(expand=True,compact=True)
  self.assertEqual(after,before)
  self.assertTrue(all(item['navigation_phase_updates']=={'0':8} for item in [before,*before['items'].values()]))
