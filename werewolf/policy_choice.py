"""Select exact score ties; candidates and information laws belong to callers."""
from fractions import Fraction as F


def optimal_targets(scores,*,maximize):
    scores=tuple(scores)
    if not scores:raise ValueError('Complete nonempty candidate scores required')
    best=(max if maximize else min)(v for _,v in scores)
    return tuple(target for target,value in scores if value==best)


def uniform_policy(targets):
    targets=tuple(targets)
    if not targets:raise ValueError('Nonempty legal targets required')
    return tuple((target,F(1,len(targets))) for target in targets)
