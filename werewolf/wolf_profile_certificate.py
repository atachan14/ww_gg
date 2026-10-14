"""Fixed-public-profile certificates through the existing common action flow.

No replacement Board, acquisition ledger or private posterior is constructed.
Unsupported later profile dependencies remain Pending; this is not a new solver
for those later choices, nor an automatic selection among incomplete results.
"""
from .actor_information import wolf_information_groups
from .policy_certificates import certify_uniform_profiles
from .policy_dependencies import Dependency
from .information_set_forecast import InformationSetForecast,Pending
from .root_secret_flow import RootSecretEngine


class FixedPublicWolfProfile(RootSecretEngine):
    def __init__(self,board,state,past,rules,strategy,profile,**kwargs):
        super().__init__(rules,strategy,**kwargs)
        self.anchor=(board,state,past)
        self.fixed_profile=profile
        self.fixed_kernel={(info.initial_roster,info.attacks):policy for info,policy in profile}

    def full_renamed_key(self,b,state,past,private,observer,*,target=None,physical=None):
        # The public profile contains player IDs too. Until its entire
        # information/action map has a proved bijection serializer, use the
        # COMPLETE identity key, not a renamed Board with an unrenamed profile.
        return ('fixed-complete-profile',self.fixed_profile,self.rules,self.strategy,
                b,state,past,private,observer,target,physical)
    def public_night_policies(self,b,state,past=()):
        before=self.night_sources.get((b,state,past),state)
        node=Dependency('fixed-wolf-profile',(self.rules,self.strategy,b,before,past,self.fixed_profile))
        self.policy_dependencies.request(node)
        if (b,before,past)!=self.anchor:
            raise Pending('root_guard_profile_continuation_unresolved')
        return self.fixed_kernel

    # Certification must traverse the common action flow, not a proposal's
    # private-only shortcut or a scalar guessed from an individual role world.
    def act(self,*args,**kwargs):return InformationSetForecast.act(self,*args,**kwargs)
    def solve(self,*args,**kwargs):return InformationSetForecast.solve(self,*args,**kwargs)


def certify_wolf_profiles(board,state,past,rules,strategy,*,max_profiles=4096,
                          max_work=250000,max_seconds=20):
    if board.phase!='night' or board.winner:raise ValueError('Continuing public night required')
    if state.public_roles!=tuple(sorted(board.worlds)):raise ValueError('Complete public prior required')
    groups=wolf_information_groups(state)
    legal=tuple((info,tuple(p for p in board.alive if strategy.include_self_bite or
                 not info.initial_roster&(1<<(p-1)))) for info,mass,group in groups)
    def evaluate(profile):
        # Request-local isolation is intentional: no scalar certified under
        # one provisional public profile can escape into another candidate.
        engine=FixedPublicWolfProfile(board,state,past,rules,strategy,profile,max_work=max_work)
        scores={}
        for info,mass,group in groups:
            rows=[]
            for target in dict(legal)[info]:
                node=Dependency('candidate-deviation',(board,state,past,info,target,profile))
                with engine.policy_dependencies.evaluating(node):
                    rows.append((target,engine.act(board,state,past,target,group,None)))
            scores[info]=tuple(rows)
        return scores
    return certify_uniform_profiles(legal,evaluate,maximize=False,max_profiles=max_profiles,
                                    max_work=max_work,max_seconds=max_seconds)
