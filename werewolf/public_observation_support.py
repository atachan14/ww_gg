"""Condition generated PUBLIC support without Bayesian role reweighting.

Callers enumerate the complete public joint law and every configured actor
kernel before entering. An owner-conditioned law or action intervention is not
an input to this public observation operation. Physical mass stays separate.
"""
from dataclasses import replace
from fractions import Fraction as F
from .exact import replace_worlds
from .seer_acquisition import normalize


def condition_generated_support(board,source,entries):
    totals={}
    for h in entries:totals[h.roles]=totals.get(h.roles,F())+h.mass
    kept=tuple(w for w in board.worlds if totals.get(w[:-1],F())>0)
    mass=sum((w[-1] for w in kept),F())
    if not mass:raise ValueError('public_generated_observation_zero_support')
    public=replace_worlds(board,tuple((*w[:-1],w[-1]/mass) for w in kept),wolf_count=None)
    weights={w[:-1]:w[-1] for w in public.worlds}
    joint=replace(source,hypotheses=normalize(tuple(replace(h,
        mass=weights[h.roles]*h.mass/totals[h.roles]) for h in entries if h.roles in weights)))
    if joint.public_roles!=tuple(sorted(public.worlds)):
        raise ValueError('Generated public law and role prior disagree')
    return public,joint
