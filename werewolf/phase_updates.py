"""Shared phase facts, independent of action selection or viewer information.

An observed corpse conditions public support globally. A forced wolf action
still uses exact.action_outcomes' separate chosen-action law.
"""
from dataclasses import replace
from fractions import Fraction
from .exact import replace_worlds, action_outcomes


def acquisition_roster(player_count, history, day):
    """Slot1 is initial; slot N is before night N-1 casualties."""
    dead = {e.target for e in history
            if e.day < day-1 or e.day == day-1 and e.phase == 'day'}
    return tuple(p for p in range(1, player_count+1) if p not in dead)


def acquisition_rosters(board):
    return tuple(acquisition_roster(board.player_count, board.history, day)
                 for day in range(1, board.day+1))


def condition_night_corpse(board, target, rules,*,guard_state=None):
    """Compatibility only: never multiply by a wolf policy likelihood."""
    if board.initial_hunter_count==1:
        from .guard_model import condition_guard_observation
        return condition_guard_observation(board,(target,),rules,state=guard_state)
    worlds = tuple(w for w in board.worlds
                   if rules.allow_self_bite or not w[0] & (1 << (target-1)))
    mass = sum((w[-1] for w in worlds), Fraction())
    if not mass:
        raise ValueError('Night corpse has no compatible public hypothesis')
    return replace_worlds(board, tuple((*w[:-1], w[-1]/mass) for w in worlds))


def observed_night_strategy(rules, strategy):
    return replace(strategy, include_self_bite=rules.allow_self_bite)


def night_observation_outcomes(board, target, rules, strategy,*,guard_state=None):
    return action_outcomes(condition_night_corpse(board, target, rules,guard_state=guard_state), target,
                           rules, observed_night_strategy(rules, strategy))
