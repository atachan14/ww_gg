"""One day execution on the small JOINT-SUPPORT prototype law only.

No Model A adapter, night, report generation, policy optimization or game solve.
Representatives are evaluated once; label-dependent posteriors need an explicit
known within-block swap for materialization, never an isomorphism search.
"""
from collections import Counter
from dataclasses import dataclass, replace
from fractions import Fraction as F
from time import perf_counter
from .partitioned_match_groups import SharedContext, UnsupportedPartition, ChoiceClass
from .constructive_cut_out import ConstructiveCutOutGroups
from werewolf.exact import winner_for, PublicEvent
from werewolf.seer_acquisition import Hypothesis, Acquisition, normalize


@dataclass(frozen=True)
class ExecutionBranch:
    winner: str | None
    mass: F
    role_joint_mass: tuple
    posterior: object
    alive: tuple
    phase: str
    execution: PublicEvent


@dataclass(frozen=True)
class RepresentativeAction:
    targets: tuple
    selection_mass: F
    branches: tuple

    @property
    def representative(self):return self.targets[0]

    @property
    def multiplicity(self):return len(self.targets)


@dataclass(frozen=True)
class OneStepResult:
    context: SharedContext
    view: str
    actions: tuple
    aggregate: tuple
    law_semantics: str = 'prototype_joint_support'


def _role(h,target):
    return next((r for r,mask in enumerate(h.roles) if mask & (1<<(target-1))),4)


class OneStepExecution:
    supported_law = 'prototype_joint_support'
    def __init__(self, engine):
        if type(engine) is not ConstructiveCutOutGroups:
            raise TypeError('Constructive small-law engine required')
        self.engine=engine
        self.stats=Counter(candidate_evaluations=0,legal_candidates=0,hypotheses_scanned=0,
                           posterior_normalizations=0,materialized_targets=0,
                           materialization_hypotheses=0,generator_checks=0)

    def evaluate(self,context,*,view,law_semantics='prototype_joint_support',representatives=True):
        started=perf_counter()
        try:return self._evaluate(context,view,law_semantics,representatives)
        finally:self.stats['evaluation_seconds']+=perf_counter()-started

    def _evaluate(self,context,view,law_semantics,representatives):
        if type(representatives) is not bool:return UnsupportedPartition('explicit representative/full-labelled comparison mode required')
        if law_semantics!=self.supported_law:
            return UnsupportedPartition('expected '+self.supported_law+'; no implicit law conversion')
        if type(context) is not SharedContext or context.baseline is not self.engine.baseline:
            return UnsupportedPartition('different complete context')
        if view not in ('public','private') or (view=='public')!=(context.scope=='public'):
            return UnsupportedPartition('explicit separate public/private context required')
        if context.alive!=tuple(range(1,self.engine.baseline.players+1)) or any(e.kind in ('death','select') for e in context.events):
            return UnsupportedPartition('one initial Day1 execution before death/selected-instruction records only')
        law=context.public if view=='public' else context.private
        if any(h.guards or h.attacks for h in law.hypotheses):
            return UnsupportedPartition('night histories outside one-step execution scope')
        legal=context.alive
        choices=self.engine.uniform_choices(context,legal)
        if isinstance(choices,UnsupportedPartition):return choices
        self.stats['legal_candidates']+=len(legal)
        if not representatives:
            # Same-kernel labelled reference, not a production fallback.
            choices=tuple(ChoiceClass((p,),1,F(1,len(legal))) for p in legal)
        actions=[];aggregate={}
        for choice in choices:
            target=choice.targets[0];self.stats['candidate_evaluations']+=1
            buckets={}
            scan_started=perf_counter()
            for h in law.hypotheses:
                self.stats['hypotheses_scanned']+=1
                wolves=sum(bool(h.roles[0] & (1<<(p-1))) for p in legal if p!=target)
                winner=winner_for(len(legal)-1,wolves)
                entries,mass,roles=buckets.setdefault(winner,([],F(),[F()]*5))
                entries.append(h);roles[_role(h,target)]+=h.mass
                buckets[winner]=entries,mass+h.mass,roles
            self.stats['joint_scan_seconds']+=perf_counter()-scan_started
            branches=[]
            for winner in ('village','wolf',None):
                if winner not in buckets:continue
                entries,mass,roles=buckets[winner]
                normalization_started=perf_counter()
                posterior=replace(law,hypotheses=normalize(entries))
                self.stats['posterior_normalizations']+=1
                self.stats['posterior_seconds']+=perf_counter()-normalization_started
                branch=ExecutionBranch(winner,mass,tuple(roles),posterior,
                    tuple(p for p in legal if p!=target),'day' if winner else 'night',PublicEvent(1,'day',target))
                branches.append(branch)
                for r,q in enumerate(roles):
                    aggregate[winner,r]=aggregate.get((winner,r),F())+choice.mass*q
            actions.append(RepresentativeAction(choice.targets,choice.mass,tuple(branches)))
        return OneStepResult(context,view,tuple(actions),tuple(sorted(aggregate.items(),key=repr)),law_semantics=law_semantics)

    def materialize(self,result,target):
        """Explicit optional label transport, separately charged from evaluation.

        Complete posteriors are not multiplied/copied into all target rows unless
        requested. Aggregation uses only invariant winner/role masses.
        """
        if type(result) is not OneStepResult or result.context.baseline is not self.engine.baseline:
            return UnsupportedPartition('different result context')
        if type(target) is not int:return UnsupportedPartition('original integer target required')
        action=next((a for a in result.actions if target in a.targets),None)
        if action is None:return UnsupportedPartition('target not evaluated')
        started=perf_counter();self.stats['materialized_targets']+=1
        try:
            if target==action.representative:return action.branches
            a=action.representative
            def player(p):return target if p==a else a if p==target else p
            def mask(m):return sum(1<<(player(p)-1) for p in range(1,result.context.baseline.players+1) if m&(1<<(p-1)))
            branches=[]
            for branch in action.branches:
                hs=[]
                for h in branch.posterior.hypotheses:
                    self.stats['materialization_hypotheses']+=1
                    acquisitions=tuple(sorted(Acquisition(r.day,player(r.player),player(r.target),r.color) for r in h.acquisitions))
                    hs.append(Hypothesis(tuple(mask(m) for m in h.roles),acquisitions,h.mass))
                # The initial roster is the entire set; private owner/targets
                # have singleton groups. No hidden observer transport is guessed.
                law=replace(branch.posterior,hypotheses=normalize(hs))
                branches.append(replace(branch,posterior=law,alive=tuple(sorted(player(p) for p in branch.alive)),execution=replace(branch.execution,target=player(branch.execution.target))))
            return tuple(branches)
        finally:self.stats['materialization_seconds']+=perf_counter()-started