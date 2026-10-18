"""Approved single-reporter future marginal law; joint correlation unselected."""
from fractions import Fraction as F
from .seer_acquisition import SeerReport
from .seer_future_uniform import FuturePending,validate_roster


def fake_uniform_options(alive,player,past):
    """Own PUBLIC unreported legal targets first (including corpses); target and color uniform.

    This is for a future-night report, not a rule for initial declarations.
    It deliberately does not inspect teammate identities or private scans.
    When every legal target was reported, revisit all legal targets uniformly;
    white/black remain the approved uniform colors, even for a revisited target.
    """
    validate_roster(alive)
    if type(player)is not int or player not in alive:raise ValueError('Living fake reporter required')
    if not isinstance(past,tuple) or any(not isinstance(r,SeerReport) for r in past):raise ValueError('Own public report history required')
    legal=tuple(sorted(p for p in alive if p!=player))
    seen={r.target for r in past if r.player==player}
    preferred=tuple(p for p in legal if p not in seen)
    targets=preferred or legal
    if not targets:return FuturePending('no_legal_fake_report_target')
    return tuple(((target,color),F(1,2*len(targets))) for target in targets for color in ('white','black'))


def fake_joint_options(alive,reporters,past):
    """Only zero/one reporter can be combined without a joint-law decision."""
    if not isinstance(reporters,tuple) or len(set(reporters))!=len(reporters):raise ValueError('Distinct fake reporters required')
    if len(reporters)>1:return FuturePending('multiple_fake_report_correlation_unselected')
    if not reporters:return (((),F(1)),)
    options=fake_uniform_options(alive,reporters[0],past)
    if isinstance(options,FuturePending):return options
    return tuple((((reporters[0],target,color),),q) for (target,color),q in options)
