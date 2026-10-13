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


def action_flow(board, state, target, policy):
    """Policy hooks: acquire, outcomes, project, morning_value, day_value.

    Acquisition always receives the pre-casualty Board. Terminal branches never
    project or publish. Legacy skips acquisition for an entirely terminal action;
    Model A retains its eager acquisition/observer-support validation contract.
    This flag affects work/validation, not the terminal payoff.
    """
    night = board.phase == 'night'
    acquired = state
    ready = False
    if night and policy.acquire_terminal:
        acquired = policy.acquire(board, state)
        ready = True
    value = F()
    for outcome in policy.outcomes(board, state, target):
        if outcome.board.winner is not None:
            continuation = F(outcome.board.winner == 'village')
        else:
            if night and not ready:
                acquired = policy.acquire(board, state)
                ready = True
            projected = policy.project(board, acquired, outcome, target)
            continuation = (policy.morning_value(projected) if night
                            else policy.day_value(projected))
        value += outcome.probability * continuation
    return value
