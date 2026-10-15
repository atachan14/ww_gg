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
from .calculation_budget import CalculationBudgetExceeded,calculation_budget,tick


class _PolicyRead(Exception):pass


def require_profile(result,*,dependent=False):
    if result.selected is not None:return result.selected
    if dependent and result.status=='budget_unfinished':
        raise CalculationBudgetExceeded('Complete profile continuation budget exceeded')
    raise Pending('root_guard_profile_'+result.status)


def renamed_profile_search(result,ids,order=None):
    """Transport a COMPLETE certificate using its full-source bijection."""
    from dataclasses import replace
    from .actor_information import WolfInformation
    from .night_knowledge import WolfAttack
    def info(i):
        mask=sum(1<<(ids[p]-1) for p in range(len(ids)) if i.initial_roster&(1<<p))
        return WolfInformation(mask,tuple(WolfAttack(a.night,ids[a.target-1]) for a in i.attacks))
    def rows(values):
        mapped={info(i):tuple(sorted((ids[t-1],q) for t,q in row)) for i,row in values}
        sequence=order if order is not None else sorted(mapped,key=lambda i:(i.initial_roster,i.attacks))
        if set(sequence)!=set(mapped):raise ValueError('Complete renamed information partition required')
        return tuple((i,mapped[i]) for i in sequence)
    if result.selected is None:raise ValueError('Only a complete unique certificate may be transported')
    c=result.selected
    return replace(result,certified=(ProfileCertificate(rows(c.profile),rows(c.scores)),))


class WolfProfileResolver:
    """Complete public-context memoization, including later-night proofs.

    Only a finished unique profile is reused as a policy. Incomplete search
    results remain diagnostics, not cached choices. Parent calculation deadlines
    are inherited by each nested certificate; the profile-work cap is shared.
    """
    def __init__(self,rules,strategy,*,max_profiles=4096,max_work=250000,max_seconds=20,canonical_certificates=True):
        if type(max_profiles)is not int or max_profiles<1:raise ValueError('Positive profile limit required')
        self.rules=rules;self.strategy=strategy;self.max_profiles=max_profiles
        self.max_work=max_work;self.max_seconds=max_seconds
        self.cache={};self.active=set();self.diagnostics={};self.profiles_evaluated=0
        self.dependencies=DependencyGraph()
        # Only pure physical/public branch construction is shared between
        # candidate profiles. Full Boards and joint ledgers remain in keys.
        self.branch_cache={};self.branch_stats={"calls":0,"hits":0}
        self.row_reuse_stats={"classes":0,"hits":0,"vector_hits":0}
        self.candidate_rule_cache={};self.acquisition_cache={}
        self.canonical_certificates=canonical_certificates
        self.certificate_cache={};self.certificate_cache_size=0
        self.certificate_cache_stats={'calls':0,'hits':0}
        self.acquisition_stats={"calls":0,"hits":0}

    def branch(self,key,compute):
        self.branch_stats['calls']+=1
        if key in self.branch_cache:
            self.branch_stats['hits']+=1
            return self.branch_cache[key]
        value=compute()  # Pending/errors never install partial branches.
        if len(self.branch_cache)<4096:self.branch_cache[key]=value
        return value

    def acquisition(self,key,compute):
        self.acquisition_stats['calls']+=1
        if key in self.acquisition_cache:
            self.acquisition_stats['hits']+=1
            return self.acquisition_cache[key]
        value=compute()
        # Acquired complete ledgers can be large; keep this independent of the
        # much larger pure-Board cache. Failed generations never enter it.
        if len(self.acquisition_cache)>=16:self.acquisition_cache.pop(next(iter(self.acquisition_cache)))
        self.acquisition_cache[key]=value
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
                    canonical=None
                    # Cache complete contexts within the input-size cap. The full source,
                    # every secret ledger/mass and all rules enter the key. Limits
                    # bound retained serialized input, not the mathematical domain.
                    if self.canonical_certificates and len(state.hypotheses)<=4000:
                        from .exact_renaming import canonical_key
                        self.certificate_cache_stats['calls']+=1
                        canonical=canonical_key(board,state,past,state,None,self.rules,self.strategy,
                                                return_mapping=True,serialization_cache={})
                        if canonical is not None and canonical[0] in self.certificate_cache:
                            ids=canonical[1];inverse=tuple(ids.index(p)+1 for p in range(1,len(ids)+1))
                            order=tuple(i for i,mass,group in wolf_information_groups(state))
                            result=renamed_profile_search(self.certificate_cache[canonical[0]],inverse,order)
                            self.certificate_cache_stats['hits']+=1
                            self.cache[key]=result;self.diagnostics[key]=result
                            return result
                    result=certify_wolf_profiles(board,state,past,self.rules,self.strategy,
                        max_profiles=self.max_profiles,max_work=self.max_work,
                        max_seconds=self.max_seconds,resolver=self)
                self.diagnostics[key]=result
                if result.selected is not None:
                    self.cache[key]=result
                    if (canonical is not None and canonical[0] not in self.certificate_cache and
                        len(self.certificate_cache)<128 and
                        self.certificate_cache_size+len(state.hypotheses)<=32000):
                        self.certificate_cache[canonical[0]]=renamed_profile_search(result,canonical[1])
                        self.certificate_cache_size+=len(state.hypotheses)
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
        # Per-engine memo retains complete profile identity. Cross-engine
        # renaming is performed only by the complete candidate-row compiler,
        # which maps the profile, source, private law and target together.
        return ('fixed-complete-profile',self.fixed_profile,self.rules,self.strategy,
                b,state,past,private,observer,target,physical)
    def acquire(self,b,state):
        compute=lambda:super(FixedPublicWolfProfile,self).acquire(b,state)
        if self.resolver is None:return compute()
        return self.resolver.acquisition((self.rules,self.strategy,b,state),compute)

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
    def act(self,b,state,past,target,private,observer,*,physical=None):
        owned=self.owned_night_action(b,state,past,target,private,observer,physical=physical)
        if owned is not None:return owned
        return InformationSetForecast.act(self,b,state,past,target,private,observer,physical=physical)
    def solve(self,*args,**kwargs):return InformationSetForecast.solve(self,*args,**kwargs)


def wolf_candidate_profile(profile,info,target,*,rules):
    """Apply one candidate rule to its proved full-public symmetry orbit."""
    return rules.candidate(profile,info,target)


def candidate_parameter_independence(board,strategy,candidate_rules,*,terminal):
    # The fixed profile is consumed only at the anchor kernel. If each
    # candidate overwrites every row, none of its parameters survives.
    if all(len(rows)==len(candidate_rules.actions) for rows in candidate_rules.replacements.values()):
        return 'candidate_rule_independent'
    if not terminal:return None
    if strategy.day=='random':return 'terminal_policy_independent'
    # Every next execution is terminal and public reports are inactive (proved
    # by the caller). If all full role worlds have the same best action set,
    # every positive Model-A mixture has exactly that same day policy.
    from .exact import winner_for
    policies=set()
    for world in board.worlds:
        living=world[0]&board.alive_mask
        scores=tuple((p,int(winner_for(len(board.alive)-1,
            living.bit_count()-bool(living&(1<<(p-1))))=='village')) for p in board.alive)
        best=max(v for p,v in scores)
        policies.add(tuple(p for p,v in scores if v==best))
    if len(policies)==1:return 'terminal_policy_independent'
    return None


def certify_wolf_profiles(board,state,past,rules,strategy,*,max_profiles=4096,
                          max_work=250000,max_seconds=20,resolver=None):
    if resolver is None:
        return WolfProfileResolver(rules,strategy,max_profiles=max_profiles,max_work=max_work,
                                   max_seconds=max_seconds).resolve(board,state,past)
    if board.phase!='night' or board.winner:raise ValueError('Continuing public night required')
    if state.public_roles!=tuple(sorted(board.worlds)):raise ValueError('Complete public prior required')
    groups=wolf_information_groups(state)
    from .candidate_policy import CandidateRules
    source=(board,state,past)
    if source not in resolver.candidate_rule_cache:
        resolver.candidate_rule_cache[source]=CandidateRules(board,state,past,rules,strategy)
    candidate_rules=resolver.candidate_rule_cache[source]
    legal=tuple((info,tuple(p for p in board.alive if strategy.include_self_bite or
                 not info.initial_roster&(1<<(p-1)))) for info,mass,group in groups)
    from .policy_choice import uniform_policy
    # A candidate applies the same rule to exactly renamed information/action
    # pairs. Private focal identity is not promoted to public information.
    row_values={};vector_values={};row_keys={};key_marginals={};owned_sources={}
    legal_actions=dict(legal)
    fixed_public_choices=(strategy.day=='random' and strategy.guard_position==('uniform',) and
        not any(board.claims[p-1]==role and strategy.disclosure_for(role)!='none'
                for p in board.alive for role in ('seer','medium')))
    roster_cut=fixed_public_choices and len(board.alive)==4
    def row_context(info,candidate):
        if not roster_cut:return board,state,candidate
        # Conditional-value decomposition only; never returned as a public
        # Board. All own-roster histories and complete acquisition ledgers stay.
        # The current candidate rows come from the ORIGINAL public rule map.
        # The only later night has three survivors, whose fixed public-day
        # continuation is independent of candidate-profile symmetry grouping.
        mask=info.initial_roster
        if mask not in owned_sources:
            from .actor_information import condition_actor_state
            from .exact import replace_worlds
            law=condition_actor_state(state,lambda h:h.roles[0]==mask)
            owned_sources[mask]=(replace_worlds(board,law.public_roles,wolf_count=None),law)
        own_board,law=owned_sources[mask]
        return own_board,law,tuple((i,p) for i,p in candidate if i.initial_roster==mask)
    # Exact terminal dependency boundary: after GJ, every execution ends the
    # game and there is no active public ability report. Public day choices
    # then depend on Q's supported full role worlds, not hidden-history mixing.
    # Compile support possibilities from EVERY source hypothesis; carry the
    # original histories/masses through the actual common evaluator unchanged.
    terminal=(len(board.alive)==3 and not any(board.claims[p-1]==role and
        strategy.disclosure_for(role)!='none' for p in board.alive for role in ('seer','medium')))
    if terminal:
        from dataclasses import replace
        terminal=FixedPublicWolfProfile(board,state,past,rules,strategy,()).terminal_day(
            replace(board,phase='day'),state)
    terminal_table=None;terminal_physics={};terminal_inputs={}
    if terminal:
        from .terminal_followup import terminal_payoff_table
        terminal_table=terminal_payoff_table(board,rules,strategy)
        terminal=terminal_table is not None
    supports={};owned_support={}
    if terminal:
        from .guard_model import guard_choices
        from .actor_information import WolfInformation
        for h in state.hypotheses:
            tick()
            actor=next((a for a in board.alive if h.roles[3]&(1<<(a-1))),None)
            if actor is None:continue
            owned=WolfInformation.from_hypothesis(h)
            mask=sum(1<<(t-1) for t,q in guard_choices(board,actor,rules,strategy.guard_position,guards=h.guards))
            rows=supports.setdefault(h.roles,{})
            rows[owned]=rows.get(owned,0)|mask
            owned_support[owned]=owned_support.get(owned,0)|mask
    terminal_classes=tuple(sorted({candidate_rules.classes[info,target]
        for info,actions in legal for target in actions
        if owned_support.get(info,0)&(1<<(target-1))})) if terminal else ()

    def evaluate_raw(profile,*,independence_only=False,requested=None):
        scores={};reads=0;spent=False;public_support={};vector_key=None
        if terminal and requested is None:
            masks={owned:sum(1<<(t-1) for t,q in policy) for owned,policy in profile}
            for candidate_class in terminal_classes:
                overrides=candidate_rules.replacement_masks[candidate_class]
                public_support[candidate_class]=tuple(roles for roles,owners in sorted(supports.items())
                    if any(overrides.get(owned,masks[owned])&allowed for owned,allowed in owners.items()))
            # This is exactly the sequence of already-proved terminal row keys.
            # Source, private groups and physical histories are fixed in this closure.
            vector_key=tuple(public_support.items())
            if vector_key in vector_values:
                tick();resolver.row_reuse_stats['vector_hits']+=1
                return vector_values[vector_key]
        for info,mass,group in groups:
            if requested is not None and info not in requested:continue
            row=[]
            for target in legal_actions[info]:
                candidate=None
                candidate_class=candidate_rules.classes[info,target]
                if len(candidate_rules.replacements[candidate_class])==len(groups):
                    # The full candidate kernel is its exact public orbit, so
                    # the proved source isomorphism maps the kernel as well.
                    key=('complete-candidate-orbit',candidate_class)
                elif terminal:
                    if not owned_support.get(info,0)&(1<<(target-1)):
                        key=(info,target,'physical-terminal')
                    else:
                        key=(info,target,'terminal-public-role-support',
                             public_support[candidate_rules.classes[info,target]])
                else:
                    candidate=wolf_candidate_profile(profile,info,target,rules=candidate_rules)
                    value_board,value_state,value_profile=row_context(info,candidate)
                    identity=(info,target,value_profile)
                    if identity not in row_keys:
                        exact=None
                        # Larger joint inputs retain complete identity; the
                        # conditional decomposition keeps all records too.
                        if len(value_state.hypotheses)<=128:
                            from .exact_renaming import canonical_key
                            exact=canonical_key(value_board,value_state,past,group,None,rules,strategy,target=target,
                                wolf_profiles=((value_board,value_state,past,value_profile),),marginal_cache=key_marginals)
                        row_keys[identity]=('complete-renamed-candidate',exact) if exact is not None else identity
                    key=row_keys[identity]
                if key not in row_values:
                    if not spent:resolver.spend_profile();spent=True
                    if candidate is None:candidate=wolf_candidate_profile(profile,info,target,rules=candidate_rules)
                    value_board,value_state,value_profile=row_context(info,candidate)
                    engine=FixedPublicWolfProfile(value_board,value_state,past,rules,strategy,value_profile,
                        resolver=resolver,stop_on_policy_read=independence_only,max_work=max_work)
                    node=Dependency('candidate-action',(board,state,past,info,target,candidate))
                    with engine.policy_dependencies.evaluating(node):
                        if terminal:
                            from .fixed_actor_continuation import physical_actor_outcomes
                            from .terminal_followup import terminal_followup_value
                            physical_key=(info,target)
                            if physical_key not in terminal_physics:
                                from .terminal_followup import terminal_physical_measures,terminal_physical_input
                                if info not in terminal_inputs:terminal_inputs[info]=terminal_physical_input(group)
                                measures=terminal_physical_measures(board,group,engine,target,
                                    physical_input=terminal_inputs[info])
                                terminal_physics[physical_key]=(physical_actor_outcomes(board,group,engine,target)
                                                               if measures is None else measures)
                            support=(public_support[candidate_class] if candidate_class in public_support else
                                     tuple(roles for roles,owners in sorted(supports.items())))
                            value,policy_reads=terminal_followup_value(board,support,
                                terminal_physics[physical_key],terminal_table,strategy)
                        else:
                            value=engine.act(value_board,value_state,past,target,group,None)
                            policy_reads=engine.policy_reads
                    row_values[key]=(value,policy_reads)
                    resolver.row_reuse_stats['classes']+=1
                else:
                    tick();resolver.row_reuse_stats['hits']+=1
                value,count=row_values[key];reads+=count;row.append((target,value))
            scores[info]=tuple(row)
        result=(scores,reads)
        if terminal and requested is None:vector_values[vector_key]=result
        return result
    from .policy_choice import uniform_policy
    probe=tuple((info,uniform_policy(actions)) for info,actions in legal)
    total=1
    for info,actions in legal:total*=(1<<len(actions))-1
    if not terminal:
        from .policy_certificates import certify_dependency_profiles
        dependencies={info:set().union(*(set(candidate_rules.actions)-
            set(candidate_rules.replacements[candidate_rules.classes[info,target]])
            for target in actions)) for info,actions in legal}
        # With fixed public day choices and no future public abilities, an
        # owned wolf law conditions on its initial roster. Per-role generated
        # normalization is independent of all other rosters' kernel rows;
        # their global Q normalization cancels under that observation.
        # The implemented observation quotient is bounded to four survivors;
        # later three-survivor candidate values are profile-group independent.
        # Larger sources retain all cross-roster dependencies unless the
        # original complete candidate rule itself overwrites those parameters.
        isolated=fixed_public_choices and len(board.alive)<=4
        if isolated:
            dependencies={info:{other for other in rows if other.initial_roster==info.initial_roster}
                          for info,rows in dependencies.items()}
        return certify_dependency_profiles(legal,
            lambda profile,requested:evaluate_raw(profile,requested=requested)[0],dependencies,
            maximize=False,max_profiles=max_profiles,max_work=max_work,max_seconds=max_seconds)
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
    independence=candidate_parameter_independence(board,strategy,candidate_rules,terminal=terminal)
    if probed is not None and (probed[1]==0 or independence is not None):
        # Complete common scores are now proved independent of the anchor
        # parameters: either no policy was read, the candidate overwrote all
        # rows, or every possible terminal public support has the same policy.
        # No profile is dropped; these scores cover the full original domain.
        chosen,rows=best_response_profile(legal,probed[0],maximize=False)
        return ProfileSearch('unique',total,1,(ProfileCertificate(chosen,rows),),
                             proof='policy_independent_scores' if probed[1]==0 else independence)
    def evaluate(profile):
        return probed[0] if profile==probe and probed is not None else evaluate_raw(profile)[0]
    if terminal and terminal_classes:
        from .policy_certificates import certify_support_profiles,uniform_options
        role_rows=tuple(sorted(supports.items()))
        def support_mask(owner,targets):
            return sum(1<<index for index,(roles,owners) in enumerate(role_rows)
                       if owners.get(owner,0)&targets)
        forced=tuple(0 for c in terminal_classes)
        for index,c in enumerate(terminal_classes):
            mask=0
            for owned,targets in candidate_rules.replacement_masks[c].items():
                mask|=support_mask(owned,targets)
            forced=(*forced[:index],mask,*forced[index+1:])
        contributions={}
        for info,actions in legal:
            entries=[]
            for policy in uniform_options(actions):
                mask=support_mask(info,sum(1<<(t-1) for t,q in policy))
                entries.append((policy,tuple(0 if info in candidate_rules.replacement_masks[c] else mask
                                             for c in terminal_classes)))
            contributions[info]=tuple(entries)
        result=certify_support_profiles(legal,evaluate,contributions,forced,maximize=False,
            max_profiles=max_profiles,max_work=max_work,max_seconds=max_seconds)
    else:
        result=certify_uniform_profiles(legal,evaluate,maximize=False,max_profiles=max_profiles,
            max_work=max_work,max_seconds=max_seconds,stop_on_undefined=True)
    return result
