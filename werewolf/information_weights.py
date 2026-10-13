"""Transfer public report likelihoods to a separate observer measure.

This is chance weighting only, never an actor policy or public belief update.
"""
from dataclasses import replace
from fractions import Fraction as F
from .seer_acquisition import Hypothesis, normalize


def observer_report_weights(source, private, branches, *, incomplete):
    public={}
    for h in source.hypotheses:
        key=(h.roles,h.acquisitions);public[key]=public.get(key,F())+h.mass
    own={}
    for h in private.hypotheses:own.setdefault((h.roles,h.acquisitions),[]).append(h)
    result=[]
    for q,b,state,past in branches:
        entries=tuple(Hypothesis(h.roles,h.acquisitions,
                      q*h.mass*personal.mass/public[(h.roles,h.acquisitions)],personal.guards,personal.attacks)
                      for h in state.hypotheses if (h.roles,h.acquisitions) in own
                      for personal in own[h.roles,h.acquisitions])
        mass=sum((h.mass for h in entries),F())
        if mass:
            result.append((mass,b,state,past,replace(state,hypotheses=normalize(entries))))
    if sum((q for q,*_ in result),F())!=1:
        raise incomplete()
    return result
