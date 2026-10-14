"""Opt-in complete root secrets under existing uniform acquisition rules.

This API never replaces the fixed-CO entry or an unsupported max with random.
Public Model A role weights and actual branch measures remain distinct.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from .seer_acquisition import from_board,normalize
from .seer_future_uniform import TrueScanState,FuturePending,acquire_uniform
from .actor_information import condition_actor_state
from .evaluation_branch import ActionInputs,physical_board
from .information_set_forecast import InformationSetForecast,InformationSetActionPolicy,Pending
from .action_flow import resolve_action
from .night_knowledge import WolfAttack
from .calculation_budget import calculation_budget,CalculationBudgetExceeded
from .forecast_result import Forecast
from .exact import legal_targets


@dataclass(frozen=True)
class RootSecretBranch:
    public: object
    public_law: TrueScanState
    physical: object
    physical_law: TrueScanState
    past: tuple = ()

    def __post_init__(self):
        if self.public_law.public_roles!=tuple(sorted(self.public.worlds)):
            raise ValueError('Public role prior must remain owned by public Board')
        if self.physical_law.public_roles!=tuple(sorted(self.physical.worlds)):
            raise ValueError('Physical role law must match actual branch Board')
        physical_board(self.public,self.physical_law,self.physical)


@dataclass(frozen=True)
class RootActorView:
    belief: TrueScanState
    physical_law: TrueScanState


def prepare_root_secrets(board,rules,*,max_work=250000):
    if board.day!=1 or board.phase!='day' or board.history or board.alive!=tuple(range(1,board.player_count+1)):
        return FuturePending('root_secret_initial_board_required')
    initial=TrueScanState(from_board(board),initial_rule=rules.initial_seer,tracked=None)
    law=acquire_uniform(initial,board.alive,max_work=max_work)
    if isinstance(law,FuturePending):return law
    return RootSecretBranch(board,law,board,law)


def observe_root_public(branch,public,compatible,*,past=None):
    """Use externally updated Model A Q; condition history within each world.

    The caller supplies an existing public observation predicate, never an
    optimized-action likelihood for public roles. Physical evidence uses P.
    """
    kept=tuple(h for h in branch.public_law.hypotheses if compatible(h))
    totals={}
    for h in kept:totals[h.roles]=totals.get(h.roles,F())+h.mass
    if any(not totals.get(w[:-1]) for w in public.worlds):
        return FuturePending('root_secret_public_history_zero_support')
    weights={w[:-1]:w[-1] for w in public.worlds}
    public_law=replace(branch.public_law,hypotheses=normalize(tuple(
        replace(h,mass=weights[h.roles]*h.mass/totals[h.roles]) for h in kept if h.roles in weights)))
    predicate=lambda h:h.roles in weights and compatible(h)
    if not any(predicate(h) for h in branch.physical_law.hypotheses):
        return FuturePending('root_secret_physical_zero_support')
    physical_law=condition_actor_state(branch.physical_law,predicate)
    physical=physical_board(public,physical_law,branch.physical)
    return RootSecretBranch(public,public_law,physical,physical_law,branch.past if past is None else tuple(past))


def root_actor_view(branch,compatible,*,guards=(),attacks=()):
    if not any(compatible(h) for h in branch.public_law.hypotheses):
        return FuturePending('root_secret_actor_belief_zero_support')
    if not any(compatible(h) for h in branch.physical_law.hypotheses):
        return FuturePending('root_secret_actor_physical_zero_support')
    return RootActorView(condition_actor_state(branch.public_law,compatible,guards=guards,attacks=attacks),
                         condition_actor_state(branch.physical_law,compatible,guards=guards,attacks=attacks))


def root_scope(branch,rules,strategy):
    if strategy.day!='random' or strategy.night!='random':return 'root_secret_max_unimplemented'
    if branch.public.initial_hunter_count:return 'root_secret_guard_continuation_unimplemented'
    if rules.allow_self_bite and not strategy.include_self_bite:
        return 'root_secret_self_bite_policy_support_unimplemented'
    # Initial full-disclosure omissions retain the existing fixed-CO contract.
    if strategy.disclosure_for('seer')=='all':
        published={(r.player,r.acquired_day) for r in branch.past}
        if any(a.player in branch.public.alive and branch.public.claims[a.player-1]=='seer' and
               (a.player,a.day) not in published for h in branch.public_law.hypotheses for a in h.acquisitions):
            return 'full_disclosure_truth_not_conditioned'
    if (strategy.disclosure_for('medium')=='all' and strategy.fake_reports=='max' and
        any(branch.public.claims[p-1]=='medium' for p in branch.public.alive)):
        return 'root_secret_max_unimplemented'
    return None


class RootSecretPolicy(InformationSetActionPolicy):
    def project(self,b,payload,outcome,target):
        continuation=super().project(b,payload,outcome,target)
        if b.phase!='night':return continuation
        known=(WolfAttack(b.day,target),)
        # In this non-guard path the corpse publicly identifies the bite.
        return replace(continuation,
            public_state=condition_actor_state(continuation.public_state,lambda h:True,attacks=known),
            private=condition_actor_state(continuation.private,lambda h:True,attacks=known))


class RootSecretEngine(InformationSetForecast):
    def __init__(self,rules,strategy,**kwargs):
        super().__init__(rules,strategy,retire_uninformative_scans=False,memoize_flows=False,**kwargs)
        self.action_policy=RootSecretPolicy(self)

    def exchangeable(self,b):return False  # Keep the complete latent acquisition flow.
    def value_law(self,state):return state  # No history compression in this entry.


def step_root_action(branch,target,rules,strategy,*,max_work=250000,max_seconds=20):
    """Explicit action intervention through the shared ability/death/report flow."""
    reason=root_scope(branch,rules,strategy)
    if reason:return FuturePending(reason)
    if branch.public.winner:return FuturePending('root_secret_terminal_action')
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            e=RootSecretEngine(rules,strategy,max_work=max_work)
            acquired,outcomes=resolve_action(branch.public,ActionInputs(branch.public_law,branch.past,
                branch.physical_law,None,branch.physical),target,e.action_policy)
            result=[]
            for o in outcomes:
                c=e.action_policy.project(branch.public,acquired,o,target)
                if branch.public.phase=='night' and o.board.winner is None:
                    choices=e.push(c.public_state,c.private,e.morning(c.public,c.public_state,c.past))
                else:choices=((F(1),c.public,c.public_state,c.past,c.private),)
                for q,b,s,past,own in choices:
                    result.append((o.probability*q,RootSecretBranch(b,s,physical_board(b,own,c.physical),own,past)))
            return tuple(result)
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)


def root_secret_value(branch,rules,strategy,*,actor=None,max_work=250000,max_seconds=20):
    if branch.public.winner:return F(branch.public.winner=='village')
    reason=root_scope(branch,rules,strategy)
    if reason:return FuturePending(reason)
    own=branch.physical_law if actor is None else actor.physical_law
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            e=RootSecretEngine(rules,strategy,max_work=max_work)
            return e.solve(branch.public,branch.public_law,branch.past,own,None,
                           physical=physical_board(branch.public,own,branch.physical))
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)


def root_screen_eligible(board,rules,strategy):
    """Existing initial screen subset; no change to fixed-CO/max entrypoints."""
    return (bool(board.initial_seer_count) and not board.initial_hunter_count and
            board.day==1 and board.phase=='day' and not board.history and
            board.alive==tuple(range(1,board.player_count+1)) and
            strategy.day=='random' and strategy.night=='random' and
            not (rules.allow_self_bite and not strategy.include_self_bite) and
            not any(board.claims[p-1]=='seer' for p in board.alive) and
            not (strategy.disclosure_for('medium')=='all' and strategy.fake_reports=='max' and
                 any(board.claims[p-1]=='medium' for p in board.alive)))


def root_screen_forecast(board,rules,strategy,*,max_work=250000,max_seconds=20):
    """Full initial screen metrics from one complete latent secret law."""
    if not root_screen_eligible(board,rules,strategy):
        return FuturePending('root_secret_screen_scope_unimplemented')
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            branch=prepare_root_secrets(board,rules,max_work=max_work)
            if isinstance(branch,FuturePending):return branch
            e=RootSecretEngine(rules,strategy,max_work=max_work)
            value=e.solve(board,branch.public_law,(),branch.physical_law,None,physical=branch.physical)
            targets=legal_targets(board,rules,strategy)
            actions=tuple((t,e.act(board,branch.public_law,(),t,branch.physical_law,None,
                                  physical=branch.physical)) for t in targets)
            from .model_a_public import horizon_for_action
            horizons=tuple((t,horizon_for_action(e,board,branch.public_law,(),t,branch.physical_law))
                           for t in targets)
            return Forecast(value,actions,horizons)
    except CalculationBudgetExceeded:return FuturePending('root_secret_budget_exceeded')
    except Pending as error:return FuturePending(error.reason)
