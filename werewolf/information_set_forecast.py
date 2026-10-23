"""Model A: roster-informed wolf choices; compatibility-only public beliefs.

Physical branch mass and public decision beliefs are separate. Wolf policies
average unknown roles/acquisitions within a PUBLIC-prior roster group before
maximizing. Observer-only evidence never enters the policy cache or ranking.
"""
from .calculation_budget import DEFAULT_MAX_WORK, DEFAULT_MAX_SECONDS
from dataclasses import replace
from fractions import Fraction as F
from functools import lru_cache
from contextlib import nullcontext
from math import comb
from .exact import (action_outcomes, legal_targets, replace_worlds, report_actions,
                    random_report_outcomes, merge_report_outcomes, BoardOutcome, winner_for, has_future_medium)
from .seer_acquisition import Hypothesis, from_board, normalize
from .seer_future_uniform import TrueScanState, FuturePending, acquire_uniform
from .belief_projection import project_private
from .morning_publications import future_publications, public_report_branches
from .phase_updates import night_observation_outcomes
from .action_flow import action_flow, FlowOutcome, unchanged_death_outcomes
from .night_acquisition import acquire_laws
from .information_weights import observer_report_weights
from .morning_flow import report_flow, continuation_value
from .calculation_budget import calculation_budget, tick, CalculationBudgetExceeded
from .evaluation_branch import ActionInputs,ContinuationInputs,physical_board,require_public_observation
from .actor_information import WolfInformation,wolf_information_groups,condition_actor_state
from .policy_choice import optimal_targets,uniform_policy


class Pending(Exception):
    def __init__(self, reason): self.reason=reason


@lru_cache(None)
def exchangeable_value(n,w,phase,strategy):
    winner=winner_for(n,w)
    if winner:return F(winner=='village')
    if phase=='day':
        return F(w,n)*exchangeable_value(n-1,w-1,'night',strategy)+F(n-w,n)*exchangeable_value(n-1,w,'night',strategy)
    enemy=exchangeable_value(n-1,w,'day',strategy)
    if not strategy.include_self_bite:return enemy
    friend=exchangeable_value(n-1,w-1,'day',strategy)
    return min(friend,enemy) if strategy.night=='max' else F(w,n)*friend+F(n-w,n)*enemy


class InformationSetForecast:
    def __init__(self, rules, strategy, *, max_work=DEFAULT_MAX_WORK, trace=None, memoize_flows=True,
                 retire_uninformative_scans=True, exact_renaming=True, track_acquisition_provenance=False):
        self.rules=rules;self.strategy=strategy;self.max_work=max_work;self.trace=trace
        if track_acquisition_provenance:
            from .acquisition_provenance import AcquisitionLedger,UniformAcquisitionCache
            self.acquisition_provenance=AcquisitionLedger(self)
        else:self.acquisition_provenance=None
        self.board_sources={}
        self.board_action_options={}
        self.board_action_kernels={}
        self.board_key_hashes={}
        self.board_replay_stats={"requests":0,"hits":0}
        self.values={};self.scores={};self.policies={};self.acquired=UniformAcquisitionCache() if track_acquisition_provenance else {}
        self.symmetries={}
        self.reduced_descriptors={}
        self.action_values={}
        self.public_support_values={};self.public_support_stats={"calls":0,"hits":0}
        self.memoize_flows=memoize_flows
        self.retire_uninformative_scans=retire_uninformative_scans
        self.mornings={};self.publication_values={}
        self.exact_renaming=exact_renaming
        self.exact_keys={}
        self.expansions={"actions":0,"values":0}
        self.renaming_stats={"requests":0,"key_hits":0,"supported":0}
        self.day_bounds={}
        self.joint_descriptors={}
        self.joint_keys={}
        self.action_policy=InformationSetActionPolicy(self)

    def wolf_cells(self,state):return wolf_information_groups(state)
    def group_scope(self,groups):return nullcontext()
    def actor_scope(self,info):return nullcontext()
    def target_orbits(self,targets):return tuple((p,) for p in targets)
    def weighted_actor_targets(self,policy):return policy

    def scalar_descriptor(self,b,s):
        from .medium_value_key import public_descriptor
        return public_descriptor(b,s,self.rules,self.strategy)

    def value_law(self,state):
        # Uniform guards/repeat permission and the supported wolf policies do
        # not depend on these histories. Preserve records in flow payloads;
        # scalar memoization may marginalize them after role conditioning.
        if self.rules.allow_repeat_guard and self.strategy.night=='random' and any(h.guards or h.attacks for h in state.hypotheses):
            from .seer_acquisition import Hypothesis
            return replace(state,hypotheses=normalize(tuple(Hypothesis(h.roles,h.acquisitions,h.mass) for h in state.hypotheses)))
        return state

    def cached_flow(self,cache,key,compute,kind):
        if self.trace is not None:
            stats=self.trace.setdefault('flow_memo',{})
            stats[kind+'_calls']=stats.get(kind+'_calls',0)+1
        if self.memoize_flows and key in cache:
            tick()
            if self.trace is not None:stats[kind+'_hits']=stats.get(kind+'_hits',0)+1
            return cache[key]
        result=compute()  # Exceptions/Pending never install an incomplete value.
        if self.memoize_flows:cache[key]=result
        return result

    def public_support(self,key,compute):
        """Reuse completed full public laws, independently of scalar shortcuts."""
        self.public_support_stats['calls']+=1
        if key in self.public_support_values:
            self.public_support_stats['hits']+=1
            return self.public_support_values[key]
        value=compute()
        if len(self.public_support_values)>=16:self.public_support_values.pop(next(iter(self.public_support_values)))
        self.public_support_values[key]=value
        return value

    pending=Pending

    def exchangeable(self,b):
        from .guard_model import live_guard_mass
        if live_guard_mass(b):return False
        # Exact reduction: no future information, and all live locations are
        # exchangeable in the PUBLIC wolf marginal. Public max ties are uniform.
        if self.strategy.disclosure_for('medium')=='all' and has_future_medium(b):return False
        # This fast path has no acquisition/publication ledger. Even a known
        # fake can have an unspecified initial declaration; validate it in the
        # full flow before marginalizing its later role-independent noise.
        if self.strategy.disclosure_for('seer')=='all' and any(b.claims[p-1]=='seer' for p in b.alive):return False
        masses={}
        for mask,q in b.belief:
            live=mask&b.alive_mask;masses[live]=masses.get(live,F())+q
        counts=b.wolf_count_distribution;n=len(b.alive)
        return len(masses)==sum(comb(n,w) for w in counts) and all(q==counts[m.bit_count()]/comb(n,m.bit_count()) for m,q in masses.items())

    def checked(self, value):
        if isinstance(value,FuturePending):raise Pending(value.reason)
        return value

    def informative_seer(self,b):
        co=tuple(p for p in b.alive if b.claims[p-1]=='seer')
        if not co:return False
        # A single publicly exposed fake emits role-independent noise under
        # the selected uniform law. Do not invent a multi-fake joint law.
        return (not self.retire_uninformative_scans or len(co)>1 or
                any(b.role_probability(p,'seer') for p in co))

    def can_retire_scans(self,b,s,past):
        if self.informative_seer(b):return False
        co=tuple(p for p in b.alive if b.claims[p-1]=='seer')
        if co and s.initial_rule!='none' and not any(r.player==co[0] and r.acquired_day==1 for r in past):
            return False  # The initial fake law is still unspecified.
        return True

    def project(self,state,board):
        return project_private(state,board,marginalize_private=False)

    def acquire(self,b,state):
        key=(b,state)
        tracked_cache=False
        if self.acquisition_provenance is not None:
            from .acquisition_provenance import UniformAcquisitionCache
            tracked_cache=type(self.acquired)is UniformAcquisitionCache
        if tracked_cache:
            try:
                result,ticket=self.acquired._lookup(key)
            except KeyError:
                result=self.checked(acquire_uniform(state,b.alive,max_work=self.max_work,position=self.strategy.seer_position))
                ticket=None if self.acquisition_provenance is None else self.acquisition_provenance._record_uniform(b,state,result)
                self.acquired._store_generated(key,result,ticket)
            else:
                if self.acquisition_provenance is not None:self.acquisition_provenance._record_cache_equivalence(b,state,result,ticket)
            return result
        if key not in self.acquired:
            generated=self.checked(acquire_uniform(state,b.alive,max_work=self.max_work,
                                                    position=self.strategy.seer_position))
            self.acquired[key]=generated
            if self.acquisition_provenance is not None:
                self.acquisition_provenance._record_uniform(b,state,generated)
        return self.acquired[key]

    def canonical_payoff_key(self,*args,**kwargs):
        from .exact_renaming import canonical_key
        return canonical_key(*args,**kwargs)

    def full_renamed_key(self,b,s,past,private,observer,*,target=None,physical=None):
        if not self.exact_renaming or not self.memoize_flows or not b.initial_hunter_count:return None
        source=(self.rules,self.strategy,b,s,past,private,observer,target,physical)
        stats=self.renaming_stats;stats['requests']+=1
        if source in self.exact_keys:
            stats['key_hits']+=1;return self.exact_keys[source]
        from .exact_renaming import canonical_key
        key=self.canonical_payoff_key(b,s,past,private,observer,self.rules,self.strategy,target=target,physical=physical)
        if key is not None:stats['supported']+=1
        self.exact_keys[source]=key
        return key

    def full_target_equivalence(self,b,s,x,y,past,private):
        first=self.full_renamed_key(b,s,past,private,None,target=x)
        return first is not None and first==self.full_renamed_key(b,s,past,private,None,target=y)

    def actor_equivalent_targets(self,b,s,x,y,past,private):
        if b.initial_hunter_count:return self.full_target_equivalence(b,s,x,y,past,private)
        return self.equivalent_targets(b,s,x,y,past)

    def equivalent_targets(self,b,s,x,y,past=()):
        if b.initial_hunter_count:return self.full_target_equivalence(b,s,x,y,past,s)

        # Exact permutation test on the PUBLIC joint law, including own scan
        # histories. Both targets are currently alive, hence shared all past
        # rosters. A published scan on either target breaks this shortcut.
        if b.initial_hunter_count:return False
        if b.initial_seer_count and not any(b.claims[p-1]=='seer' for p in b.alive):return False
        if b.claims[x-1]!='latent' or b.claims[y-1]!='latent':return False
        if any(r.target in (x,y) for r in past):return False
        key=(b,s,past)
        if key not in self.symmetries:
            medium=sum(1<<(p-1) for p in b.alive if b.claims[p-1]=='medium')
            seer=sum(1<<(p-1) for p in b.alive if b.claims[p-1]=='seer')
            masses={}
            for h in s.hypotheses:
                records=tuple(a for a in h.acquisitions if seer&(1<<(a.player-1)))
                k=(h.roles[0],h.roles[1]&medium,h.roles[2]&seer,records)
                masses[k]=masses.get(k,F())+h.mass
            self.symmetries[key]=masses
        masses=self.symmetries[key];a=1<<(x-1);c=1<<(y-1)
        for (w,m,t,records),q in masses.items():
            swapped=w^(a|c) if bool(w&a)!=bool(w&c) else w
            scans=tuple(replace(r,target=y if r.target==x else x if r.target==y else r.target) for r in records)
            if masses.get((swapped,m,t,scans),F())!=q:return False
        return True

    def physical_children(self,b,target):
        return action_outcomes(b,target,self.rules,self.strategy)

    def public_children(self,b,target,guard_state=None):
        if b.phase=='day':return action_outcomes(b,target,self.rules,self.strategy)
        try:
            return night_observation_outcomes(b,target,self.rules,self.strategy,guard_state=guard_state)
        except ValueError:
            raise Pending('information_set_public_corpse_inconsistent')

    def record_group_publication(self,b,s,past,child,law,history,kind):
        """Optional constructed-group witness; never changes a branch or policy."""
        pass

    def publications(self,b,s,past):
        # Public law only: never key or generate this cache with viewer evidence.
        from .board_future import record_publications
        def generate():
            rows=self.generate_publications(b,s,past)
            if self.acquisition_provenance is not None:self.acquisition_provenance._record_publications(b,s,past,rows)
            return rows
        branches=self.cached_flow(self.publication_values,(b,s,past),generate,'publication')
        for q,child,law,history in branches:
            self.record_group_publication(b,s,past,child,law,history,'seer')
        return record_publications(self,b,s,past,branches,provider='publications')

    def generate_publications(self,b,s,past):
        if (self.strategy.disclosure_for('seer')=='none' or
                self.retire_uninformative_scans and self.can_retire_scans(b,s,past)):
            return ((F(1),b,s,past),)
        branches=self.checked(future_publications(s,past,b.alive,b.claims,
                                                  fake_policy=self.strategy.fake_seer_policy))
        return public_report_branches(b,past,branches)

    def scalar(self,b,s,past):return self.solve(b,s,past,s,None)

    def continuation_context(self,b,s,past,private,observer):
        if (self.retire_uninformative_scans and observer is None and b.initial_seer_count and not b.initial_hunter_count and
                self.can_retire_scans(b,s,past)):
            from .evaluation_projection import project_retired_seers
            b,s,private=project_retired_seers(b,s,private)
            return b,s,(),private,observer
        return b,s,past,private,observer

    def renamed_value_key(self,b,s,past,private,target=None):
        from .joint_value_key import public_variants,value_key
        if (not b.initial_seer_count or b.initial_hunter_count or
                b.claims.count('latent')>4 or
                sum(b.claims[p-1]=='seer' for p in b.alive)!=1):return None
        source=(b,s,past)
        key=(*source,private,target)
        if key in self.joint_keys:return self.joint_keys[key]
        if source not in self.joint_descriptors:self.joint_descriptors[source]=public_variants(b,s,past)
        value=value_key(self.joint_descriptors[source],private,target,public_same=private==s)
        self.joint_keys[key]=value
        return value

    def morning(self,b,s,past):
        from .board_future import record_publications
        def generate():
            ledger=self.acquisition_provenance
            if ledger is not None:ledger._begin_morning(b,s,past)
            try:rows=self.generate_morning(b,s,past)
            except BaseException:
                if ledger is not None:ledger._abort_morning(b,s,past)
                raise
            if ledger is not None:ledger._record_morning(b,s,past,rows)
            return rows
        branches=self.cached_flow(self.mornings,(b,s,past),generate,'morning')
        return record_publications(self,b,s,past,branches)

    def record_report_component(self,b,s,past,outcome,state,rows):
        if self.acquisition_provenance is not None:self.acquisition_provenance._record_component(b,s,past,outcome,state,rows)

    def record_report_choices(self,b,s,past,scored,chosen):
        """Optional exact-choice audit; no observation or selection changes."""
        pass

    def generate_morning(self,b,s,past):
        actions=report_actions(b) if self.strategy.disclosure_for('medium')=='all' else ()
        if not actions:return self.publications(b,s,past)
        outcomes=self.report_outcomes(b,s,past,actions)
        return tuple(report_flow(outcomes,s,past,self,source_board=b))

    def report_outcomes(self,b,s,past,actions,evaluate=None):
        # One configured instruction choice, shared by scalar and full history.
        if self.strategy.fake_reports=='random':outcomes=random_report_outcomes(b)
        else:
            scored=[]
            for action in actions:
                value=(evaluate(action.outcomes) if evaluate is not None else
                       continuation_value(report_flow(action.outcomes,s,past,self,source_board=b,fake_colors=action.fake_colors),self.scalar))
                scored.append((action,value))
            tied=optimal_targets(scored,maximize=False)
            chosen=uniform_policy(tied)
            self.record_report_choices(b,s,past,tuple(scored),chosen)
            outcomes=merge_report_outcomes(BoardOutcome(o.probability*q,o.board)
                                           for action,q in chosen for o in action.outcomes)
        return outcomes

    def push(self,source,private,branches):
        result=observer_report_weights(source,private,branches,
            incomplete=lambda:Pending('information_set_report_likelihood_incomplete'))
        if self.acquisition_provenance is not None:self.acquisition_provenance._record_push(source,private,branches,result)
        return result

    def report_children(self,payload):
        """Existing morning kernels, actual masses and ordinary evidence.

        Optional provenance never changes the public or private distribution.
        Q-only counterfactual rows remain in morning(), not normalized as P.
        """
        child,st,past,own,observer=self.continuation_context(*payload)
        rows=self.morning(child,st,past)
        if rows==((F(1),child,st,past),):
            if all(a is b for a,b in zip((child,st,past,own,observer),tuple(payload))):result=payload
            else:result=ContinuationInputs(child,st,past,own,observer,physical_board(child,own,payload.physical))
            return ((F(1),F(1),result),)
        weighted=self.push(st,own,rows)
        from .board_future import reconstruct_publication,publication_key
        counts={}
        for mass,b,q,p,private in weighted:
            key=publication_key(b,p);counts[key]=counts.get(key,0)+1
        result=[]
        for mass,b,q,p,private in weighted:
            public=[r[0] for r in rows if r[1] is b and r[2] is q and r[3] is p]
            rebuilt=reconstruct_publication(self,payload,b,q,p,private,physical_board(b,private,payload.physical),
                replay_unique=counts[publication_key(b,p)]==1)
            result.append((public[0] if len(public)==1 else None,mass,rebuilt))
        return tuple(result)

    def act(self,b,s,past,target,private,observer,*,physical=None):
        if type(target)is not int or target not in b.alive:
            raise Pending('information_set_internal_illegal_action')
        b,s,past,private,observer=self.continuation_context(b,s,past,private,observer)
        physical=physical_board(b,private,physical)
        if self.memoize_flows:
            # Public rankings call this with their own public/actor law. Viewer
            # payoffs include BOTH the private law and observer identity.
            key=('joint-action',b,s,past,target,self.value_law(private),observer)
            key=self.full_renamed_key(b,s,past,private,observer,target=target,physical=physical) or key
            return self.cached_flow(self.action_values,key,
                                    lambda:self.uncached_act(b,s,past,target,private,observer,physical=physical),'action')
        return self.uncached_act(b,s,past,target,private,observer,physical=physical)

    def uncached_act(self,b,s,past,target,private,observer,*,physical=None):
        action_key=None
        if observer is None:
            if self.memoize_flows:
                action_key=self.renamed_value_key(b,s,past,private,target)
                if action_key is not None and action_key in self.action_values:
                    tick();return self.action_values[action_key]
            from .medium_value_key import public_descriptor,private_action_key
            source=(b,s)
            if source not in self.reduced_descriptors:
                self.reduced_descriptors[source]=self.scalar_descriptor(b,s)
            if action_key is None:action_key=private_action_key(self.reduced_descriptors[source],private,target)
            if action_key is not None and action_key in self.action_values:
                tick();return self.action_values[action_key]
        tick(len(s.hypotheses)+len(private.hypotheses))
        private_board=physical_board(b,private,physical)
        if target not in legal_targets(private_board,self.rules,self.strategy):
            raise Pending('information_set_internal_illegal_action')
        self.expansions["actions"]+=1
        payload=ActionInputs(s,past,private,observer,private_board)
        if self.acquisition_provenance is not None:
            receipt=self.acquisition_provenance.receipt_for_frame(b,payload)
            if receipt is not None:payload=replace(payload,provenance=receipt)
        value=action_flow(b,payload,target,self.action_policy)
        if action_key is not None:self.action_values[action_key]=value
        return value

    def personal_view(self,payload,information):
        from .actor_information import condition_personal,WolfInformation
        from .board_future import reconstruct_information
        mass,own=condition_personal(payload.private,information)
        observer=payload.observer if type(information)is WolfInformation else information
        child=ContinuationInputs(payload.public,payload.public_state,payload.past,own,observer,
            physical_board(payload.public,own,payload.physical))
        if self.acquisition_provenance is not None:self.acquisition_provenance._record_information_output(payload,child,information,mass)
        return mass,reconstruct_information(self,payload,child,information,mass)

    def wolf_choices(self,payload):
        """Actual P partition masses; policies computed only from public Q."""
        from .board_future import reconstruct_information
        if payload.public.phase!='night':raise ValueError('Wolf choice requires night')
        rows=wolf_information_groups(payload.private)
        ledger=self.acquisition_provenance
        if ledger is not None:ledger.stats['wolf_partition_hypothesis_visits']+=len(payload.private.hypotheses)
        result=[]
        for info,mass,group in rows:
            child=ContinuationInputs(payload.public,payload.public_state,payload.past,group,payload.observer,
                physical_board(payload.public,group,payload.physical))
            if ledger is not None:
                ledger._record_information_output(payload,child,info,mass)
                # Partition visits are counted once above, not once per row.
                ledger.stats['information_semantic_hypothesis_visits']-=len(payload.private.hypotheses)
            child=reconstruct_information(self,payload,child,info,mass)
            policy=self.wolf_policy(payload.public,payload.public_state,payload.past,info.initial_roster,info.attacks)
            for target,q in policy:
                receipt=None if ledger is None else ledger._record_choice(child,info,mass,target,q,policy)
                result.append((mass*q,child,target,receipt))
        return tuple(result)

    def wolf_policy(self,b,s,past,mask,history=()):
        if s.public_roles!=tuple(sorted(b.worlds)):
            raise ValueError('Wolf policy requires the public role prior')
        info=WolfInformation(mask,history)
        key=(b,s,past,info)
        if key in self.policies:return self.policies[key]
        # This conditional law starts from the PUBLIC joint prior, never the viewer.
        try:
            if self.acquisition_provenance is None:group=info.condition_public(s)
            else:
                from .actor_information import condition_personal
                information_mass,group=condition_personal(s,info)
        except ValueError:raise Pending('information_set_roster_missing')
        targets=tuple(p for p in b.alive if self.strategy.include_self_bite or not mask&(1<<(p-1)))
        if self.strategy.night=='random':scores=();chosen=targets
        else:
            if self.exchangeable(b):
                w=(mask&b.alive_mask).bit_count();n=len(b.alive)
                scores=tuple((p,exchangeable_value(n-1,w-int(bool(mask&(1<<(p-1)))),'day',self.strategy)) for p in targets)
            else:
                computed=[];representatives=[]
                for p in targets:
                    prior=next((v for t,v in representatives
                                if bool(mask&(1<<(p-1)))==bool(mask&(1<<(t-1))) and self.actor_equivalent_targets(b,s,p,t,past,group)),None)
                    value=self.act(b,s,past,p,group,None) if prior is None else prior
                    if prior is None:representatives.append((p,value))
                    computed.append((p,value))
                scores=tuple(computed)
            chosen=optimal_targets(scores,maximize=False)
        if not chosen:raise Pending('information_set_no_legal_bite')
        result=uniform_policy(chosen);self.policies[key]=result
        if self.acquisition_provenance is not None and self.strategy.night=='random':
            self.acquisition_provenance._record_policy(b,s,past,info,information_mass,result)
        if self.trace is not None:
            self.trace.setdefault('wolf_policies',[]).append({'history':b.history,'mask':mask,'scores':scores,'policy':result})
        return result

    def day_scores(self,b,s,past):
        key=(b,s,past)
        if key not in self.scores:
            self.scores[key]=tuple(self.score_day_targets(b,s,past))
        graph=getattr(self,'evaluation_graph',None)
        if graph is not None:graph.record_day_scores(b,s,past,self.scores[key])
        return self.scores[key]

    def score_day_targets(self,b,s,past):
        representatives=[]
        for p in b.alive:
            prior=next((v for t,v in representatives if self.equivalent_targets(b,s,p,t,past)),None)
            value=self.act(b,s,past,p,s,None) if prior is None else prior
            if prior is None:representatives.append((p,value))
            yield p,value

    def public_day_max(self,b,s,past):
        key=(b,s,past)
        if key not in self.day_bounds:
            if key in self.scores:self.day_bounds[key]=max(v for _,v in self.scores[key])
            else:
                computed=[]
                for p,value in self.score_day_targets(b,s,past):
                    computed.append((p,value))
                    if value==1:
                        # Only the scalar bound is complete. Do not cache a
                        # partial score vector or choose one of the max ties.
                        self.day_bounds[key]=F(1)
                        break
                else:
                    self.scores[key]=tuple(computed)
                    self.day_bounds[key]=max(v for _,v in computed)
        return self.day_bounds[key]

    def solve(self,b,s,past,private,observer,*,physical=None):
        if b.winner is not None:return F(b.winner=='village')
        from .guard_model import scope_reason
        from .guard_history_prior import public_history_ready,guard_history_ready
        ready=public_history_ready(b,s) if self.rules.allow_repeat_guard else guard_history_ready(b,s)
        reason=scope_reason(b,self.rules,self.strategy,ready,joint_max=getattr(self,'joint_guard_max',False))
        if reason:raise Pending(reason)
        b,s,past,private,observer=self.continuation_context(b,s,past,private,observer)
        physical=physical_board(b,private,physical)
        key=(b,s,past,self.value_law(private),observer)
        full=self.full_renamed_key(b,s,past,private,observer,physical=physical)
        if full is not None:key=full
        if observer is None and full is None:
            from .medium_value_key import public_descriptor,private_value_key
            source=(b,s)
            if source not in self.reduced_descriptors:
                self.reduced_descriptors[source]=self.scalar_descriptor(b,s)
            reduced=self.renamed_value_key(b,s,past,private) if self.memoize_flows else None
            if reduced is None:reduced=private_value_key(self.reduced_descriptors[source],private)
            if reduced is not None:key=reduced
        if key in self.values:
            value=self.values[key];graph=getattr(self,'evaluation_graph',None)
            if graph is not None:graph.record_day_value(ContinuationInputs(b,s,past,private,observer,physical),value,'cached-random-day-value')
            return value
        from .win_certificate import certify
        if certify(b,s,private,self.strategy,self.rules,observer) is not None:
            self.cutoff_hits=getattr(self,'cutoff_hits',0)+1
            self.values[key]=F(1);return F(1)
        self.expansions["values"]+=1
        tick(len(private.hypotheses))
        if b.winner is not None:return F(b.winner=='village')
        if self.exchangeable(b):
            value=sum((h.mass*exchangeable_value(len(b.alive),(h.roles[0]&b.alive_mask).bit_count(),b.phase,self.strategy)
                       for h in private.hypotheses),F())
            self.values[key]=value
            graph=getattr(self,'evaluation_graph',None)
            if graph is not None:
                from .evaluation_branch import ContinuationInputs as GraphInputs
                graph.record_counts(GraphInputs(b,s,past,private,observer,physical),value)
                graph.record_day_value(GraphInputs(b,s,past,private,observer,physical),value,'exchangeable-count-recurrence')
            return value
        if b.phase=='day':
            if (not b.initial_hunter_count and self.strategy.day=='max' and observer is None and self.memoize_flows and
                    self.public_day_max(b,s,past)==1 and
                    {(h.roles,h.acquisitions) for h in private.hypotheses}<=
                    {(h.roles,h.acquisitions) for h in s.hypotheses}):
                # A public expected probability of one implies one in every
                # supported world. Any supported private restriction also has
                # value one, independently of which equally optimal action wins.
                self.values[key]=F(1);return F(1)
            if self.strategy.day=='random':targets=b.alive
            else:
                targets=optimal_targets(self.day_scores(b,s,past),maximize=True)
            value=sum((len(g)*self.act(b,s,past,g[0],private,observer,physical=physical) for g in self.target_orbits(targets)),F())/len(targets)
        else:
            value=F()
            ledger=self.acquisition_provenance
            frame=ContinuationInputs(b,s,past,private,observer,physical)
            receipt=None if ledger is None else ledger.receipt_for_frame(b,frame)
            if receipt is not None and self.strategy.night=='random':
                ledger.stats['uniform_wolf_solve_uses']+=1
                frame=replace(frame,provenance=receipt,board_data=ledger.request_for(receipt))
                value=sum((mass*self.act(*child[:3],target,child.private,child.observer,physical=child.physical)
                    for mass,child,target,proof in self.wolf_choices(frame)),F())
            else:
                shared=getattr(self,'joint_night_value',lambda frame:None)(frame)
                if shared is not None:value=shared
                else:
                    for info,mass,group in self.wolf_cells(private):
                        group_board=physical_board(b,group,physical)
                        with self.actor_scope(info):
                            policy=self.wolf_policy(b,s,past,info.initial_roster,info.attacks)
                            value+=mass*sum((q*self.act(b,s,past,p,group,observer,physical=group_board)
                                            for p,q in self.weighted_actor_targets(policy)),F())
        self.values[key]=value
        graph=getattr(self,'evaluation_graph',None)
        if graph is not None:graph.record_day_value(ContinuationInputs(b,s,past,private,observer,physical),value)
        return value


    def evaluate(self,b,s,past,*,observer=None,mask=None,private_board=None,private_attacks=()):
        if s.public_roles!=tuple(sorted(b.worlds)):
            raise ValueError('Public acquisition prior must match public Board')
        from .guard_history_prior import matches
        knows_attacks=mask is not None or bool(private_attacks)
        compatible=lambda h:(not knows_attacks or matches(h.attacks,private_attacks)) and (observer(h,s) if observer is not None else h.roles[0]==mask) and (private_board is None or h.roles in {w[:-1] for w in private_board.worlds})
        if not any(compatible(h) for h in s.hypotheses):raise ValueError('Inconsistent observer')
        private=condition_actor_state(s,compatible,attacks=private_attacks)
        if observer is not None:return self.solve(b,s,past,private,observer)
        targets=tuple(p for p in b.alive if self.strategy.include_self_bite or not mask&(1<<(p-1)))
        return tuple((p,self.act(b,s,past,p,private,None)) for p in targets)


class InformationSetActionPolicy:
    """Public compatibility updates, separate physical weights and observer law."""
    terminal_preflight_safe = False

    def __init__(self,engine):self.engine=engine

    def action_recorder(self,board,payload):
        graph=getattr(self.engine,'evaluation_graph',None)
        if graph is None or not (graph.recorded_day_scope(board,payload) or graph.personal_flow_scope(board,payload) or graph.personal_max_scope(board,payload) or graph.wolf_observer_scope(board,payload)):return None
        return lambda target,acquired,outcomes,value:graph.record_action(board,payload,target,acquired,outcomes,value)

    def morning_recorder(self,payload):
        graph=getattr(self.engine,'evaluation_graph',None)
        if graph is None or not (graph.personal_flow_scope(payload.public,payload) or graph.personal_max_scope(payload.public,payload) or graph.wolf_observer_scope(payload.public,payload)):return None
        return lambda branches,value:graph.record_morning(payload,branches,value)

    def acquire(self,b,payload):
        s,past,private,observer,physical=payload;e=self.engine
        laws=acquire_laws(b,s,lambda source,alive:e.acquire(b,source),private=private,observer=observer,
                          inconsistent=lambda:Pending('seer_view_scan_outside_public_support'),
                          record_observer=(None if getattr(e,'acquisition_provenance',None) is None else
                              lambda before,generated,after,obs,mass:e.acquisition_provenance._record_observed(b,before,generated,after,obs,mass)))
        result=ActionInputs(laws.public,past,laws.private,observer,physical_board(b,laws.private,physical))
        ledger=getattr(e,'acquisition_provenance',None)
        if ledger is not None:
            receipt=ledger._bind(b,payload,result)
            if receipt is not None:result=replace(result,provenance=receipt)
        return result

    def night_outcomes(self,frame,prepared):
        from .guard_model import guarded_outcomes
        return guarded_outcomes(frame,unchanged_death_outcomes(frame,self.outcomes,prepared),self.engine)

    def outcomes(self,b,payload,target):
        s,past,private,observer,physical=payload;e=self.engine
        public_rows=e.public_children(b,target,s)
        public={o.board.winner:o.board for o in public_rows}
        result=tuple(FlowOutcome(o.probability,o.board,public.get(o.board.winner))
                     for o in e.physical_children(physical,target))
        ledger=getattr(e,'acquisition_provenance',None)
        if ledger is not None:ledger._record_deaths(b,payload,target,public_rows,result)
        return result

    def project(self,b,payload,outcome,target):
        from .board_future import reconstruct_child
        return reconstruct_child(self.engine,b,payload,outcome,target,
            lambda:self._project_roles(b,payload,outcome,target))

    def _project_roles(self,b,payload,outcome,target):
        from .board_roles import project_generated
        return project_generated(self.engine,b,payload,outcome,target)

    def morning_value(self,payload):
        child,st,past,own,observer=payload;e=self.engine
        recorder=getattr(self,'morning_recorder',lambda payload:None)(payload)
        ledger=getattr(e,'acquisition_provenance',None)
        if ledger is not None and ledger._reports_supported() and ledger.groups_for(payload.provenance,child,payload) is not None:
            return sum((mass*e.solve(*source,physical=source.physical) for q,mass,source in e.report_children(payload)),F())
        child,st,past,own,observer=e.continuation_context(child,st,past,own,observer)
        published=e.morning(child,st,past)
        if published==((F(1),child,st,past),):
            # No observation occurred. Keep the physical/observer measure;
            # a report likelihood ratio would spuriously intersect it with Q.
            physical=physical_board(child,own,payload.physical)
            value=e.solve(child,st,past,own,observer,physical=physical)
            if recorder is not None:
                source=ContinuationInputs(child,st,past,own,observer,physical)
                recorder(((F(1),source,value),),value)
            return value
        branches=e.push(st,own,published)
        from .board_future import reconstruct_publication,publication_key
        observations={}
        for q,c,ns,p,priv in branches:
            key=publication_key(c,p);observations[key]=observations.get(key,0)+1
        recorded=[] if recorder is not None else None
        def evaluate(c,ns,p,priv):
            rebuilt=reconstruct_publication(e,payload,c,ns,p,priv,
                                            physical_board(c,priv,payload.physical),
                                            replay_unique=observations[publication_key(c,p)]==1)
            value=e.solve(*rebuilt,physical=rebuilt.physical)
            if recorded is not None:recorded.append((rebuilt,value))
            return value
        value=continuation_value(branches,evaluate)
        if recorder is not None:recorder(tuple((branch[0],source,result) for branch,(source,result) in zip(branches,recorded)),value)
        return value

    def day_value(self,payload):return self.engine.solve(*payload,physical=payload.physical)


def information_forecast(b,s,past,rules,strategy,*,observer=None,mask=None,private_board=None,private_attacks=(),max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS,trace=None):
    if s.public_roles!=tuple(sorted(b.worlds)):
        raise ValueError('Public acquisition prior must match public Board')
    from .guard_history_prior import seed_history
    try:s=seed_history(b,s) if strategy.night=='max' and b.initial_hunter_count else s
    except ValueError:return FuturePending('guard_public_history_zero_support')
    required={a.night for h in s.hypotheses for a in h.attacks}
    if mask is not None and not required<={a.night for a in private_attacks}:return FuturePending('wolf_guard_attack_history_missing')
    if observer is None:
        from .evaluation_projection import project_evaluation
        before=len(s.hypotheses);b,s=project_evaluation(b,s,strategy)
        if trace is not None:trace['evaluation_projection']=(before,len(s.hypotheses))
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            from .local_reuse import make_view_engine
            engine=make_view_engine(InformationSetForecast,b,rules,strategy,max_work=max_work,trace=trace)
            return engine.evaluate(b,s,past,observer=observer,mask=mask,private_board=private_board,private_attacks=private_attacks)
    except CalculationBudgetExceeded:return FuturePending('information_set_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)
