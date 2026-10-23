"""Opt-in complete root secrets under existing uniform acquisition rules.

This API never replaces the fixed-CO entry or an unsupported max with random.
Public Model A role weights and actual branch measures remain distinct.
"""
from .calculation_budget import DEFAULT_MAX_WORK, DEFAULT_MAX_SECONDS
from .seer_intervention import scan_intervention_matches
from dataclasses import dataclass,replace,asdict
from fractions import Fraction as F
from .seer_acquisition import from_board,normalize
from .seer_future_uniform import TrueScanState,FuturePending,acquire_uniform
from .actor_information import condition_actor_state
from .evaluation_branch import ActionInputs,ContinuationInputs,physical_board
from .information_set_forecast import InformationSetForecast,InformationSetActionPolicy,Pending
from .action_flow import resolve_action
from .night_knowledge import WolfAttack
from .calculation_budget import calculation_budget,CalculationBudgetExceeded
from .forecast_result import Forecast
from .exact import legal_targets,Strategy


@dataclass(frozen=True)
class RootSecretBranch:
    public: object
    public_law: TrueScanState
    physical: object
    physical_law: TrueScanState
    past: tuple = ()

    def __post_init__(self):
        if self.public_law.public_roles!=tuple(sorted(self.public.worlds)):
            raise ValueError('Public role prior must remain owned by public Board')
        if self.physical_law.public_roles!=tuple(sorted(self.physical.worlds)):
            raise ValueError('Physical role law must match actual branch Board')
        physical_board(self.public,self.physical_law,self.physical)


@dataclass(frozen=True)
class RootActorView:
    belief: TrueScanState
    physical_law: TrueScanState


def prepare_root_secrets(board,rules,*,max_work=DEFAULT_MAX_WORK):
    if board.day!=1 or board.phase!='day' or board.history or board.alive!=tuple(range(1,board.player_count+1)):
        return FuturePending('root_secret_initial_board_required')
    initial=TrueScanState(from_board(board),initial_rule=rules.initial_seer,tracked=None)
    law=acquire_uniform(initial,board.alive,max_work=max_work)
    if isinstance(law,FuturePending):return law
    return RootSecretBranch(board,law,board,law)


def observe_root_public(branch,public,compatible,*,past=None):
    """Use externally updated Model A Q; condition history within each world.

    The caller supplies an existing public observation predicate, never an
    optimized-action likelihood for public roles. Physical evidence uses P.
    """
    from .belief_projection import restore_public_history_weights
    try:public_law=restore_public_history_weights(branch.public_law,public,compatible)
    except ValueError:return FuturePending('root_secret_public_history_zero_support')
    weights={w[:-1]:w[-1] for w in public.worlds}
    predicate=lambda h:h.roles in weights and compatible(h)
    if not any(predicate(h) for h in branch.physical_law.hypotheses):
        return FuturePending('root_secret_physical_zero_support')
    physical_law=condition_actor_state(branch.physical_law,predicate)
    physical=physical_board(public,physical_law,branch.physical)
    return RootSecretBranch(public,public_law,physical,physical_law,branch.past if past is None else tuple(past))


def root_actor_view(branch,compatible,*,guards=(),attacks=()):
    if not any(compatible(h) for h in branch.public_law.hypotheses):
        return FuturePending('root_secret_actor_belief_zero_support')
    if not any(compatible(h) for h in branch.physical_law.hypotheses):
        return FuturePending('root_secret_actor_physical_zero_support')
    return RootActorView(condition_actor_state(branch.public_law,compatible,guards=guards,attacks=attacks),
                         condition_actor_state(branch.physical_law,compatible,guards=guards,attacks=attacks))


def root_policy_supported(strategy,*,hunters,seers,mediums):
    if strategy.day=='random':
        return strategy.night in (('random','max') if hunters==1 else ('random',))
    return (strategy.day=='max' and strategy.night=='max' and hunters==1
            and not seers and not mediums)


def root_strategy_supported(board,strategy):
    return root_policy_supported(strategy,hunters=board.initial_hunter_count,
                                 seers=board.initial_seer_count,mediums=board.initial_medium_count)


def root_max_history_needed(game,board):
    """Retain legacy fixed-known-hunter max entry contracts.

    Saved root histories still need their full ledger if the INITIAL public
    hunter was unknown, even when a later observation identifies its location.
    """
    if not game.get('history'):return len({w[3] for w in board.worlds})>1
    from .exact import initial_board,condition_claims,ClaimPolicy
    first=game['history'][0]
    seed=initial_board(board.player_count,game.get('wolves',1),board.initial_medium_count,
                       board.initial_seer_count,board.initial_hunter_count,experimental_cast=True)
    seed=condition_claims(seed,tuple(first.get('claims',('latent',)*board.player_count)),
                          ClaimPolicy(**first.get('claim_policy',{})))
    return len({w[3] for w in seed.worlds})>1


def root_scope(branch,rules,strategy,*,_known_publications=()):
    if not root_strategy_supported(branch.public,strategy):return 'root_secret_max_unimplemented'
    from .guard_model import scope_reason
    reason=scope_reason(branch.public,rules,strategy,True,joint_max=True)
    if reason:return reason
    if rules.allow_self_bite and not strategy.include_self_bite:
        return 'root_secret_self_bite_policy_support_unimplemented'
    # Initial full-disclosure omissions retain the existing fixed-CO contract.
    if strategy.disclosure_for('seer')=='all':
        # Closed full-disclosure snapshots know that a report occurred even
        # when its input CONTENT was later withdrawn. This proof carries only
        # (owner, acquisition-day), never a retired target/color or acquisition.
        published={(r.player,r.acquired_day) for r in branch.past}|set(_known_publications)
        if any(a.player in branch.public.alive and branch.public.claims[a.player-1]=='seer' and
               (a.player,a.day) not in published for h in branch.public_law.hypotheses for a in h.acquisitions):
            return 'full_disclosure_truth_not_conditioned'
    if (strategy.disclosure_for('medium')=='all' and strategy.fake_reports=='max' and
        any(branch.public.claims[p-1]=='medium' for p in branch.public.alive)):
        return 'root_secret_max_unimplemented'
    return None


class RootSecretPolicy(InformationSetActionPolicy):
    def action_recorder(self,board,payload):
        day=super().action_recorder(board,payload)
        if day is not None:return day
        graph=getattr(self.engine,'evaluation_graph',None)
        if graph is None or board.phase!='night' or not graph.hunter_flow_scope(board,payload):return None
        return lambda target,acquired,outcomes,value:graph.record_action(board,payload,target,acquired,outcomes,value)

    def morning_recorder(self,payload):
        graph=getattr(self.engine,'evaluation_graph',None)
        if graph is None or not graph.hunter_flow_scope(payload.public,payload):return None
        return lambda branches,value:graph.record_morning(payload,branches,value)

    def acquire(self,b,payload):
        acquired=super().acquire(b,payload)
        self.engine.night_sources[b,acquired.public_state,payload.past]=payload.public_state
        return acquired



class RootSecretEngine(InformationSetForecast):
    retain_joint_guard_history=True
    joint_guard_max=True
    def __init__(self,rules,strategy,**kwargs):
        super().__init__(rules,strategy,retire_uninformative_scans=False,memoize_flows=strategy.night=='max',**kwargs)
        self.action_policy=RootSecretPolicy(self)
        self.night_sources={};self.night_kernels={}
        self.verified_actor_kernels=set();self.verifying_actor_mask=None
        self.candidate_profiles=();self.candidate_profile_ids={};self.candidate_contexts=();self.candidate_rule_cache={}
        self.actor_candidate_keys={};self.actor_proposals={};self.actor_certificates={}
        self.owned_flow_engines={}
        from .policy_dependencies import DependencyGraph
        self.policy_dependencies=DependencyGraph()
        self._profile_resolver=None

    def certified_night_policies(self,b,state,past=()):
        from .wolf_profile_certificate import WolfProfileResolver,require_profile
        if self._profile_resolver is None:
            self._profile_resolver=WolfProfileResolver(self.rules,self.strategy,max_work=self.max_work)
        from .policy_dependencies import Dependency
        self.policy_dependencies.request(Dependency('profile-proof',(self.rules,self.strategy,b,state,past)))
        result=self._profile_resolver.resolve(b,state,past)
        self.policy_dependencies.include(self._profile_resolver.dependencies)
        selected=require_profile(result)
        key=(b,state,past)
        kernel={(info.initial_roster,info.attacks):policy for info,policy in selected.profile}
        self.night_kernels[key]=kernel
        self.verified_actor_kernels.add(key)
        return kernel

    def full_renamed_key(self,b,s,past,private,observer,*,target=None,physical=None):
        if self.candidate_contexts and self.memoize_flows:
            source=(b,s,past,private,observer,target,physical,self.candidate_profiles,self.verifying_actor_mask)
            if source not in self.exact_keys:
                from .exact_renaming import canonical_key
                self.exact_keys[source]=self.canonical_payoff_key(b,s,past,private,observer,self.rules,self.strategy,
                    target=target,physical=physical,wolf_profiles=self.candidate_contexts,
                    actor_mask=self.verifying_actor_mask)
            complete=self.exact_keys[source]
            return ('root-candidate-complete',complete) if complete is not None else ('root-candidate-identity',source)
        key=super().full_renamed_key(b,s,past,private,observer,target=target,physical=physical)
        if not self.memoize_flows:return None
        # Proof-only actor continuation and ordinary public evaluation cannot
        # share certificates. Keep full ledgers; unsupported renamings fall
        # back to identity rather than a reduced role/history descriptor.
        exact=key or (self.rules,self.strategy,b,s,past,private,observer,target,physical)
        return ('root-complete-payoff',self.verifying_actor_mask,self.candidate_profiles,exact)

    def actor_candidate_key(self,b,state,past,group,target):
        source=(self.rules,self.strategy,b,state,past,group,target)
        if source not in self.actor_candidate_keys:
            from .exact_renaming import canonical_key
            self.actor_candidate_keys[source]=canonical_key(b,state,past,group,None,
                self.rules,self.strategy,target=target)
        return self.actor_candidate_keys[source]

    def public_night_policies(self,b,state,past=()):
        from .policy_dependencies import Dependency,DependencyCycle
        before=self.night_sources.get((b,state,past),state)
        node=Dependency('wolf-policy',(self.rules,self.strategy,b,before,past))
        self.policy_dependencies.request(node)
        if (b,before,past) in self.night_kernels:
            return self._public_night_policies(b,state,past)
        try:
            with self.policy_dependencies.evaluating(node):
                return self._public_night_policies(b,state,past)
        except DependencyCycle as error:
            raise Pending('root_guard_policy_dependency_cycle') from error

    def _public_night_policies(self,b,state,past=()):
        from .actor_information import wolf_information_groups
        from .fixed_actor_continuation import fixed_actor_value
        from .policy_dependencies import Dependency
        from .policy_choice import optimal_targets,uniform_policy
        before=self.night_sources.get((b,state,past),state)
        if before.public_roles!=tuple(sorted(b.worlds)):
            raise Pending('root_guard_max_public_prior_mismatch')
        key=(b,before,past)
        if key not in self.night_kernels and self.strategy.night=='max' and (self.strategy.day=='max' or
                b.initial_seer_count or b.initial_medium_count):
            # The actor-only proposal deliberately excludes mixed-role states.
            # Do not expand its physical tree merely to discover that later;
            # use the complete shared certificate directly.
            return self.certified_night_policies(b,before,past)
        if key not in self.night_kernels:
            result={};verify=[]
            if self.strategy.night=='random':
                from .actor_information import wolf_information_keys
                rows=((info,None,None) for info in wolf_information_keys(before))
            else:rows=wolf_information_groups(before)
            for info,mass,group in rows:
                targets=tuple(p for p in b.alive if self.strategy.include_self_bite or
                              not info.initial_roster&(1<<(p-1)))
                if self.strategy.night=='random':chosen=targets
                else:
                    scores=[]
                    for p in targets:
                        candidate=self.actor_candidate_key(b,before,past,group,p)
                        node=Dependency('actor-proposal',(b,before,past,info,p))
                        self.policy_dependencies.request(node)
                        if candidate is not None and candidate in self.actor_proposals:
                            value=self.actor_proposals[candidate]
                            self.policy_dependencies.completed.add(node)
                        else:
                            with self.policy_dependencies.evaluating(node):
                                value=fixed_actor_value(b,before,self,info=info,target=p,allow_actor_only=True)
                            if candidate is not None and value is not None:self.actor_proposals[candidate]=value
                        scores.append((p,value))
                    scores=tuple(scores)
                    if any(v is None for p,v in scores):
                        return self.certified_night_policies(b,before,past)
                    chosen=optimal_targets(scores,maximize=False)
                    if len({h.roles for h in group.hypotheses})>1:verify.append((info,group,scores))
                result[info.initial_roster,info.attacks]=uniform_policy(chosen)
            # A full proposal is visible only inside its common-flow proof.
            # No unknown-role actor-only value escapes unless EVERY candidate
            # agrees with the fixed PUBLIC-kernel Model A continuation.
            self.night_kernels[key]=result
            try:
                certified=[]
                for info,group,scores in verify:
                    previous=self.verifying_actor_mask;self.verifying_actor_mask=info.initial_roster
                    try:
                        checked=[]
                        for p,v in scores:
                            candidate=self.actor_candidate_key(b,before,past,group,p)
                            node=Dependency('common-candidate',(b,before,past,info,p))
                            with self.policy_dependencies.evaluating(node):
                                if candidate is not None and candidate in self.actor_certificates:
                                    value=self.actor_certificates[candidate]
                                else:
                                    from .wolf_profile_certificate import wolf_candidate_profile
                                    profile=tuple((owned,result[owned.initial_roster,owned.attacks])
                                                  for owned,mass,law in wolf_information_groups(before))
                                    from .candidate_policy import CandidateRules
                                    if key not in self.candidate_rule_cache:
                                        self.candidate_rule_cache[key]=CandidateRules(b,before,past,self.rules,self.strategy)
                                    rules_for_candidates=self.candidate_rule_cache[key]
                                    tested=wolf_candidate_profile(profile,info,p,rules=rules_for_candidates)
                                    previous_kernel=self.night_kernels[key]
                                    previous_profiles=self.candidate_profiles
                                    previous_contexts=self.candidate_contexts
                                    self.night_kernels[key]={(owned.initial_roster,owned.attacks):policy
                                                             for owned,policy in tested}
                                    identity=(key,tested)
                                    token=self.candidate_profile_ids.setdefault(identity,len(self.candidate_profile_ids)+1)
                                    self.candidate_profiles=(*previous_profiles,token)
                                    self.candidate_contexts=(*previous_contexts,(b,before,past,tested))
                                    try:value=self.act(b,before,past,p,group,None)
                                    finally:
                                        self.night_kernels[key]=previous_kernel
                                        self.candidate_profiles=previous_profiles
                                        self.candidate_contexts=previous_contexts
                            checked.append((p,value));certified.append((candidate,value))
                        checked=tuple(checked)
                    finally:self.verifying_actor_mask=previous
                    if checked!=scores:raise Pending('root_actor_continuation_belief_divergence')
                self.verified_actor_kernels.add(key)
                for candidate,value in certified:
                    if candidate is not None:self.actor_certificates[candidate]=value
            except BaseException:
                self.night_kernels.pop(key,None);raise
        return self.night_kernels[key]

    def wolf_policy(self,b,s,past,mask,history=()):
        if self.strategy.night!='max' or not b.initial_hunter_count:
            return super().wolf_policy(b,s,past,mask,history)
        from .actor_information import WolfInformation
        info=WolfInformation(mask,history)
        try:info.condition_public(s)
        except ValueError:raise Pending('information_set_roster_missing')
        kernel=self.public_night_policies(b,s,past)
        if (mask,info.attacks) not in kernel:raise Pending('information_set_roster_missing')
        return kernel[mask,info.attacks]

    def owned_night_action(self,b,s,past,target,private,observer,*,physical=None):
        # Conditional scalar decomposition, not a replacement public Board or
        # a physical-only proposal. Public choices are fixed, and the only
        # subsequent night has three survivors and fixed public day choices.
        if (self.verifying_actor_mask is not None or b.phase!='night' or len(b.alive)!=4 or
            len(s.rosters)!=b.day or observer is not None or
            self.strategy.day!='random' or self.strategy.night!='max' or
            self.strategy.guard_position!=('uniform',) or
            any(b.claims[p-1]==role and self.strategy.disclosure_for(role)!='none'
                for p in b.alive for role in ('seer','medium')) or
            len({h.roles[0] for h in s.hypotheses})<=1):return None
        from .actor_information import wolf_information_groups,condition_actor_state
        from .exact import replace_worlds
        from .wolf_profile_certificate import FixedPublicWolfProfile
        kernels=self.public_night_policies(b,s,past)
        before=self.night_sources.get((b,s,past),s)
        resolver=getattr(self,'resolver',None) or self._profile_resolver
        if resolver is None:return None  # Preserve the existing verified actor-cut route.
        value=F()
        for info,mass,group in wolf_information_groups(private):
            law=condition_actor_state(before,lambda h:h.roles[0]==info.initial_roster)
            own_board=replace_worlds(b,law.public_roles,wolf_count=None)
            profile=tuple((i,kernels[i.initial_roster,i.attacks])
                          for i,m,g in wolf_information_groups(law))
            key=(own_board,law,past,profile)
            if key not in self.owned_flow_engines:
                child=FixedPublicWolfProfile(own_board,law,past,self.rules,self.strategy,profile,
                    resolver=resolver,max_work=self.max_work)
                if len(self.owned_flow_engines)<32:self.owned_flow_engines[key]=child
            else:child=self.owned_flow_engines[key]
            value+=mass*child.act(own_board,law,past,target,group,None,
                physical=physical_board(own_board,group,physical))
            self.policy_dependencies.include(child.policy_dependencies)
        return value

    def act(self,b,s,past,target,private,observer,*,physical=None):
        if type(target)is not int or target not in b.alive:
            raise Pending('information_set_internal_illegal_action')
        checked=physical_board(b,private,physical)
        if target not in legal_targets(checked,self.rules,self.strategy):
            raise Pending('information_set_internal_illegal_action')
        if self.strategy.night=='random':
            from .fixed_actor_continuation import fixed_uniform_action_value
            uniform=fixed_uniform_action_value(b,s,private,self,target,observer=observer,physical=checked,past=past)
            if uniform is not None:return uniform
            from .terminal_followup import uniform_terminal_action_value
            terminal=uniform_terminal_action_value(b,s,private,self,target,observer=observer,physical=checked)
            if terminal is not None:return terminal
        owned_value=self.owned_night_action(b,s,past,target,private,observer,physical=physical)
        if owned_value is not None:return owned_value
        if b.phase=='night' and self.strategy.night=='max' and observer is None:
            from .actor_information import wolf_information_groups
            if self.verifying_actor_mask is not None:
                groups=wolf_information_groups(private)
                # This law starts as the PUBLIC-derived actor infoset in the
                # proof above, then only its own actions/public outcomes split
                # it. Singleton roles are actual actor knowledge, never viewer
                # restriction; remaining unknown guard records stay integrated.
                if (len(groups)==1 and groups[0][0].initial_roster==self.verifying_actor_mask and
                        len({h.roles for h in private.hypotheses})==1):
                    from .fixed_actor_continuation import fixed_actor_value
                    part=fixed_actor_value(checked,private,self,info=groups[0][0],target=target)
                    if part is not None:return part
                return super().act(b,s,past,target,private,observer,physical=physical)
            if b.initial_seer_count or b.initial_medium_count:
                return super().act(b,s,past,target,private,observer,physical=physical)
            from .fixed_actor_continuation import fixed_actor_value
            value=F();resolved=True
            for info,mass,group in wolf_information_groups(private):
                try:part=fixed_actor_value(b,s,self,info=info,target=target,measure=group,allow_actor_only=True)
                except ValueError:part=None
                if part is None:resolved=False;break
                actor=info.condition_public(s)
                if len({h.roles for h in actor.hypotheses})>1:
                    self.public_night_policies(b,s,past)
                    source=self.night_sources.get((b,s,past),s)
                    if (b,source,past) not in self.verified_actor_kernels:
                        raise Pending('root_actor_continuation_unverified')
                value+=mass*part
            if resolved:return value
        return super().act(b,s,past,target,private,observer,physical=physical)

    def solve(self,b,s,past,private,observer,*,physical=None):
        if self.strategy.day=='random' and self.strategy.night=='random' and observer is None:
            from .fixed_actor_continuation import fixed_uniform_action_value
            uniform=fixed_uniform_action_value(b,s,private,self,None,physical=physical_board(b,private,physical),past=past)
            if uniform is not None:
                graph=getattr(self,'evaluation_graph',None)
                if graph is not None:graph.record_day_value(ContinuationInputs(b,s,past,private,observer,physical_board(b,private,physical)),uniform,'uniform-value-reduction')
                return uniform
        if self.verifying_actor_mask is not None and observer is None:
            from .actor_information import wolf_information_groups
            groups=wolf_information_groups(private)
            if (len(groups)==1 and groups[0][0].initial_roster==self.verifying_actor_mask and
                    len({h.roles for h in private.hypotheses})==1):
                from .fixed_actor_continuation import fixed_actor_value
                actual=physical_board(b,private,physical)
                value=fixed_actor_value(actual,private,self,info=groups[0][0])
                if value is not None:return value
        return super().solve(b,s,past,private,observer,physical=physical)

    def exchangeable(self,b):return False  # Keep the complete latent acquisition flow.
    def value_law(self,state):return state  # No history compression in this entry.


def step_root_action(branch,target,rules,strategy,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS,publish=True,_engine=None,_observed_alive=None,_known_publications=()):
    """Explicit action intervention through the shared ability/death/report flow."""
    reason=root_scope(branch,rules,strategy,_known_publications=_known_publications)
    if reason:return FuturePending(reason)
    if branch.public.winner:return FuturePending('root_secret_terminal_action')
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            e=_engine or RootSecretEngine(rules,strategy,max_work=max_work)
            if (e.rules,e.strategy)!=(rules,strategy):raise ValueError('Action engine configuration mismatch')
            own=branch.physical_law;physical=branch.physical
            if branch.public.phase=='night':
                from .exact import forced_action_worlds,replace_worlds
                from .belief_projection import project_private
                physical=replace_worlds(physical,forced_action_worlds(physical,target,rules,strategy))
                own=project_private(own,physical,marginalize_private=False)
            acquired,outcomes=resolve_action(branch.public,ActionInputs(branch.public_law,branch.past,
                own,None,physical),target,e.action_policy,observed_alive=_observed_alive)
            result=[]
            for o in outcomes:
                c=e.action_policy.project(branch.public,acquired,o,target)
                if publish and branch.public.phase=='night' and o.board.winner is None:
                    choices=e.push(c.public_state,c.private,e.morning(c.public,c.public_state,c.past))
                else:choices=((F(1),c.public,c.public_state,c.past,c.private),)
                for q,b,s,past,own in choices:
                    result.append((o.probability*q,RootSecretBranch(b,s,physical_board(b,own,c.physical),own,past)))
            return tuple(result)
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)


def root_secret_value(branch,rules,strategy,*,actor=None,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS):
    if branch.public.winner:return F(branch.public.winner=='village')
    reason=root_scope(branch,rules,strategy)
    if reason:return FuturePending(reason)
    own=branch.physical_law if actor is None else actor.physical_law
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            e=RootSecretEngine(rules,strategy,max_work=max_work)
            return e.solve(branch.public,branch.public_law,branch.past,own,None,
                           physical=physical_board(branch.public,own,branch.physical))
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)


def root_screen_eligible(board,rules,strategy):
    """Uniform roots and certified C/H/W day-max; legacy known hunters stay separate."""
    return (bool(board.initial_seer_count or board.initial_hunter_count) and
            board.initial_hunter_count<=1 and
            board.day==1 and board.phase=='day' and not board.history and
            board.alive==tuple(range(1,board.player_count+1)) and
            root_strategy_supported(board,strategy) and
            (strategy.day=='random' or root_max_history_needed({},board)) and
            not (rules.allow_self_bite and not strategy.include_self_bite) and
            not any(board.claims[p-1]=='seer' for p in board.alive) and
            not (strategy.disclosure_for('medium')=='all' and strategy.fake_reports=='max' and
                 any(board.claims[p-1]=='medium' for p in board.alive)))


def root_screen_forecast(board,rules,strategy,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS):
    """Full initial screen metrics from one complete latent secret law."""
    if not root_screen_eligible(board,rules,strategy):
        return FuturePending('root_secret_screen_scope_unimplemented')
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            branch=prepare_root_entry({},board,rules,strategy,max_work=max_work,max_seconds=max_seconds)
            if isinstance(branch,FuturePending):return branch
            return root_branch_forecast(branch,rules,strategy,max_work=max_work,max_seconds=max_seconds)
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)


def root_replay_eligible(game,board,rules,strategy):
    """Saved supported policies and observed publications; no invented CO law."""
    if (not game.get('history') or not (board.initial_seer_count or board.initial_hunter_count) or
            board.initial_hunter_count>1):
        return False
    snapshots=(*game['history'],game)
    return (root_strategy_supported(board,strategy) and
            (strategy.day=='random' or root_max_history_needed(game,board)) and
            not (rules.allow_self_bite and not strategy.include_self_bite) and
            all(root_strategy_supported(board,Strategy(**step.get('policy',{}))) for step in snapshots))


def prepare_root_entry(game,board,rules,strategy,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS):
    """Shared public/private entry selection; None preserves the legacy route.

    A supported entry that cannot be prepared returns Pending, never None.
    Forecast budgets remain owned by the caller's existing public/private API.
    """
    if root_screen_eligible(board,rules,strategy):
        return prepare_root_secrets(board,rules,max_work=max_work)
    if root_replay_eligible(game,board,rules,strategy):
        return replay_root_secrets(game,board,rules,strategy,max_work=max_work,max_seconds=max_seconds,
                                   _historical_disclosure_proof=True)
    return None


def observe_root_snapshot(branch,game,index,rules,*,guard_priors=None):
    """Replay the existing public observations, then condition the joint ledger.

    Hand reports remain truth-support filters. Their target frequencies never
    replace Model A role weights or introduce a fake-report selection law.
    """
    from .seer_manual import replay,migrate_game
    from .report_publication import publication_slot
    from .seer_acquisition import SeerReport,condition_publications
    snapshot=game['history'][index] if index<len(game['history']) else game
    slot=2*(branch.public.day-1)+(branch.public.phase=='night')
    prefix={**game,'history':game['history'][:index],
            'claims':snapshot.get('claims',['latent']*branch.public.player_count),
            'claim_policy':snapshot.get('claim_policy',{}),'policy':snapshot.get('policy',{}),
            'result_disclosure_model':snapshot.get('result_disclosure_model'),
            'rules':asdict(rules),'seer_mode':'information-fixed-v1',
            'seer_options':{'initial_rule':rules.initial_seer,'likelihood':'compatibility'},
            'seer_inputs':[r for r in game.get('seer_inputs',()) if publication_slot(game,'seer',r)<=slot],
            'reports':[r for r in game.get('reports',()) if publication_slot(game,'medium',r)<=slot]}
    _,progress=replay(migrate_game(prefix),guard_priors=guard_priors or {})
    observed=progress.board
    reports=tuple(SeerReport(r['day'],max(r['day'],1+publication_slot(game,'seer',r)//2),
                            r['reporter'],r['target'],r['color'])
                  for r in prefix['seer_inputs'] if r['target'] is not None and r['color'] is not None)
    try:kept=condition_publications(branch.public_law.hypotheses,reports)
    except ValueError:return FuturePending('root_secret_public_history_zero_support')
    signatures={(h.roles,h.acquisitions,h.guards,h.attacks) for h in kept}
    return observe_root_public(branch,observed,
        lambda h:(h.roles,h.acquisitions,h.guards,h.attacks) in signatures,past=reports)


def replay_root_secrets(game,board,rules,strategy,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS,_collect_guard_priors=False,_historical_disclosure_proof=True,_group_observer=None):
    """Recreate actual joint histories; observed bites use the configured policy.

    Q is restored from the existing public replay only after P is conditioned.
    Actions recorded in history are observations, not target-row interventions.
    """
    from .exact import initial_board,condition_claims,group_initial_board,ClaimPolicy
    if _collect_guard_priors and not game.get('history'):return {}
    if not root_replay_eligible(game,board,rules,strategy):
        return FuturePending('root_secret_replay_scope_unimplemented')
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            seed=initial_board(board.player_count,game.get('wolves',1),game.get('mediums',0),
                               game.get('seers',0),game.get('hunters',0),experimental_cast=True)
            first=game['history'][0]
            claims=tuple(first.get('claims',('latent',)*board.player_count))
            cp=ClaimPolicy(**first.get('claim_policy',{}))
            seed=(group_initial_board(seed,claims,cp) if game.get('model')=='group'
                  else condition_claims(seed,claims,cp))
            guard_priors={}
            branch=prepare_root_secrets(seed,rules,max_work=max_work)
            if isinstance(branch,FuturePending):return branch
            if _group_observer is not None:_group_observer.record('initial',branch,None)
            for index,step in enumerate(game['history']):
                branch=observe_root_snapshot(branch,game,index,rules,guard_priors=guard_priors)
                if isinstance(branch,FuturePending):return branch
                if _group_observer is not None:_group_observer.record('snapshot',branch,index)
                policy=Strategy(**step['policy']);target=step['target']
                known_publications=()
                if _historical_disclosure_proof and step.get('result_disclosure_model')=='full-observed-v1':
                    from .result_disclosure import snapshot as disclosure_snapshot
                    _,reported=disclosure_snapshot(game,branch.public,branch.public.claims)
                    known_publications=tuple((p,day) for kind,day,p in reported if kind=='seer')
                if branch.public.phase=='night':guard_priors[index]=branch.public_law
                if not rules.allow_repeat_guard and branch.public.phase=='night' and 'observation' not in step:
                    return FuturePending('guard_saved_observation_required')
                candidates=branch.public.alive if branch.public.phase=='night' and target is None else (target,)
                selected=[]
                engine=RootSecretEngine(rules,policy,max_work=max_work)
                kernels=(engine.public_night_policies(branch.public,branch.public_law,branch.past)
                         if branch.public.phase=='night' else {})
                for action in candidates:
                    active=branch;mass=F(1)
                    if branch.public.phase=='night':
                        legal=lambda h:policy.include_self_bite or not h.roles[0]&(1<<(action-1))
                        from .actor_information import condition_wolf_choice
                        try:mass,own=condition_wolf_choice(branch.physical_law,kernels,action,compatible=legal)
                        except ValueError:continue
                        active=replace(branch,physical_law=own,
                                       physical=physical_board(branch.public,own,branch.physical))
                    expected=branch.public.alive if target is None else tuple(p for p in branch.public.alive if p!=target)
                    children=step_root_action(active,action,rules,policy,max_work=max_work,
                                              max_seconds=max_seconds,publish=False,_engine=engine,
                                              _observed_alive=expected,_known_publications=known_publications)
                    if isinstance(children,FuturePending):return children
                    selected.extend((mass*q,c) for q,c in children if not c.public.winner and c.public.alive==expected)
                if not selected:
                    if _collect_guard_priors and index==len(game['history'])-1:return guard_priors
                    return FuturePending('root_secret_replay_observation_zero_support')
                template=selected[0][1]
                entries=normalize(tuple(replace(h,mass=q*h.mass) for q,c in selected for h in c.physical_law.hypotheses))
                own=replace(template.physical_law,hypotheses=entries)
                physical=physical_board(template.public,own,template.physical)
                # Uniform saved policies depend only on roles and owned records.
                # Restore Q per world, retaining the observed guard/bite mixture.
                branch=observe_root_public(RootSecretBranch(physical,own,physical,own,template.past),
                                           template.public,lambda h:True)
                if isinstance(branch,FuturePending):return branch
                if _group_observer is not None:_group_observer.record('observed-action',branch,(index,target))
            branch=observe_root_snapshot(branch,game,len(game['history']),rules,guard_priors=guard_priors)
            if isinstance(branch,FuturePending):return branch
            if _group_observer is not None:_group_observer.record('snapshot',branch,len(game['history']))
            if _collect_guard_priors:
                if branch.public.phase=='night':guard_priors[len(game['history'])]=branch.public_law
                return guard_priors
            facts=('alive','day','phase','history')
            if any(getattr(branch.public,k)!=getattr(board,k) for k in facts):
                return FuturePending('root_secret_replay_board_mismatch')
            result=observe_root_public(branch,board,lambda h:True)
            if _group_observer is not None and not isinstance(result,FuturePending):_group_observer.record('finished',result,None)
            return result
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)


def root_branch_forecast(branch,rules,strategy,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS):
    """One retained joint law supplies overview, target rows and dawn values."""
    reason=root_scope(branch,rules,strategy)
    if reason:return FuturePending(reason)
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            from .local_reuse import make_root_engine
            e=make_root_engine(RootSecretEngine,branch.public,rules,strategy,max_work=max_work)
            b=branch.public;s=branch.public_law;past=branch.past;own=branch.physical_law
            value=e.solve(b,s,past,own,None,physical=branch.physical)
            from .belief_projection import project_private
            from .exact import forced_action_worlds,replace_worlds
            from .model_a_public import horizon_for_action
            targets=legal_targets(b,rules,strategy)
            laws={t:project_private(own,replace_worlds(branch.physical,
                forced_action_worlds(branch.physical,t,rules,strategy)),marginalize_private=False)
                if b.phase=='night' else own for t in targets}
            actions=tuple((t,e.act(b,s,past,t,laws[t],None,
                physical=physical_board(b,laws[t],branch.physical))) for t in targets)
            horizons=tuple((t,horizon_for_action(e,b,s,past,t,laws[t])) for t in targets)
            return Forecast(value,actions,horizons)
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)



def root_seer_forecast(branch,player,acquisitions,rules,strategy,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS,_actor=None):
    """Own scan interventions over the unchanged public joint policy law."""
    from .seer_future_uniform import candidates
    compatible=lambda h:bool(h.roles[2]&(1<<(player-1))) and all(a in h.acquisitions for a in acquisitions)
    actor=_actor if _actor is not None else root_actor_view(branch,compatible)
    if isinstance(actor,FuturePending):return actor
    histories={tuple(a for a in h.acquisitions if a.player==player) for h in actor.physical_law.hypotheses}
    if len(histories)!=1:return FuturePending('seer_view_past_private_history_unresolved')
    choices={candidates(h,player,branch.public.alive) for h in actor.physical_law.hypotheses}
    if len(choices)!=1:return FuturePending('seer_view_target_generation_support_unresolved')
    reason=root_scope(branch,rules,strategy)
    if reason:return FuturePending(reason)
    day=branch.public.day+1;values=[]
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            from .local_reuse import make_root_engine
            engine=make_root_engine(RootSecretEngine,branch.public,rules,strategy,max_work=max_work)
            from .fixed_actor_continuation import fixed_uniform_action_value
            invariant=fixed_uniform_action_value(branch.public,branch.public_law,actor.physical_law,
                engine,None,physical=physical_board(branch.public,actor.physical_law,branch.physical),past=branch.past)
            if invariant is not None:
                # Current scan choices were validated above against OWN known
                # history. In this fixed/no-report scope no future selector
                # reads the scan; its unit-mass kernel cannot change this value.
                return tuple((target,invariant) for target in next(iter(choices)))
            for target in next(iter(choices)):
                if getattr(engine,'structured_seer_observer',False):
                    from .seer_intervention import SeerObserver
                    observer=SeerObserver(player,tuple(acquisitions),day,target)
                else:
                    def observer(h,state,target=target):
                        return compatible(h) and scan_intervention_matches(h,state,player,day,target)
                value=engine.solve(branch.public,branch.public_law,branch.past,actor.physical_law,
                    observer,physical=physical_board(branch.public,actor.physical_law,branch.physical))
                values.append((target,value))
            return tuple(values)
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)


def root_guard_forecast(branch,player,guards,rules,strategy,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS,_actor=None):
    """Owner guard records condition P; public policy continues using Q."""
    from .guard_view_forecast import guard_forecast
    compatible=lambda h:bool(h.roles[3]&(1<<(player-1))) and all(g in h.guards for g in guards)
    actor=_actor if _actor is not None else root_actor_view(branch,compatible)
    if isinstance(actor,FuturePending):return actor
    from .exact import replace_worlds
    private=replace_worlds(branch.public,actor.belief.public_roles)
    return guard_forecast(branch.public,player,private,branch.public_law,branch.past,rules,strategy,
        guards=guards,private_state=actor.physical_law,engine_factory=RootSecretEngine,
        max_work=max_work,max_seconds=max_seconds)


def root_wolf_forecast(branch,players,attacks,rules,strategy,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS,_actor=None):
    """Aggregate unknown other roles and their secrets before each wolf action."""
    mask=sum(1<<(p-1) for p in players)
    actor=_actor if _actor is not None else root_actor_view(branch,lambda h:h.roles[0]==mask and all(a in h.attacks for a in attacks))
    if isinstance(actor,FuturePending):return actor
    reason=root_scope(branch,rules,strategy)
    if reason:return FuturePending(reason)
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            from .model_a_public import horizon_for_action
            from .local_reuse import make_root_engine
            engine=make_root_engine(RootSecretEngine,branch.public,rules,strategy,max_work=max_work)
            own=actor.physical_law;b=branch.public;state=branch.public_law;past=branch.past
            physical=physical_board(b,own,branch.physical)
            targets=legal_targets(physical,rules,strategy)
            values=tuple((t,engine.act(b,state,past,t,own,None,physical=physical)) for t in targets)
            dawn={t:horizon_for_action(engine,b,state,past,t,own) for t in targets}
            return values,dawn,actor.belief
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)


from functools import lru_cache


@lru_cache(maxsize=16)
def _guard_night_priors(history_key,rules,max_work,max_seconds):
    import json
    from .exact import initial_board
    game=json.loads(history_key)
    seed=initial_board(game['players'],game.get('wolves',1),game.get('mediums',0),
                       game.get('seers',0),game.get('hunters',0),experimental_cast=True)
    # Collect facts of saved nights even when today's strategy is outside the
    # new value scope. Every saved step keeps its own ORIGINAL policy.
    collecting={**game,'policy':{**game['policy'],'day':'random','night':'random'}}
    result=replay_root_secrets(collecting,seed,rules,Strategy(**collecting['policy']),
        max_work=max_work,max_seconds=max_seconds,_collect_guard_priors=True)
    if isinstance(result,FuturePending):raise Pending(result.reason)
    return tuple(sorted(result.items()))


def root_guard_night_priors(game,rules,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS):
    """Public-owned night laws for observation replay; no private data in cache."""
    from .public_prior import public_history_key
    try:return dict(_guard_night_priors(public_history_key(game),rules,max_work,max_seconds))
    except Pending as error:return FuturePending(error.reason)
