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
            hook=getattr(policy,'record_group_publication',None)
            if hook is not None:hook(source_board,source,past,outcome.board,state,past,'medium')
            from .board_future import record_medium_instruction
            record_medium_instruction(policy,source_board,source,past,outcome,fake_colors,law=state)
        publications=policy.publications(outcome.board,state,past)
        component=getattr(policy,'record_report_component',None)
        if component is not None and source_board is not None:component(source_board,source,past,outcome,state,publications)
        for probability, board, joint, reports in publications:
            yield outcome.probability * probability, board, joint, reports


def continuation_value(branches, evaluate):
    """Use the caller's branch measure; never infer a new policy from weights."""
    return sum((probability * evaluate(*payload)
                for probability, *payload in branches), F())
