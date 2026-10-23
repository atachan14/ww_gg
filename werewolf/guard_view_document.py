"""Viewer-owned Table guard evidence and cursor; never changes public history.

Saved documents contain user inputs and exact generator recipes, no posterior
law, action probabilities or solved values. Restore always binds the public owner.
"""
from dataclasses import replace,asdict
from fractions import Fraction as F
from hashlib import sha256
from threading import RLock
from .actor_information import GuardInformation,GuardSelection,condition_personal
from .private_view import condition_private
from .guard_effect import GuardIntent
from .guard_model import guard_choices
from .navigation_game import NavigationGame
from .navigation_tree import NavigationTree
from .public_convergence import state_key,transport_view_source
from .calculation_tree import input_snapshot
from .calculation_budget import calculation_budget,DEFAULT_MAX_WORK,DEFAULT_MAX_SECONDS
from .information_set_forecast import Pending

class GuardViewDocument:
 role='hunter'
 def __init__(self,public,owner,players,results,*,target=None):
  occurrence=public.game.history.occurrence(owner);base=public.game.history.state(owner).node
  source=base.read();self.names=occurrence.names
  if source.observer is not None:raise ValueError('Choose guard view from a public occurrence')
  if source.public.phase!='night' or source.public.winner:raise ValueError('Guard Table view requires an ongoing night')
  self.public=public;self.owner=owner;self.data=public.data;self.lock=RLock();self.revision=0;self.views=None
  self.players=tuple(players);self.results=tuple(dict(r) for r in results);self.target=target
  display=transport_view_source(source,self.names.forward)
  rules=public.data.game_data.rules;strategy=base._Node__calculation._ClosedCalculation__strategy
  view=condition_private(display.public,'hunter',self.players,self.results,rules=rules)
  guards=tuple(GuardIntent(g.night,self.names.canonical(g.actor),self.names.canonical(g.target)) for g in view.guards)
  information=GuardInformation(self.names.canonical(self.players[0]),guards)
  # Q conditions actor belief; P conditions physical continuation separately.
  _,self.belief=condition_personal(source.public_state,information)
  try:_,root=base.personal(information)
  except ValueError as error:raise Pending('root_secret_actor_physical_zero_support') from error
  self.root=root
  if target is not None:
   _,self.root=root.personal(GuardSelection(information.actor,guards,source.public.day,self.names.canonical(target)))
  self.game=NavigationGame(self.root,names=self.names)
  self.anchor=sha256(repr((input_snapshot(public.data),owner,state_key(display))).encode()).hexdigest()[:24]
 def tree(self):
  if self.views is None:self.views=NavigationTree(self)
  return self.views
 def targets(self):
  source=self.root.read();e=self.root._Node__calculation._ClosedCalculation__engine;actor=source.observer.actor
  choices={tuple(p for p,q in guard_choices(source.public,actor,e.rules,e.strategy.guard_position,guards=h.guards)) for h in source.private.hypotheses}
  if len(choices)!=1:raise Pending('guard_view_target_generation_support_unresolved')
  return tuple(self.names.display(p) for p in next(iter(choices)))
 def result(self,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS):
  from .board_roles import private_role_rates
  from .player_view import private_api_rows
  from .evaluation_branch import physical_board
  from .model_a_public import horizon_for_action
  from .by_dawn import HorizonValues
  from .actor_information import wolf_information_groups
  base=self.public.game.history.state(self.owner).node;source=self.root.read();information=source.observer
  e=self.root._Node__calculation._ClosedCalculation__engine;values={};dawn={};records={}
  with calculation_budget(max_work,max_seconds=max_seconds):
   for target in self.targets():
    _,node=base.personal(GuardSelection(information.actor,information.guards,source.public.day,self.names.canonical(target)))
    s=node.read()
    with e.group_scope(node.groups),node.relation_scope():value=e.solve(*s,physical=s.physical)
    values[target]=value;v=w=F()
    for info,mass,own in wolf_information_groups(s.private):
     for attack,q in e.wolf_policy(s.public,s.public_state,s.past,info.initial_roster,info.attacks):
      h=horizon_for_action(e,s.public,s.public_state,s.past,attack,own,observer=s.observer)
      v+=mass*q*h.village_win;w+=mass*q*h.wolf_win
    dawn[target]=HorizonValues(v,w)
    record=e.evaluation_graph.personal_program(s,node.groups)
    records[str(target)]='evaluated' if record is not None else 'value-only'
  belief_source=replace(source,private=self.belief,physical=physical_board(source.public,self.belief,source.physical))
  belief=transport_view_source(belief_source,self.names.forward).physical
  return dict(players=private_api_rows(private_role_rates(belief),targets=tuple(values),final_values=values,dawn_for=dawn.get),acquisitions=[],reason='本人の護衛履歴を保持し、公開情報の方針で評価します。',recorded_guards=records,private_view=self.export())
 def table_projection(self,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS):
  """The anchored night Table compares guards, not hypothetical wolf victims."""
  source=self.game.node.read()
  if self.game.current!=self.game.history.root or source.public.phase!='night' or source.public.winner:return None,None
  result=self.result(max_work=max_work,max_seconds=max_seconds)
  node=self.game.node;calculation=node._Node__calculation;e=calculation._ClosedCalculation__engine
  with calculation_budget(max_work,max_seconds=max_seconds),calculation._ClosedCalculation__kernel(),e.group_scope(node.groups),node.relation_scope():
   value=e.solve(*source,physical=source.physical)
  from .forecast_result import Forecast
  return result,Forecast(value,())
 def export(self):
  return dict(version=1,owner=self.owner,anchor=self.anchor,role=self.role,players=list(self.players),results=[dict(r) for r in self.results],target=self.target,revision=self.revision,history=self.game.export())
 @classmethod
 def restore(cls,public,record):
  if type(record)is not dict or set(record)!={'version','owner','anchor','role','players','results','target','revision','history'} or type(record['version'])is not int or record['version']!=1 or record['role']!=cls.role or type(record['revision'])is not int or record['revision']<0:raise ValueError('Guard view evidence document required')
  view=cls(public,record['owner'],record['players'],record['results'],target=record['target'])
  if view.anchor!=record['anchor']:raise ValueError('Public owner changed')
  view.game=NavigationGame.restore(view.root,record['history'],names=view.names);view.revision=record['revision']
  return view
