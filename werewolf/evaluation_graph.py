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

class EvaluationGraph:
 def __init__(self,engine):self.engine=engine;self.values={};self.refinements={};self.programs={}
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
 def record_counts(self,source,value):
  if not self.supports(source):return
  b=source.public;counts={}
  for h in source.private.hypotheses:
   key=(len(b.alive),(h.roles[0]&b.alive_mask).bit_count(),b.phase)
   counts[key]=counts.get(key,F())+h.mass
  self.values[source]=ValueRecord(value,'exchangeable-count-recurrence',tuple((*key,mass) for key,mass in sorted(counts.items())))
 def value(self,source):
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
