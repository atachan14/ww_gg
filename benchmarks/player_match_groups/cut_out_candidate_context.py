"""Inherited product-group candidate orbits. No law search or permutations."""
from dataclasses import dataclass
from .cut_out_day_night import point_fix
from werewolf.policy_choice import uniform_policy
from werewolf.information_set_forecast import Pending


@dataclass(frozen=True)
class PublicCandidateContext:
    origin:object
    board:object
    state:object
    past:tuple
    groups:tuple
    steps:tuple=()

    def matches(self,b,s,past):return (self.board,self.state,self.past)==(b,s,past)

    def day_child(self,b,payload,child,target):
        from werewolf.board_future import ActionEvidence
        request=getattr(child,'board_data',None)
        if (self.steps or not self.matches(b,payload.public_state,payload.past) or b.phase!='day'
            or b.day!=1 or b.history or child.public.winner or child.public.phase!='night'
            or child.public.day!=1 or child.public.claims!=b.claims or child.past!=self.past
            or len(child.public.history)!=1 or child.public.history[0].target!=target
            or request is None or request.origin is not self.origin or not request.history
            or not isinstance(request.history[-1],ActionEvidence) or request.history[-1].target!=target):return None
        # The common death transition is equivariant. Stabilize only this NEW
        # public observation. Never inspect a law to discover a smaller group.
        return PublicCandidateContext(self.origin,child.public,child.public_state,child.past,
            point_fix(self.groups,target),(('day-death',target),))


def initial_candidate_context(graph):
    from .cut_out_model_a import ModelAInitialGroups
    from werewolf.exact import Rules,Strategy
    if type(graph.engine) is not ModelAInitialGroups:return None
    spec=graph.engine.baseline.spec
    if (spec.players not in (4,5) or spec.seers!=1 or spec.mediums not in (0,1)
        or spec.claims not in (('latent',)*spec.players,('medium','medium')+('latent',)*(spec.players-2))
        or 'medium' in spec.claims and spec.mediums!=1 or spec.reports
        or spec.rules not in (Rules(initial_seer='none'),Rules(initial_seer='random_white'))
        or spec.strategy!=Strategy(day='max',night='max',fake_reports=spec.strategy.fake_reports)):return None
    root=graph.origin()
    if root.public.history or root.past or root.public.reports:return None
    return PublicCandidateContext(graph.origin,root.public,root.public_state,root.past,graph.engine.start().groups)


class CutOutCandidateRules:
    """Ordered distinct (one-wolf, target) orbits of inherited block products."""
    def __init__(self,context,b,s,past,groups):
        if (type(context) is not PublicCandidateContext or not context.matches(b,s,past)
            or len(context.steps)!=1 or b.phase!='night' or b.day!=1 or b.initial_hunter_count):
            raise Pending('cut_out_candidate_context_unproved')
        self.context=context;self.actions={};self.classes={}
        block={p:i for i,g in enumerate(context.groups) for p in g}
        if set(block)!=set(range(1,b.player_count+1)):raise Pending('cut_out_candidate_partition_unproved')
        classes={}
        for info,mass,group in groups:
            if info.attacks or info.initial_roster.bit_count()!=1:
                raise Pending('cut_out_candidate_owned_history_unproved')
            wolf=info.initial_roster.bit_length()
            if wolf not in b.alive:raise Pending('cut_out_candidate_dead_roster')
            actions=tuple(p for p in b.alive if p!=wolf);self.actions[info]=actions
            for target in actions:
                # For a product of symmetric blocks, ordered-pair orbit identity
                # is exactly both block IDs and equality of the two positions.
                key=(block[wolf],block[target],wolf==target)
                self.classes[info,target]=classes.setdefault(key,len(classes))
        self.replacements={};self.replacement_masks={}
        for c in classes.values():
            rows={}
            for info,actions in self.actions.items():
                matches=tuple(p for p in actions if self.classes[info,p]==c)
                if matches:rows[info]=uniform_policy(matches)
            self.replacements[c]=rows
            self.replacement_masks[c]={i:sum(1<<(p-1) for p,q in row) for i,row in rows.items()}
        self.stats=dict(canonical_calls=0,law_permutation_checks=0,law_rows_read_for_grouping=0,
            pair_count=len(self.classes),orbit_count=len(classes),inherited_steps=len(context.steps))

    def candidate(self,profile,info,target):
        if target not in self.actions[info]:raise ValueError('Legal candidate required')
        rows=self.replacements[self.classes[info,target]]
        return tuple((owned,rows.get(owned,policy)) for owned,policy in profile)
