"""Force the viewer's next scan inside an unchanged public acquisition law.

Supported targets are the existing unvisited/uniform generator's common support.
Its target probability is constant across viewer-compatible hypotheses; dividing
out that constant conditions an intervention, without reweighting the role prior.
Public decisions see the full prior, including every possible target and fake CO.
"""
from .calculation_budget import DEFAULT_MAX_WORK, DEFAULT_MAX_SECONDS
from fractions import Fraction as F
from .seer_future_uniform import FuturePending, candidates, scan_target_players
from .information_set_forecast import InformationSetForecast, Pending
from .seer_intervention import scan_intervention_matches
from .calculation_budget import calculation_budget, tick, CalculationBudgetExceeded


def seer_forecast(public, player, acquisitions, rules, strategy, *, scan_state, past=(),
                  max_work=DEFAULT_MAX_WORK, max_seconds=DEFAULT_MAX_SECONDS, trace=None):
    acquisitions=tuple(acquisitions)
    if strategy.disclosure_for('seer') != 'all':
        return FuturePending('seer_view_unpublished_own_action_unimplemented')
    if public.claims[player-1] != 'seer' or (scan_state.tracked is not None and player not in scan_state.tracked):
        return FuturePending('seer_view_latent_future_co_unimplemented')
    def compatible(h):
        return bool(h.roles[2] & (1 << (player-1))) and all(a in h.acquisitions for a in acquisitions)
    supported = tuple(h for h in scan_state.hypotheses if compatible(h))
    if not supported:
        raise ValueError('秘密の取得履歴と公開の真結果が両立しません。')
    histories = {tuple(a for a in h.acquisitions if a.player == player) for h in supported}
    if len(histories) != 1:
        return FuturePending('seer_view_past_private_history_unresolved')
    choices = {candidates(h, player, scan_target_players(scan_state,range(1,public.player_count+1))) for h in supported}
    if len(choices) != 1:
        return FuturePending('seer_view_target_generation_support_unresolved')
    targets = next(iter(choices)); day = public.day + 1; values = []
    engine=InformationSetForecast(rules,strategy,max_work=max_work,trace=trace)
    try:
        with calculation_budget(max_work, max_seconds=max_seconds):
            for target in targets:
                tick()
                def observer(h, state, target=target):
                    return compatible(h) and scan_intervention_matches(h,state,player,day,target)
                # Keep the existing per-target work limit and shared outer time
                # deadline; reuse PUBLIC rankings across private interventions.
                try:
                    with calculation_budget(max_work,max_seconds=max_seconds):
                        value=engine.evaluate(public,scan_state,past,observer=observer)
                except CalculationBudgetExceeded:
                    return FuturePending('information_set_budget_exceeded')
                values.append((target, value))
    except CalculationBudgetExceeded:
        return FuturePending('seer_view_continuation_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)
    return tuple(values)
