"""Fixed-public-profile certificates through the existing common action flow.

No replacement Board, acquisition ledger or private posterior is constructed.
Later public contexts use bounded complete-profile proofs. Unsupported or
unproved dependencies remain Pending, never an arbitrary completed choice.
"""
from .actor_information import wolf_information_groups
from .policy_certificates import certify_uniform_profiles
from .policy_dependencies import Dependency,DependencyGraph
from .information_set_forecast import InformationSetForecast,Pending
from .root_secret_flow import RootSecretEngine
from .policy_certificates import ProfileSearch,ProfileCertificate,best_response_profile
from .calculation_budget import CalculationBudgetExceeded,calculation_budget


class _PolicyRead(Exception):pass


def require_profile(result,*,dependent=False):
    if result.selected is not None:return result.selected
    if dependent and result.status=='budget_unfinished':
        raise CalculationBudgetExceeded('Complete profile continuation budget exceeded')
    raise Pending('root_guard_profile_'+result.status)


class WolfProfileResolver:
    """Complete public-context memoization, including later-night proofs.

    Only a finished unique profile is reused as a policy. Incomplete search
    results remain diagnostics, not cached choices. Parent calculation deadlines
    are inherited by each nested certificate; the profile-work cap is shared.
    """
    def __init__(self,rules,strategy,*,max_profiles=4096,max_work=250000,max_seconds=20):
        if type(max_profiles)is not int or max_profiles<1:raise ValueError('Positive profile limit required')
        self.rules=rules;self.strategy=strategy;self.max_profiles=max_profiles
        self.max_work=max_work;self.max_seconds=max_seconds
        self.cache={};self.active=set();self.diagnostics={};self.profiles_evaluated=0
        self.dependencies=DependencyGraph()

    def spend_profile(self):
        if self.profiles_evaluated>=self.max_profiles:
            raise CalculationBudgetExceeded('Aggregate complete-profile work limit exceeded')
        self.profiles_evaluated+=1

    def resolve(self,board,state,past=()):
        key=(board,state,past)
        node=Dependency('profile-proof',(self.rules,self.strategy,*key))
        self.dependencies.request(node)
        if key in self.cache:return self.cache[key]
        if key in self.active:
            return ProfileSearch('dependency_unfinished',0,0,reason='cyclic_profile_dependency')
        self.active.add(key)
        try:
            with self.dependencies.evaluating(node):
                with calculation_budget(self.max_work,max_seconds=self.max_seconds):
                    result=certify_wolf_profiles(board,state,past,self.rules,self.strategy,
                        max_profiles=self.max_profiles,max_work=self.max_work,
                        max_seconds=self.max_seconds,resolver=self)
                self.diagnostics[key]=result
                if result.selected is not None:self.cache[key]=result
                return result
        finally:self.active.remove(key)


class FixedPublicWolfProfile(RootSecretEngine):
    def __init__(self,board,state,past,rules,strategy,profile,*,resolver=None,stop_on_policy_read=False,**kwargs):
        super().__init__(rules,strategy,**kwargs)
        self.anchor=(board,state,past)
        self.fixed_profile=profile
        self.resolver=resolver
        self.future_kernels={}
        self.policy_reads=0
        self.stop_on_policy_read=stop_on_policy_read
        self.fixed_kernel={(info.initial_roster,info.attacks):policy for info,policy in profile}

    def full_renamed_key(self,b,state,past,private,observer,*,target=None,physical=None):
        # The public profile contains player IDs too. Until its entire
        # information/action map has a proved bijection serializer, use the
        # COMPLETE identity key, not a renamed Board with an unrenamed profile.
        return ('fixed-complete-profile',self.fixed_profile,self.rules,self.strategy,
                b,state,past,private,observer,target,physical)
    def public_night_policies(self,b,state,past=()):
        self.policy_reads+=1
        if self.stop_on_policy_read:raise _PolicyRead()
        before=self.night_sources.get((b,state,past),state)
        node=Dependency('fixed-wolf-profile',(self.rules,self.strategy,b,before,past,self.fixed_profile))
        self.policy_dependencies.request(node)
        key=(b,before,past)
        if key==self.anchor:return self.fixed_kernel
        if self.resolver is None:raise Pending('root_guard_profile_continuation_unresolved')
        if key not in self.future_kernels:
            selected=require_profile(self.resolver.resolve(b,before,past),dependent=True)
            self.future_kernels[key]={(info.initial_roster,info.attacks):policy
                                      for info,policy in selected.profile}
        return self.future_kernels[key]

    # Certification must traverse the common action flow, not a proposal's
    # private-only shortcut or a scalar guessed from an individual role world.
    def act(self,*args,**kwargs):return InformationSetForecast.act(self,*args,**kwargs)
    def solve(self,*args,**kwargs):return InformationSetForecast.solve(self,*args,**kwargs)


def certify_wolf_profiles(board,state,past,rules,strategy,*,max_profiles=4096,
                          max_work=250000,max_seconds=20,resolver=None):
    if resolver is None:
        return WolfProfileResolver(rules,strategy,max_profiles=max_profiles,max_work=max_work,
                                   max_seconds=max_seconds).resolve(board,state,past)
    if board.phase!='night' or board.winner:raise ValueError('Continuing public night required')
    if state.public_roles!=tuple(sorted(board.worlds)):raise ValueError('Complete public prior required')
    groups=wolf_information_groups(state)
    legal=tuple((info,tuple(p for p in board.alive if strategy.include_self_bite or
                 not info.initial_roster&(1<<(p-1)))) for info,mass,group in groups)
    def evaluate_raw(profile,*,independence_only=False):
        # Request-local isolation is intentional: no scalar certified under
        # one provisional public profile can escape into another candidate.
        resolver.spend_profile()
        engine=FixedPublicWolfProfile(board,state,past,rules,strategy,profile,
                                      resolver=resolver,stop_on_policy_read=independence_only,max_work=max_work)
        scores={}
        for info,mass,group in groups:
            rows=[]
            for target in dict(legal)[info]:
                node=Dependency('candidate-deviation',(board,state,past,info,target,profile))
                with engine.policy_dependencies.evaluating(node):
                    rows.append((target,engine.act(board,state,past,target,group,None)))
            scores[info]=tuple(rows)
        return scores,engine.policy_reads
    from .policy_choice import uniform_policy
    probe=tuple((info,uniform_policy(actions)) for info,actions in legal)
    total=1
    for info,actions in legal:total*=(1<<len(actions))-1
    probed=None
    try:
        probed=evaluate_raw(probe,independence_only=total>max_profiles)
    except _PolicyRead:
        return ProfileSearch('budget_unfinished',total,0,reason='profile_count_limit')
    except Pending:pass
    except CalculationBudgetExceeded:
        return ProfileSearch('budget_unfinished',total,0,reason='profile_probe_budget')
    if probed is not None and probed[1]==0:
        # All candidate/chance paths completed without reading ANY policy.
        # This controlled common engine reads a profile only through the
        # provider above; therefore these exact scores hold for every profile.
        # Prove the single uniform best response directly, without enumerating
        # exponentially many irrelevant kernels or inventing a terminal value.
        chosen,rows=best_response_profile(legal,probed[0],maximize=False)
        return ProfileSearch('unique',total,1,(ProfileCertificate(chosen,rows),),
                             proof='policy_independent_scores')
    def evaluate(profile):
        if profile==probe and probed is not None:return probed[0]
        return evaluate_raw(profile)[0]
    return certify_uniform_profiles(legal,evaluate,maximize=False,max_profiles=max_profiles,
                                    max_work=max_work,max_seconds=max_seconds)
