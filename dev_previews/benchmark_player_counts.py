"""Bounded exact count-scope probes; no live sessions or servers."""
import json,time
from copy import deepcopy
from fractions import Fraction as F
from functools import lru_cache
from tests.test_manual_public_input import ManualPublicInputTests
from werewolf.board_flow import BoardData
from werewolf.closed_calculation import ClosedCalculation
from werewolf.calculation_budget import calculation_budget,budget_usage,CalculationBudgetExceeded
from werewolf.navigation_store import NavigationDocument
from werewolf.navigation_tree import NavigationTree

@lru_cache(None)
def oracle(n,w,phase):
 if not w:return F(1)
 if w>=n-w:return F()
 if phase=='night':return oracle(n-1,w,'day')
 return F(w,n)*oracle(n-1,w-1,'night')+F(n-w,n)*oracle(n-1,w,'night')
def data(n,policy='max',wolves=1,seers=1):
 g=deepcopy(ManualPublicInputTests().root().data.to_game());g.update(players=n,wolves=wolves,seers=seers,claims=['latent']*n)
 g['policy'].update(day=policy,night=policy,fake_reports=policy,win_cutoff=False)
 return BoardData.from_game(g)
def run(n,policy,wolves=1):
 start=time.perf_counter();rows=[]
 try:
  with calculation_budget(250000,max_seconds=12):
   doc=NavigationDocument(data(n,policy,wolves));view=NavigationTree(doc)
   for target in (None,1,2):
    if target is not None:doc.game.action(target)
    s=doc.game.node.read();value=doc.game.node.forecast().village_win
    physical={}
    for h in s.private.hypotheses:
     w=(h.roles[0]&s.public.alive_mask).bit_count();physical[w]=physical.get(w,F())+h.mass
    expected=sum(q*oracle(len(s.public.alive),w,s.public.phase) for w,q in physical.items())
    if value!=expected:raise AssertionError((value,expected))
    rows.append(dict(day=s.public.day,phase=s.public.phase,alive=len(s.public.alive),value=str(value),work=budget_usage()['work']))
   result=dict(n=n,wolves=wolves,policy=policy,status='exact',rows=rows,seconds=round(time.perf_counter()-start,3))
   print(json.dumps(result),flush=True)
 except CalculationBudgetExceeded as error:
  result=dict(n=n,wolves=wolves,policy=policy,status='budget',rows=rows,seconds=round(time.perf_counter()-start,3),kind=error.kind)
  print(json.dumps(result),flush=True)
def staged(n):
 start=time.perf_counter()
 try:
  with calculation_budget(500000,max_seconds=15):
   doc=NavigationDocument(data(n));view=NavigationTree(doc)
   root=view.read(expand=True);doc.game.action(1)
   night=view.read(view.current_key(),True)
   leaves=[]
   def collect(s):
    leaves.extend(s.get('leaves',()))
    for branch in s.get('branches',()):collect(branch['children'])
   collect(night['night_stages'])
   destinations=set(r['node'] for r in leaves)
   doc.game.action(2);current=view.read(view.current_key(),True)
   cold=NavigationDocument.restore(doc.export())
   assert cold.game.node.read()==doc.game.node.read()
   print(json.dumps(dict(n=n,stage='exact',leaves=len(leaves),public_destinations=len(destinations),current=current['node'],phase=[current['day'],current['phase']],work=budget_usage()['work'],seconds=round(time.perf_counter()-start,3))),flush=True)
 except CalculationBudgetExceeded as error:
  print(json.dumps(dict(n=n,stage='budget',kind=error.kind,seconds=round(time.perf_counter()-start,3))),flush=True)

if __name__=='__main__':
 for n in (7,8,9):
  for policy in ('random','max'):run(n,policy)
 for n in (8,9):staged(n)
 for n in (8,9):run(n,'max',2)
