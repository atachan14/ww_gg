"""Public-only model A facade. No viewer or secrets enter its inputs.

Night row interventions preserve the existing live-count prior. Subsequent
actions and public belief updates follow the information-set model.
"""
from fractions import Fraction as F
from .exact import replace_worlds, forced_action_worlds, legal_targets
from .action_flow import resolve_action
from .seer_acquisition import normalize
from .seer_future_uniform import FuturePending
from .public_prior import public_history_key, prepare_public_prior
from .information_set_forecast import InformationSetForecast, Pending
from .belief_projection import project_private
from .evaluation_projection import project_evaluation
from .calculation_budget import calculation_budget, tick, CalculationBudgetExceeded
from .forecast_result import Forecast
from .actor_information import wolf_information_groups
from .evaluation_branch import ActionInputs,physical_board
from .by_dawn import HorizonValues
from dataclasses import replace
from functools import lru_cache
import json


def horizon_for_action(engine,board,state,past,target,private=None,*,observer=None):
    """One execution and one roster-informed night, or the current night only.

    Select bites using FINAL continuation values, then count only terminal mass
    through dawn. Generated reports cannot themselves change the winner rule.
    """
    private=state if private is None else private
    physical=physical_board(board,private)
    acquired,outcomes=resolve_action(board,ActionInputs(state,past,private,observer,physical),target,engine.action_policy)
    village=wolf=F()
    for o in outcomes:
        tick(len(private.hypotheses))
        if o.board.winner:
            v=F(o.board.winner=='village');w=F(o.board.winner=='wolf')
        elif board.phase=='night':v=w=F()
        else:
            continuation=engine.action_policy.project(board,acquired,o,target)
            child,public,past,own,_=continuation;v=w=F()
            for info,mass,group in wolf_information_groups(own):
                physical_next=physical_board(child,group,continuation.physical)
                for bite,q in engine.wolf_policy(child,public,past,info.initial_roster,info.attacks):
                    _,night_outcomes=resolve_action(child,ActionInputs(public,past,group,observer,physical_next),bite,engine.action_policy)
                    for final in night_outcomes:
                        v+=mass*q*final.probability*F(final.board.winner=='village')
                        w+=mass*q*final.probability*F(final.board.winner=='wolf')
        village+=o.probability*v;wolf+=o.probability*w
    return HorizonValues(village,wolf)


def public_forecast(board,state,past,rules,strategy,*,max_work=250000,max_seconds=20):
    """Public overview, target rows and horizon under the approved intervention."""
    if state.public_roles!=tuple(sorted(board.worlds)):
        raise ValueError('Public acquisition prior must match public Board')
    from .guard_history_prior import seed_history
    try:state=seed_history(board,state) if strategy.night=='max' and board.initial_hunter_count else state
    except ValueError:return FuturePending('guard_public_history_zero_support')
    board,state=project_evaluation(board,state,strategy)
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            engine=InformationSetForecast(rules,strategy,max_work=max_work)
            if engine.exchangeable(board):
                from .exchangeable_public import exchangeable_forecast
                return exchangeable_forecast(board,strategy)
            value=engine.scalar(board,state,past)
            targets=legal_targets(board,rules,strategy)
            own={t:project_private(state,replace_worlds(board,forced_action_worlds(board,t,rules,strategy)))
                 if board.phase=='night' else state for t in targets}
            actions=tuple((t,engine.act(board,state,past,t,own[t],None)) for t in targets)
            horizon=tuple((t,horizon_for_action(engine,board,state,past,t,own[t])) for t in targets)
            return Forecast(value,actions,horizon)
    except CalculationBudgetExceeded:return FuturePending('information_set_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)


@lru_cache(maxsize=16)
def _complete_public_snapshot(history_key,board,rules,strategy,max_work,max_seconds):
    result=_evaluate_public_game(json.loads(history_key),board,rules,strategy,
                                 max_work=max_work,max_seconds=max_seconds)
    if isinstance(result,FuturePending):raise Pending(result.reason)
    return result


def clear_public_cache():_complete_public_snapshot.cache_clear()
def public_cache_info():return _complete_public_snapshot.cache_info()


def evaluate_public_game(game,board,rules,strategy,*,max_work=250000,max_seconds=20):
    try:
        return _complete_public_snapshot(public_history_key(game),board,rules,strategy,max_work,max_seconds)
    except Pending as error:return FuturePending(error.reason)


def _evaluate_public_game(game,board,rules,strategy,*,max_work,max_seconds):
    if board.winner:return Forecast(F(board.winner=='village'),())
    from .root_secret_flow import root_screen_eligible,root_screen_forecast
    if root_screen_eligible(board,rules,strategy):
        return root_screen_forecast(board,rules,strategy,max_work=max_work,max_seconds=max_seconds)
    from .root_secret_flow import root_replay_eligible,replay_root_secrets,root_branch_forecast
    if root_replay_eligible(game,board,rules,strategy):
        branch=replay_root_secrets(game,board,rules,strategy,max_work=max_work,max_seconds=max_seconds)
        if isinstance(branch,FuturePending):return branch
        return root_branch_forecast(branch,rules,strategy,max_work=max_work,max_seconds=max_seconds)
    from .guard_model import scope_reason
    from .guard_history_prior import role_exchangeable
    reason=scope_reason(board,rules,strategy,board.guard_prior_roster is not None)
    if reason:return FuturePending(reason)
    if InformationSetForecast(rules,strategy).exchangeable(board):
        from .exchangeable_public import exchangeable_forecast
        try:
            with calculation_budget(max_work,max_seconds=max_seconds):
                return exchangeable_forecast(board,strategy)
        except CalculationBudgetExceeded:return FuturePending('information_set_budget_exceeded')
    prepared=prepare_public_prior(game,board,rules,
        track_live_seers=strategy.disclosure_for('seer')=='all',max_work=max_work)
    if isinstance(prepared,FuturePending):return prepared
    state,past=prepared
    return public_forecast(board,state,past,rules,strategy,max_work=max_work,max_seconds=max_seconds)
