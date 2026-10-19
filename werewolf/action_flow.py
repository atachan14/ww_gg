"""One action's phase order; information and strategy laws stay in policies.

Selection is already complete when this function is entered. The policy owns
the public/physical distribution distinction and morning strategic reports.
Only this flow decides when to acquire, stop at a winner, project after death,
and dispatch morning versus ordinary continuation.
"""
from dataclasses import dataclass
from fractions import Fraction as F


@dataclass(frozen=True)
class FlowOutcome:
    probability: F
    board: object
    context: object = None


@dataclass(frozen=True)
class NightFrame:
    """Fixed action, original roster, and separately prepared ability payload.

    The payload belongs to its information policy; the common flow cannot use
    private evidence to change actor choice. A resolver may inspect after only
    for physical effects specified by an approved ability law.
    """
    board: object
    target: int
    before: object
    after: object
    terminal_payoffs: bool = False
    observed_alive: tuple | None = None


def unchanged_death_outcomes(frame, resolve, prepared=None):
    """Current scans do not affect casualties; reuse a safe preflight if any."""
    return prepared if prepared is not None else resolve(frame.board, frame.after, frame.target)


def resolve_action(board,state,target,policy,*,terminal_payoffs=False,observed_alive=None):
    """Shared physical resolution; full observation contexts by default.

    Scalar/horizon callers may stop terminal payoffs before public belief
    generation. Those terminal outcomes need no continuation context. History
    callers keep the default and validate every retained public/secret law.
    Saved observation replay may restrict resulting alive rosters, after action
    selection/acquisition. Retained branch probabilities are never renormalized.
    An opt-in terminal_outcomes hook runs only for scalar/horizon requests,
    after the same acquisition contract. It must decline with None if any
    physical branch continues; ordinary history requests always use full laws.
    """
    from .board_future import before_action,after_acquisition,reuse_resolution,remember_resolution
    role_source=before_action(policy,board,state)
    reused=reuse_resolution(policy,board,state,target,terminal_payoffs,observed_alive)
    if reused is not None:return reused
    night = board.phase == 'night'
    acquired = state
    if night:
        prepared = policy.outcomes(board,state,target) if policy.terminal_preflight_safe else None
        if prepared is None or any(o.board.winner is None for o in prepared):
            acquired = policy.acquire(board,state)
        terminal = getattr(policy,'terminal_outcomes',None) if terminal_payoffs else None
        outcomes = terminal(board,acquired,target) if terminal is not None else None
        if outcomes is None:
            outcomes = policy.night_outcomes(NightFrame(board,target,state,acquired,terminal_payoffs,observed_alive),prepared)
    else:
        terminal = getattr(policy,'terminal_outcomes',None) if terminal_payoffs else None
        outcomes = terminal(board,state,target) if terminal is not None else None
        if outcomes is None:outcomes = policy.outcomes(board,state,target)
    after_acquisition(policy,board,acquired,role_source,target=target,
                      terminal_payoffs=terminal_payoffs,observed_alive=observed_alive)
    if observed_alive is not None:
        outcomes=tuple(o for o in outcomes if o.board.alive==observed_alive)
    remember_resolution(policy,board,state,target,terminal_payoffs,observed_alive,(acquired,outcomes))
    return acquired,outcomes


def action_flow(board, state, target, policy):
    """Policy hooks: acquire, outcomes, night_outcomes, project, continuations.

    Acquisition always receives the pre-casualty Board. Terminal branches never
    project or publish. Legacy skips acquisition for an entirely terminal action;
    Model A retains its eager acquisition/observer-support validation contract.
    A policy may preflight terminal death only when acquisition cannot change
    casualties. Future casualty-changing laws must disable terminal preflight.
    """
    acquired,outcomes=resolve_action(board,state,target,policy,terminal_payoffs=True)
    night=board.phase=='night'
    value = F()
    for outcome in outcomes:
        if outcome.board.winner is not None:
            continuation = F(outcome.board.winner == 'village')
        else:
            projected = policy.project(board, acquired, outcome, target)
            continuation = (policy.morning_value(projected) if night
                            else policy.day_value(projected))
        value += outcome.probability * continuation
    return value


def observe_action(source,target,engine):
    """One saved H0 action observation, distinct from a target intervention.

    Public Model-A role weights come from the common projected Board. Its
    within-world history mixture follows the observed actual choice. P keeps
    the actual choice and physical continuation likelihoods separately.
    """
    from .evaluation_branch import ActionInputs,ContinuationInputs,physical_board
    from .actor_information import wolf_information_keys,condition_wolf_choice
    from .belief_projection import restore_public_history_weights
    from .exact import legal_targets
    from .information_set_forecast import Pending
    b=source.public
    if b.initial_hunter_count or (engine.strategy.day,engine.strategy.night)!=('random','random'):
        raise Pending('saved_action_uniform_H0_only')
    if source.observer is not None:raise ValueError('Observe public history before choosing an owner view')
    if b.winner is not None or type(target)is not int or target not in legal_targets(source.physical,engine.rules,engine.strategy):raise ValueError('Illegal observed action target')
    own=source.private
    if b.phase=='night':
        policies={(i.initial_roster,i.attacks):engine.wolf_policy(b,source.public_state,source.past,i.initial_roster,i.attacks)
                  for i in wolf_information_keys(own)}
        try:mass,own=condition_wolf_choice(own,policies,target)
        except ValueError as error:raise Pending('saved_action_choice_zero_support') from error
    else:mass=F(1,len(legal_targets(source.physical,engine.rules,engine.strategy)))
    physical=physical_board(b,own,source.physical)
    acquired,outcomes=resolve_action(b,ActionInputs(source.public_state,source.past,own,None,physical),target,engine.action_policy,terminal_payoffs=False)
    selected=[o for o in outcomes if o.board.winner is None]
    if len(selected)!=1:raise Pending('saved_action_continuation_zero_support')
    outcome=selected[0];child=engine.action_policy.project(b,acquired,outcome,target)
    # Restore Model-A Q per world without replacing P's observed event mass.
    try:public=restore_public_history_weights(child.private,child.public)
    except ValueError as error:raise Pending('saved_action_public_history_zero_support') from error
    return mass*outcome.probability,ContinuationInputs(child.public,public,child.past,child.private,None,child.physical)
