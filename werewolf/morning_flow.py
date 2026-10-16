"""Morning branch plumbing, without selecting strategic report instructions.

Policies own projection and publication laws. Continuations own information
sets; this module only composes chance weights and dispatches each branch.
"""
from fractions import Fraction as F


def report_flow(outcomes, source, past, policy, *, source_board=None, fake_colors=None):
    """Lazily project a report outcome, publish, then expose its next state.

    Laziness preserves the legacy ordering of generation/budget checks versus
    recursive evaluation. No observer state is supplied to publication policy.
    """
    for outcome in outcomes:
        state = policy.project(source, outcome.board)
        if source_board is not None:
            from .board_future import record_medium_instruction
            record_medium_instruction(policy,source_board,source,past,outcome,fake_colors,law=state)
        for probability, board, joint, reports in policy.publications(outcome.board, state, past):
            yield outcome.probability * probability, board, joint, reports


def continuation_value(branches, evaluate):
    """Use the caller's branch measure; never infer a new policy from weights."""
    return sum((probability * evaluate(*payload)
                for probability, *payload in branches), F())
