"""Public-only model A facade. No viewer or secrets enter its inputs.

Night overview policy is supported. Night row intervention semantics are being
reviewed separately; absent that contract, no target comparison is fabricated.
"""
from fractions import Fraction as F
from .exact import replace_worlds
from .action_flow import resolve_action
from .seer_acquisition import normalize
from .seer_future_uniform import FuturePending
from .public_prior import public_history_key, prepare_public_prior
from .information_set_forecast import InformationSetForecast, Pending
from .calculation_budget import calculation_budget, tick, CalculationBudgetExceeded
from .forecast_result import Forecast
from .by_dawn import HorizonValues
from dataclasses import replace
from functools import lru_cache
import json


def horizon_for_action(engine,board,state,past,target,private=None):
    """One execution and one roster-informed night, or the current night only.

    Select bites using FINAL continuation values, then count only terminal mass
    through dawn. Generated reports cannot themselves change the winner rule.
    """
    private=state if private is None else private
    physical=replace_worlds(board,private.public_roles)
    _,outcomes=resolve_action(board,(state,past,private,None,physical),target,engine.action_policy)
    village=wolf=F()
    for o in outcomes:
        tick(len(private.hypotheses))
        if o.board.winner:
            v=F(o.board.winner=='village');w=F(o.board.winner=='wolf')
        elif board.phase=='night':v=w=F()
        else:
            child=o.context;public=engine.project(state,child);own=engine.project(private,o.board)
            groups={};v=w=F()
            for h in own.hypotheses:groups.setdefault(h.roles[0],[]).append(h)
            for mask,hs in groups.items():
                mass=sum((h.mass for h in hs),F())
                group=replace(own,hypotheses=normalize(tuple(hs)))
                physical_next=replace_worlds(child,group.public_roles)
                for bite,q in engine.wolf_policy(child,public,past,mask):
                    _,night_outcomes=resolve_action(child,(public,past,group,None,physical_next),bite,engine.action_policy)
                    for final in night_outcomes:
                        v+=mass*q*final.probability*F(final.board.winner=='village')
                        w+=mass*q*final.probability*F(final.board.winner=='wolf')
        village+=o.probability*v;wolf+=o.probability*w
    return HorizonValues(village,wolf)


def public_forecast(board,state,past,rules,strategy,*,max_work=250000,max_seconds=20):
    """Complete public overview and day rows; night rows await their contract."""
    if state.public_roles!=tuple(sorted(board.worlds)):
        raise ValueError('Public acquisition prior must match public Board')
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            engine=InformationSetForecast(rules,strategy,max_work=max_work)
            if engine.exchangeable(board):
                from .exchangeable_public import exchangeable_forecast
                return exchangeable_forecast(board,strategy)
            value=engine.scalar(board,state,past)
            targets=board.alive if board.phase=='day' and board.winner is None else ()
            actions=tuple((t,engine.act(board,state,past,t,state,None)) for t in targets)
            horizon=tuple((t,horizon_for_action(engine,board,state,past,t)) for t in targets)
            return Forecast(value,actions,horizon,
                            ('night_actions','night_horizon') if board.phase=='night' and board.winner is None else ())
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
