"""Uniform H0 target-orbit consumer of constructed closed-node partitions."""
from contextlib import contextmanager
from fractions import Fraction as F
from .information_set_forecast import InformationSetForecast,InformationSetActionPolicy
from .group_partition import _fix,_report_groups


class GroupedPolicy(InformationSetActionPolicy):
    def morning_value(self,payload):
        e=self.engine;value=F()
        for q,mass,child in e.report_children(payload):
            with e.group_scope(_report_groups(e.groups,child)):
                value+=mass*e.solve(*child,physical=child.physical)
        return value


class GroupedForecast(InformationSetForecast):
    def __init__(self,*args,aggregate_wolf=False,aggregate_reports=False,**kwargs):
        super().__init__(*args,**kwargs)
        if (self.strategy.day,self.strategy.night,self.strategy.fake_reports)!=('random',)*3:raise ValueError('Uniform representative mode only')
        self.aggregate_wolf=aggregate_wolf;self.aggregate_reports=aggregate_reports
        self.report_kernels={};self.value_laws={}
        self.groups=();self.orbit_stats={'target_members':0,'target_representatives':0}
        self.action_policy=GroupedPolicy(self)

    # Constructed partitions replace discovery by full-law label permutations.
    # Ordinary named memo keys still retain all numerical inputs.
    def renamed_value_key(self,*args,**kwargs):return None
    def full_renamed_key(self,*args,**kwargs):return None
    def scalar_descriptor(self,*args,**kwargs):return None

    def exchangeable(self,b):
        # Uniform execution of three survivors with one wolf always ends.
        # The common count recurrence is independent of all report/scan history.
        if b.phase=='day' and len(b.alive)==3 and not b.initial_hunter_count and set(b.wolf_count_distribution)=={1}:return True
        return super().exchangeable(b)

    def value_law(self,state):
        # Exact derived value of the same owned immutable input; no state orbit.
        key=(self.rules.allow_repeat_guard,self.strategy.night,state)
        if key not in self.value_laws:self.value_laws[key]=super().value_law(state)
        return self.value_laws[key]

    def report_partition(self,b,past):
        if not self.aggregate_reports or not self.groups:return ()
        from types import SimpleNamespace
        reporters={p for p in b.alive if b.claims[p-1]=='seer'}
        refined=_report_groups(self.groups,SimpleNamespace(public=b,past=past))
        parts=tuple(sorted(tuple(sorted(p for p in group if p in reporters)) for group in refined if any(p in reporters for p in group)))
        return parts if any(len(g)>1 for g in parts) else ()

    def morning(self,b,s,past):
        # Compact coefficients describe different families in different private
        # stabilizers. Cache intrinsic public events, not quotient row sets.
        if self.report_partition(b,past):return self.generate_morning(b,s,past)
        return super().morning(b,s,past)

    def publications(self,b,s,past):
        partition=self.report_partition(b,past)
        if not partition:return super().publications(b,s,past)
        from .morning_publications import compile_publications
        key=(b,s,past)
        if key not in self.report_kernels:
            self.report_kernels[key]=self.checked(compile_publications(s,past,b.alive,b.claims,
                fake_policy=self.strategy.fake_seer_policy,seed=self.publication_values.get(key,()),board=b))
        return self.checked(self.report_kernels[key].branches(partition))

    def generate_publications(self,b,s,past):
        kernel=self.report_kernels.get((b,s,past)) if self.aggregate_reports else None
        if kernel is not None:return self.checked(kernel.branches(tuple((p,) for p in kernel.reporters)))
        return super().generate_publications(b,s,past)

    def report_counts(self):
        return dict(kernels=len(self.report_kernels),public_event_laws=sum(sum(v is not None for v in k.events.values()) for k in self.report_kernels.values()),
            fallback_public_vectors=sum(len(rows) for key,rows in self.publication_values.items() if key not in self.report_kernels),
            compiled_candidates=sum(k.stats['candidates'] for k in self.report_kernels.values()),
            newly_built_vectors=sum(k.stats['built_vectors'] for k in self.report_kernels.values()),
            emitted_vectors=sum(k.stats['emitted_vectors'] for k in self.report_kernels.values()),
            named_vectors_covered=sum(k.stats['named_vectors_covered'] for k in self.report_kernels.values()))

    @contextmanager
    def group_scope(self,groups):
        before=self.groups;self.groups=groups
        try:yield
        finally:self.groups=before

    def target_orbits(self,targets):
        available=set(targets)
        result=tuple(tuple(p for p in group if p in available) for group in self.groups)
        result=tuple(g for g in result if g)
        covered={p for g in result for p in g}
        result+=tuple((p,) for p in targets if p not in covered)
        self.orbit_stats['target_members']+=len(targets)
        self.orbit_stats['target_representatives']+=len(result)
        return result

    def wolf_cells(self,state):
        from .actor_information import wolf_information_orbits
        rows=(wolf_information_orbits(state,self.groups) if self.aggregate_wolf and any(len(g)>1 for g in self.groups)
              else super().wolf_cells(state))
        self.orbit_stats['solver_wolf_cells']=self.orbit_stats.get('solver_wolf_cells',0)+len(rows)
        self.orbit_stats['solver_wolf_hypotheses']=self.orbit_stats.get('solver_wolf_hypotheses',0)+len(state.hypotheses)
        return rows

    @contextmanager
    def actor_scope(self,info):
        # Wolf-owned roster membership is a condition, not singleton identity.
        groups=[]
        for group in self.groups:
            for member in (False,True):
                part=tuple(p for p in group if bool(info.initial_roster&(1<<(p-1)))==member)
                if part:groups.append(part)
        with self.group_scope(_fix(tuple(groups),(a.target for a in info.attacks))):yield

    def weighted_actor_targets(self,policy):
        probabilities=dict(policy)
        return tuple((g[0],sum((probabilities[p] for p in g),F())) for g in self.target_orbits(tuple(probabilities)))

    def act(self,b,s,past,target,private,observer,*,physical=None):
        with self.group_scope(_fix(self.groups,(target,))):
            return super().act(b,s,past,target,private,observer,physical=physical)
