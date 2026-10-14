"""Approved uniform guard law and its current information-set scope.

Owner records stay outside the public prior. Uniform bites and exact terminal
base cases are supported for hidden guardians; larger max policies stay explicit.
"""
from dataclasses import dataclass, replace
from fractions import Fraction as F
from .action_flow import FlowOutcome
from .evaluation_branch import require_public_observation
from .guard_night import guard_targets
from .guard_effect import GuardIntent,guard_blocks_attack
from .exact import replace_worlds,winner_for
from .seer_acquisition import Hypothesis,normalize,public_worlds
from .night_knowledge import WolfAttack
from .calculation_budget import tick


def live_guard_mass(board):
    return sum((board.role_probability(p,'hunter') for p in board.alive),F())


def known_guardian(board):
    if not live_guard_mass(board):return None
    return next((p for p in board.alive if board.role_probability(p,'hunter')==1),None)


def scope_reason(board,rules,strategy=None,latent_ready=False,*,joint_max=False):
    if not board.initial_hunter_count:return None
    if board.initial_hunter_count!=1:return 'guard_multiple_hunters_unimplemented'
    if not rules.allow_repeat_guard:
        if strategy is None or strategy.day!='random' or strategy.night not in (('random','max') if joint_max else ('random',)):
            return 'guard_no_repeat_max_unimplemented'
        if rules.allow_self_bite and not strategy.include_self_bite:return 'guard_no_repeat_self_bite_policy_unimplemented'
        if not latent_ready:return 'guard_no_repeat_history_missing'
    hidden_hunter=len({w[3] for w in board.worlds})>1
    hidden_past_bite=any(not any(e.phase=='night' and e.day==night for e in board.history) for night in range(1,board.day))
    # Exact base cases: any successful night is followed by a terminal public
    # execution, so hidden bite knowledge cannot change a later wolf action.
    terminal_next_execution=(not board.initial_medium_count and not board.initial_seer_count and
                             (len(board.alive)<=3 and board.phase=='day' or
                              not hidden_past_bite and (len(board.alive)<=3 or
                              len(board.alive)==4 and board.phase=='day')))
    from .guard_history_prior import role_exchangeable,hero_deducible
    closed_cast=not rules.allow_self_bite and not board.initial_medium_count and not board.initial_seer_count
    closed_history_case=closed_cast and (role_exchangeable(board) and not hidden_past_bite and
                        (len(board.alive)==5 and board.phase=='day' or len(board.alive)==4) or
                        latent_ready and (len(board.alive)<=3 or len(board.alive)==4 and board.phase=='day'))
    if not joint_max and hidden_hunter and (live_guard_mass(board) or hidden_past_bite) and not terminal_next_execution and not closed_history_case and not hero_deducible(board) and (strategy is None or strategy.night!='random'):
        return 'guard_hidden_attack_max_unimplemented'
    return None


def guard_choices(board,actor,rules,position=('uniform',),*,guards=()):
    if tuple(position)!=('uniform',):raise ValueError('Unsupported ordered guard-position items')
    from .guard_history_prior import previous_guard
    targets=guard_targets(board,actor,rules,previous_guard(guards,actor,board.day))
    return tuple((p,F(1,len(targets))) for p in targets)


@dataclass(frozen=True)
class GuardObserver:
    board: object
    actor: int
    target: int
    allowed_roles: tuple

    def __call__(self,h,state):
        return h.roles in self.allowed_roles


@dataclass(frozen=True)
class GuardContext:
    public: object
    private: object
    public_state: object = None


def condition_guard_observation(board,deaths,rules,*,state=None):
    """Ability likelihood only; never multiply by the wolf selection policy.

    A corpse identifies the bite, so its uniform guard-failure chance is known.
    No corpse identifies no bite target: retain Model A compatible role priors,
    requiring a guardian alive on that night, without inventing an attack prior.
    """
    if len(deaths)>1:raise ValueError('Multiple deaths unsupported')
    if not rules.allow_repeat_guard:
        return condition_joint_guard_observation(board,deaths,rules,state)
    target=deaths[0] if deaths else None;entries=[]
    for world in board.worlds:
        actor=next((p for p in board.alive if world[3]&(1<<(p-1))),None)
        if target is None:weight=F(actor is not None)
        elif not rules.allow_self_bite and world[0]&(1<<(target-1)):weight=F()
        else:weight=F(1) if actor is None or actor==target else F(len(board.alive)-2,len(board.alive)-1)
        if weight:entries.append((*world[:-1],world[-1]*weight))
    total=sum((w[-1] for w in entries),F())
    if not total:raise ValueError('Night observation has no compatible guard world')
    return replace_worlds(board,tuple((*w[:-1],w[-1]/total) for w in entries),wolf_count=None)


def condition_joint_guard_observation(board,deaths,rules,state):
    """History-dependent ability evidence, keeping public role Q separate from P."""
    from .seer_acquisition import from_board
    from .seer_future_uniform import TrueScanState
    from .guard_history_prior import guard_history_ready
    if state is None:
        if board.day>1 and live_guard_mass(board):raise ValueError('guard_no_repeat_history_missing')
        state=TrueScanState(from_board(board))
    if not guard_history_ready(board,state):raise ValueError('guard_no_repeat_history_missing')
    target=deaths[0] if deaths else None;totals={};effects={}
    for h in state.hypotheses:
        tick();totals[h.roles]=totals.get(h.roles,F())+h.mass
        actor=next((p for p in board.alive if h.roles[3]&(1<<(p-1))),None)
        choices=((None,F(1)),) if actor is None else guard_choices(board,actor,rules,guards=h.guards)
        if not choices:raise ValueError('guard_no_legal_target_unselected')
        if target is None:
            supported=actor is not None and any(p is not None and (rules.allow_self_bite or
                not h.roles[0]&(1<<(p-1))) for p,q in choices)
            effects[h.roles]=max(effects.get(h.roles,F()),F(supported))
        else:
            effect=F() if not rules.allow_self_bite and h.roles[0]&(1<<(target-1)) else sum((q for p,q in choices if p!=target),F())
            effects[h.roles]=effects.get(h.roles,F())+h.mass*effect
    entries=[]
    for world in board.worlds:
        role=world[:-1]
        if role not in totals:raise ValueError('guard_public_history_zero_support')
        factor=effects.get(role,F()) if target is None else effects.get(role,F())/totals[role]
        if factor:entries.append((*role,world[-1]*factor))
    total=sum((w[-1] for w in entries),F())
    if not total:raise ValueError('Night observation has no compatible guard history')
    return replace_worlds(board,tuple((*w[:-1],w[-1]/total) for w in entries),wolf_count=None)


def public_context(context):
    return context.public if isinstance(context,GuardContext) else context


def public_guard_branch_law(board,state,child,attack,blocked,engine,*,policies=None,past=()):
    graph=getattr(engine,'policy_dependencies',None)
    if graph is None:
        return _public_guard_branch_law(board,state,child,attack,blocked,engine,policies=policies,past=past)
    from .policy_dependencies import Dependency
    profile=None if policies is None else tuple(sorted(policies.items()))
    node=Dependency('public-support',(board,state,child,attack,blocked,past,profile))
    # A supplied/cached complete profile may close this recorded dependency.
    # Do not reject that legitimate fixed-profile proof as infinite recursion.
    with graph.evaluating(node,allow_reentry=True):
        return _public_guard_branch_law(board,state,child,attack,blocked,engine,policies=policies,past=past)


def _public_guard_branch_law(board,state,child,attack,blocked,engine,*,policies=None,past=()):
    """Public-owned generated support; no viewer restriction chooses this law.

    The complete kernel covers every public wolf information set. Observations
    remove zero-support roles only; positive likelihoods never reweight Q.
    """
    from .actor_information import WolfInformation,wolf_information_groups
    from .policy_choice import uniform_policy
    from .public_observation_support import condition_generated_support
    infos=tuple(info for info,mass,group in wolf_information_groups(state))
    if policies is None:
        if engine.strategy.night!='random':
            provider=getattr(engine,'public_night_policies',None)
            if provider is None:raise engine.pending('guard_max_public_kernel_unresolved')
            policies=provider(board,state,past)
        else:
            policies={(info.initial_roster,info.attacks):uniform_policy(tuple(p for p in board.alive
                if engine.strategy.include_self_bite or not info.initial_roster&(1<<(p-1)))) for info in infos}
    for info in infos:
        key=(info.initial_roster,info.attacks)
        if key not in policies:raise engine.pending('guard_public_kernel_incomplete')
        kernel=policies[key]
        if (not kernel or len({p for p,q in kernel})!=len(kernel) or
            any(type(p)is not int or p not in board.alive or
                not engine.strategy.include_self_bite and info.initial_roster&(1<<(p-1)) or
                not isinstance(q,F) or q<=0 for p,q in kernel) or
            sum((q for p,q in kernel),F())!=1):
            raise ValueError('Complete legal public wolf kernel required')
    entries=[]
    for h in state.hypotheses:
        tick()
        actor=next((p for p in board.alive if h.roles[3]&(1<<(p-1))),None)
        if actor is None and blocked:continue
        choices=((None,F(1)),) if actor is None else guard_choices(board,actor,engine.rules,engine.strategy.guard_position,guards=h.guards)
        if not choices:raise engine.pending('guard_no_legal_target_unselected')
        for bite,qa in policies[h.roles[0],h.attacks]:
            if not blocked and bite!=attack:continue
            for target,qg in choices:
                tick()
                intent=GuardIntent(board.day,actor,target) if actor is not None else None
                success=intent is not None and guard_blocks_attack(intent,bite)
                if success!=blocked:continue
                entries.append(Hypothesis(h.roles,h.acquisitions,h.mass*qa*qg,
                    h.guards+((intent,) if intent else ()),h.attacks+(WolfAttack(board.day,bite),)))
    try:return condition_generated_support(child,state,tuple(entries))
    except ValueError as error:raise engine.pending(str(error))


def guarded_outcomes(frame,outcomes,engine):
    b=frame.board
    if not b.initial_hunter_count:return outcomes
    from .guard_history_prior import public_history_ready,guard_history_ready
    s,past,private,observer,physical=frame.after
    ready=public_history_ready(b,s) if engine.rules.allow_repeat_guard else guard_history_ready(b,s)
    reason=scope_reason(b,engine.rules,engine.strategy,ready,joint_max=getattr(engine,'joint_guard_max',False))
    if reason:raise engine.pending(reason)
    groups={};public={o.board.winner:o.context for o in outcomes};templates={o.board.winner:o.board for o in outcomes}
    success=None
    for h in private.hypotheses:
        actor=next((p for p in b.alive if h.roles[3]&(1<<(p-1))),None)
        choices=((None,F(1)),) if actor is None else guard_choices(b,actor,engine.rules,engine.strategy.guard_position,guards=h.guards)
        if (actor is not None and isinstance(observer,GuardObserver) and observer.actor==actor and
                observer.board.day==b.day and observer.target in {p for p,q in choices}):
            choices=((observer.target,F(1)),)
        if not choices:raise engine.pending('guard_no_legal_target_unselected')
        for target,q in choices:
            intent=GuardIntent(b.day,actor,target) if actor is not None else None
            blocked=intent is not None and guard_blocks_attack(intent,frame.target)
            alive=b.alive if blocked else tuple(p for p in b.alive if p!=frame.target)
            wolf=(h.roles[0]&sum(1<<(p-1) for p in alive)).bit_count()
            winner=winner_for(len(alive),wolf)
            guards=h.guards+((intent,) if intent else ())
            recorded=Hypothesis(h.roles,h.acquisitions,h.mass*q,guards,h.attacks+(WolfAttack(b.day,frame.target),))
            groups.setdefault((blocked,winner),[]).append(recorded)
    result=[]
    for (blocked,winner),entries in groups.items():
        mass=sum((h.mass for h in entries),F());hs=normalize(entries)
        if blocked:
            if success is None:success=replace(condition_guard_observation(b,(),engine.rules,state=s),day=b.day+1,phase='day')
            if engine.strategy.night=='max' and len(b.alive)==4 and known_guardian(b) is None:
                success=replace(success,guard_prior_roster=(b.day,b.alive))
            child=success;template=success
        else:child=public.get(winner);template=templates[winner]
        child=require_public_observation(child,template,engine.pending)
        own=replace(private,hypotheses=hs)
        base=physical if blocked else template
        physical_child=replace_worlds(base,public_worlds(hs),wolf_count=None,
                                     alive=child.alive,day=child.day,phase=child.phase,
                                     history=child.history,guard_prior_roster=child.guard_prior_roster)
        if getattr(engine,'retain_joint_guard_history',False) or not engine.rules.allow_repeat_guard:
            child,st=public_guard_branch_law(b,s,child,frame.target,blocked,engine,past=past)
        else:st=engine.project(s,child)
        from .guard_history_prior import hero_deducible
        if not getattr(engine,'retain_joint_guard_history',False) and blocked and engine.strategy.night=='max' and len(child.alive)>3 and known_guardian(b) is None and not hero_deducible(b):
            from .guard_history_prior import extend_success
            st=extend_success(st,b.day,b.alive)
        result.append(FlowOutcome(mass,physical_child,GuardContext(child,own,st)))
    return tuple(result)
