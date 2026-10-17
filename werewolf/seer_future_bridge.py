"""Manual observed prior -> future fixed-CO continuation; never alter hand likelihood."""
from .calculation_budget import DEFAULT_MAX_WORK, DEFAULT_MAX_SECONDS
from .seer_future_forecast import forecast
from .seer_future_uniform import FuturePending
from .calculation_budget import calculation_budget, CalculationBudgetExceeded
from .public_observed_prior import prepare_game


def evaluate_game(g,board,rules,strategy,*,max_work=DEFAULT_MAX_WORK):
    if strategy.disclosure_for('seer')=='none':
        # No future acquisition/use/publication: retain already observed evidence.
        from .exact import build_tree,evaluate_tree,legal_targets
        from .seer_future_forecast import Forecast
        try:
            with calculation_budget(max_work):
                root=build_tree(board,rules,strategy);evaluation=evaluate_tree(root,strategy)
                return Forecast(evaluation.board_value(root).village_win,tuple((t,evaluation.action_value(root,t).village_win) for t in legal_targets(board,rules,strategy)))
        except CalculationBudgetExceeded:return FuturePending('future_public_continuation_budget_exceeded')
    prepared=prepare_game(g,board,max_work=max_work)
    if isinstance(prepared,FuturePending):return prepared
    state,past=prepared
    return forecast(board,state,past,rules,strategy,max_work=max_work)
