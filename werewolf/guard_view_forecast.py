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


def guard_forecast(board,actor,private_board,state,past,rules,strategy,*,guards=(),max_work=250000,max_seconds=20):
    from .guard_history_prior import seed_history
    try:state=seed_history(board,state) if strategy.night=='max' else state
    except ValueError:return FuturePending('guard_public_history_zero_support')
    reason=scope_reason(board,rules,strategy,any(h.attacks for h in state.hypotheses))
    if reason:return FuturePending(reason)
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            engine=InformationSetForecast(rules,strategy,max_work=max_work)
            allowed=tuple(w[:-1] for w in private_board.worlds)
            own=replace(state,hypotheses=normalize(tuple(replace(h,guards=guards or h.guards) for h in state.hypotheses if h.roles in allowed and all(not h.guards or any(old==g for old in h.guards) for g in guards))))
            values={};dawn={}
            for target,_ in guard_choices(board,actor,rules,strategy.guard_position):
                observer=GuardObserver(board,actor,target,allowed)
                values[target]=engine.solve(board,state,past,own,observer)
                v=w=F();groups={}
                for h in own.hypotheses:groups.setdefault((h.roles[0],h.attacks),[]).append(h)
                for (mask,history),hs in groups.items():
                    mass=sum((h.mass for h in hs),F())
                    group=replace(own,hypotheses=normalize(hs))
                    physical=replace_worlds(board,group.public_roles)
                    for attack,q in engine.wolf_policy(board,state,past,mask,history):
                        tick()
                        _,outcomes=resolve_action(board,(state,past,group,observer,physical),attack,engine.action_policy)
                        for o in outcomes:
                            v+=mass*q*o.probability*F(o.board.winner=='village')
                            w+=mass*q*o.probability*F(o.board.winner=='wolf')
                dawn[target]=HorizonValues(v,w)
            return values,dawn
    except CalculationBudgetExceeded:return FuturePending('information_set_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)
