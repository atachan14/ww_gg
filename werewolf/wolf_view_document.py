"""Pack-owned Table evidence/cursor over the existing exact evaluator."""
from dataclasses import replace
from hashlib import sha256
from threading import RLock
from .guard_view_document import GuardViewDocument
from .actor_information import WolfInformation,WolfObserver,condition_personal
from .private_view import condition_private
from .navigation_game import NavigationGame
from .public_convergence import state_key,transport_view_source,transport_record
from .calculation_tree import input_snapshot
from .calculation_budget import calculation_budget,DEFAULT_MAX_WORK,DEFAULT_MAX_SECONDS
from .information_set_forecast import Pending

class WolfViewDocument(GuardViewDocument):
 role='wolf'
 @staticmethod
 def supports(public,players):
  s=public.game.node.read();e=public.game.node._Node__calculation._ClosedCalculation__engine
  return (not s.public.initial_hunter_count and s.public.initial_role_counts['wolf']==1
   and any(s.public.claims[p-1]=='seer' for p in s.public.alive)
   and not e.rules.allow_self_bite and not e.strategy.include_self_bite
   and e.strategy.disclosure_for('seer')=='all'
   and (e.strategy.day,e.strategy.night,e.strategy.fake_reports)==('random',)*3)
 def __init__(self,public,owner,players,results,*,target=None):
  occurrence=public.game.history.occurrence(owner);base=public.game.history.state(owner).node
  source=base.read();e=base._Node__calculation._ClosedCalculation__engine;self.names=occurrence.names
  if (source.public.initial_hunter_count or source.public.initial_role_counts['wolf']!=1
   or e.rules.allow_self_bite or e.strategy.include_self_bite or e.strategy.disclosure_for('seer')!='all'
   or (e.strategy.day,e.strategy.night,e.strategy.fake_reports)!=('random',)*3
   or not any(source.public.claims[p-1]=='seer' for p in source.public.alive)):raise Pending('wolf_table_recorded_scope_unimplemented')
  if source.observer is not None or source.public.phase!='night' or source.public.winner:raise ValueError('Choose pack view from an ongoing public night')
  if target is not None:raise ValueError('Pack targets are compared as exact action rows')
  self.public=public;self.owner=owner;self.data=public.data;self.lock=RLock();self.revision=0;self.views=None
  self.players=tuple(players);self.results=tuple(dict(r) for r in results);self.target=None
  display=transport_view_source(source,self.names.forward)
  view=condition_private(display.public,'wolf',self.players,self.results,rules=e.rules)
  mask=sum(1<<(self.names.canonical(p)-1) for p in self.players)
  inverse=tuple(self.names.canonical(p) for p in range(1,source.public.player_count+1))
  known=tuple(transport_record(a,inverse) for a in view.attacks)
  histories={h.attacks for h in source.private.hypotheses if h.roles[0]==mask and all(a in h.attacks for a in known)}
  if not histories:raise ValueError('Pack evidence outside generated history')
  if len(histories)!=1:raise Pending('wolf_view_past_attack_history_unresolved')
  information=WolfObserver(mask,next(iter(histories)))
  _,self.belief=condition_personal(source.public_state,WolfInformation(mask,information.attacks))
  _,self.root=base.personal(information)
  self.game=NavigationGame(self.root,names=self.names)
  self.anchor=sha256(repr((input_snapshot(public.data),owner,state_key(display))).encode()).hexdigest()[:24]
 def targets(self):
  from .exact import legal_targets
  s=self.root.read();e=self.root._Node__calculation._ClosedCalculation__engine
  return tuple(self.names.display(p) for p in legal_targets(s.physical,e.rules,e.strategy))
 def result(self,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS):
  from .board_roles import private_role_rates
  from .player_view import private_api_rows
  from .evaluation_branch import physical_board
  from .model_a_public import horizon_for_action
  s=self.root.read();e=self.root._Node__calculation._ClosedCalculation__engine;values={};dawn={}
  info=WolfInformation(s.observer.initial_roster,s.observer.attacks)
  with calculation_budget(max_work,max_seconds=max_seconds),e.group_scope(self.root.groups),self.root.relation_scope(),e.actor_scope(info):
   for displayed in self.targets():
    target=self.names.canonical(displayed)
    values[displayed]=e.act(*s[:3],target,s.private,s.observer,physical=s.physical)
    dawn[displayed]=horizon_for_action(e,s.public,s.public_state,s.past,target,s.private,observer=s.observer)
   e.solve(*s,physical=s.physical)
   record=e.evaluation_graph.personal_program(s,self.root.groups)
  belief_source=replace(s,private=self.belief,physical=physical_board(s.public,self.belief,s.physical))
  belief=transport_view_source(belief_source,self.names.forward).physical
  return dict(players=private_api_rows(private_role_rates(belief),targets=tuple(values),final_values=values,dawn_for=dawn.get),acquisitions=[],reason='仲間と襲撃履歴を保持し、公開方針で評価します。',recorded_attacks='evaluated' if record is not None else 'value-only',private_view=self.export())
