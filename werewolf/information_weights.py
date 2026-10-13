"""Transfer public report likelihoods to a separate observer measure.

This is chance weighting only, never an actor policy or public belief update.
"""
from dataclasses import replace
from fractions import Fraction as F
from .seer_acquisition import Hypothesis, normalize


def observer_report_weights(source, private, branches, *, incomplete):
    public={(h.roles,h.acquisitions):h.mass for h in source.hypotheses}
    own={(h.roles,h.acquisitions):h.mass for h in private.hypotheses}
    result=[]
    for q,b,state,past in branches:
        entries=tuple(Hypothesis(h.roles,h.acquisitions,
                      q*h.mass*own[(h.roles,h.acquisitions)]/public[(h.roles,h.acquisitions)])
                      for h in state.hypotheses if (h.roles,h.acquisitions) in own)
        mass=sum((h.mass for h in entries),F())
        if mass:
            result.append((mass,b,state,past,replace(state,hypotheses=normalize(entries))))
    if sum((q for q,*_ in result),F())!=1:
        raise incomplete()
    return result
