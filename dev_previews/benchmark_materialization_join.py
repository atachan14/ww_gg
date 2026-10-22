"""Bounded named boundary benchmark; no server/session changes."""
from fractions import Fraction as F
from math import factorial
from statistics import median
from time import perf_counter
from werewolf.anonymous_belief import Belief,Law
from werewolf.anonymous_materialization import assignments,hypothesis,expand_laws
from werewolf.seer_acquisition import normalize
from werewolf.calculation_budget import calculation_budget,budget_usage,tick

def previous(law,groups):
 rows=[]
 for mass,atom in law.rows:
  count=1
  for index,group in enumerate(groups):
   count*=factorial(len(group)-sum(name in group for name,ref in atom.pins))
   for cell in atom.population.cells:
    if cell.group==index:count//=factorial(cell.count)
  for names,cells in assignments(atom,groups):tick();rows.append(hypothesis(atom.population,names,cells,mass/count))
 return normalize(tuple(rows))

if __name__=='__main__':
 for n in (8,9):
  b=Belief.initial((tuple(range(1,n+1)),),dict(wolf=1,seer=1,villager=n-2)).refine(((1,),tuple(range(2,n+1))))
  p=Law.weighted((mass*(2 if atom.population.people[dict(atom.pins)[1]].role=='wolf' else 1),atom) for mass,atom in b.q.rows)[1]
  for label,laws in [('unequal',(b.q,p)),('same',(b.q,b.q))]:
   output={}
   for mode,fn in [('previous',lambda:tuple(previous(law,b.groups) for law in laws)),('joined',lambda:expand_laws(laws,b.groups))]:
    times=[]
    for _ in range(5):
     with calculation_budget(100000,max_seconds=10):
      start=perf_counter();rows=fn();times.append(perf_counter()-start);work=budget_usage()['work']
    output[mode]=(rows,work,round(median(times),5))
   assert output['previous'][0]==output['joined'][0]
   print(dict(n=n,laws=label,named_rows=[len(r) for r in rows],previous_work=output['previous'][1],joined_work=output['joined'][1],previous_seconds=output['previous'][2],joined_seconds=output['joined'][2]))
