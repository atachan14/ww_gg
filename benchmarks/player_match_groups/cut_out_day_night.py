"""Constructed groups through Day1 execution + one random wolf night.

Formal initial prior is carried, never reallocated. Wolf-owned information
conditions the temporary actor law BEFORE uniform policy choice. Stop after
casualties, before Day2 publication. No future game solve or new strategy.
"""
from collections import Counter
from dataclasses import dataclass,replace,fields
from fractions import Fraction as F
from time import perf_counter
from .cut_out_model_a import ModelAInitialGroups,ModelAOneStepExecution
from .partitioned_match_groups import UnsupportedPartition
from werewolf.exact import action_outcomes,replace_worlds,MediumReport
from werewolf.actor_information import wolf_information_groups
from werewolf.fixed_actor_continuation import physical_actor_outcomes
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.seer_acquisition import Hypothesis,Acquisition,normalize
from werewolf.night_knowledge import WolfAttack
from werewolf.exact_renaming import BOARD_FIELDS


def point_fix(groups,*positions):
    fixed=set(positions)
    result=[]
    for group in groups:
        by={}
        for p in group:by.setdefault(('fixed',p) if p in fixed else ('remaining',),[]).append(p)
        result.extend(tuple(g) for g in by.values())
    return tuple(result)


def moved_law(law,a,b,n):
    if a==b:return law
    def player(p):return b if p==a else a if p==b else p
    def mask(m):return sum(1<<(player(p)-1) for p in range(1,n+1) if m&(1<<(p-1)))
    entries=[]
    for h in law.hypotheses:
        if h.guards:raise ValueError('hunter history outside closed scope')
        acquisitions=tuple(sorted(Acquisition(r.day,player(r.player),player(r.target),r.color) for r in h.acquisitions))
        attacks=tuple(WolfAttack(r.night,player(r.target)) for r in h.attacks)
        entries.append(Hypothesis(tuple(mask(m) for m in h.roles),acquisitions,h.mass,(),attacks))
    return replace(law,hypotheses=normalize(entries),
        rosters=tuple(tuple(sorted(player(p) for p in roster)) for roster in law.rosters),
        tracked=None if law.tracked is None else tuple(sorted(player(p) for p in law.tracked)))


def moved_board(board,law,a,b):
    if a==b:return board
    if ({f.name for f in fields(board)}!=BOARD_FIELDS or board.guard_prior_roster is not None
        or any(type(r) is not MediumReport or r.day!=2 for r in board.reports)):
        raise ValueError('unknown Board/report/guard transport schema')
    def player(p):return b if p==a else a if p==b else p
    claims=dict((player(p),c) for p,c in enumerate(board.claims,1))
    return replace_worlds(board,law.public_roles,wolf_count=None,
        alive=tuple(sorted(player(p) for p in board.alive)),claims=tuple(claims[p] for p in range(1,board.player_count+1)),
        history=tuple(replace(e,target=player(e.target)) for e in board.history),
        # First generated medium vector follows the existing opportunity order.
        reports=tuple(sorted((MediumReport(r.day,player(r.reporter),player(r.target),r.color) for r in board.reports),key=lambda r:(r.day,r.reporter,r.target))),
        medium_opportunities=tuple(sorted((d,player(p),player(t)) for d,p,t in board.medium_opportunities)),
        report_resolved=tuple(sorted((d,player(p),player(t)) for d,p,t in board.report_resolved)))


@dataclass(frozen=True)
class ChildState:
    board: object
    law: object
    groups: tuple
    past: tuple
    stage: str = 'after_execution'


@dataclass(frozen=True)
class NightObservation:
    target: int
    mass: F
    child: ChildState


@dataclass(frozen=True)
class DayBranch:
    mass: F
    child: ChildState
    night: tuple


@dataclass(frozen=True)
class DayClass:
    targets: tuple
    selection_mass: F
    branches: tuple


@dataclass(frozen=True)
class NightChoiceClass:
    execution_target: int
    wolf_mask: int
    targets: tuple
    actor_mass: F
    selection_mass: F

    @property
    def multiplicity(self):return len(self.targets)


@dataclass(frozen=True)
class DayNightResult:
    initial_context: object
    classes: tuple
    terminal_mass: tuple
    night_choice_classes: tuple


class CutOutDayNight:
    def __init__(self,engine):
        if type(engine) is not ModelAInitialGroups:raise TypeError('constructed formal initial adapter only')
        self.engine=engine
        self.kernel=InformationSetForecast(engine.baseline.rules,engine.baseline.strategy,
            max_work=100000,exact_renaming=False,memoize_flows=False)
        self.stats=Counter(generator_checks=0,full_permutation_searches=0,initial_reallocations=0,
            day_candidates=0,wolf_information_groups=0,night_candidates=0,full_night_candidates=0,
            labelled_night_choices=0,transport_hypotheses=0)

    def _fix(self,groups,*positions):
        started=perf_counter()
        result=point_fix(groups,*positions)
        self.stats['partition_positions']+=sum(map(len,groups))
        self.stats['partition_seconds']+=perf_counter()-started
        return result

    def _move(self,board,law,a,b):
        started=perf_counter()
        if a!=b:self.stats['transport_hypotheses']+=len(law.hypotheses)
        result=moved_law(law,a,b,board.player_count)
        result_board=moved_board(board,result,a,b)
        self.stats['transport_seconds']+=perf_counter()-started
        return result_board,result

    def _night(self,child,grouped):
        board,law=child.board,child.law
        if board.phase!='night' or board.winner is not None:raise ValueError('continuing night child required')
        started=perf_counter();actors=wolf_information_groups(law)
        self.stats['actor_condition_seconds']+=perf_counter()-started
        self.stats['wolf_information_groups']+=len(actors)
        by_observation={};templates={};metadata_source=None
        self.stats['actor_condition_input_hypotheses']+=len(law.hypotheses)
        for info,actor_mass,actor_law in actors:
            if info.initial_roster.bit_count()!=1 or info.attacks:raise ValueError('one living wolf, no previous night only')
            actor=info.initial_roster.bit_length()
            if actor not in board.alive:raise ValueError('dead wolf cannot reach a continuing night')
            # The choice reads PUBLIC law plus own roster, not another actor's
            # scans. Current scans are acquired later inside physical kernel.
            policy_started=perf_counter()
            self.stats['night_policy_calls']+=1
            policy=dict(self.kernel.wolf_policy(board,law,child.past,info.initial_roster,info.attacks))
            self.stats['night_policy_seconds']+=perf_counter()-policy_started
            expected={p:F(1,len(board.alive)-1) for p in board.alive if p!=actor}
            if policy!=expected:raise ValueError('not the established uniform no-self-bite policy')
            actor_groups=self._fix(child.groups,actor)
            choices=tuple(tuple(p for p in group if p in policy) for group in actor_groups)
            choices=tuple(c for c in choices if c)
            if not grouped:choices=tuple((p,) for p in policy)
            self.stats['full_night_candidates']+=len(policy)
            for targets in choices:
                self._choice_audit.append(NightChoiceClass(board.history[-1].target,info.initial_roster,targets,actor_mass,sum((policy[p] for p in targets),F())))
                representative=targets[0];self.stats['night_candidates']+=1
                started=perf_counter()
                physical=replace_worlds(board,actor_law.public_roles,wolf_count=None)
                outcomes=physical_actor_outcomes(physical,actor_law,self.kernel,representative)
                self.stats['physical_kernel_seconds']+=perf_counter()-started
                # Includes acquisition and its within-world secret expansion;
                # no early marginalization or relabelling is hidden in kernel.
                self.stats['kernel_input_hypotheses']+=len(actor_law.hypotheses)
                self.stats['kernel_output_hypotheses']+=sum(len(st.hypotheses) for q,b,st in outcomes)
                for target in targets:
                    self.stats['labelled_night_choices']+=1
                    for chance,template,joint in outcomes:
                        labelled,st=self._move(template,joint,representative,target)
                        metadata=lambda x:(x.rosters,x.initial_rule,x.tracked,x.observed_prefix)
                        if metadata_source is None:metadata_source=st
                        elif metadata(st)!=metadata(metadata_source):raise ValueError('inconsistent inherited acquisition metadata')
                        key=(target,labelled.winner,labelled.day,labelled.phase,labelled.alive)
                        weight=actor_mass*policy[target]*chance
                        by_observation.setdefault(key,[]).extend(replace(h,mass=h.mass*weight) for h in st.hypotheses)
                        templates[key]=labelled
        result=[]
        started=perf_counter()
        for key,entries in sorted(by_observation.items(),key=repr):
            target=key[0];mass=sum((h.mass for h in entries),F())
            # Same metadata for all actor groups: original acquisition rosters,
            # tracked owners and prefix remain inherited, never reconstructed.
            template=templates[key]
            sample=metadata_source
            self.stats['public_merge_input_hypotheses']+=len(entries)
            posterior=replace(sample,hypotheses=normalize(entries))
            public=replace_worlds(template,posterior.public_roles,wolf_count=None)
            groups=self._fix(child.groups,target)
            result.append(NightObservation(target,mass,ChildState(public,posterior,groups,child.past,'before_publication' if public.winner is None else 'terminal')))
        self.stats['public_observation_merge_seconds']+=perf_counter()-started
        if sum((o.mass for o in result),F())!=1:raise ValueError('night probability mass lost')
        return tuple(result)

    def evaluate(self,*,representatives=True):
        if type(representatives) is not bool:return UnsupportedPartition('explicit grouped/full-labelled mode only')
        started=perf_counter();context=self.engine.start();self._choice_audit=[]
        day_evaluator=ModelAOneStepExecution(self.engine)
        day=day_evaluator.evaluate(context,representatives=representatives)
        self.stats['day_joint_hypotheses_scanned']+=day_evaluator.stats['hypotheses_scanned']
        self.stats['day_kernel_seconds']+=day_evaluator.stats['evaluation_seconds']
        self.stats['day_posterior_seconds']+=day_evaluator.stats['posterior_seconds']
        classes=[];terminal={}
        for action in day.actions:
            target=action.representative;self.stats['day_candidates']+=1
            # Official transition templates, conditioned from the inherited
            # Board. This never calls initial prior/CO allocation again.
            template_started=perf_counter()
            templates={o.board.winner:o.board for o in action_outcomes(self.engine.baseline.board,target,
                self.engine.baseline.rules,self.engine.baseline.strategy)}
            self.stats['day_template_seconds']+=perf_counter()-template_started
            branches=[]
            for branch in action.branches:
                board=templates[branch.winner];law=branch.posterior
                if tuple(sorted(board.worlds))!=law.public_roles:raise ValueError('day child lost inherited role mass')
                child=ChildState(board,law,self._fix(context.groups,target),self.engine.baseline.past,'after_execution' if board.winner is None else 'terminal')
                night=() if board.winner is not None else self._night(child,representatives)
                branches.append(DayBranch(branch.mass,child,night))
                if board.winner is not None:
                    terminal[board.winner]=terminal.get(board.winner,F())+action.selection_mass*branch.mass
                else:
                    for obs in night:
                        winner=obs.child.board.winner
                        terminal[winner]=terminal.get(winner,F())+action.selection_mass*branch.mass*obs.mass
            classes.append(DayClass(action.targets,action.selection_mass,tuple(branches)))
        self.stats['acquisition_cache_entries']=len(self.kernel.acquired)
        self.stats['evaluation_seconds']+=perf_counter()-started
        return DayNightResult(context,tuple(classes),tuple(sorted(terminal.items(),key=repr)),tuple(self._choice_audit))

    def labelled_paths(self,result,target):
        """Return conditional paths for ONE original execution target.

        Class selection mass is k/N; one labelled target has 1/N. Returned path
        masses are conditional on the chosen execution; caller multiplies 1/N.
        """
        if result.initial_context is not self.engine.start() or type(target) is not int:
            return UnsupportedPartition('issued initial result and original target only')
        action=next((a for a in result.classes if target in a.targets),None)
        if action is None:return UnsupportedPartition('target outside original action classes')
        representative=action.targets[0];paths=[]
        def player(p):return target if p==representative else representative if p==target else p
        for branch in action.branches:
            items=((None,F(1),branch.child),) if not branch.night else tuple((o.target,o.mass,o.child) for o in branch.night)
            for bite,mass,child in items:
                board,law=self._move(child.board,child.law,representative,target)
                groups=tuple(tuple(sorted(player(p) for p in group)) for group in child.groups)
                labelled=ChildState(board,law,groups,child.past,child.stage)
                paths.append((None if bite is None else player(bite),branch.mass*mass,labelled))
        return tuple(sorted(paths,key=lambda x:repr((x[0],x[2].board.winner))))