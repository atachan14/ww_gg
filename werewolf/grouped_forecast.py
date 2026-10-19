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
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if (self.strategy.day,self.strategy.night,self.strategy.fake_reports)!=('random',)*3:raise ValueError('Uniform representative mode only')
        self.groups=();self.orbit_stats={'target_members':0,'target_representatives':0}
        self.action_policy=GroupedPolicy(self)

    # Constructed partitions replace discovery by full-law label permutations.
    # Ordinary named memo keys still retain all numerical inputs.
    def renamed_value_key(self,*args,**kwargs):return None
    def full_renamed_key(self,*args,**kwargs):return None
    def scalar_descriptor(self,*args,**kwargs):return None

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
