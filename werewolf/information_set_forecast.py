"""Model A: roster-informed wolf choices; compatibility-only public beliefs.

Physical branch mass and public decision beliefs are separate. Wolf policies
average unknown roles/acquisitions within a PUBLIC-prior roster group before
maximizing. Observer-only evidence never enters the policy cache or ranking.
"""
from dataclasses import replace
from fractions import Fraction as F
from functools import lru_cache
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
    def __init__(self, rules, strategy, *, max_work=250000, trace=None, memoize_flows=True,
                 retire_uninformative_scans=True, exact_renaming=True):
        self.rules=rules;self.strategy=strategy;self.max_work=max_work;self.trace=trace
        self.board_sources={}
        self.board_action_options={}
        self.board_action_kernels={}
        self.board_key_hashes={}
        self.board_replay_stats={"requests":0,"hits":0}
        self.values={};self.scores={};self.policies={};self.acquired={}
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
        if key not in self.acquired:
            self.acquired[key]=self.checked(acquire_uniform(state,b.alive,max_work=self.max_work,
                                                          position=self.strategy.seer_position))
        return self.acquired[key]

    def full_renamed_key(self,b,s,past,private,observer,*,target=None,physical=None):
        if not self.exact_renaming or not self.memoize_flows or not b.initial_hunter_count:return None
        source=(self.rules,self.strategy,b,s,past,private,observer,target,physical)
        stats=self.renaming_stats;stats['requests']+=1
        if source in self.exact_keys:
            stats['key_hits']+=1;return self.exact_keys[source]
        from .exact_renaming import canonical_key
        key=canonical_key(b,s,past,private,observer,self.rules,self.strategy,target=target,physical=physical)
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

    def publications(self,b,s,past):
        # Public law only: never key or generate this cache with viewer evidence.
        from .board_future import record_publications
        branches=self.cached_flow(self.publication_values,(b,s,past),
                                  lambda:self.generate_publications(b,s,past),'publication')
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
        branches=self.cached_flow(self.mornings,(b,s,past),
                                  lambda:self.generate_morning(b,s,past),'morning')
        return record_publications(self,b,s,past,branches)

    def generate_morning(self,b,s,past):
        actions=report_actions(b) if self.strategy.disclosure_for('medium')=='all' else ()
        if not actions:return self.publications(b,s,past)
        if self.strategy.fake_reports=='random':outcomes=random_report_outcomes(b)
        else:
            scored=[]
            for action in actions:
                value=continuation_value(report_flow(action.outcomes,s,past,self,source_board=b,fake_colors=action.fake_colors),self.scalar)
                scored.append((action,value))
            tied=optimal_targets(scored,maximize=False)
            outcomes=merge_report_outcomes(BoardOutcome(o.probability*q,o.board)
                                           for action,q in uniform_policy(tied) for o in action.outcomes)
        return tuple(report_flow(outcomes,s,past,self,source_board=b))

    def push(self,source,private,branches):
        return observer_report_weights(source,private,branches,
            incomplete=lambda:Pending('information_set_report_likelihood_incomplete'))

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
                self.reduced_descriptors[source]=public_descriptor(b,s,self.rules,self.strategy)
            if action_key is None:action_key=private_action_key(self.reduced_descriptors[source],private,target)
            if action_key is not None and action_key in self.action_values:
                tick();return self.action_values[action_key]
        tick(len(s.hypotheses)+len(private.hypotheses))
        private_board=physical_board(b,private,physical)
        if target not in legal_targets(private_board,self.rules,self.strategy):
            raise Pending('information_set_internal_illegal_action')
        self.expansions["actions"]+=1
        value=action_flow(b,ActionInputs(s,past,private,observer,private_board),target,self.action_policy)
        if action_key is not None:self.action_values[action_key]=value
        return value

    def wolf_policy(self,b,s,past,mask,history=()):
        if s.public_roles!=tuple(sorted(b.worlds)):
            raise ValueError('Wolf policy requires the public role prior')
        info=WolfInformation(mask,history)
        key=(b,s,past,info)
        if key in self.policies:return self.policies[key]
        # This conditional law starts from the PUBLIC joint prior, never the viewer.
        try:group=info.condition_public(s)
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
        if self.trace is not None:
            self.trace.setdefault('wolf_policies',[]).append({'history':b.history,'mask':mask,'scores':scores,'policy':result})
        return result

    def day_scores(self,b,s,past):
        key=(b,s,past)
        if key not in self.scores:
            self.scores[key]=tuple(self.score_day_targets(b,s,past))
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
                self.reduced_descriptors[source]=public_descriptor(b,s,self.rules,self.strategy)
            reduced=self.renamed_value_key(b,s,past,private) if self.memoize_flows else None
            if reduced is None:reduced=private_value_key(self.reduced_descriptors[source],private)
            if reduced is not None:key=reduced
        if key in self.values:return self.values[key]
        self.expansions["values"]+=1
        tick(len(private.hypotheses))
        if b.winner is not None:return F(b.winner=='village')
        if self.exchangeable(b):
            value=sum((h.mass*exchangeable_value(len(b.alive),(h.roles[0]&b.alive_mask).bit_count(),b.phase,self.strategy)
                       for h in private.hypotheses),F())
            self.values[key]=value;return value
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
            value=sum((self.act(b,s,past,p,private,observer,physical=physical) for p in targets),F())/len(targets)
        else:
            value=F()
            for info,mass,group in wolf_information_groups(private):
                group_board=physical_board(b,group,physical)
                value+=mass*sum((q*self.act(b,s,past,p,group,observer,physical=group_board)
                                for p,q in self.wolf_policy(b,s,past,info.initial_roster,info.attacks)),F())
        self.values[key]=value
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

    def acquire(self,b,payload):
        s,past,private,observer,physical=payload;e=self.engine
        laws=acquire_laws(b,s,lambda source,alive:e.acquire(b,source),private=private,observer=observer,
                          inconsistent=lambda:Pending('seer_view_scan_outside_public_support'))
        return ActionInputs(laws.public,past,laws.private,observer,physical_board(b,laws.private,physical))

    def night_outcomes(self,frame,prepared):
        from .guard_model import guarded_outcomes
        return guarded_outcomes(frame,unchanged_death_outcomes(frame,self.outcomes,prepared),self.engine)

    def outcomes(self,b,payload,target):
        s,past,private,observer,physical=payload;e=self.engine
        public={o.board.winner:o.board for o in e.public_children(b,target,s)}
        return tuple(FlowOutcome(o.probability,o.board,public.get(o.board.winner))
                     for o in e.physical_children(physical,target))

    def project(self,b,payload,outcome,target):
        from .board_future import reconstruct_child
        return reconstruct_child(self.engine,b,payload,outcome,target,
            lambda:self._project_roles(b,payload,outcome,target))

    def _project_roles(self,b,payload,outcome,target):
        from .board_roles import project_generated
        return project_generated(self.engine,b,payload,outcome,target)

    def morning_value(self,payload):
        child,st,past,own,observer=payload;e=self.engine
        child,st,past,own,observer=e.continuation_context(child,st,past,own,observer)
        published=e.morning(child,st,past)
        if published==((F(1),child,st,past),):
            # No observation occurred. Keep the physical/observer measure;
            # a report likelihood ratio would spuriously intersect it with Q.
            return e.solve(child,st,past,own,observer,
                           physical=physical_board(child,own,payload.physical))
        branches=e.push(st,own,published)
        from .board_future import reconstruct_publication,publication_key
        observations={}
        for q,c,ns,p,priv in branches:
            key=publication_key(c,p);observations[key]=observations.get(key,0)+1
        def evaluate(c,ns,p,priv):
            rebuilt=reconstruct_publication(e,payload,c,ns,p,priv,
                                            physical_board(c,priv,payload.physical),
                                            replay_unique=observations[publication_key(c,p)]==1)
            return e.solve(*rebuilt,physical=rebuilt.physical)
        return continuation_value(branches,evaluate)

    def day_value(self,payload):return self.engine.solve(*payload,physical=payload.physical)


def information_forecast(b,s,past,rules,strategy,*,observer=None,mask=None,private_board=None,private_attacks=(),max_work=250000,max_seconds=20,trace=None):
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
            engine=InformationSetForecast(rules,strategy,max_work=max_work,trace=trace)
            return engine.evaluate(b,s,past,observer=observer,mask=mask,private_board=private_board,private_attacks=private_attacks)
    except CalculationBudgetExceeded:return FuturePending('information_set_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)
