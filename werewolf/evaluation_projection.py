"""Marginalize roles with no future effects in the current fixed-CO model.

Only solver inputs are projected; rendered/replayed Boards stay unchanged.
Wolf identities and living medium-CO truth bits retain their joint weights.
Latent medium locations, ability-free hunters and nonpublishing seers cannot
affect future actions/reports. A representative valid medium mask preserves
Board count invariants without treating its latent positions as new evidence.
"""
from dataclasses import replace
from fractions import Fraction as F
from .seer_acquisition import from_board, Hypothesis
from .seer_future_uniform import TrueScanState


def project_evaluation(board,state,strategy):
    if strategy.disclosure_for('seer')=='all' and any(board.claims[p-1]=='seer' for p in board.alive):
        return project_fixed_co_roles(board,state)
    return project_without_future_seers(board,state)


def project_without_future_seers(board,state):
    relevant=sum(1<<(p-1) for p in board.alive if board.claims[p-1]=='medium')
    groups={}
    for wolf,medium,seer,hunter,mass in board.worlds:
        key=(wolf,medium&relevant)
        representative,q=groups.get(key,(medium,F()))
        groups[key]=(min(representative,medium),q+mass)
    projected=replace(board,belief=(),wolf_count=None,initial_seer_count=0,initial_hunter_count=0,
                      world_belief=(),role_belief=tuple((w,m,q) for (w,_),(m,q) in sorted(groups.items())))
    joint=TrueScanState(from_board(projected),state.rosters,state.initial_rule,tracked=(),
                        observed_prefix=state.observed_prefix)
    return projected,joint


def project_fixed_co_roles(board,state):
    """Fixed CO: retain wolves, publishing role truth and their acquisitions.

    Medium/seer locations outside living COs and ability-free hunter locations
    have no future public effect. Registered guard effects must disable this
    reduction; the current model has no hunter actions or private guard ledger.
    Keep a valid original joint placement, not independently invented masks.
    Public probabilities and observer ledgers stay on their original Boards.
    """
    relevant=sum(1<<(p-1) for p in board.alive if board.claims[p-1]=='medium')
    seers=tuple(p for p in board.alive if board.claims[p-1]=='seer' and
                (state.tracked is None or p in state.tracked))
    seer_truth=sum(1<<(p-1) for p in board.alive if board.claims[p-1]=='seer')
    groups={}
    for w,m,s,h,q in board.worlds:
        key=(w,m&relevant,s&seer_truth)
        representative,mass=groups.get(key,((w,m,s,h),F()))
        groups[key]=(min(representative,(w,m,s,h)),mass+q)
    roles={key:r for key,(r,_) in groups.items()}
    from .exact import replace_worlds
    projected=replace_worlds(board,tuple((*roles[key],q) for key,(_,q) in sorted(groups.items())),wolf_count=None)
    hypotheses={}
    for hypothesis in state.hypotheses:
        w,m,s,h=hypothesis.roles
        key=(roles[w,m&relevant,s&seer_truth],
             tuple(a for a in hypothesis.acquisitions if a.player in seers))
        hypotheses[key]=hypotheses.get(key,F())+hypothesis.mass
    joint=replace(state,tracked=seers,hypotheses=tuple(Hypothesis(r,a,q) for (r,a),q in sorted(hypotheses.items())))
    return projected,joint


def project_retired_seers(board,state,private):
    """Solver-only retirement when publishing seers no longer convey information.

    Historical scan correlations remain in the current role/medium truth law.
    The caller must exclude scan observers; their acquisitions cannot retire.
    """
    projected,joint=project_without_future_seers(board,state)
    relevant=sum(1<<(p-1) for p in board.alive if board.claims[p-1]=='medium')
    lookup={(w,m&relevant):(w,m,s,h) for w,m,s,h,_ in projected.worlds}
    groups={}
    for hypothesis in private.hypotheses:
        w,m,_,_=hypothesis.roles
        roles=lookup[w,m&relevant]
        groups[roles]=groups.get(roles,F())+hypothesis.mass
    own=replace(joint,hypotheses=tuple(Hypothesis(roles,(),q) for roles,q in sorted(groups.items())))
    return projected,joint,own
