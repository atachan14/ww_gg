"""Separate opt-in two-night induction, minimum six-player W1/S1/H0 cases."""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from collections import Counter
from math import comb,prod
from weakref import WeakKeyDictionary
from .cut_out_joint_night_forecast import *
from .cut_out_uniform_game import CutOutUniformEngine,OfficialLabelledEngine
from werewolf.board_future import ConditionEvidence,PublicationEvidence,source_key

_nodes=WeakKeyDictionary()

@dataclass(frozen=True,eq=False)
class NightNode:
 cap:object
 source:object
 request:object
 groups:tuple
 orbits:tuple


def issue_node(engine,source,request):
 cap=engine.cap;root=require(cap)
 if cap.night_limit!=2 or source.public.phase!='night' or not root.public.day<=source.public.day<root.public.day+2:raise Pending('joint_two_night_scope')
 if request not in engine.trusted_requests or request.origin is not cap.request.origin or request.history[:len(cap.request.history)]!=cap.request.history:raise Pending('joint_two_night_unowned_recipe')
 if any(type(op) not in (ActionEvidence,ConditionEvidence,PublicationEvidence) for op in request.history):raise Pending('joint_two_night_unknown_recipe')
 if request.roles()!=source:raise Pending('joint_two_night_Q_P_source_mismatch')
 context=engine.inherited_groups.require(source.public,source.public_state,source.past)
 groups=engine.groups(source.public,source.past,source.private,source.observer,public_state=source.public_state)
 # Existing completed action/acquisition/publication receipts refine groups;
 # no world permutation search or reconstruction from an initial prior here.
 if source.observer!=engine.view:raise Pending('joint_two_night_view_mismatch')
 attacks={h.attacks for h in source.private.hypotheses}
 if len(attacks)!=1:raise Pending('joint_two_night_attack_signature_unproved')
 attacks=next(iter(attacks));result=[];b=source.public
 signatures={tuple(sum(bool(h.roles[0]&(1<<(p-1))) for p in g) for g in groups) for h in source.private.hypotheses}
 for counts in sorted(signatures):
  roster=sum(1<<(p-1) for g,k in zip(groups,counts) for p in g[:k])
  mult=prod(comb(len(g),k) for g,k in zip(groups,counts));mass=sum((h.mass for h in source.private.hypotheses if h.roles[0]==roster and h.attacks==attacks),F())
  if not mass:raise Pending('joint_two_night_occupancy_unproved')
  legal=tuple(p for p in b.alive if not roster&(1<<(p-1)))
  for g in groups:
   choices=tuple(p for p in g if p in legal)
   if choices:result.append(Orbit(roster,attacks,choices[0],groups,counts,mult*len(choices),mass*mult*F(len(choices),len(legal))))
 if sum((o.mass for o in result),F())!=1:raise Pending('joint_two_night_mass_unproved')
 node=NightNode(cap,source,request,groups,tuple(result));_nodes[node]=(cap,source,request,groups,node.orbits,context)
 return node


def require_node(node):
 if type(node)is not NightNode or node not in _nodes:raise Pending('joint_two_night_issued_node_required')
 cap,source,request,groups,orbits,context=_nodes[node]
 require(cap)
 if (node.cap,node.source,node.request,node.groups,node.orbits)!=(cap,source,request,groups,orbits):raise Pending('joint_two_night_node_changed')
 return node


class TwoRecordedPolicy(FullRecordedPolicy):
 def project(self,b,payload,outcome,target):
  result=super().project(b,payload,outcome,target)
  if not getattr(self.engine,'_board_evidence_snapshot',False):
   request=self.engine.board_sources[source_key(result.public,ActionInputs(result.public_state,result.past,result.private,result.observer,result.physical),self.engine)]
   self.engine.trusted_requests.add(request)
  return result


class TwoNightEngine(JointForecastEngine):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.trusted_requests=set();self.joint_nodes=[];self.action_policy=TwoRecordedPolicy(self)
 def solve(self,b,s,past,private,observer,*,physical=None):
  root=require(self.cap)
  if b.winner:return F(b.winner=='village')
  if b.phase!='night':return CutOutUniformEngine.solve(self,b,s,past,private,observer,physical=physical)
  if not root.public.day<=b.day<root.public.day+2:raise Pending('joint_two_night_third_night_unproved')
  physical=physical_board(b,private,physical);key=(b,s,past,private,observer,physical)
  if key in self.values:return self.values[key]
  source=ContinuationInputs(b,s,past,private,observer,physical)
  request=self.board_sources.get(source_key(b,ActionInputs(s,past,private,observer,physical),self))
  if request is None:raise Pending('joint_two_night_source_recipe_required')
  node=issue_node(self,source,request);self.joint_nodes.append(node)
  if b==root.public:self.root_orbits=node.orbits;self.root_context=source;self.root_request=request
  self.costs['joint_nodes_night'+str(b.day)]+=1
  self.costs['joint_calls_night'+str(b.day)]+=len(node.orbits)
  self.costs['joint_literal_night'+str(b.day)]+=sum(o.multiplicity for o in node.orbits)
  value=F()
  for orbit in node.orbits:
   own=condition_actor_state(private,lambda h:h.roles[0]==orbit.roster and h.attacks==orbit.attacks)
   value+=orbit.mass*self.act(b,s,past,orbit.target,own,observer,physical=physical_board(b,own,physical))
  self.values[key]=value;return value


class TwoNightReference(LabelledForecastEngine):
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs);self.night_inputs={}
 def solve(self,b,s,past,private,observer,*,physical=None):
  root=self.graph.origin().public
  if not b.winner and b.phase=='night':
   if b.day>=root.day+2:raise Pending('joint_two_night_third_night_unproved')
   source=ContinuationInputs(b,s,past,private,observer,physical_board(b,private,physical));self.night_inputs[source]=source
  return OfficialLabelledEngine.solve(self,b,s,past,private,observer,physical=physical)


def evaluate_two(cap,view=None,reference=False):
 from .cut_out_max_fixture import complete_table
 if cap.night_limit!=2:raise Pending('joint_two_night_explicit_cap_required')
 source,request,groups=view_source(cap,view);graph=ExperimentalGraph(cap)
 engine=TwoNightReference(graph,view=view) if reference else TwoNightEngine(graph,cap=cap,view=view)
 engine.capture_terminal=True
 if not reference:engine.trusted_requests.add(request)
 with calculation_budget(2000000,max_seconds=30),calculation_origin(graph.data):
  remember(engine,request,source)
  value=engine.solve(*source,physical=source.physical)
  targets=legal_targets(source.physical,engine.rules,engine.strategy)
  actions=tuple((p,engine.act(*source[:3],p,source.private,source.observer,physical=source.physical)) for p in targets)
  dawn=tuple((p,horizon_for_action(engine,source.public,source.public_state,source.past,p,source.private,observer=source.observer)) for p in targets)
 result=Forecast(value,actions,dawn)
 return result,engine,complete_table(graph,result,view)