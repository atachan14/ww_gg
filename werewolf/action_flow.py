"""One action's phase order; information and strategy laws stay in policies.

Selection is already complete when this function is entered. The policy owns
the public/physical distribution distinction and morning strategic reports.
Only this flow decides when to acquire, stop at a winner, project after death,
and dispatch morning versus ordinary continuation.
"""
from dataclasses import dataclass
from fractions import Fraction as F


@dataclass(frozen=True)
class FlowOutcome:
    probability: F
    board: object
    context: object = None


@dataclass(frozen=True)
class NightFrame:
    """Fixed action, original roster, and separately prepared ability payload.

    The payload belongs to its information policy; the common flow cannot use
    private evidence to change actor choice. A resolver may inspect after only
    for physical effects specified by an approved ability law.
    """
    board: object
    target: int
    before: object
    after: object
    terminal_payoffs: bool = False


def unchanged_death_outcomes(frame, resolve, prepared=None):
    """Current scans do not affect casualties; reuse a safe preflight if any."""
    return prepared if prepared is not None else resolve(frame.board, frame.after, frame.target)


def resolve_action(board,state,target,policy,*,terminal_payoffs=False):
    """Shared physical resolution; full observation contexts by default.

    Scalar/horizon callers may stop terminal payoffs before public belief
    generation. Those terminal outcomes need no continuation context. History
    callers keep the default and validate every retained public/secret law.
    """
    night = board.phase == 'night'
    acquired = state
    if night:
        prepared = policy.outcomes(board,state,target) if policy.terminal_preflight_safe else None
        if prepared is None or any(o.board.winner is None for o in prepared):
            acquired = policy.acquire(board,state)
        outcomes = policy.night_outcomes(NightFrame(board,target,state,acquired,terminal_payoffs),prepared)
    else:
        outcomes = policy.outcomes(board,state,target)
    return acquired,outcomes


def action_flow(board, state, target, policy):
    """Policy hooks: acquire, outcomes, night_outcomes, project, continuations.

    Acquisition always receives the pre-casualty Board. Terminal branches never
    project or publish. Legacy skips acquisition for an entirely terminal action;
    Model A retains its eager acquisition/observer-support validation contract.
    A policy may preflight terminal death only when acquisition cannot change
    casualties. Future casualty-changing laws must disable terminal preflight.
    """
    acquired,outcomes=resolve_action(board,state,target,policy,terminal_payoffs=True)
    night=board.phase=='night'
    value = F()
    for outcome in outcomes:
        if outcome.board.winner is not None:
            continuation = F(outcome.board.winner == 'village')
        else:
            projected = policy.project(board, acquired, outcome, target)
            continuation = (policy.morning_value(projected) if night
                            else policy.day_value(projected))
        value += outcome.probability * continuation
    return value
