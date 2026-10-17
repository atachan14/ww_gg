"""Reweight joint acquisitions onto an updated role prior without changing owners."""
from .seer_acquisition import Hypothesis, Acquisition, normalize
from dataclasses import fields
from functools import lru_cache
from .seer_future_uniform import TrueScanState
from .exact import _immutable_complete_roles


@lru_cache(maxsize=1)
def _identity_schema():
    # Static type metadata only; no world, observer or posterior is retained.
    from .guard_effect import GuardIntent
    from .night_knowledge import WolfAttack
    expected=((TrueScanState,('hypotheses','rosters','initial_rule','tracked','observed_prefix')),
              (Hypothesis,('roles','acquisitions','mass','guards','attacks')),
              (Acquisition,('day','player','target','color')),
              (GuardIntent,('night','actor','target')),(WolfAttack,('night','target')))
    return all(tuple(f.name for f in fields(kind))==names for kind,names in expected),GuardIntent,WolfAttack


def _normalized_immutable_state(state):
    """Prove the existing normalize() would preserve every complete hypothesis.

    Strict ordered full keys exclude duplicates and noncanonical ordering.
    All metadata must be immutable; existing constructor validation then
    remains valid. Unknown/subclass inputs keep the original rebuild path.
    """
    from fractions import Fraction
    known,GuardIntent,WolfAttack=_identity_schema()
    if (not known or type(state)is not TrueScanState or type(state.hypotheses)is not tuple or not state.hypotheses or
            type(state.rosters)is not tuple or type(state.initial_rule)is not str or
            type(state.observed_prefix)is not int or
            any(type(r)is not tuple or any(type(p)is not int for p in r) for r in state.rosters) or
            state.tracked is not None and (type(state.tracked)is not tuple or any(type(p)is not int for p in state.tracked))):
        return False
    previous=None
    for h in state.hypotheses:
        if (type(h)is not Hypothesis or type(h.roles)is not tuple or type(h.mass)is not Fraction or
                type(h.acquisitions)is not tuple or type(h.guards)is not tuple or type(h.attacks)is not tuple or
                any(type(a)is not Acquisition or type(a.color)is not str for a in h.acquisitions) or
                any(type(g)is not GuardIntent for g in h.guards) or any(type(a)is not WolfAttack for a in h.attacks)):
            return False
        key=(h.roles,h.acquisitions,h.guards,h.attacks)
        if previous is not None and not previous<key:return False
        previous=key
    return True


def project_private(state,board,*,marginalize_private=False):
    old=dict((r[:-1],r[-1]) for r in state.public_roles)
    worlds=board.worlds
    new=dict((r[:-1],r[-1]) for r in worlds)
    if (not marginalize_private and old==new and _immutable_complete_roles(worlds) and
            _normalized_immutable_state(state)):return state
    tracked=tuple(p for p in board.alive if board.claims[p-1]=='seer' and (state.tracked is None or p in state.tracked)) if marginalize_private else state.tracked
    entries=tuple(Hypothesis(h.roles,tuple(a for a in h.acquisitions if not marginalize_private or a.player in tracked),h.mass*new[h.roles]/old[h.roles],h.guards,h.attacks) for h in state.hypotheses if h.roles in new)
    return TrueScanState(normalize(entries),state.rosters,state.initial_rule,tracked,state.observed_prefix)

