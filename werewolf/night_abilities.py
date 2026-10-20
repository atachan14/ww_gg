"""Exact role-ordered ability stages, before simultaneous night casualties.

The program is a generative factorization, not a sequence of shared-information
policies. Each seer chooses using only that seer's earlier acquisitions. A later
actor never receives the previous actor's result. Wolf/guard policy hooks must
be bound to the night-start information frame, before partitioning this measure.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from .calculation_budget import tick

ROLE_ORDER=('medium','seer','hunter','wolf')

@dataclass(frozen=True)
class AbilityStep:
    kind:str
    actor:int | None
    value:object
    visible_to:tuple=()

@dataclass(frozen=True)
class AbilityPath:
    hypothesis:object
    steps:tuple=()


def seer_paths(h,alive,day,initial_rule,position=('unvisited','uniform'),*,tracked=None,missing_only=False):
    from .seer_future_uniform import candidates
    from .seer_acquisition import Acquisition
    if tuple(position)!=('unvisited','uniform'):raise ValueError('Unsupported ordered scan-position filters')
    actors=tuple(sorted(p for p in alive if h.roles[2]&(1<<(p-1)) and (tracked is None or p in tracked))) if day!=1 or initial_rule!='none' else ()
    rows=(AbilityPath(h),)
    for actor in actors:
        if missing_only and any(a.player==actor and a.day==day for a in h.acquisitions):continue
        # Every actor's filter reads its own PRE-night records. Rows produced
        # by another actor can alter neither legal targets nor choice weights.
        targets=tuple(p for p in alive if p!=actor and not h.roles[0]&(1<<(p-1))) if day==1 and initial_rule=='random_white' else candidates(h,actor,alive)
        if not targets:raise ValueError('no_legal_true_seer_target; terminal handling belongs to caller')
        generated=[]
        for row in rows:
            for target in targets:
                tick();color='black' if h.roles[0]&(1<<(target-1)) else 'white'
                acquisition=Acquisition(day,actor,target,color)
                own=replace(row.hypothesis,acquisitions=tuple(sorted((*row.hypothesis.acquisitions,acquisition))),mass=row.hypothesis.mass/F(len(targets)))
                generated.append(AbilityPath(own,(*row.steps,AbilityStep('seer_target',actor,target,(actor,)),AbilityStep('seer_result',actor,color,(actor,)))))
        rows=tuple(generated)
    return rows


def recorded_steps(h,day):
    """The same role/actor order for an already generated physical leaf."""
    steps=[]
    for a in sorted((a for a in h.acquisitions if a.day==day),key=lambda a:a.player):
        steps.extend((AbilityStep('seer_target',a.player,a.target,(a.player,)),AbilityStep('seer_result',a.player,a.color,(a.player,))))
    for g in sorted((g for g in h.guards if g.night==day-1),key=lambda g:g.actor):steps.append(AbilityStep('guard_target',g.actor,g.target,(g.actor,)))
    for a in h.attacks:
        if a.night==day-1:steps.append(AbilityStep('wolf_target',None,a.target,()))
    return tuple(steps)



def complete_initial(state,alive):
    """Expand only marginalized initial actors, retaining existing Q/P weights."""
    if state.tracked is None:return state
    from .seer_acquisition import normalize
    entries=tuple(p.hypothesis for h in state.hypotheses for p in seer_paths(h,alive,1,state.initial_rule,missing_only=True))
    return replace(state,hypotheses=normalize(entries),tracked=None)


def stage_schema(*,mediums=0,seers=0,hunters=0):
    """Role-table integration contract; counts do not enable unsupported laws."""
    return (tuple(('medium_result',i) for i in range(mediums))+
        tuple((kind,i) for i in range(seers) for kind in ('seer_target','seer_result'))+
        tuple(('guard_target',i) for i in range(hunters))+(('wolf_target',0),))
