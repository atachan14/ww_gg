"""Explicit single-world guarded nights, using the common action pipeline.

No automatic guard policy or probabilistic public conditioning is supplied.
Callers must supply a fixed guard intent independent of the selected attack.
"""
from fractions import Fraction
from .exact import Rules, PublicEvent, actual_role, replace_worlds
from .action_flow import FlowOutcome, resolve_action
from .guard_effect import GuardIntent, resolve_guard


def guard_targets(board, actor, rules, previous=None):
    if not isinstance(rules,Rules) or type(actor) is not int or actor not in board.alive:
        raise ValueError('Living guardian and Game rules required')
    if not rules.allow_repeat_guard:
        raise ValueError('No-repeat guard rule is not implemented yet')
    return tuple(p for p in board.alive if p!=actor)


class FixedGuardNight:
    """Common-flow physical policy; never use as a forecast selection law."""
    terminal_preflight_safe=False

    def __init__(self,rules):
        self.rules=rules

    def acquire(self,board,intent):
        # The independent choice is already fixed; no attack argument is given.
        if not isinstance(intent,GuardIntent) or intent.night!=board.day:
            raise ValueError('Guard intent must belong to this night')
        if intent.target not in guard_targets(board,intent.actor,self.rules):
            raise ValueError('Living nonself guard target required')
        return intent

    def night_outcomes(self,frame,prepared=None):
        b=frame.board
        if b.phase!='night' or b.winner is not None or len(b.worlds)!=1:
            raise ValueError('Nonterminal complete-world night required')
        world=b.worlds[0]
        roles=tuple(actual_role(b,world,p) for p in range(1,b.player_count+1))
        if roles[frame.target-1]=='wolf' and not self.rules.allow_self_bite:
            raise ValueError('Game rules forbid attacking a wolf')
        effect=resolve_guard(roles,b.alive,frame.after,frame.target)
        history=b.history+tuple(PublicEvent(b.day,'night',d.player) for d in effect.deaths)
        child=replace_worlds(b,(world,),alive=effect.survivors,history=history,
                             phase='day',day=b.day+1)
        # No success notification or guard target enters the public Board.
        return (FlowOutcome(Fraction(1),child),)


def resolve_fixed_guard_night(board,intent,attack,rules=Rules()):
    """Resolve one known world; shared order obtains intent before casualties.

    This returns a Board transition, not a posterior of a public observation.
    It does not select future actions or publish the guardian's private intent.
    """
    if type(attack) is not int or attack not in board.alive:
        raise ValueError('Living attack target required')
    return resolve_action(board,intent,attack,FixedGuardNight(rules))[1]
