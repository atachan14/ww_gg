"""Reweight joint acquisitions onto an updated role prior without changing owners."""
from .seer_acquisition import Hypothesis, normalize
from .seer_future_uniform import TrueScanState


def project_private(state,board,*,marginalize_private=False):
    old=dict((r[:-1],r[-1]) for r in state.public_roles)
    new=dict((r[:-1],r[-1]) for r in board.worlds)
    tracked=tuple(p for p in board.alive if board.claims[p-1]=='seer' and (state.tracked is None or p in state.tracked)) if marginalize_private else state.tracked
    entries=tuple(Hypothesis(h.roles,tuple(a for a in h.acquisitions if not marginalize_private or a.player in tracked),h.mass*new[h.roles]/old[h.roles]) for h in state.hypotheses if h.roles in new)
    return TrueScanState(normalize(entries),state.rosters,state.initial_rule,tracked,state.observed_prefix)

