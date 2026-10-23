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

@dataclass(frozen=True)
class ProgramRecord:
 program:object
 value:F
 evaluated_sources:tuple
 reason:str='evaluated-role-ordered-program'

@dataclass(frozen=True)
class ArrivalRecord:
 probability:F
 source:object
 target:int
 updates:tuple
 value:F

@dataclass(frozen=True)
class PublicProjection:
 edges:tuple
 arrivals:tuple
 value:F
 reason:str='evaluated-public-mixture'

class EvaluationGraph:
 def __init__(self,engine):self.engine=engine;self.values={};self.refinements={};self.programs={};self.projections={}
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
   and (e.strategy.day,e.strategy.night,e.strategy.fake_reports)==('random',)*3
   and any(c in ('seer','medium') for c in b.claims)
   and source not in getattr(e,'anonymous_beliefs',{}))
 def record_program(self,source,groups,program,value):
  if not self.program_scope(source) or program.method!='anonymous-relational-v1':return
  # Record only after the evaluator has completed this exact owned program.
  # No zero-policy path receives an invented continuation value.
  self.programs[source,tuple(groups)]=ProgramRecord(program,value,tuple(program.values))
 def evaluated_program(self,source,groups,*,evaluate=False):
  key=(source,tuple(groups))
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
 def public_projection(self,source,groups,*,evaluate=False):
  key=(source,tuple(groups))
  if key in self.projections:return self.projections[key]
  record=self.evaluated_program(source,groups,evaluate=evaluate)
  if record is None:return None
  program=record.program
  # This migration covers uniform policies only. Counterfactual-policy laws
  # remain on the explicit legacy path until independently recorded.
  if any(leaf.mass!=leaf.counter or leaf.arrival is None or leaf.population is None or leaf.named_transport is None for leaf in program.leaves):return None
  from .public_convergence import public_transport,transport_source,public_key,mix
  afters={};befores={};total=F();weighted=F()
  from .calculation_budget import tick
  for leaf in program.leaves:
   tick()
   if not leaf.mass:continue
   if leaf.source not in program.values:return None
   weight=leaf.mass;value=program.values[leaf.source]
   mapping=public_transport(source,leaf.source,groups)
   after=transport_source(self._named_leaf(leaf,leaf.source,groups),mapping)
   before_mapping=public_transport(source,leaf.arrival,groups)
   before=transport_source(self._named_leaf(leaf,leaf.arrival,groups),before_mapping)
   target=mapping[leaf.target-1];a=public_key(after);b=public_key(before)
   row=afters.setdefault(a,dict(rows=[],mass=F(),weighted=F(),target=target))
   row['rows'].append((weight,after));row['mass']+=weight;row['weighted']+=weight*value
   row=befores.setdefault(b,dict(rows=[],mass=F(),weighted=F(),target=target,links={}))
   row['rows'].append((weight,before));row['mass']+=weight;row['weighted']+=weight*value
   row['links'][a]=row['links'].get(a,F())+weight
   total+=weight;weighted+=weight*value
  if total!=1 or weighted!=record.value:raise ValueError('Recorded public mixture changed evaluated mass/value')
  edges=[];sources={}
  for identity,row in afters.items():
   child=mix(row['rows']);sources[identity]=child
   self.values[child]=ValueRecord(row['weighted']/row['mass'],'evaluated-public-mixture')
   edges.append(Edge(row['mass'],child,row['target']))
  arrivals=[]
  for row in befores.values():
   child=mix(row['rows'])
   if child.public.winner:continue
   updates=tuple(Edge(weight/row['mass'],sources[a],row['target']) for a,weight in row['links'].items())
   if sum(edge.probability for edge in updates)!=1:raise ValueError('Recorded update mass changed')
   value=row['weighted']/row['mass']
   if sum(edge.probability*self.values[edge.source].value for edge in updates)!=value:raise ValueError('Recorded update value changed')
   arrivals.append(ArrivalRecord(row['mass'],child,row['target'],updates,value))
  result=PublicProjection(tuple(edges),tuple(arrivals),weighted)
  self.projections[key]=result;return result
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
  if not self.supports(source):return None
  key=(source,tuple(groups),target)
  if key in self.refinements:return self.refinements[key]
  e=self.engine;b=source.public
  if b.phase=='day':
   if target is None:raise ValueError('Execution refinement requires a target')
   from .action_flow import resolve_action
   from .evaluation_branch import ActionInputs
   from .board_future import outcome_key
   acquired,outcomes=resolve_action(b,ActionInputs(source.public_state,source.past,source.private,source.observer,source.physical),target,e.action_policy)
   edges=tuple(Edge(o.probability,e.action_policy.project(b,acquired,o,target),target,outcome_key(o)) for o in outcomes)
   value=e.act(*source[:3],target,source.private,source.observer,physical=source.physical)
  else:
   if target is not None:raise ValueError('Public night refinement integrates attack policy')
   from .public_convergence import public_night_observations
   edges=tuple(Edge(mass,child,chosen) for mass,child,chosen in public_night_observations(e,source,groups))
   value=self.value(source)
  if sum((edge.probability for edge in edges),F())!=1:raise ValueError('Evaluator refinement lost probability mass')
  refined=sum((edge.probability*self.value(edge.source) for edge in edges),F())
  if refined!=value:raise ValueError('Evaluator refinement changed exact value')
  result=Refinement(value,edges);self.refinements[key]=result;return result
