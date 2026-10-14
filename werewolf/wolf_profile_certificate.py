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
from .policy_certificates import ProfileSearch,ProfileCertificate,ProfileIssue,best_response_profile
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
        # Only pure physical/public branch construction is shared between
        # candidate profiles. Full Boards and joint ledgers remain in keys.
        self.branch_cache={};self.branch_stats={"calls":0,"hits":0}

    def branch(self,key,compute):
        self.branch_stats['calls']+=1
        if key in self.branch_cache:
            self.branch_stats['hits']+=1
            return self.branch_cache[key]
        value=compute()  # Pending/errors never install partial branches.
        if len(self.branch_cache)<4096:self.branch_cache[key]=value
        return value

    def spend_profile(self):
        if self.profiles_evaluated>=self.max_profiles:
            raise CalculationBudgetExceeded('Aggregate complete-profile work limit exceeded')
        self.profiles_evaluated+=1

    def resolve(self,board,state,past=()):
        key=(board,state,past)
        node=Dependency('profile-proof',(self.rules,self.strategy,*key))
        self.dependencies.request(node)
        if key in self.cache:return self.cache[key]
        prior=self.diagnostics.get(key)
        if prior is not None and prior.status in ('multiple','no_admissible_profile','undefined_observations'):
            return prior  # Reuse refusal evidence, never a kernel/choice.
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
    def physical_children(self,b,target):
        compute=lambda:super(FixedPublicWolfProfile,self).physical_children(b,target)
        if self.resolver is None:return compute()
        return self.resolver.branch(('physical',self.rules,self.strategy,b,target),compute)

    def public_children(self,b,target,guard_state=None):
        compute=lambda:super(FixedPublicWolfProfile,self).public_children(b,target,guard_state)
        if self.resolver is None:return compute()
        return self.resolver.branch(('public',self.rules,self.strategy,b,target,guard_state),compute)

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

    def terminal_day(self,b,state):
        # Every legal execution must physically terminate in EVERY public
        # role world. Then no scan/report/guard/attack memory or future kernel
        # is consulted by the common action flow. Reuse is local to one exact
        # certificate input with all of its fixed private deviation groups;
        # only the public secret mixing can then be omitted from the key.
        if b.phase!='day' or b.winner or state.public_roles!=tuple(sorted(b.worlds)):return False
        from .exact import winner_for
        return all(winner_for(len(b.alive)-1,
            (w[0]&b.alive_mask).bit_count()-bool(w[0]&(1<<(p-1)))) is not None
            for w in b.worlds for p in b.alive)

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
    terminal_rows={}
    def evaluate_raw(profile,*,independence_only=False):
        # Ordinary scalar caches remain isolated by candidate. Only the
        # proved terminal dependency class below shares complete score rows.
        engine=FixedPublicWolfProfile(board,state,past,rules,strategy,profile,
                                      resolver=resolver,stop_on_policy_read=independence_only,max_work=max_work)
        signature=None
        # A proof of the dependency boundary, not a different payoff model:
        # with no active public ability reports and three survivors, every
        # death is terminal and a GJ precedes terminal executions only. Private
        # acquisitions are still generated and retained by the common flow.
        # Thus the
        # fixed profile can affect candidate scores solely through the FULL
        # public Board after GJ. Keep the complete joint law in the actual flow.
        if (not independence_only and len(board.alive)==3 and
                not any(board.claims[p-1]==role and strategy.disclosure_for(role)!='none'
                        for p in board.alive for role in ('seer','medium'))):
            from .guard_model import guard_choices,condition_guard_observation,public_guard_branch_law
            from dataclasses import replace
            possible=False
            for h in state.hypotheses:
                actor=next((a for a in board.alive if h.roles[3]&(1<<(a-1))),None)
                if actor is not None and any(strategy.include_self_bite or not h.roles[0]&(1<<(a-1))
                        for a,q in guard_choices(board,actor,rules,strategy.guard_position,guards=h.guards)):
                    possible=True;break
            if possible:
                acquired=engine.acquire(board,state)
                engine.night_sources[board,acquired,past]=state
                child=replace(condition_guard_observation(board,(),rules,state=acquired),day=board.day+1,phase='day')
                kernel=engine.public_night_policies(board,acquired,past)
                public,joint=public_guard_branch_law(board,acquired,child,None,True,engine,policies=kernel,past=past)
                if engine.terminal_day(public,joint):signature=('terminal-after-gj',public)
            else:signature=('all-physical-terminal',)
            if signature in terminal_rows:return terminal_rows[signature],engine.policy_reads
        resolver.spend_profile()
        scores={}
        for info,mass,group in groups:
            rows=[]
            for target in dict(legal)[info]:
                node=Dependency('candidate-deviation',(board,state,past,info,target,profile))
                with engine.policy_dependencies.evaluating(node):
                    rows.append((target,engine.act(board,state,past,target,group,None)))
            scores[info]=tuple(rows)
        if signature is not None:terminal_rows[signature]=scores
        return scores,engine.policy_reads
    from .policy_choice import uniform_policy
    probe=tuple((info,uniform_policy(actions)) for info,actions in legal)
    total=1
    for info,actions in legal:total*=(1<<len(actions))-1
    if total>max_profiles:
        # A legal deterministic candidate is refusal evidence only, never a
        # selected policy. It can expose undefined continuations even when the
        # full domain is too large to certify.
        probe=tuple((info,uniform_policy(actions[:1])) for info,actions in legal)
    probed=None
    try:
        probed=evaluate_raw(probe)
    except _PolicyRead:
        return ProfileSearch('budget_unfinished',total,0,reason='profile_count_limit')
    except Pending as error:
        if error.reason in ('public_generated_observation_zero_support',
                            'root_guard_profile_undefined_observations'):
            return ProfileSearch('undefined_observations',total,1,issues=(
                ProfileIssue(probe,'undefined_observation',error.reason),),
                reason='undefined_candidate_witness',proof='undefined_witness')
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
                                    max_work=max_work,max_seconds=max_seconds,stop_on_undefined=True)
