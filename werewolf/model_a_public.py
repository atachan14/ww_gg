"""Public-only model A facade. No viewer or secrets enter its inputs.

Night row interventions preserve the existing live-count prior. Subsequent
actions and public belief updates follow the information-set model.
"""
from .calculation_budget import DEFAULT_MAX_WORK, DEFAULT_MAX_SECONDS
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
    if observer is None and getattr(engine,'trace',None) is None:
        key=(board,engine.rules,engine.strategy,past,id(state),id(private),target)
        completed=getattr(engine,'uniform_action_horizons',{}).get(key)
        if completed is not None and completed[0] is state and completed[1] is private:
            tick();return HorizonValues(*completed[2])
    physical=physical_board(board,private)
    if board.phase=='night' and getattr(engine,'joint_guard_max',False) and board.initial_hunter_count:
        from .fixed_actor_continuation import physical_actor_outcomes
        acquired=engine.action_policy.acquire(board,ActionInputs(state,past,private,observer,physical))
        outcomes=physical_actor_outcomes(board,acquired.private,engine,target,acquire=False,observer=observer)
        return HorizonValues(sum((q*F(child.winner=='village') for q,child,joint in outcomes),F()),
                             sum((q*F(child.winner=='wolf') for q,child,joint in outcomes),F()))
    acquired,outcomes=resolve_action(board,ActionInputs(state,past,private,observer,physical),target,engine.action_policy,terminal_payoffs=True)
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
                    _,night_outcomes=resolve_action(child,ActionInputs(public,past,group,observer,physical_next),bite,engine.action_policy,terminal_payoffs=True)
                    for final in night_outcomes:
                        v+=mass*q*final.probability*F(final.board.winner=='village')
                        w+=mass*q*final.probability*F(final.board.winner=='wolf')
        village+=o.probability*v;wolf+=o.probability*w
    return HorizonValues(village,wolf)


def public_forecast(board,state,past,rules,strategy,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS,match_groups=False,match_view=None,match_audit=False,diagnostics=None):
    """Public overview, target rows and horizon under the approved intervention."""
    if state.public_roles!=tuple(sorted(board.worlds)):
        raise ValueError('Public acquisition prior must match public Board')
    from .guard_history_prior import seed_history
    try:state=seed_history(board,state) if strategy.night=='max' and board.initial_hunter_count else state
    except ValueError:return FuturePending('guard_public_history_zero_support')
    board,state=project_evaluation(board,state,strategy)
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            if match_groups or diagnostics is not None:
                from .match_groups import make_engine
                engine=make_engine(board,state,past,rules,strategy,enabled=match_groups,view=match_view,audit=match_audit,max_work=max_work)
            else:
                from .local_reuse import make_public_engine
                engine=make_public_engine(InformationSetForecast,board,state,past,rules,strategy,max_work=max_work)
            if engine.exchangeable(board):
                from .exchangeable_public import exchangeable_forecast
                return exchangeable_forecast(board,strategy)
            value=engine.scalar(board,state,past)
            targets=legal_targets(board,rules,strategy)
            own={t:project_private(state,replace_worlds(board,forced_action_worlds(board,t,rules,strategy)))
                 if board.phase=='night' else state for t in targets}
            actions=tuple((t,engine.act(board,state,past,t,own[t],None)) for t in targets)
            horizon=tuple((t,horizon_for_action(engine,board,state,past,t,own[t])) for t in targets)
            if diagnostics is not None:
                diagnostics.update(engine.stats,actual_action_expansions=engine.expansions['actions'],actual_value_expansions=engine.expansions['values'],audited_batches=len(engine.audits))
            return Forecast(value,actions,horizon)
    except CalculationBudgetExceeded:return FuturePending('information_set_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)


@lru_cache(maxsize=16)
def _complete_public_snapshot(history_key,board,rules,strategy,max_work,max_seconds,local_mode=False):
    from .local_reuse import reuse_scope
    with reuse_scope(local_mode):
        result=_evaluate_public_game(json.loads(history_key),board,rules,strategy,
                                     max_work=max_work,max_seconds=max_seconds)
    if isinstance(result,FuturePending):raise Pending(result.reason)
    return result


def clear_public_cache():_complete_public_snapshot.cache_clear()
def public_cache_info():return _complete_public_snapshot.cache_info()


def evaluate_public_game(game,board,rules,strategy,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS):
    from .local_reuse import enabled
    try:
        return _complete_public_snapshot(public_history_key(game),board,rules,strategy,max_work,max_seconds,enabled())
    except Pending as error:return FuturePending(error.reason)


def _evaluate_public_game(game,board,rules,strategy,*,max_work,max_seconds):
    from .board_roles import prepare_evaluation
    prepared=prepare_evaluation(game,board,rules,strategy,
                                max_work=max_work,max_seconds=max_seconds)
    return evaluate_prepared_public(prepared,board,rules,strategy,
                                    max_work=max_work,max_seconds=max_seconds)


def evaluate_prepared_public(prepared,board,rules,strategy,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS):
    """Stage 3b consumes 3a state; it does not prepare role evidence itself."""
    if board.winner:return Forecast(F(board.winner=='village'),())
    kind,value=prepared
    if kind=='pending' or isinstance(value,FuturePending):return value
    if kind=='root':
        from .root_secret_flow import root_branch_forecast
        return root_branch_forecast(value,rules,strategy,max_work=max_work,max_seconds=max_seconds)
    if kind=='exchangeable':
        from .exchangeable_public import exchangeable_forecast
        try:
            with calculation_budget(max_work,max_seconds=max_seconds):
                return exchangeable_forecast(board,strategy)
        except CalculationBudgetExceeded:return FuturePending('information_set_budget_exceeded')
    state,past=value
    return public_forecast(board,state,past,rules,strategy,max_work=max_work,max_seconds=max_seconds)
