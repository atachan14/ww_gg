"""Configured-policy H0 consumer of constructed closed-node partitions."""
from contextlib import contextmanager
from fractions import Fraction as F
from .information_set_forecast import InformationSetForecast,InformationSetActionPolicy,exchangeable_value
from .group_partition import _fix,_report_groups,_frame_groups
from .calculation_budget import tick


class GroupedPolicy(InformationSetActionPolicy):
    def morning_value(self,payload):
        e=self.engine;value=e.terminal_report_value(payload)
        if value is not None:return value
        value=F()
        for q,mass,child in e.report_children(payload):
            with e.group_scope(_report_groups(e.groups,child)):
                value+=mass*e.solve(*child,physical=child.physical)
        return value


class GroupedForecast(InformationSetForecast):
    def __init__(self,*args,aggregate_wolf=False,aggregate_reports=False,**kwargs):
        super().__init__(*args,**kwargs)
        if (self.strategy.day,self.strategy.night,self.strategy.fake_reports) not in (('random',)*3,('max',)*3):raise ValueError('Uniform or MAX representative mode only')
        self.aggregate_wolf=aggregate_wolf;self.aggregate_reports=aggregate_reports
        self.report_kernels={};self.value_laws={};self.scalar_projections={}
        from .morning_publications import PublicMomentCache
        self.terminal_moments=PublicMomentCache()
        self.groups=();self.orbit_stats={'target_members':0,'target_representatives':0}
        self.action_policy=GroupedPolicy(self)
        self.joint_actions={};self.joint_outcomes={}
        self.joint_stats=dict(compiled_kernels=0,representative_actions=0,named_actions=0,resolved_actions=0,named_outcomes=0,outcome_representatives=0)

    def joint_night_value(self,source):
        from .night_program import compile_night
        program=compile_night(self,source,self.groups)
        if program is not None:return program.root.value(self)
        from .joint_action_kernel import supported,compile_actions,group_outcomes,continuation_value
        if not supported(self,source):return None
        groups=compile_actions(self,source,self.groups)
        return sum((group.policy_mass*continuation_value(self,((weight*outcome.probability,outcome)
            for plan,weight,outcome in group_outcomes(self,group))) for group in groups if group.policy_mass),F())

    def uncached_act(self,b,s,past,target,private,observer,*,physical=None):
        from .evaluation_branch import ContinuationInputs,physical_board
        from .joint_action_kernel import supported,resolve_outcomes,continuation_value
        source=ContinuationInputs(b,s,past,private,observer,physical_board(b,private,physical))
        if supported(self,source):
            from .exact import legal_targets
            from .information_set_forecast import Pending
            if target not in legal_targets(source.physical,self.rules,self.strategy):raise Pending('information_set_internal_illegal_action')
            self.expansions['actions']+=1
            return continuation_value(self,((o.probability,o) for o in resolve_outcomes(self,source,target,self.groups)))
        return super().uncached_act(b,s,past,target,private,observer,physical=physical)

    def scalar_laws(self,b,s,private,observer):
        if getattr(self,'retain_complete_abilities',False):return s,private
        # Only ephemeral scalar inputs; named/observed/history frames stay full.
        if (not self.aggregate_reports or self.strategy.day!='max' or b.initial_hunter_count
            or not b.initial_seer_count or self.retire_uninformative_scans
            or self.acquisition_provenance is not None or self.trace is not None):return s,private
        from .actor_information import PersonalInformation
        from .seer_intervention import SeerObserver
        if observer is not None and type(observer) not in (PersonalInformation,SeerObserver):return s,private
        tick(0)
        keep=tuple(sorted(set(b.alive)|({observer.actor} if observer is not None else set())))
        from .evaluation_projection import project_inactive_acquisitions
        def projected(state):
            key=(state,keep)
            if key in self.scalar_projections:return self.scalar_projections[key]
            result=project_inactive_acquisitions(state,keep)
            if result is not state:self.scalar_projections[key]=result
            return result
        q,p=projected(s),projected(private)
        if q is not s or p is not private:
            # Discarding an unsupported private coordinate cannot create support.
            from .information_weights import observer_projection_ratios
            from .information_set_forecast import Pending
            observer_projection_ratios(s,private,incomplete=lambda:Pending('information_set_report_likelihood_incomplete'))
        return q,p

    def solve(self,b,s,past,private,observer,*,physical=None):
        with self.frame_scope(b,past,observer):
            s,private=self.scalar_laws(b,s,private,observer)
            return super().solve(b,s,past,private,observer,physical=physical)

    # Constructed partitions replace discovery by full-law label permutations.
    # Named flow/action keys retain all inputs; only the proved constant
    # terminal scalar uses a shared value key.
    def renamed_value_key(self,*args,**kwargs):return None
    def full_renamed_key(self,b,s,past,private,observer,*,target=None,physical=None):
        # Only the already-proved constant terminal scalar, never a joint law
        # or a forced named action. Common solve checks run before this key.
        if target is None and self.memoize_flows and self.terminal_uniform_day(b):
            tick(0)  # Cache reuse still observes cancellation and time/work stops.
            return ('uniform-terminal-day',self.rules,self.strategy)
        return None
    def scalar_descriptor(self,*args,**kwargs):return None

    def terminal_uniform_day(self,b):
        return self.strategy.day=='random' and self.terminal_execution_day(b)

    def terminal_execution_day(self,b):
        return b.phase=='day' and len(b.alive)==3 and not b.initial_hunter_count and set(b.wolf_count_distribution)=={1}

    def exchangeable(self,b):
        # Uniform execution of three survivors with one wolf always ends.
        # The common count recurrence is independent of all report/scan history.
        if self.terminal_uniform_day(b):return True
        return super().exchangeable(b)

    def value_law(self,state):
        # Exact derived value of the same owned immutable input; no state orbit.
        key=(self.rules.allow_repeat_guard,self.strategy.night,state)
        if key not in self.value_laws:self.value_laws[key]=super().value_law(state)
        return self.value_laws[key]

    def report_partition(self,b,past):
        if self.strategy.day!='random' or not self.aggregate_reports or not self.groups:return ()
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
        return self.checked(self.publication_kernel(b,s,past).branches(partition))

    def publication_kernel(self,b,s,past):
        from .morning_publications import compile_publications
        key=(b,s,past)
        if key not in self.report_kernels:
            self.report_kernels[key]=self.checked(compile_publications(s,past,b.alive,b.claims,
                fake_policy=self.strategy.fake_seer_policy,seed=self.publication_values.get(key,()),board=b))
        return self.report_kernels[key]

    def terminal_report_value(self,payload):
        # Only an unobserved scalar AFTER acquisition/physical projection.
        # Compile every positive-Q medium family before transferring P, even
        # when a family has zero viewer mass. No seer event law is constructed.
        b,s,past,own,observer=payload
        if self.strategy.day=='max':return self.terminal_max_report_value(payload)
        if (not self.aggregate_reports or self.retire_uninformative_scans or self.acquisition_provenance is not None
            or not self.terminal_uniform_day(b) or
            any(self.strategy.disclosure_for(role)!='all' for role in ('seer','medium'))):return None
        from .exact import report_actions,random_report_outcomes
        tick(0)
        outcomes=random_report_outcomes(b) if report_actions(b) else ()
        rows=tuple((o.probability,o.board,self.project(s,o.board),past) for o in outcomes) if outcomes else ((F(1),b,s,past),)
        for q,child,law,history in rows:self.publication_kernel(child,law,history)
        constant=exchangeable_value(3,1,'day',self.strategy)
        return sum((mass*constant for mass,*rest in self.push(s,own,rows)),F())

    def terminal_max_report_value(self,payload):
        b,s,past,own,observer=payload
        if (not self.aggregate_reports or self.retire_uninformative_scans or self.acquisition_provenance is not None
            or self.trace is not None or not self.terminal_execution_day(b)
            or any(self.strategy.disclosure_for(role)!='all' for role in ('seer','medium'))):return None
        from .exact import report_actions
        from .information_set_forecast import Pending
        incomplete=lambda:Pending('information_set_report_likelihood_incomplete')
        def score(outcomes):
            return sum((o.probability*self.publication_kernel(o.board,law,past).terminal_execution_value(
                law,o.board.alive,incomplete=incomplete,cache=self.terminal_moments)
                for o in outcomes for law in (self.project(s,o.board),)),F())
        actions=report_actions(b)
        outcomes=self.report_outcomes(b,s,past,actions,evaluate=score) if actions else ()
        rows=tuple((o.probability,o.board,self.project(s,o.board),past) for o in outcomes) if outcomes else ((F(1),b,s,past),)
        # Validate all Q families, including zero-P observations, before push.
        for q,child,law,history in rows:self.publication_kernel(child,law,history)
        return sum((mass*self.publication_kernel(child,law,history).terminal_execution_value(
            private,child.alive,incomplete=incomplete,cache=self.terminal_moments)
            for mass,child,law,history,private in self.push(s,own,rows)),F())

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

    @property
    def max_grouped(self):
        return (self.strategy.day=='max' and self.aggregate_wolf and self.aggregate_reports and not self.strategy.include_self_bite
                and not self.retire_uninformative_scans and self.acquisition_provenance is None and self.trace is None)

    @contextmanager
    def frame_scope(self,b,past,observer=None,*,target=None):
        tick(0)
        groups=() if self.strategy.day=='max' and b.initial_hunter_count else _frame_groups(self.groups,b,past,observer,target=target)
        with self.group_scope(groups):yield

    def equivalent_targets(self,b,s,x,y,past=()):
        if self.max_grouped and any(x in group and y in group for group in self.groups):return True
        return super().equivalent_targets(b,s,x,y,past)

    def wolf_policy(self,b,s,past,mask,history=()):
        from .actor_information import WolfInformation
        with self.frame_scope(b,past),self.actor_scope(WolfInformation(mask,history)):
            return super().wolf_policy(b,s,past,mask,history)

    def target_orbits(self,targets):
        if self.strategy.day!='random' and not self.max_grouped:return super().target_orbits(targets)
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
        if self.strategy.day!='random' and not self.max_grouped:return super().wolf_cells(state)
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
        with self.frame_scope(b,past,observer,target=target):
            s,private=self.scalar_laws(b,s,private,observer)
            return super().act(b,s,past,target,private,observer,physical=physical)
