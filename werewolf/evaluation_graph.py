"""Evaluator-owned exact values and lazy public-state refinements.

Count reductions are exact value records, never invented named worlds. A public
refinement uses the existing evaluator transition kernel and verifies its weighted
child values before publishing edges. Private P and public Q stay in each source.
"""
from dataclasses import dataclass
from fractions import Fraction as F

@dataclass(frozen=True)
class ValueRecord:
 value:F
 reduction:str
 counts:tuple=()

@dataclass(frozen=True)
class Edge:
 probability:F
 source:object
 target:int
 observation:object=None

@dataclass(frozen=True)
class Refinement:
 value:F
 edges:tuple
 reason:str='public-state-refinement'
 selection_probability:F|None=None

@dataclass(frozen=True)
class ProgramRecord:
 program:object
 value:F
 evaluated_sources:tuple
 policies:tuple=()
 reason:str='evaluated-role-ordered-program'

@dataclass(frozen=True)
class ArrivalRecord:
 probability:F
 source:object
 target:int
 updates:tuple
 value:F|None

@dataclass(frozen=True)
class PublicProjection:
 edges:tuple
 arrivals:tuple
 value:F|None
 reason:str='evaluated-public-mixture'

@dataclass(frozen=True)
class DayDecisionRecord:
 scores:tuple
 policy:tuple
 information:str='public-Q'
 complete:bool=True

@dataclass(frozen=True)
class EvaluatedOutcome:
 outcome:object
 source:object
 value:F

@dataclass(frozen=True)
class ActionRecord:
 acquired:object
 outcomes:tuple
 value:F
 policies:tuple=()

@dataclass(frozen=True)
class MorningRecord:
 branches:tuple
 value:F

class EvaluationGraph:
 def __init__(self,engine):self.engine=engine;self.values={};self.refinements={};self.programs={};self.projections={};self.day_decisions={};self.actions={};self.mornings={}
 def random_day_scope(self,board,payload):
  from .actor_information import PersonalInformation,GuardInformation,GuardSelection
  from .seer_intervention import SeerObserver
  from .evaluation_branch import ContinuationInputs
  source=ContinuationInputs(board,payload.public_state,payload.past,payload.private,payload.observer,payload.physical)
  return (board.phase=='day' and not board.winner
   and (self.engine.strategy.day,self.engine.strategy.night,self.engine.strategy.fake_reports)==('random',)*3
   and (payload.observer is None or type(payload.observer) in (PersonalInformation,SeerObserver,GuardInformation,GuardSelection))
   and source not in getattr(self.engine,'anonymous_beliefs',{}))
 def record_day_value(self,source,value,reduction='evaluated-random-day-value'):
  if self.random_day_scope(source.public,source):self.values.setdefault(source,ValueRecord(value,reduction))
 def day_refinement(self,source,groups,target,*,evaluate=True):
  if not self.random_day_scope(source.public,source):return None
  from .exact import legal_targets
  from .evaluation_branch import ActionInputs
  from .action_flow import action_flow,resolve_action
  from .board_future import outcome_key
  b=source.public;e=self.engine;groups=tuple(groups)
  if target not in legal_targets(source.physical,e.rules,e.strategy):raise ValueError('Legal execution target required')
  key=(source,groups,target)
  if key in self.refinements:return self.refinements[key]
  payload=ActionInputs(source.public_state,source.past,source.private,source.observer,source.physical)
  record=self.recorded_action(b,payload,target);requested=False
  if record is None and evaluate:
   expected=e.act(*source[:3],target,source.private,source.observer,physical=source.physical)
   record=self.recorded_action(b,payload,target)
   if record is None:
    # A cached scalar/shortcut retained no transition. Only an explicit detail
    # request enters the SAME evaluator flow; normal value solving is unchanged.
    actual=action_flow(b,payload,target,e.action_policy);requested=True
    if actual!=expected:raise ValueError('Requested day detail changed scalar value')
    record=self.recorded_action(b,payload,target)
  if record is None:return None
  acquired=record.acquired;rows=record.outcomes
  if any(row.source is None and row.outcome.context is None for row in rows):
   if not evaluate:return None
   # Compact terminal payoffs have no posterior. Obtain full context only at
   # this requested history boundary, never invent it from a payoff/count.
   acquired,outcomes=resolve_action(b,payload,target,e.action_policy,terminal_payoffs=False)
   old={outcome_key(row.outcome):row for row in rows}
   if len(old)!=len(rows):raise ValueError('Ambiguous retained day observations')
   rebuilt=[]
   for outcome in outcomes:
    row=old[outcome_key(outcome)]
    if row.outcome.probability!=outcome.probability:raise ValueError('Day detail changed outcome mass')
    child=row.source if row.source is not None else e.action_policy._project_roles(b,acquired,outcome,target)
    rebuilt.append(EvaluatedOutcome(outcome,child,row.value))
   rows=tuple(rebuilt);requested=True
  edges=[];weighted=F()
  for row in rows:
   child=row.source
   if child is None:
    if row.outcome.board.winner is None:raise ValueError('Missing continuing day state')
    child=e.action_policy._project_roles(b,acquired,row.outcome,target)
   self.values.setdefault(child,ValueRecord(row.value,'evaluated-day-child' if row.source is not None else 'retained-terminal-context'))
   edges.append(Edge(row.outcome.probability,child,target,outcome_key(row.outcome)));weighted+=row.outcome.probability*row.value
  if sum(edge.probability for edge in edges)!=1 or weighted!=record.value:raise ValueError('Recorded day mass/value changed')
  probability=F(1,len(legal_targets(source.public,e.rules,e.strategy)))
  result=Refinement(record.value,tuple(edges),'requested-evaluated-day-detail' if requested else 'evaluated-random-day-action',probability)
  self.refinements[key]=result
  return result
 def hunter_flow_scope(self,board,payload):
  e=self.engine
  from .actor_information import PersonalInformation,GuardInformation,GuardSelection
  from .seer_intervention import SeerObserver
  return (board.initial_hunter_count==1 and (payload.observer is None or type(payload.observer) in (PersonalInformation,SeerObserver,GuardInformation,GuardSelection))
   and (e.strategy.day,e.strategy.night,e.strategy.fake_reports)==('random',)*3)
 def personal_flow_scope(self,board,payload):
  """Supported seer ownership through the ordinary evaluated action flow."""
  from .actor_information import PersonalInformation
  from .seer_intervention import SeerObserver
  e=self.engine;observer=payload.observer
  return (not board.initial_hunter_count and
   (type(observer)is SeerObserver or type(observer)is PersonalInformation and observer.role=='seer')
   and (e.strategy.day,e.strategy.night,e.strategy.fake_reports)==('random',)*3
   and any(c in ('seer','medium') for c in board.claims) and e.strategy.disclosure_for('seer')=='all')
 def recorded_flow_scope(self,board,payload):
  return self.hunter_flow_scope(board,payload) or self.personal_flow_scope(board,payload)
 def record_action(self,board,payload,target,acquired,outcomes,value):
  if not (self.random_day_scope(board,payload) or self.recorded_flow_scope(board,payload)):return
  from .actor_information import wolf_information_keys
  policies=() if board.phase=='day' else tuple((info,self.engine.policies.get((board,payload.public_state,payload.past,info))) for info in wolf_information_keys(payload.private))
  self.actions[board,payload,target]=ActionRecord(acquired,tuple(EvaluatedOutcome(*row) for row in outcomes),value,policies)
 def recorded_action(self,board,payload,target):
  return self.actions.get((board,payload,target))
 def record_morning(self,payload,branches,value):
  self.mornings[payload]=MorningRecord(tuple(branches),value)
 def supports(self,source):
  e=self.engine;b=source.public
  return (source not in getattr(e,'anonymous_beliefs',{})
   and source.observer is None and not b.initial_hunter_count and not e.strategy.include_self_bite
   and (e.strategy.day,e.strategy.night,e.strategy.fake_reports)==('random',)*3
   and not any(c!='latent' for c in b.claims) and not source.past and not b.reports
   and e.exchangeable(b))
 def program_scope(self,source):
  e=self.engine;b=source.public
  return (b.phase=='night' and not b.winner and source.observer is None
   and not b.initial_hunter_count and not e.strategy.include_self_bite
   and ((e.strategy.day,e.strategy.night,e.strategy.fake_reports)==('random',)*3 or e.strategy.night=='max')
   and any(c in ('seer','medium') for c in b.claims)
   and source not in getattr(e,'anonymous_beliefs',{}))
 def day_scope(self,source):
  e=self.engine;b=source.public
  return (b.phase=='day' and not b.winner and e.strategy.day=='max'
   and not b.initial_hunter_count and source.observer is None
   and source not in getattr(e,'anonymous_beliefs',{}))
 def record_day_scores(self,board,public,past,scores):
  if self.engine.strategy.day!='max' or board.phase!='day' or board.winner or board.initial_hunter_count:return
  scores=tuple(scores)
  # The ordinary evaluator installs this cache only after every candidate is
  # evaluated. A scalar bound/early win certificate is not a decision table.
  if {target for target,value in scores}!=set(board.alive):return
  best=max(value for target,value in scores);chosen=tuple(target for target,value in scores if value==best)
  policy=tuple((target,F(1,len(chosen)) if target in chosen else F()) for target,value in scores)
  self.day_decisions[board,public,past]=DayDecisionRecord(scores,policy)
 def day_decision(self,source,*,evaluate=False):
  if not self.day_scope(source):return None
  key=(source.public,source.public_state,source.past)
  if key not in self.day_decisions and evaluate:self.engine.day_scores(*key)
  return self.day_decisions.get(key)
 def record_program(self,source,groups,program,value):
  if not self.program_scope(source) or program.method!='anonymous-relational-v1':return
  # Record only after the evaluator has completed this exact owned program.
  # No zero-policy path receives an invented continuation value.
  # Policies were committed from night-start public Q and actor memory before
  # result partitions. Retain those actual cache entries, not viewer-P choices.
  policies=tuple((info,self.engine.policies[source.public,source.public_state,source.past,info]) for info in dict.fromkeys(leaf.information for leaf in program.leaves))
  self.programs[source,tuple(groups)]=ProgramRecord(program,value,tuple(program.values),policies)
 def _recorded_action_program(self,source,groups):
  if source.public.phase!='night' or source.public.winner or not self.recorded_flow_scope(source.public,source) or source in getattr(self.engine,'anonymous_beliefs',{}):return None
  key=(source,tuple(groups))
  if key not in self.programs:
   found=self.hunter_rows(source)
   if found is None:return None
   from .recorded_hunter_program import factor
   program=factor(source,tuple(groups),found[0])
   if program is None:return None
   policies=tuple((info,self.engine.policies[source.public,source.public_state,source.past,info]) for info in dict.fromkeys(row[5] for row in found[0]))
   reason='factored-evaluated-personal-action-flow' if source.observer is not None else 'factored-evaluated-action-flow'
   self.programs[key]=ProgramRecord(program,found[1],tuple(program.values),policies,reason)
  return self.programs[key]
 def personal_program(self,source,groups,*,evaluate=False):
  """Read completed observer-conditioned records; never request missing detail.

  Public convergence deliberately excludes these sources. Keep this explicit
  boundary; observer-aware projection/navigation uses its separate entry.
  """
  if source.observer is None:return None
  record=self._recorded_action_program(source,groups)
  if record is None and evaluate and self.personal_flow_scope(source.public,source):
   # Explicit detail requests enter the existing evaluator action flow. A
   # reused scalar alone is not evidence that its transition was retained.
   from .actor_information import wolf_information_groups
   from .evaluation_branch import ActionInputs,physical_board
   from .action_flow import action_flow
   e=self.engine;b=source.public
   for info,mass,own in wolf_information_groups(source.private):
    for target,q in e.wolf_policy(b,source.public_state,source.past,info.initial_roster,info.attacks):
     if not q:continue
     payload=ActionInputs(source.public_state,source.past,own,source.observer,physical_board(b,own,source.physical))
     if self.recorded_action(b,payload,target) is None:
      expected=e.act(b,payload.public_state,payload.past,target,own,source.observer,physical=payload.physical)
      if self.recorded_action(b,payload,target) is None:
       actual=action_flow(b,payload,target,e.action_policy)
       if actual!=expected:raise ValueError('Requested personal detail changed scalar value')
   record=self._recorded_action_program(source,groups)
  if record is not None:self.values.setdefault(source,ValueRecord(record.value,'evaluated-personal-action-flow'))
  return record
 def evaluated_program(self,source,groups,*,evaluate=False):
  # The existing Tree entry is public. A personal record must not silently enter
  # its public-only convergence/transport path.
  if source.observer is not None:return None
  key=(source,tuple(groups))
  if source.public.initial_hunter_count:return self._recorded_action_program(source,groups)
  if key not in self.programs and evaluate and self.program_scope(source):
   self.engine.solve(*source,physical=source.physical)
  # A count/value shortcut may never have formed an ability program. It remains
  # an explicit fallback, rather than compiling detail to pretend it was traced.
  return self.programs.get(key)
 def _named_leaf(self,leaf,template,groups):
  """Explicit named Board boundary of the actual anonymous evaluation leaf."""
  from dataclasses import replace
  from .anonymous_belief import Atom,Law
  from .anonymous_materialization import expand
  from .evaluation_branch import physical_board
  pop=leaf.population;transport=leaf.named_transport
  names=list(transport.people);free=[list(row) for row in transport.free]
  public=set(p for group in groups if len(group)==1 for p in group)
  for record in (*template.public.history,*template.past,*template.public.reports):
   for field in ('player','reporter','target'):
    if hasattr(record,field):public.add(getattr(record,field))
  pins=[]
  for name in sorted(public):
   if name not in names:
    cell=next(i for i,row in enumerate(free) if name in row)
    pop,ref=pop.bind(cell);names.append(name);free[cell].remove(name)
   pins.append((name,names.index(name)))
  law=Law.weighted(((F(1),Atom(pop,tuple(pins))),))[1]
  own=replace(template.private,hypotheses=expand(law,groups))
  return replace(template,private=own,physical=physical_board(template.public,own,template.physical),board_data=None,provenance=None)
 def hunter_rows(self,source):
  b=source.public;e=self.engine
  if b.phase!='night' or b.winner or not self.recorded_flow_scope(b,source) or source in getattr(e,'anonymous_beliefs',{}):return None
  from .actor_information import wolf_information_groups
  from .evaluation_branch import ActionInputs,physical_board
  rows=[];expected=F();offset=0
  for info,mass,own in wolf_information_groups(source.private):
   policy=e.policies.get((b,source.public_state,source.past,info))
   if policy is None:return None
   payload=ActionInputs(source.public_state,source.past,own,source.observer,physical_board(b,own,source.physical))
   for target,q in policy:
    if not q:continue
    action=self.recorded_action(b,payload,target)
    if action is None:return None # A value-only reduction is not a state trace.
    expected+=mass*q*action.value
    for index,outcome in enumerate(action.outcomes):
     if outcome.source is None:return None # Terminal-payoff reductions kept no Board.
     morning=self.mornings.get(outcome.source)
     if morning is None:return None
     rows.extend((mass*q*outcome.outcome.probability*p,outcome.source,after,target,value,info,offset,index,outcome.outcome) for p,after,value in morning.branches)
   offset+=len(policy)
  return tuple(rows),expected
 def hunter_projection(self,source,groups):
  if source.observer is not None:return None
  found=self.hunter_rows(source)
  if found is None:return None
  rows,expected=found
  return self._public_mixture(source,groups,(row[:5] for row in rows),expected=expected)
 def personal_projection(self,source,groups,*,counter=False):
  if source.observer is None:return None
  key=(source,tuple(groups),'personal')
  if key in self.projections:return self.projections[key]
  found=self.hunter_rows(source)
  if found is None:return None
  result=self._public_mixture(source,groups,(row[:5] for row in found[0]),expected=found[1],personal=True)
  from dataclasses import replace
  result=replace(result,reason='evaluated-personal-mixture')
  self.projections[key]=result;return result
 def public_projection(self,source,groups,*,evaluate=False,counter=False):
  key=(source,tuple(groups),counter)
  if key in self.projections:return self.projections[key]
  if source.public.initial_hunter_count:
   if counter:return self.public_projection(source,groups) # Supported hunter policies are uniform.
   result=self.hunter_projection(source,groups)
   if result is not None:self.projections[key]=result
   return result
  record=self.evaluated_program(source,groups,evaluate=evaluate)
  if record is None:return None
  program=record.program
  if any(leaf.arrival is None or leaf.population is None or leaf.named_transport is None for leaf in program.leaves):return None
  if counter and all(leaf.mass==leaf.counter for leaf in program.leaves):
   result=self.public_projection(source,groups,evaluate=evaluate)
   self.projections[key]=result;return result
  rows=[]
  for leaf in program.leaves:
   weight=leaf.counter if counter else leaf.mass
   if not weight:continue
   value=program.values.get(leaf.source)
   if value is None and not counter:return None
   rows.append((weight,self._named_leaf(leaf,leaf.arrival,groups),self._named_leaf(leaf,leaf.source,groups),leaf.target,value))
  result=self._public_mixture(source,groups,rows,counter=counter,expected=None if counter else record.value)
  self.projections[key]=result;return result
 def _public_mixture(self,source,groups,rows,*,counter=False,expected=None,personal=False):
  from .public_convergence import public_transport,transport_source,public_key,mix
  if personal:
   from .personal_convergence import public_transport,transport_source,observation_key as public_key,mix
  afters={};befores={};total=F();weighted=F();known=True
  from .calculation_budget import tick
  def add(table,identity,weight,child,target,value):
   row=table.setdefault(identity,dict(rows=[],mass=F(),weighted=F(),known=True,target=target,links={}))
   row['rows'].append((weight,child));row['mass']+=weight
   if value is None:row['known']=False
   else:row['weighted']+=weight*value
   return row
  for weight,before,after,target,value in rows:
   tick()
   if value is None:known=False
   mapping=public_transport(source,after,groups);after=transport_source(after,mapping)
   before_mapping=public_transport(source,before,groups);before=transport_source(before,before_mapping)
   target=mapping[target-1];a=public_key(after);b=public_key(before)
   add(afters,a,weight,after,target,value)
   row=add(befores,b,weight,before,target,value);row['links'][a]=row['links'].get(a,F())+weight
   total+=weight
   if value is not None:weighted+=weight*value
  if total!=1 or expected is not None and weighted!=expected:raise ValueError('Recorded public mixture changed evaluated mass/value')
  edges=[];sources={};values={}
  for identity,row in afters.items():
   child=mix(row['rows']);sources[identity]=child
   value=row['weighted']/row['mass'] if row['known'] else None;values[identity]=value
   if value is not None:self.values[child]=ValueRecord(value,'evaluated-counterfactual-mixture' if counter else 'evaluated-public-mixture')
   edges.append(Edge(row['mass'],child,row['target']))
  arrivals=[]
  for row in befores.values():
   child=mix(row['rows'])
   if child.public.winner:continue
   updates=tuple(Edge(weight/row['mass'],sources[a],row['target']) for a,weight in row['links'].items())
   if sum(edge.probability for edge in updates)!=1:raise ValueError('Recorded update mass changed')
   value=row['weighted']/row['mass'] if row['known'] else None
   if value is not None and all(values[a] is not None for a in row['links']) and sum(weight/row['mass']*values[a] for a,weight in row['links'].items())!=value:raise ValueError('Recorded update value changed')
   arrivals.append(ArrivalRecord(row['mass'],child,row['target'],updates,value))
  result=PublicProjection(tuple(edges),tuple(arrivals),weighted if known else None)
  return result
 def record_counts(self,source,value):
  if not self.supports(source):return
  b=source.public;counts={}
  for h in source.private.hypotheses:
   key=(len(b.alive),(h.roles[0]&b.alive_mask).bit_count(),b.phase)
   counts[key]=counts.get(key,F())+h.mass
  self.values[source]=ValueRecord(value,'exchangeable-count-recurrence',tuple((*key,mass) for key,mass in sorted(counts.items())))
 def value(self,source):
  if source in self.values:return self.values[source].value
  value=self.engine.solve(*source,physical=source.physical)
  if source not in self.values and not source.public.winner:self.record_counts(source,value)
  if source not in self.values:self.values[source]=ValueRecord(value,'terminal' if source.public.winner else 'exact-continuation')
  return value
 def refine(self,source,groups,target=None):
  if self.random_day_scope(source.public,source):return self.day_refinement(source,groups,target)
  decision=self.day_decision(source)
  maximum=decision is not None and self.day_scope(source)
  # A value-only shortcut is not permission to force a full MAX policy table.
  # Ordinary selection/inspection requests complete that table separately.
  if not self.supports(source) and not maximum:return None
  key=(source,tuple(groups),target)
  if key in self.refinements:return self.refinements[key]
  e=self.engine;b=source.public
  if b.phase=='day':
   if target is None:raise ValueError('Execution refinement requires a target')
   if maximum and source.private==source.public_state and source.physical==source.public:value=dict(decision.scores)[target]
   else:value=e.act(*source[:3],target,source.private,source.observer,physical=source.physical)
   from .action_flow import resolve_action
   from .evaluation_branch import ActionInputs
   from .board_future import outcome_key
   acquired,outcomes=resolve_action(b,ActionInputs(source.public_state,source.past,source.private,source.observer,source.physical),target,e.action_policy)
   edges=tuple(Edge(o.probability,e.action_policy.project(b,acquired,o,target),target,outcome_key(o)) for o in outcomes)
  else:
   if target is not None:raise ValueError('Public night refinement integrates attack policy')
   from .public_convergence import public_night_observations
   edges=tuple(Edge(mass,child,chosen) for mass,child,chosen in public_night_observations(e,source,groups))
   value=self.value(source)
  if sum((edge.probability for edge in edges),F())!=1:raise ValueError('Evaluator refinement lost probability mass')
  refined=sum((edge.probability*self.value(edge.source) for edge in edges),F())
  if refined!=value:raise ValueError('Evaluator refinement changed exact value')
  probability=dict(decision.policy)[target] if maximum else F(1,len(b.alive)) if b.phase=='day' else None
  result=Refinement(value,edges,'MAX-execution-refinement' if maximum else 'public-state-refinement',probability)
  self.refinements[key]=result;return result
