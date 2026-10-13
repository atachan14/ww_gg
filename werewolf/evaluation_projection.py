"""Marginalize roles with no future effects in the current fixed-CO model.

Only solver inputs are projected; rendered/replayed Boards stay unchanged.
Wolf identities and living medium-CO truth bits retain their joint weights.
Latent medium locations, ability-free hunters and nonpublishing seers cannot
affect future actions/reports. A representative valid medium mask preserves
Board count invariants without treating its latent positions as new evidence.
"""
from dataclasses import replace
from fractions import Fraction as F
from .seer_acquisition import from_board
from .seer_future_uniform import TrueScanState


def project_evaluation(board,state,strategy):
    if strategy.disclosure_for('seer')=='all' and any(board.claims[p-1]=='seer' for p in board.alive):
        return board,state
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
