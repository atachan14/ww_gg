"""Viewer evidence projection only. Never pass this Board to the public solver.

This projection does not choose future actions or mutate public claims/reports.
Final action values require a solver retaining the separate public information set.
"""
from dataclasses import dataclass
from fractions import Fraction
from .exact import actual_role, replace_worlds
from .seer_acquisition import Acquisition


@dataclass(frozen=True)
class PrivateView:
    board: object
    role: str
    players: tuple[int, ...]
    acquisitions: tuple[Acquisition, ...] = ()


def condition_private(board, role, players, results=(), *, rules):
    players=tuple(players)
    if role not in ('wolf','seer','hunter','medium'):
        raise ValueError('Unsupported private viewpoint')
    required=board.initial_role_counts['wolf'] if role=='wolf' else 1
    if (len(players)!=required or len(set(players))!=required or
        any(type(p) is not int or not 1<=p<=board.player_count for p in players)):
        raise ValueError('Select the required viewpoint players')
    if role!='wolf' and players[0] not in board.alive:
        raise ValueError('Ability viewer must be alive')
    mask=sum(1<<(p-1) for p in players)
    candidates=tuple(w for w in board.worlds if
        (w[0]==mask if role=='wolf' else actual_role(board,w,players[0])==role))
    if not candidates:raise ValueError('Inconsistent private viewpoint')
    if results and role not in ('seer','medium'):
        raise ValueError('Result evidence is unsupported for this role')
    seen=set();acquisitions=[]
    for result in results:
        if set(result)!={'day','target','color'}:raise ValueError('Invalid private evidence shape')
        day,target,color=result['day'],result['target'],result['color']
        if type(day) is not int or not 1<=day<=board.day or day in seen:
            raise ValueError('Invalid private evidence day')
        seen.add(day)
        # Missing fields stay unknown. They are not fabricated as white results.
        if target is None or color is None:
            if target is not None and (type(target) is not int or not 1<=target<=board.player_count):raise ValueError('Invalid private target')
            if color not in (None,'white','black'):raise ValueError('Invalid private color')
            continue
        if type(target) is not int or not 1<=target<=board.player_count or target==players[0] or color not in ('white','black'):
            raise ValueError('Invalid private result')
        if role=='seer':
            if day==1 and (rules.initial_seer=='none' or rules.initial_seer=='random_white' and color=='black'):
                raise ValueError('Private result conflicts with initial seer rule')
            # Night N acquires result slot N+1 before that night's casualty.
            dead={event.target for event in board.history if event.day<day-1 or event.day==day-1 and event.phase=='day'}
            if target in dead or players[0] in dead:raise ValueError('Private scan target was unavailable')
            acquisitions.append(Acquisition(day,players[0],target,color))
        else:
            executions={event.target for event in board.history if event.phase=='day' and event.day==day-1}
            if target not in executions:raise ValueError('Private medium result has no matching execution')
        candidates=tuple(w for w in candidates if bool(w[0]&(1<<(target-1)))==(color=='black'))
        if not candidates:raise ValueError('Inconsistent private evidence')
    total=sum((w[-1] for w in candidates),Fraction())
    private=replace_worlds(board,tuple((*w[:4],w[-1]/total) for w in candidates))
    return PrivateView(private,role,players,tuple(sorted(acquisitions)))
