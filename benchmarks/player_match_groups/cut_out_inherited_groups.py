"""Group witnesses carried by completed common transitions, never law search."""
from dataclasses import dataclass,fields
from collections import Counter
from .cut_out_day_night import point_fix
from werewolf.information_set_forecast import Pending


@dataclass(frozen=True,eq=False)
class InheritedGroups:
    board:object
    state:object
    past:tuple
    groups:tuple
    parent:object=None
    event:str='initial-CO/report'
    new_fixed:tuple=()
    depth:int=0


class InheritedGroupRegistry:
    def __init__(self,graph):
        from .cut_out_model_a import ModelAInitialGroups
        if type(graph.engine) is not ModelAInitialGroups:raise Pending('inherited_initial_group_witness_required')
        root=graph.origin();b=root.public
        if b.player_count not in (4,5) or b.initial_hunter_count or b.history or b.day!=1 or b.phase!='day':
            raise Pending('inherited_initial_group_scope_unproved')
        self.contexts={};self.by_board={};self.stats=Counter(root_group_reads=1)
        self.install(InheritedGroups(b,root.public_state,root.past,graph.engine.start().groups))

    def install(self,context):
        key=context.board,context.state,context.past
        previous=self.contexts.get(key)
        if previous is not None:
            if previous.groups!=context.groups:raise Pending('inherited_group_path_conflict')
            return previous
        self.contexts[key]=context
        self.by_board.setdefault((context.board,context.past),[]).append(context)
        self.stats[context.event]+=1
        self.stats['max_depth']=max(self.stats['max_depth'],context.depth)
        return context

    def require(self,b,s,past):
        context=self.contexts.get((b,s,past))
        if context is None:raise Pending('inherited_group_context_required')
        return context

    def for_value(self,b,past,s=None):
        if s is not None:return self.require(b,s,past)
        # Compatibility for inspection-only callers. Never infer from a law.
        contexts=self.by_board.get((b,past),())
        if not contexts or any(c.groups!=contexts[0].groups for c in contexts):
            raise Pending('inherited_group_context_missing_or_ambiguous')
        return contexts[0]

    def child(self,parent,b,s,past,event,fixed=()):
        positions=tuple(sorted(set(fixed)))
        if any(p not in range(1,b.player_count+1) for p in positions):raise Pending('inherited_group_bad_endpoint')
        self.stats['new_endpoint_positions']+=len(positions)
        return self.install(InheritedGroups(b,s,past,point_fix(parent.groups,*positions),parent,event,positions,parent.depth+1))

    def private_groups(self,context,fixed,cache):
        key=(context,tuple(sorted(fixed)))
        if key not in cache:
            base=(self.private_groups(context.parent,fixed,cache) if context.parent is not None
                  else point_fix(context.groups,*sorted(fixed)))
            cache[key]=point_fix(base,*context.new_fixed) if context.parent is not None else base
            self.stats['private_context_splits']+=1
        return cache[key]

    def acquisition(self,b,before,after,past):
        parent=self.require(b,before,past)
        if b.phase!='night' or after.rosters!=before.rosters+(b.alive,):
            raise Pending('inherited_acquisition_transition_unproved')
        return self.child(parent,b,after,past,'symmetric-acquisition')

    def action(self,b,payload,child,target):
        parent=self.require(b,payload.public_state,payload.past);c=child.public
        if (c.claims!=b.claims or c.reports!=b.reports or child.past!=payload.past
            or c.history[:len(b.history)]!=b.history or len(c.history)!=len(b.history)+1
            or c.history[-1].target!=target or c.history[-1].phase!=b.phase
            or c.alive!=tuple(p for p in b.alive if p!=target)
            or c.day!=(b.day if c.winner else b.day+(b.phase=='night'))
            or c.phase!=(b.phase if c.winner else 'night' if b.phase=='day' else 'day')):
            raise Pending('inherited_action_transition_unproved')
        return self.child(parent,c,child.public_state,child.past,'death-'+b.phase,(target,))

    def publication(self,b,s,past,c,ns,new_past,kind):
        parent=self.require(b,s,past)
        if (type(c)is not type(b) or c.claims!=b.claims or c.reports[:len(b.reports)]!=b.reports
            or new_past[:len(past)]!=past
            or any(getattr(b,f.name)!=getattr(c,f.name) for f in fields(b)
                   if f.name not in ('worlds','belief','role_belief','world_belief','reports','report_resolved'))):
            raise Pending('inherited_publication_or_CO_transition_unproved')
        if (b,s,past)==(c,ns,new_past):return parent
        fixed=set()
        for r in c.reports[len(b.reports):]:fixed.update((r.reporter,r.target))
        for r in new_past[len(past):]:fixed.update((r.player,r.target))
        for day,player,target in set(c.report_resolved)-set(b.report_resolved):fixed.update((player,target))
        return self.child(parent,c,ns,new_past,'publication-'+kind,fixed)
