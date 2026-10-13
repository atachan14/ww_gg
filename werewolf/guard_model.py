"""Approved uniform guard law and its current information-set scope.

A public-known guardian needs no hidden attack ledger for future uniform guards.
An uncertain guardian does: keep that case explicit until the ledger is modeled.
"""
from dataclasses import dataclass, replace
from fractions import Fraction as F
from .action_flow import FlowOutcome
from .guard_night import guard_targets
from .guard_effect import GuardIntent,guard_blocks_attack


def live_guard_mass(board):
    return sum((board.role_probability(p,'hunter') for p in board.alive),F())


def known_guardian(board):
    if not live_guard_mass(board):return None
    return next((p for p in board.alive if board.role_probability(p,'hunter')==1),None)


def scope_reason(board,rules):
    if not board.initial_hunter_count:return None
    if board.initial_hunter_count!=1:return 'guard_multiple_hunters_unimplemented'
    if not rules.allow_repeat_guard:return 'guard_no_repeat_unimplemented'
    if live_guard_mass(board) and known_guardian(board) is None:
        return 'guard_hidden_attack_history_unimplemented'
    return None


def guard_choices(board,actor,rules,position=('uniform',)):
    if tuple(position)!=('uniform',):raise ValueError('Unsupported ordered guard-position items')
    targets=guard_targets(board,actor,rules)
    return tuple((p,F(1,len(targets))) for p in targets)


@dataclass(frozen=True)
class GuardObserver:
    board: object
    actor: int
    target: int
    allowed_roles: tuple

    def __call__(self,h,state):
        return h.roles in self.allowed_roles


def guarded_outcomes(frame,outcomes,engine):
    """Physical guard law after acquisition; public success hides the bite target.

    Public corpse updates keep Model A compatibility semantics. With a known
    guardian, the uniform failure probability is constant over compatible worlds.
    The private branch retains the action's conditional roles and acquisitions.
    """
    b=frame.board
    reason=scope_reason(b,engine.rules)
    if reason:raise engine.pending(reason)
    actor=known_guardian(b)
    if actor is None:return outcomes
    observer=frame.after[3]
    if isinstance(observer,GuardObserver) and observer.board==b:
        chance=F(guard_blocks_attack(GuardIntent(b.day,actor,observer.target),frame.target))
    else:
        chance=sum((q for target,q in guard_choices(b,actor,engine.rules,engine.strategy.guard_position) if guard_blocks_attack(GuardIntent(b.day,actor,target),frame.target)),F())
    result=[FlowOutcome(o.probability*(1-chance),o.board,o.context) for o in outcomes if chance<1]
    if chance:
        physical=frame.after[4]
        public=replace(b,day=b.day+1,phase='day')
        own=replace(physical,day=b.day+1,phase='day')
        result.append(FlowOutcome(chance,own,public))
    return tuple(result)
