"""Fixed current guard comparison; public policy never sees the viewer's intent."""
from fractions import Fraction as F
from .guard_model import GuardObserver,scope_reason,guard_choices
from .seer_future_uniform import FuturePending
from .information_set_forecast import InformationSetForecast,Pending
from .action_flow import resolve_action
from .by_dawn import HorizonValues
from .calculation_budget import calculation_budget,CalculationBudgetExceeded,tick
from .actor_information import wolf_information_groups,condition_actor_state
from .evaluation_branch import ActionInputs,physical_board


def guard_forecast(board,actor,private_board,state,past,rules,strategy,*,guards=(),max_work=250000,max_seconds=20,private_state=None,engine_factory=InformationSetForecast):
    from .guard_history_prior import seed_history,guard_matches,public_history_ready,guard_history_ready
    try:state=seed_history(board,state) if strategy.night=='max' else state
    except ValueError:return FuturePending('guard_public_history_zero_support')
    reason=scope_reason(board,rules,strategy,public_history_ready(board,state) if rules.allow_repeat_guard else guard_history_ready(board,state),joint_max=getattr(engine_factory,'joint_guard_max',False))
    if reason:return FuturePending(reason)
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            engine=engine_factory(rules,strategy,max_work=max_work)
            allowed=tuple(w[:-1] for w in private_board.worlds)
            own=condition_actor_state(state if private_state is None else private_state,lambda h:h.roles in allowed and guard_matches(h.guards,guards),guards=guards)
            choices={tuple(p for p,q in guard_choices(board,actor,rules,strategy.guard_position,guards=h.guards)) for h in own.hypotheses}
            if len(choices)!=1:return FuturePending('guard_view_target_generation_support_unresolved')
            targets=next(iter(choices))
            values={};dawn={}
            for target in targets:
                observer=GuardObserver(board,actor,target,allowed)
                values[target]=engine.solve(board,state,past,own,observer)
                v=w=F()
                if board.phase=='day':
                    from .model_a_public import horizon_for_action
                    from .policy_choice import optimal_targets
                    executions=board.alive if strategy.day=='random' else optimal_targets(engine.day_scores(board,state,past),maximize=True)
                    horizons=tuple(horizon_for_action(engine,board,state,past,p,own,observer=observer) for p in executions)
                    dawn[target]=HorizonValues(sum((h.village_win for h in horizons),F())/len(horizons),
                                               sum((h.wolf_win for h in horizons),F())/len(horizons))
                    continue
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
