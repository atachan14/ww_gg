"""Seer Table evidence bound to the public occurrence and existing typed evaluator."""
from dataclasses import replace,asdict
from hashlib import sha256
from threading import RLock
from .guard_view_document import GuardViewDocument
from .actor_information import PersonalInformation,condition_personal
from .seer_intervention import SeerObserver
from .private_view import condition_private
from .navigation_game import NavigationGame
from .public_convergence import state_key,transport_view_source
from .calculation_tree import input_snapshot
from .calculation_budget import calculation_budget,DEFAULT_MAX_WORK,DEFAULT_MAX_SECONDS
from .information_set_forecast import Pending

class SeerViewDocument(GuardViewDocument):
 role='seer'
 @staticmethod
 def observation_scope(board):
  # Guard effects already have retained exact records even without a CO.
  # Unguarded all-hidden roots keep their legitimate value-only adapter.
  return board.initial_hunter_count==1 or any(board.claims[p-1] in ('seer','medium') for p in board.alive)
 @staticmethod
 def supports(public,players):
  if hasattr(public.game.node,'owned'):return False # Explicit private request retains its existing compatibility adapter.
  if len(players)!=1:return False
  node=public.game.node
  s=node.read();strategy=node._Node__calculation._ClosedCalculation__strategy
  return (type(players[0])is int and 1<=players[0]<=s.public.player_count
   and SeerViewDocument.observation_scope(s.public)
   and strategy.disclosure_for('seer')=='all'
   and ((strategy.day,strategy.night,strategy.fake_reports)==('random',)*3 or
    not s.public.initial_hunter_count and (strategy.day,strategy.night,strategy.fake_reports)==('max',)*3
    and s.public.claims[public.game.occurrence.names.canonical(players[0])-1]=='seer'))
 def __init__(self,public,owner,players,results,*,target=None):
  occurrence=public.game.history.occurrence(owner);base=public.game.history.state(owner).node
  source=base.read();self.names=occurrence.names
  strategy=base._Node__calculation._ClosedCalculation__strategy
  if (strategy.day,strategy.night,strategy.fake_reports) not in (('random',)*3,('max',)*3) or strategy.disclosure_for('seer')!='all':raise Pending('seer_table_recorded_strategy_unimplemented')
  if source.observer is not None:raise ValueError('Choose seer view from public occurrence')
  if source.public.phase!='night' or source.public.winner:raise ValueError('Seer Table view requires ongoing night')
  self.public=public;self.owner=owner;self.data=public.data;self.lock=RLock();self.revision=0;self.views=None
  self.players=tuple(players);self.results=tuple(dict(r) for r in results);self.target=target
  display=transport_view_source(source,self.names.forward)
  view=condition_private(display.public,'seer',self.players,self.results,rules=public.data.game_data.rules)
  from .public_convergence import transport_record
  inverse=tuple(self.names.canonical(p) for p in range(1,source.public.player_count+1))
  acquisitions=tuple(transport_record(a,inverse) for a in view.acquisitions)
  information=PersonalInformation(self.names.canonical(self.players[0]),'seer',acquisitions)
  if strategy.day=='max' and (source.public.initial_hunter_count or source.public.claims[information.actor-1]!='seer'):raise Pending('seer_table_recorded_strategy_unimplemented')
  if not self.observation_scope(source.public):raise Pending('seer_table_value_only_root_reduction')
  _,self.belief=condition_personal(source.public_state,information)
  _,root=base.personal(information);self.root=root
  histories={tuple(a for a in h.acquisitions if a.player==information.actor) for h in root.read().private.hypotheses}
  if len(histories)!=1:raise Pending('seer_view_past_private_history_unresolved')
  self.acquisitions=next(iter(histories))
  if target is not None:
   if target not in self.targets():raise ValueError('Illegal own scan target')
   _,self.root=base.personal(SeerObserver(information.actor,self.acquisitions,source.public.day+1,self.names.canonical(target)))
  self.game=NavigationGame(self.root,names=self.names)
  self.anchor=sha256(repr((input_snapshot(public.data),owner,state_key(display))).encode()).hexdigest()[:24]
 def targets(self):
  from .seer_future_uniform import candidates
  source=self.root.read();actor=source.observer.actor
  choices={candidates(h,actor,source.public.alive) for h in source.private.hypotheses}
  if len(choices)!=1:raise Pending('seer_view_target_generation_support_unresolved')
  return tuple(self.names.display(p) for p in next(iter(choices)))
 def result(self,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS):
  from .board_roles import private_role_rates
  from .player_view import private_api_rows
  from .evaluation_branch import physical_board
  base=self.public.game.history.state(self.owner).node;source=self.root.read();e=self.root._Node__calculation._ClosedCalculation__engine
  values={};records={}
  with calculation_budget(max_work,max_seconds=max_seconds):
   for target in self.targets():
    _,node=base.personal(SeerObserver(source.observer.actor,self.acquisitions,source.public.day+1,self.names.canonical(target)))
    s=node.read()
    with e.group_scope(node.groups),node.relation_scope():values[target]=e.solve(*s,physical=s.physical)
    records[str(target)]='evaluated' if e.evaluation_graph.personal_program(s,node.groups) is not None else 'value-only'
   with e.group_scope(self.root.groups),self.root.relation_scope():e.solve(*source,physical=source.physical)
   e.evaluation_graph.personal_program(source,self.root.groups)
  belief_source=replace(source,private=self.belief,physical=physical_board(source.public,self.belief,source.physical))
  belief=transport_view_source(belief_source,self.names.forward).physical
  from .public_convergence import transport_record
  acquisitions=[asdict(transport_record(a,self.names.forward)) for a in self.acquisitions]
  return dict(players=private_api_rows(private_role_rates(belief),targets=tuple(values),final_values=values),acquisitions=acquisitions,reason='本人の取得履歴と公開方針で評価します。',recorded_scans=records,private_view=self.export())
