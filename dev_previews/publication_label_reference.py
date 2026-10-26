"""Previous label-only full transport flow for independent timing controls."""
import inspect,sys
from werewolf.tree_public_updates import event_label


def legacy_label(before,after):
    events=[dict(kind='seer',player=r.player,day=r.acquired_day,published_day=r.published_day,target=r.target,color=r.color) for r in after.past if r not in before.past]
    events.extend(dict(kind='medium',player=r.reporter,day=r.day,target=r.target,color=r.color) for r in after.public.reports if r not in before.public.reports)
    events.extend(dict(kind='co',player=p,role=claim) for p,claim in enumerate(after.public.claims,1) if claim!=before.public.claims[p-1])
    return event_label(events) or '更新なし'

def install():
 from werewolf import anonymous_role_night,tree_public_updates
 original_label=tree_public_updates.publication_label
 original_compile=anonymous_role_night.compile_abilities
 source=inspect.getsource(original_compile)
 old="label=publication_label(child,after,mapping=mapping)"
 assert source.count(old)==1,'legacy timing control needs review'
 source=source.replace('from .public_convergence import public_transport','from .public_convergence import public_transport,transport_source')
 source=source.replace(old,'label=publication_label(transport_source(child,mapping),transport_source(after,mapping))')
 namespace=dict(vars(anonymous_role_night));exec(compile(source,'<legacy-publication-label-flow>','exec'),namespace)
 replacement=namespace['compile_abilities']
 for module in list(sys.modules.values()):
  if getattr(module,'__name__','').startswith('werewolf'):
   for name,value in list(vars(module).items()):
    if value is original_label:setattr(module,name,legacy_label)
    elif value is original_compile:setattr(module,name,replacement)
