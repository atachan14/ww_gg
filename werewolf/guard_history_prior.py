"""Latent public history law for the closed, symmetric five-player guard game.

The first informative bite is a uniform max tie by permutation symmetry.
Normalize its histories within each role world: Model A role priors stay owned
by the public Board. No actual viewer history chooses this mixture.
"""
from dataclasses import replace
from fractions import Fraction as F
from .seer_acquisition import normalize
from .guard_effect import GuardIntent
from .night_knowledge import WolfAttack
from .phase_updates import acquisition_roster


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
    if board.initial_medium_count or board.initial_seer_count:return state
    if len({w[3] for w in board.worlds})==1:return state
    nights=[night for night in range(1,board.day) if not any(e.phase=='night' and e.day==night for e in board.history)]
    if not nights:return state
    if len(nights)>1:
        return replace(state,hypotheses=normalize(tuple(replace(h,guards=(),attacks=()) for h in state.hypotheses)))
    if any(h.attacks for h in state.hypotheses):return state
    # Only the four-alive success leaves another nonterminal wolf decision.
    if board.guard_prior_roster is None:return state
    night,alive=board.guard_prior_roster
    if night!=nights[0] or len(alive)!=4:return state
    return extend_success(state,night,alive)


def extend_success(state,night,alive):
    entries=[]
    for h in state.hypotheses:
        actor=next((p for p in alive if h.roles[3]&(1<<(p-1))),None)
        targets=tuple(p for p in alive if not (h.roles[0]|h.roles[3])&(1<<(p-1)))
        if actor is None or not targets:
            raise ValueError('Public role world has zero compatible private history support')
        for target in targets:
            entries.append(replace(h,mass=h.mass/F(len(targets)),
                                   guards=h.guards+(GuardIntent(night,actor,target),),
                                   attacks=h.attacks+(WolfAttack(night,target),)))
    return replace(state,hypotheses=normalize(entries))


def matches(records,known):
    supplied={r.night:r.target for r in known}
    return all(supplied.get(r.night)==r.target for r in records)


def guard_matches(records,known):
    recorded={r.night:r for r in records}
    return all(r.night not in recorded or recorded[r.night]==r for r in known)


def merge_guards(records,known):
    merged={r.night:r for r in records};merged.update({r.night:r for r in known})
    return tuple(merged[night] for night in sorted(merged))
