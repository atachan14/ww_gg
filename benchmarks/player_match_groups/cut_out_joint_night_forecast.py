"""Opt-in one-night Forecast experiment with SavedOrigin transport readback."""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from collections import Counter
from weakref import WeakKeyDictionary
from hashlib import sha256
from math import comb,prod
from types import SimpleNamespace
from time import perf_counter
from .cut_out_model_a import InitialModelASpec,adapt_model_a
from .cut_out_saved_recipes import SavedCutOutGraph
from .cut_out_uniform_game import CutOutUniformEngine,OfficialLabelledEngine,RecordedPolicy,OwnView
from .cut_out_inherited_groups import InheritedGroupRegistry,InheritedGroups
from .cut_out_day_night import point_fix
from .cut_out_user_seven_source import synthetic_registry,issue,require_bound as require_seven
from .cut_out_user_seven_source_fixture import ok
from .cut_out_joint_night_prototype import move_law,move_board
from werewolf.exact import Rules,legal_targets
from werewolf.seer_acquisition import SeerReport
from werewolf.actor_information import condition_actor_state
from werewolf.evaluation_branch import ContinuationInputs,ActionInputs,physical_board
from werewolf.board_future import ActionEvidence,GeneratedBoard,kernel_snapshot,outcome_key,remember,calculation_origin,condition_recipe
from werewolf.action_flow import resolve_action
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.calculation_budget import calculation_budget
from werewolf.forecast_result import Forecast
from werewolf.model_a_public import horizon_for_action

_issued=WeakKeyDictionary();_transports=WeakKeyDictionary()

@dataclass(frozen=True,eq=False)
class ForecastCertificate:
 registry:object
 witness:object
 source:object
 request:object
 groups:tuple
 preprocessing_seconds:float


def make_case(players=5):
 start=perf_counter()
 if type(players)is not int or players not in (4,5,7):raise Pending('joint_forecast_fixed_cases_only')
 if players==7:
  r=ok(synthetic_registry());w=ok(issue(r));root_groups=w.contexts[-1].groups;target=5
 else:
  spec=InitialModelASpec(players,('seer',)+('latent',)*(players-1),True,mediums=0,rules=Rules(initial_seer='random_white'),reports=(SeerReport(1,1,1,3,'white'),))
  r=SavedCutOutGraph(adapt_model_a(spec));w=None;root_groups=r.engine.start().groups;target=3
 source=r.origin();source=replace(source,physical=physical_board(source.public,source.private,source.physical))
 e=InformationSetForecast(r.engine.baseline.rules,r.engine.baseline.strategy,exact_renaming=False,retire_uninformative_scans=False);e.retain_joint_guard_history=True
 with calculation_budget(200000,max_seconds=3),calculation_origin(r.data):
  remember(e,r.root,source)
  payload=ActionInputs(source.public_state,source.past,source.private,None,source.physical)
  acquired,outcomes=resolve_action(source.public,payload,target,e.action_policy)
  if len(outcomes)!=1 or outcomes[0].board.winner:raise Pending('joint_forecast_fixed_nonterminal_death_only')
  child=e.action_policy.project(source.public,acquired,outcomes[0],target)
  request=r.root.child(ActionEvidence(kernel_snapshot(e),target,outcome_key(outcomes[0]),False),None)
  if request.roles()!=child:raise Pending('joint_forecast_saved_prefix_mismatch')
 cap=ForecastCertificate(r,w,child,request,point_fix(root_groups,target),perf_counter()-start)
 _issued[cap]=(r,r.data,r.engine,r.origin,r.root,r.data.inputs,r.data.to_game().get('revision',0),child,request,cap.groups,repr((r.engine.baseline.rules,r.engine.baseline.strategy)))
 return cap


def require(cap,*,source=None):
 if type(cap)is not ForecastCertificate or cap not in _issued:raise Pending('joint_forecast_issued_receipt_required')
 r,data,engine,origin,root,inputs,rev,s,request,groups,settings=_issued[cap]
 if cap.registry is not r or r.data is not data or r.engine is not engine or r.origin is not origin or r.root is not root or data.inputs!=inputs or data.to_game().get('revision',0)!=rev or cap.source is not s or cap.request is not request or cap.groups!=groups:raise Pending('joint_forecast_owner_revision_source_changed')
 if repr((engine.baseline.rules,engine.baseline.strategy))!=settings:raise Pending('joint_forecast_settings_changed')
 if cap.witness is not None:require_seven(r,cap.witness)
 if source is not None and source!=s:raise Pending('joint_forecast_one_sided_carrier_change')
 if s.public.phase!='night' or len(s.public.alive)>4:raise Pending('joint_forecast_small_night_only')
 strategy=r.engine.baseline.strategy
 if (strategy.day,strategy.night,strategy.fake_reports)!=('random',)*3 or strategy.include_self_bite or s.public.initial_hunter_count:raise Pending('joint_forecast_uniform_H0_only')
 return s


def view_source(cap,view=None):
 s=require(cap)
 if view is None:return s,cap.request,cap.groups
 if type(view)is not OwnView or view.role not in ('wolf','medium','seer','villager') or not 1<=view.player<=s.public.player_count or any(a.player!=view.player for a in view.acquisitions):raise Pending('joint_forecast_explicit_own_view_only')
 private=condition_actor_state(s.private,view.accepts)
 target=replace(s,private=private,observer=view,physical=physical_board(s.public,private,s.physical))
 recipe=condition_recipe(s,target)
 if recipe is None:raise Pending('joint_forecast_view_recipe_unproved')
 fixed={view.player}|{a.target for a in view.acquisitions}
 return target,cap.request.child(recipe,None),point_fix(cap.groups,*sorted(fixed))

@dataclass(frozen=True)
class Orbit:
 roster:int
 attacks:tuple
 target:int
 groups:tuple
 counts:tuple
 multiplicity:int
 mass:F


def produce(cap,source,groups):
 """Occupancy descriptors read once from P; no info x target enumeration."""
 require(cap);expected,_,expected_groups=view_source(cap,source.observer)
 if source!=expected or groups!=expected_groups:raise Pending('joint_forecast_Q_P_view_receipt_mismatch')
 b=source.public
 attacks={h.attacks for h in source.private.hypotheses}
 if len(attacks)!=1:raise Pending('joint_forecast_attack_history_pattern_unproved')
 attacks=next(iter(attacks))
 signatures={tuple(sum(bool(h.roles[0]&(1<<(p-1))) for p in g) for g in groups) for h in source.private.hypotheses}
 result=[]
 for counts in sorted(signatures):
  roster=sum(1<<(p-1) for g,k in zip(groups,counts) for p in g[:k])
  multiplicity=prod(comb(len(g),k) for g,k in zip(groups,counts))
  mass=sum((h.mass for h in source.private.hypotheses if h.roles[0]==roster and h.attacks==attacks),F())
  if not mass:raise Pending('joint_forecast_incomplete_occupancy_orbit')
  legal=tuple(p for p in b.alive if not roster&(1<<(p-1)))
  for group in groups:
   choices=tuple(p for p in group if p in legal)
   if choices:result.append(Orbit(roster,attacks,choices[0],groups,counts,multiplicity*len(choices),mass*multiplicity*F(len(choices),len(legal))))
 if sum((o.mass for o in result),F())!=1:raise Pending('joint_forecast_orbit_mass_unproved')
 return tuple(result)


def members(cap,source,orbit):
 """Output-only assignment restoration; no continuation generation/dedup."""
 from itertools import combinations,product
 produced=0;b=source.public;repwolf={p for p in range(1,b.player_count+1) if orbit.roster&(1<<(p-1))}
 for selected in product(*(tuple(combinations(g,k)) for g,k in zip(orbit.groups,orbit.counts))):
  wolves=set(p for subset in selected for p in subset);target_group=next(g for g in orbit.groups if orbit.target in g)
  for target in target_group:
   if target not in b.alive or target in wolves:continue
   mapping={}
   for group,assigned in zip(orbit.groups,selected):
    oldw=[p for p in group if p in repwolf];neww=list(assigned)
    fixed={orbit.target:target} if orbit.target in group else {}
    fixed.update(zip(oldw,neww))
    for old,new in zip((p for p in group if p not in fixed),(p for p in group if p not in fixed.values())):fixed[old]=new
    mapping.update(fixed)
   produced+=1;yield tuple(mapping[p] for p in range(1,b.player_count+1))
 if produced!=orbit.multiplicity:raise Pending('joint_forecast_label_multiplicity_mismatch')


class CurrentGroups(InheritedGroupRegistry):
 def __init__(self,cap):
  self.contexts={};self.by_board={};self.stats=Counter(root_group_reads=0,issued_joint_source=1)
  s=require(cap);self.install(InheritedGroups(s.public,s.public_state,s.past,cap.groups))


class FullRecordedPolicy(RecordedPolicy):
 def outcomes(self,b,payload,target):
  outcomes=super().outcomes(b,payload,target)
  if not getattr(self.engine,'_board_evidence_snapshot',False):self.engine.full_branch_records.append((b,payload,target,outcomes))
  return outcomes

class JointForecastEngine(CutOutUniformEngine):
 def __init__(self,graph,*,cap,**kwargs):
  self.cap=cap;super().__init__(graph,**kwargs);self.action_policy=FullRecordedPolicy(self);self.full_branch_records=[];self.root_orbits=()
 def make_group_registry(self,graph):return CurrentGroups(self.cap)
 def solve(self,b,s,past,private,observer,*,physical=None):
  root=require(self.cap)
  if not b.winner and b.phase=='night' and b.day!=root.public.day:raise Pending('joint_forecast_multiple_generated_nights_unproved')
  if (b,s,past)==(root.public,root.public_state,root.past):
   expected,request,groups=view_source(self.cap,self.view)
   if (private,observer)!=(expected.private,expected.observer):raise Pending('joint_forecast_unbound_root_private')
   context=replace(expected,physical=physical_board(b,private,physical));self.root_orbits=produce(self.cap,context,groups)
   self.root_context=context;self.root_request=request;value=F()
   for orbit in self.root_orbits:
    own=condition_actor_state(private,lambda h:h.roles[0]==orbit.roster and h.attacks==orbit.attacks)
    value+=orbit.mass*self.act(b,s,past,orbit.target,own,observer,physical=physical_board(b,own,context.physical))
   self.costs['joint_root_representatives']=len(self.root_orbits);self.costs['joint_literal_pairs']=sum(o.multiplicity for o in self.root_orbits)
   return value
  return super().solve(b,s,past,private,observer,physical=physical)

class LabelledForecastEngine(OfficialLabelledEngine):
 def solve(self,b,*args,**kwargs):
  root=self.graph.origin().public
  if not b.winner and b.phase=='night' and b.day!=root.day:raise Pending('joint_forecast_multiple_generated_nights_unproved')
  return super().solve(b,*args,**kwargs)
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.action_policy=FullRecordedPolicy(self);self.full_branch_records=[]

class ExperimentalGraph(SavedCutOutGraph):
 def __init__(self,cap):
  self.cap=cap;self.engine=cap.registry.engine;self.data=cap.registry.data;self.root=cap.request;self.problem=None
 def origin(self):return require(self.cap)


def evaluate(cap,view=None,reference=False):
 from .cut_out_max_fixture import complete_table
 source,request,groups=view_source(cap,view);graph=ExperimentalGraph(cap)
 engine=LabelledForecastEngine(graph,view=view) if reference else JointForecastEngine(graph,cap=cap,view=view)
 engine.capture_terminal=True
 with calculation_budget(1000000,max_seconds=5),calculation_origin(graph.data):
  remember(engine,request,source)
  value=engine.solve(*source,physical=source.physical)
  targets=legal_targets(source.physical,engine.rules,engine.strategy)
  actions=tuple((p,engine.act(*source[:3],p,source.private,source.observer,physical=source.physical)) for p in targets)
  horizon=tuple((p,horizon_for_action(engine,source.public,source.public_state,source.past,p,source.private,observer=source.observer)) for p in targets)
 result=Forecast(value,actions,horizon)
 return result,engine,complete_table(graph,result,view)

@dataclass(frozen=True,eq=False)
class TransportEvidence:
 cap:object
 expected:object
 mapping:tuple
 def __call__(self,source):
  if self not in _transports or _transports[self]!=(self.cap,self.expected,self.mapping):raise Pending('joint_forecast_unissued_transport')
  require(self.cap)
  if source!=self.expected:raise Pending('joint_forecast_transport_source_changed')
  q=move_law(source.public_state,self.mapping);p=move_law(source.private,self.mapping)
  if source.observer is not None and (self.mapping[source.observer.player-1]!=source.observer.player or any(self.mapping[a.target-1]!=a.target for a in source.observer.acquisitions)):raise Pending('joint_forecast_view_not_fixed')
  past=tuple(sorted(replace(r,player=self.mapping[r.player-1],target=self.mapping[r.target-1]) for r in source.past))
  return ContinuationInputs(move_board(source.public,q,self.mapping),q,past,p,source.observer,move_board(source.physical,p,self.mapping))


def transport_request(cap,request,expected,mapping):
 require(cap);n=cap.source.public.player_count
 if type(mapping)is not tuple or len(mapping)!=n or any(type(p)is not int for p in mapping) or set(mapping)!=set(range(1,n+1)) or any({mapping[p-1] for p in g}!=set(g) for g in cap.groups):raise Pending('joint_forecast_transport_outside_proved_blocks')
 op=TransportEvidence(cap,expected,mapping);_transports[op]=(cap,expected,mapping)
 return request.child(op,None)