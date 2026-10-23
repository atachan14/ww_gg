"""Factor actual evaluated hunter joint laws; never generate game actions.

Every atom, guard/scan memory, casualty and publication is read from completed
RootSecretEngine outputs. Anonymous symbols describe correlated incidences;
no policy is reselected and no per-atom continuation value is invented.
"""
from dataclasses import replace
from fractions import Fraction as F
from .anonymous_night import Program,Leaf,Symbol,SymbolStep,selection
from .evaluation_branch import physical_board
from .group_partition import _fix
from .board_future import outcome_key
from .joint_action_kernel import report_signature
from .tree_public_updates import publication_label
from .anonymous_abilities import dead_stage_kinds
from .ability_adapters import Divination,Guard
from .calculation_budget import tick

def factor(source,groups,rows):
 b=source.public
 # Medium private-result reconstruction is a separate adapter boundary.
 if b.initial_medium_count:return None
 groups=groups+tuple((p,) for p in range(1,b.player_count+1) if not any(p in g for g in groups))
 leaves=[];values={}
 for weight,before,after,target,value,info,owner,index,outcome in rows:
  values[after]=value
  for h in after.private.hypotheses:
   tick();symbols={};steps=[]
   def symbol(person):
    if person not in symbols:
     group=next(g for g in groups if person in g)
     symbols[person]=Symbol(len(symbols),group)
    return symbols[person]
   scans=tuple(sorted((a.player,a.target) for a in h.acquisitions if a.day==b.day+1))
   for role,ability in ((2,Divination()),(3,Guard())):
    actors=tuple(p for p in b.alive if h.roles[role]&(1<<(p-1)))
    steps.extend(SymbolStep('ability_dead',None,kind) for kind in dead_stage_kinds(bool(h.roles[role]),bool(actors),ability.stages))
    for actor in actors:
     if role==2:
      acquired=next((a for a in h.acquisitions if a.player==actor and a.day==b.day+1),None)
      if acquired is None:return None
      steps.extend((SymbolStep('seer_target',symbol(actor),symbol(acquired.target)),SymbolStep('seer_result',symbol(actor),acquired.color)))
     else:
      guard=next((g for g in h.guards if g.actor==actor and g.night==b.day),None)
      if guard is None:return None
      steps.append(SymbolStep('guard_target',symbol(actor),symbol(guard.target)))
   wolves=tuple(p for p in b.alive if h.roles[0]&(1<<(p-1)))
   owners=tuple(symbol(p) for p in wolves);victim=symbol(target)
   steps.append(SymbolStep('wolf_target',None,victim,owners))
   deaths=tuple(p for p in b.alive if p not in before.public.alive)
   if len(deaths)>1:return None
   steps.append(SymbolStep('death_notice',None,symbol(deaths[0]) if deaths else None,public_fact=before.public.winner))
   if any(c in ('seer','medium') for c in b.claims):steps.append(SymbolStep('publication',None,publication_label(before,after)))
   own=replace(after.private,hypotheses=(replace(h,mass=F(1)),))
   child=replace(after,private=own,physical=physical_board(after.public,own,after.physical),board_data=None,provenance=None)
   mass=weight*h.mass
   leaves.append(Leaf(mass,mass,child,tuple(steps),info,owner,target,index,outcome_key(outcome),report_signature(after),tuple(p for p in range(1,b.player_count+1) if h.roles[0]&(1<<(p-1))),scans,_fix(groups,tuple(symbols)),1,(),selection(h),tuple((s.index,p) for p,s in symbols.items()),arrival=before))
 program=Program(source,groups,leaves,dict(recorded_action_flow=True,generated_actions=0,permutation_checks=0))
 program.values.update(values);program.private_contexts=False
 return program
