"""One complete existing morning-publication boundary; no new action/CO rule."""
from collections import Counter
from dataclasses import dataclass,replace
from fractions import Fraction as F
from time import perf_counter
from .cut_out_model_a import ModelAInitialGroups
from .cut_out_day_night import CutOutDayNight,ChildState
from .partitioned_match_groups import UnsupportedPartition
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.seer_acquisition import SeerReport


@dataclass(frozen=True)
class PublishedPath:
    bite: int | None
    mass: F
    child: ChildState


@dataclass(frozen=True)
class PublishedDayBranch:
    mass: F
    paths: tuple


@dataclass(frozen=True)
class PublishedDayClass:
    targets: tuple
    selection_mass: F
    branches: tuple


@dataclass(frozen=True)
class MorningResult:
    initial_context: object
    classes: tuple
    terminal_mass: tuple


class CutOutMorning:
    def __init__(self,engine):
        if type(engine) is not ModelAInitialGroups:raise TypeError('formal constructed initial public adapter only')
        self.engine=engine;self.upstream=CutOutDayNight(engine)
        # Existing full-record validation mode: avoid scalar-only retirement of
        # scans/known fake noise. No report strategy or disclosure rule changes.
        self.kernel=InformationSetForecast(engine.baseline.rules,engine.baseline.strategy,max_work=100000,
            exact_renaming=False,memoize_flows=False,retire_uninformative_scans=False)
        self.stats=Counter(generator_checks=0,full_permutation_searches=0,initial_reallocations=0,
            morning_calls=0,generated_observations=0,public_fact_positions=0)

    def _publish(self,child):
        if child.board.winner is not None:return ((F(1),child),)
        if child.stage!='before_publication' or child.board.day!=2 or child.board.phase!='day':
            raise ValueError('only first morning after casualties accepted')
        if child.law.public_roles!=tuple(sorted(child.board.worlds)):raise ValueError('public prior mismatch')
        self.stats['morning_calls']+=1
        self.stats['morning_input_hypotheses']+=len(child.law.hypotheses)
        started=perf_counter()
        branches=self.kernel.morning(child.board,child.law,child.past)
        self.stats['formal_morning_seconds']+=perf_counter()-started
        # Same public physical measure here; no viewer evidence enters generation.
        started=perf_counter();weighted=self.kernel.push(child.law,child.law,branches)
        self.stats['observer_weight_seconds']+=perf_counter()-started
        if len(branches)!=len(weighted):raise ValueError('public/physical branch count mismatch')
        result=[]
        for (q,board,law,past),(mass,b,public,history,own) in zip(branches,weighted):
            if (q,board,law,past)!=(mass,b,public,history) or own!=law:
                raise ValueError('identical observer measure failed to round-trip')
            if past[:len(child.past)]!=child.past:raise ValueError('existing public history changed')
            if board.reports[:len(child.board.reports)]!=child.board.reports:raise ValueError('medium history changed')
            new_seers=past[len(child.past):]
            new_mediums=board.reports[len(child.board.reports):]
            # No assumption that input log rows or cross-role reports are a new
            # simultaneous batch. Point-fix only actually PUBLIC endpoints.
            fixed=set()
            for r in new_seers:fixed.update((r.player,r.target))
            for r in new_mediums:fixed.update((r.reporter,r.target))
            self.stats['public_fact_positions']+=len(fixed)
            groups=self.upstream._fix(child.groups,*fixed)
            self.stats['generated_observations']+=1
            self.stats['morning_output_hypotheses']+=len(law.hypotheses)
            result.append((q,ChildState(board,law,groups,past,'after_morning_publication')))
        if sum((q for q,c in result),F())!=1:raise ValueError('morning probability mass lost')
        return tuple(result)

    def evaluate(self,*,representatives=True):
        started=perf_counter();before=self.upstream.evaluate(representatives=representatives)
        if isinstance(before,UnsupportedPartition):return before
        classes=[];terminal={}
        try:
            for action in before.classes:
                branches=[]
                for day in action.branches:
                    paths=[]
                    physical=((None,F(1),day.child),) if not day.night else tuple((o.target,o.mass,o.child) for o in day.night)
                    for bite,chance,child in physical:
                        for q,published in self._publish(child):
                            paths.append(PublishedPath(bite,chance*q,published))
                            winner=published.board.winner
                            terminal[winner]=terminal.get(winner,F())+action.selection_mass*day.mass*chance*q
                    branches.append(PublishedDayBranch(day.mass,tuple(paths)))
                classes.append(PublishedDayClass(action.targets,action.selection_mass,tuple(branches)))
        except Pending as error:
            return UnsupportedPartition('existing morning law pending: '+error.reason)
        self.stats['evaluation_seconds']+=perf_counter()-started
        return MorningResult(before.initial_context,tuple(classes),tuple(sorted(terminal.items(),key=repr)))

    def labelled_paths(self,result,target):
        if type(result) is not MorningResult or result.initial_context is not self.engine.start() or type(target) is not int:
            return UnsupportedPartition('issued public result and original integer target only')
        action=next((c for c in result.classes if target in c.targets),None)
        if action is None:return UnsupportedPartition('target outside original classes')
        a=action.targets[0];prefix=self.engine.baseline.past;paths=[]
        def player(p):return target if p==a else a if p==target else p
        for day in action.branches:
            for path in day.paths:
                child=path.child
                board,law=self.upstream._move(child.board,child.law,a,target)
                # Root input order remains EXACT. Only the generated suffix is
                # mapped and sorted as the existing GeneratedPublication vector.
                if child.past[:len(prefix)]!=prefix:raise ValueError('initial past prefix changed')
                suffix=child.past[len(prefix):]
                reports=tuple(sorted(SeerReport(r.acquired_day,r.published_day,player(r.player),player(r.target),r.color) for r in suffix))
                past=prefix+reports
                groups=tuple(tuple(sorted(player(p) for p in group)) for group in child.groups)
                moved=ChildState(board,law,groups,past,child.stage)
                paths.append((None if path.bite is None else player(path.bite),day.mass*path.mass,moved))
        return tuple(sorted(paths,key=lambda row:repr((row[0],row[2].board.reports,row[2].past,row[2].board.winner))))