"""Existing Tree payload over immutable anonymous evaluator records."""
from fractions import Fraction as F
from dataclasses import asdict,replace
from hashlib import sha256
from .calculation_tree import composition_label
from .exact import ROLES
from .anonymous_owned import bounded

class AnonymousCalculationTree:
 def __init__(self,node,*,role_order=None):
  self.entry_node=node;self.data=node.data;self.root='0';self.role_order=tuple(role_order or ROLES)
  self.nodes={};self.keys={};self.snapshot=sha256(repr(node.state_identity).encode()).hexdigest()[:24];self.register(node,())
 def register(self,node,route):
  key=str(len(self.nodes));self.nodes[key]=dict(node=node,route=tuple(route),actions=None,reused=False);return key
 def value(self,key):
  node=self.nodes[key]['node'];return node.calculation.evaluator.value(node.owned.belief)
 def public_current(self,key):return True
 def route(self,key):return [list(r) for r in self.nodes[key]['route']]
 def restore(self,route):
  key=self.root
  for step in route:
   self.expand(key);target,index=step[1:3]
   key=next(b['node'] for a in self.nodes[key]['actions'] for b in a['branches'] if a['targets'][0]==target and self.nodes[b['node']]['route'][-1][2]==index)
  return key
 def expand(self,key):
  row=self.nodes[key]
  if row['actions'] is not None:return
  node=row['node'];b=node.read().public;actions=[]
  if not b.winner:
   for group in node.groups:
    targets=tuple(p for p in group if p in b.alive)
    if not targets:continue
    target=targets[0];branches=[]
    try:children=node.action(target)
    except ValueError as error:
     if str(error)=='Target cannot be legally bitten in every count hypothesis':continue
     raise
    for index,child in enumerate(children):
     identity=self.register(child.node,(*row['route'],(None,target,index,None)))
     self.nodes[identity]['day_start']=child.node.read().public.phase=='day' and not child.node.read().public.winner
     branches.append(dict(node=identity,probability=str(child.probability),variants=[],observation=child.node.read().public.winner or 'continue'))
    probability=sum(node.selection_probability(p) for p in targets)
    actions.append(dict(targets=list(targets),members=[dict(target=p,policy_mass=str(node.selection_probability(p))) for p in targets],branches=branches,policy_probability=str(probability),label='人狼が'+','.join(map(str,targets))+'を襲撃',selected=bool(probability),evaluation_transition='evaluated',q_score=None,multiplicity=len(targets)))
  row['actions']=actions
 def distribution(self,key,*,names=None):
  node=self.nodes[key]['node'];b=node.owned.belief;result=[]
  for i,(counts,mass) in enumerate(b.compositions()):
   def composition(atom):
    pop=atom.population
    return tuple(sum(p.alive and p.role==role for p in pop.people)+sum(c.count for c in pop.cells if c.alive and c.role==role) for role in ('wolf','medium','seer','hunter','villager'))
   own=b.p.condition(lambda atom:composition(atom)==counts)[1]
   value=node.calculation.evaluator.value(replace(b,p=own))
   result.append(dict(id=str(i),label=composition_label(counts,self.data.game_data,self.role_order),probability=str(mass),village_win=str(value),children=[]))
  return result
 def summary(self,key,actions=False,*,compact=False):
  row=self.nodes[key];node=row['node'];b=node.read().public;law=node.owned.belief;value=self.value(key)
  point=b
  result=dict(node=key,snapshot=self.snapshot,day=b.day,phase=b.phase,column_day=point.day,column_phase=point.phase,alive=list(b.alive),winner=b.winner,
   village_win=str(value),wolf_win=str(1-value),history=[asdict(e) for e in b.history],reports=[],public_claims=list(b.claims),players=[],native_mode=True,
   public_current=True,public_bundle=False,day_start=row.get('day_start',False),compositions=[],stage_roles=dict(seers=0,mediums=0,hunters=0),
   actions=row['actions'] if actions else None,night_stages=None,evaluation='computed',expansion='computed' if row['actions'] is not None or b.winner else 'pending',
   win_certificate=None,cutoff_marker=None,evaluation_trace=dict(owner='evaluator',representation='anonymous-owned',reduction=node.calculation.evaluator.reductions.get(law)),mode='random',public_updates=None)
  for p in (() if compact else range(1,b.player_count+1)):
   result['players'].append(dict(player=p,alive=p in b.alive,wolf_probability=str(law.q.marginal(p,law.groups,'wolf')),seer_probability=str(law.q.marginal(p,law.groups,'seer')),physical_wolf_probability=str(law.p.marginal(p,law.groups,'wolf'))))
  if b.phase=='night' and row['actions'] is not None:
   branches=[]
   for a in row['actions']:
    target=a['targets'][0];deaths=[]
    for r in a['branches']:
     deaths.append(dict(kind='death_notice',actor=None,actors=[],value=target,targets=a['targets'],label='襲撃死：'+str(target),probability=r['probability'],mass=r['probability'],children=dict(leaves=[dict(node=r['node'],probability='1',variants=[])])))
    branches.append(dict(kind='public_attack',actor=None,actors=[],value=target,targets=a['targets'],label=a['label'],probability=a['policy_probability'],mass=a['policy_probability'],children=dict(branches=deaths)))
   result['night_stages']=dict(method='evaluation-recorded-v1',branches=branches);result['actions']=[]
  if compact:
   from .tree_payload import public_tree_payload
   return public_tree_payload(result)
  return result
 @bounded
 def read(self,key,expand=False,*,compact=False):
  if expand:self.expand(key)
  result=self.summary(key,True,compact=compact);result['items']={k:self.summary(k,True,compact=compact) for k in self.nodes};return result
