"""Observer-scoped projection of completed evaluation outputs.

Q is renamed bijectively, never conditioned by owner facts. Only components with
one identical immutable observer may mix. Public-only convergence stays separate.
"""
from dataclasses import replace
from .actor_information import PersonalInformation,GuardInformation,GuardSelection,WolfObserver,information_positions
from .seer_intervention import SeerObserver
from .public_convergence import transport_record,public_key,mix as public_mix
from .group_partition import _fix

def supported(observer):return type(observer) in (PersonalInformation,SeerObserver,GuardInformation,GuardSelection,WolfObserver)

def transport_source(source,mapping):
 if not supported(source.observer):raise ValueError('Typed personal observer required')
 from .public_convergence import transport_source as public_transport_source
 observer=source.observer
 if type(observer)is WolfObserver:
  mask=sum(1<<(mapping[p-1]-1) for p in range(1,len(mapping)+1) if observer.initial_roster&(1<<(p-1)))
  moved=public_transport_source(replace(source,observer=None),mapping)
  return replace(moved,observer=WolfObserver(mask,tuple(transport_record(a,mapping) for a in observer.attacks)))
 values=dict(actor=mapping[observer.actor-1])
 if type(observer) in (GuardInformation,GuardSelection):values['guards']=tuple(transport_record(g,mapping) for g in observer.guards)
 else:values['acquisitions']=tuple(transport_record(a,mapping) for a in observer.acquisitions)
 if type(observer) in (SeerObserver,GuardSelection):values['target']=mapping[observer.target-1]
 moved=public_transport_source(replace(source,observer=None),mapping)
 return replace(moved,observer=replace(observer,**values))

def public_transport(before,after,groups):
 from .public_convergence import public_transport as public_mapping
 if not supported(before.observer) or before.observer!=after.observer:raise ValueError('Different observer frames cannot converge')
 fixed=_fix(groups,information_positions(before.observer,before.public.player_count))
 return public_mapping(before,after,fixed)

def observation_key(source):return public_key(source),source.observer

def mix(weighted):
 rows=tuple(weighted)
 if not rows or not supported(rows[0][1].observer):raise ValueError('Typed personal mixture required')
 if any(observation_key(source)!=observation_key(rows[0][1]) for weight,source in rows):raise ValueError('Different private observations cannot converge')
 return public_mix(rows)

def observe(engine,source,groups,identity,*,arrival=False,counter=False):
 """Cold recipe replay asks the SAME evaluator for its actual records.

 This is not a Tree-specific transition simulator. Value-only reductions still
 decline detail rather than manufacturing a named posterior.
 """
 from .evaluation_graph import EvaluationGraph
 from .public_convergence import digest
 graph=getattr(engine,'evaluation_graph',None)
 if graph is None:engine.evaluation_graph=graph=EvaluationGraph(engine)
 result=graph.personal_projection(source,groups,counter=counter)
 if result is None:
  engine.solve(*source,physical=source.physical)
  result=graph.personal_projection(source,groups,counter=counter)
 if result is None:
  from contextlib import nullcontext
  with engine.group_scope(groups) if hasattr(engine,'group_scope') else nullcontext():graph.personal_program(source,groups,evaluate=True)
  result=graph.personal_projection(source,groups,counter=counter)
 if result is None:
  from .information_set_forecast import Pending
  raise Pending('personal_evaluated_projection_not_retained')
 rows=result.arrivals if arrival else result.edges
 selected=next((row.source for row in rows if digest(row.source)==identity),None)
 if selected is None:raise ValueError('Personal observation unavailable in this owner frame')
 return selected
