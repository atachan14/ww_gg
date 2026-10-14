"""Fixed current guard comparison; public policy never sees the viewer's intent."""
from dataclasses import replace
from fractions import Fraction as F
from .guard_model import GuardObserver,scope_reason,guard_choices
from .exact import replace_worlds
from .seer_acquisition import normalize
from .seer_future_uniform import FuturePending
from .information_set_forecast import InformationSetForecast,Pending
from .action_flow import resolve_action
from .by_dawn import HorizonValues
from .calculation_budget import calculation_budget,CalculationBudgetExceeded,tick
from .actor_information import wolf_information_groups
from .evaluation_branch import ActionInputs,physical_board


def guard_forecast(board,actor,private_board,state,past,rules,strategy,*,guards=(),max_work=250000,max_seconds=20):
    from .guard_history_prior import seed_history,guard_matches,merge_guards,public_history_ready
    try:state=seed_history(board,state) if strategy.night=='max' else state
    except ValueError:return FuturePending('guard_public_history_zero_support')
    reason=scope_reason(board,rules,strategy,public_history_ready(board,state))
    if reason:return FuturePending(reason)
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            engine=InformationSetForecast(rules,strategy,max_work=max_work)
            allowed=tuple(w[:-1] for w in private_board.worlds)
            own=replace(state,hypotheses=normalize(tuple(replace(h,guards=merge_guards(h.guards,guards)) for h in state.hypotheses if h.roles in allowed and guard_matches(h.guards,guards))))
            values={};dawn={}
            for target,_ in guard_choices(board,actor,rules,strategy.guard_position):
                observer=GuardObserver(board,actor,target,allowed)
                values[target]=engine.solve(board,state,past,own,observer)
                v=w=F()
                for info,mass,group in wolf_information_groups(own):
                    physical=physical_board(board,group,private_board)
                    for attack,q in engine.wolf_policy(board,state,past,info.initial_roster,info.attacks):
                        tick()
                        _,outcomes=resolve_action(board,ActionInputs(state,past,group,observer,physical),attack,engine.action_policy)
                        for o in outcomes:
                            v+=mass*q*o.probability*F(o.board.winner=='village')
                            w+=mass*q*o.probability*F(o.board.winner=='wolf')
                dawn[target]=HorizonValues(v,w)
            return values,dawn
    except CalculationBudgetExceeded:return FuturePending('information_set_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)
