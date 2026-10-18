"""Limited actual7/W2 intermediate scopes, never a full initial Forecast."""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from weakref import WeakKeyDictionary
from time import perf_counter
from .cut_out_joint_night_prototype import make_case as initial_night,produce as initial_orbits,labels as initial_labels
from .cut_out_joint_night_forecast import *
from .cut_out_joint_night_forecast import _issued
from .cut_out_joint_two_nights import TwoNightEngine,TwoNightReference,NightNode,structural_orbits,_nodes
from werewolf.board_future import PublicationEvidence,ConditionEvidence,publication_key,source_key,SavedOrigin
from werewolf.seer_acquisition import normalize

_choices=WeakKeyDictionary()
_mid=WeakKeyDictionary()


def _check_choice(op):
 if type(op)is not JointObservedChoice or op not in _choices:raise Pending('seven_mid_joint_choice_not_issued')
 r,w,data,rev,expected,target,observation,settings=_choices[op]
 require_seven(r,w)
 if r.data is not data or data.to_game().get('revision',0)!=rev or (op.expected,op.target,op.observation)!=(expected,target,observation):raise Pending('seven_mid_joint_choice_owner_changed')
 if repr((op.engine.rules,op.engine.strategy))!=settings:raise Pending('seven_mid_joint_choice_settings')
 if (op.engine.strategy.day,op.engine.strategy.night,op.engine.strategy.fake_reports)!=('random',)*3:raise Pending('seven_mid_uniform_only')
 return r,w

@dataclass(frozen=True,eq=False)
class JointObservedChoice:
 engine:object
 expected:object
 target:int
 observation:tuple
 def likelihood(self,source):
  _check_choice(self)
  if source!=self.expected:raise Pending('seven_mid_joint_choice_source_changed')
  b=source.public
  return sum((h.mass/F(len(b.alive)-(h.roles[0]&b.alive_mask).bit_count()) for h in source.private.hypotheses if not h.roles[0]&(1<<(self.target-1))),F())
 def __call__(self,source):
  chance=self.likelihood(source)
  if not chance:raise Pending('seven_mid_joint_choice_zero_support')
  b=source.public
  hs=tuple(replace(h,mass=h.mass/F(len(b.alive)-(h.roles[0]&b.alive_mask).bit_count())) for h in source.private.hypotheses if not h.roles[0]&(1<<(self.target-1)))
  private=replace(source.private,hypotheses=normalize(hs))
  weighted=replace(source,private=private,physical=physical_board(b,private,source.physical))
  return ActionEvidence(self.engine,self.target,self.observation,False)(weighted)


def choice_step(r,w,source,target,engine):
 if engine.rules!=r.engine.baseline.rules or engine.strategy!=r.engine.baseline.strategy:raise Pending('seven_mid_joint_choice_not_configured_policy')
 if target not in (3,4) or any(h.roles[0]&(1<<(target-1)) for h in source.public_state.hypotheses):raise Pending('seven_mid_only_known_nonwolf_observations_proved')
 from werewolf.exact import action_outcomes
 outs=action_outcomes(source.physical,target,engine.rules,engine.strategy)
 if len(outs)!=1 or outs[0].board.winner:raise Pending('seven_mid_single_continuing_night_observation_required')
 op=JointObservedChoice(engine,source,target,outcome_key(outs[0]));_choices[op]=(r,w,r.data,r.data.to_game().get('revision',0),source,target,op.observation,repr((engine.rules,engine.strategy)))
 return op


def rebind_choice(op,engine):
 r,w=_check_choice(op);return choice_step(r,w,op.expected,op.target,engine)


def make_mid(case='agree',*,roster=None):
 start=perf_counter()
 if case not in ('agree','disagree','count-change'):raise Pending('seven_mid_report_or_prefix_unproved')
 if roster is not None and (case!='count-change' or roster!=17):raise Pending('seven_mid_roster_probe_unproved')
 executed,victim=(1,3) if case=='count-change' else (3,4)
 first=initial_night(executed);r=first.registry;w=first.witness
 root=r.origin();engine=InformationSetForecast(r.engine.baseline.rules,r.engine.baseline.strategy,exact_renaming=False,retire_uninformative_scans=False);engine.retain_joint_guard_history=True
 with calculation_budget(500000,max_seconds=10):
  outs=engine.physical_children(physical_board(root.public,root.private,root.physical),executed)
  if len(outs)!=1:raise Pending('seven_mid_initial_execution_unproved')
  request=r.root.child(ActionEvidence(kernel_snapshot(engine),executed,outcome_key(outs[0]),False),None)
  before=request.roles()
  if before!=first.source:raise Pending('seven_mid_first_night_descriptor_mismatch')
  if roster is not None:
   own=condition_actor_state(before.private,lambda h:h.roles[0]==roster)
   conditioned=replace(before,private=own,physical=physical_board(before.public,own,before.physical))
   recipe=condition_recipe(before,conditioned)
   if recipe is None:raise Pending('seven_mid_roster_recipe_unproved')
   request=request.child(recipe,None);before=conditioned
  op=choice_step(r,w,before,victim,kernel_snapshot(engine));chance=op.likelihood(before)
  request=request.child(op,None);prepub=request.roles()
  branches=engine.morning(prepub.public,prepub.public_state,prepub.past)
  def wanted(past):
   rows={row.player:(row.target,row.color) for row in past[len(prepub.past):]}
   desired={2:(5,'white')} if case=='count-change' else {1:(5,'black' if case=='agree' else 'white'),2:(5,'black')}
   return rows==desired
  qrows=[row for row in branches if wanted(row[3])]
  prows=[row for row in engine.push(prepub.public_state,prepub.private,branches) if wanted(row[3])]
  if not qrows:raise Pending('seven_mid_public_report_support_zero')
  if not prows:raise Pending('seven_mid_positive_Q_zero_P_report: exe1/bite3/private wolves1+5/P2 white5; P2 true and5 wolf; Q='+str(qrows[0][0])+' P=0')
  if len(qrows)!=1 or len(prows)!=1:raise Pending('seven_mid_report_vector_not_unique')
  publication=PublicationEvidence(kernel_snapshot(engine),publication_key(qrows[0][1],qrows[0][3]))
  request=request.child(publication,None);source=request.roles()
  groups=point_fix(first.groups,victim);rows=source.past[len(prepub.past):];fixed={row.target for row in rows}
  paired=(case=='agree' and any(group==(1,2) for group in groups) and len(rows)==2 and {row.player for row in rows}=={1,2} and len({(row.acquired_day,row.published_day,row.target,row.color) for row in rows})==1)
  if not paired:fixed.update(row.player for row in rows)
  groups=point_fix(groups,*sorted(fixed))
 cap=ForecastCertificate(r,w,source,request,groups,perf_counter()-start,1,'seven-mid')
 _issued[cap]=(r,r.data,r.engine,r.origin,r.root,r.data.inputs,r.data.to_game().get('revision',0),source,request,groups,repr((r.engine.baseline.rules,r.engine.baseline.strategy)),1,'seven-mid')
 _mid[cap]=dict(case=case,choice=chance,Q_report=qrows[0][0],P_report=prows[0][0],before=before,prepublication=prepub,first=first,paired_public_receipt=paired)
 require(cap);return cap


def issue_mid_node(engine,source,request):
 cap=engine.cap;root=require(cap)
 if cap.source_scope!='seven-mid' or source.public.phase!='night' or source.public.day!=root.public.day or len(source.public.alive)!=4:raise Pending('seven_mid_one_followup_night_scope')
 if request not in engine.trusted_requests or request.origin is not cap.request.origin or request.history[:len(cap.request.history)]!=cap.request.history:raise Pending('seven_mid_unowned_night_source')
 if any(type(op) not in (ActionEvidence,ConditionEvidence,PublicationEvidence) for op in request.history[len(cap.request.history):]):raise Pending('seven_mid_unproved_future_recipe')
 if request.roles()!=source:raise Pending('seven_mid_Q_P_recipe_mismatch')
 context=engine.inherited_groups.require(source.public,source.public_state,source.past)
 groups=engine.groups(source.public,source.past,source.private,source.observer,public_state=source.public_state)
 orbits=structural_orbits(source,groups)
 node=NightNode(cap,source,request,groups,orbits);_nodes[node]=(cap,source,request,groups,orbits,context)
 return node

class SevenMidEngine(TwoNightEngine):
 def solve(self,b,s,past,private,observer,*,physical=None):
  root=require(self.cap)
  if b.winner:return F(b.winner=='village')
  if observer is not None:raise Pending('seven_mid_public_only')
  if b.phase!='night':return CutOutUniformEngine.solve(self,b,s,past,private,observer,physical=physical)
  if b.day!=root.public.day:raise Pending('seven_mid_more_than_one_future_night_unproved')
  physical=physical_board(b,private,physical);key=(b,s,past,private,observer,physical)
  if key in self.values:return self.values[key]
  source=ContinuationInputs(b,s,past,private,observer,physical)
  request=self.board_sources.get(source_key(b,ActionInputs(s,past,private,observer,physical),self))
  if request is None:raise Pending('seven_mid_source_recipe_missing')
  node=issue_mid_node(self,source,request);self.joint_nodes.append(node);value=F()
  self.costs['joint_midnight_representatives']+=len(node.orbits);self.costs['joint_midnight_literal_pairs']+=sum(o.multiplicity for o in node.orbits)
  for orbit in node.orbits:
   own=condition_actor_state(private,lambda h:h.roles[0]==orbit.roster and h.attacks==orbit.attacks)
   value+=orbit.mass*self.act(b,s,past,orbit.target,own,None,physical=physical_board(b,own,physical))
  self.values[key]=value;return value

class SevenMidReference(TwoNightReference):
 def solve(self,b,s,past,private,observer,*,physical=None):
  root=self.graph.origin().public
  if not b.winner and b.phase=='night':
   if b.day!=root.day:raise Pending('seven_mid_reference_future_scope')
   source=ContinuationInputs(b,s,past,private,observer,physical_board(b,private,physical));self.night_inputs[source]=source
  return OfficialLabelledEngine.solve(self,b,s,past,private,observer,physical=physical)


def evaluate_mid(cap,reference=False):
 from .cut_out_max_fixture import complete_table
 source=require(cap);graph=ExperimentalGraph(cap)
 if cap not in _mid:raise Pending('seven_mid_issued_scope_required')
 engine=SevenMidReference(graph) if reference else SevenMidEngine(graph,cap=cap)
 engine.capture_terminal=True
 if not reference:engine.trusted_requests.add(cap.request)
 with calculation_budget(2000000,max_seconds=30),calculation_origin(graph.data):
  remember(engine,cap.request,source)
  value=engine.solve(*source,physical=source.physical)
  actions=tuple((p,engine.act(*source[:3],p,source.private,None,physical=source.physical)) for p in source.public.alive)
  dawn=tuple((p,horizon_for_action(engine,source.public,source.public_state,source.past,p,source.private)) for p in source.public.alive)
 result=Forecast(value,actions,dawn);return result,engine,complete_table(graph,result,None)