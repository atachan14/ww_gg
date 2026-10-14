"""Latent public history law for the closed, symmetric five-player guard game.

The first informative bite is a uniform max tie by permutation symmetry.
Normalize its histories within each role world: Model A role priors stay owned
by the public Board. No actual viewer history chooses this mixture.
"""
from fractions import Fraction as F
from .night_knowledge import merge_night_records


def hero_deducible(board):
    """Every possible initial wolf roster entails one guardian placement."""
    groups={}
    for world in board.worlds:groups.setdefault(world[0],set()).add(world[3])
    return bool(groups) and all(len(heroes)==1 for heroes in groups.values())


def role_exchangeable(board):
    if board.initial_medium_count or board.initial_seer_count:return False
    counts={w[0].bit_count() for w in board.worlds}
    if len(counts)!=1 or min(counts)<1:return False
    if set(board.wolf_count_distribution)!={1} and not (len(board.alive)==5 and board.phase=='day' and set(board.wolf_count_distribution)<={1,2}):return False
    masses={w[:-1]:w[-1] for w in board.worlds}
    for x,y in zip(board.alive,board.alive[1:]):
        a=1<<(x-1);b=1<<(y-1)
        def swap(mask):return mask^(a|b) if bool(mask&a)!=bool(mask&b) else mask
        if any(masses.get(tuple(swap(m) for m in roles))!=q for roles,q in masses.items()):return False
    return True


def seed_history(board,state):
    if hero_deducible(board):
        # Deduction makes these records redundant for choosing the next bite,
        # not disposable. The same ledger belongs to the public mixture and
        # both owner projections, including already supplied private records.
        return state
    if board.initial_medium_count or board.initial_seer_count:return state
    if len({w[3] for w in board.worlds})==1:return state
    nights=[night for night in range(1,board.day) if not any(e.phase=='night' and e.day==night for e in board.history)]
    if not nights:return state
    # Keep an existing joint ledger, including several nights. Missing records
    # are a scope/support issue, never a reason to erase known owner actions.
    if any(h.guards or h.attacks for h in state.hypotheses):return state
    if len(nights)>1:return state
    # Only the four-alive success leaves another nonterminal wolf decision.
    if board.guard_prior_roster is None:return state
    night,alive=board.guard_prior_roster
    if night!=nights[0] or len(alive)!=4:return state
    return extend_success(state,night,alive)


def public_history_ready(board,state):
    """Every public hypothesis represents all past unobserved bite nights."""
    missing={night for night in range(1,board.day)
             if not any(e.phase=='night' and e.day==night for e in board.history)}
    return bool(missing) and all(missing<={a.night for a in h.attacks}
                                 for h in state.hypotheses)


def extend_success(state,night,alive):
    # This existing entry point is restricted by its caller's first-night max
    # tie proof. It supplies that proven kernel; it is not a zero-support fill.
    from .guard_history_mixture import enumerate_guard_history_mixture
    from .seer_future_uniform import FuturePending
    policies={}
    for h in state.hypotheses:
        targets=tuple(p for p in alive if not h.roles[0]&(1<<(p-1)))
        if not targets:raise ValueError('Public role world has zero compatible private history support')
        policies[(h.roles[0],h.attacks)]=tuple((p,F(1,len(targets))) for p in targets)
    mixture=enumerate_guard_history_mixture(state,state.public_roles,night,alive,policies)
    if isinstance(mixture.public,FuturePending):
        raise ValueError('Public role world has zero compatible private history support')
    return mixture.public


def matches(records,known):
    supplied={r.night:r.target for r in known}
    return all(supplied.get(r.night)==r.target for r in records)


def guard_matches(records,known):
    recorded={r.night:r for r in records}
    return all(r.night not in recorded or recorded[r.night]==r for r in known)


def merge_guards(records,known):
    return merge_night_records(records,known)
