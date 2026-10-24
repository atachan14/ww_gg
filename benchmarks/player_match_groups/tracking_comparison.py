"""Development-only comparison for complete tracking under fixed role worlds.

Research candidate ONLY for the single-possible-owner cases studied here.
It is not imported by production or the existing broad fixtures. The proof
covers the bounded evidence tests, not general cold-source equivalence.
Partial tracking and all multi-owner contexts remain untouched.
"""
from dataclasses import replace
from werewolf.seer_acquisition import Hypothesis
from werewolf.seer_future_uniform import TrueScanState

def complete_tracking(law):
    if type(law)is not TrueScanState or law.tracked is None:return law
    if any(type(h)is not Hypothesis or type(h.roles)is not tuple for h in law.hypotheses):return law
    owners={p for h in law.hypotheses for p in range(1,h.roles[2].bit_length()+1) if h.roles[2]&(1<<(p-1))}
    return replace(law,tracked=None) if len(owners)==1 and set(law.tracked)==owners else law

def comparison_source(source):
    return replace(source,public_state=complete_tracking(source.public_state),private=complete_tracking(source.private))
