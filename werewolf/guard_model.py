"""Approved uniform guard law and its current information-set scope.

Owner records stay outside the public prior. Uniform bites and exact terminal
base cases are supported for hidden guardians; larger max policies stay explicit.
"""
from dataclasses import dataclass, replace
from fractions import Fraction as F
from .action_flow import FlowOutcome
from .guard_night import guard_targets
from .guard_effect import GuardIntent,guard_blocks_attack
from .exact import replace_worlds,winner_for
from .seer_acquisition import Hypothesis,normalize,public_worlds
from .night_knowledge import WolfAttack


def live_guard_mass(board):
    return sum((board.role_probability(p,'hunter') for p in board.alive),F())


def known_guardian(board):
    if not live_guard_mass(board):return None
    return next((p for p in board.alive if board.role_probability(p,'hunter')==1),None)


def scope_reason(board,rules,strategy=None,latent_ready=False):
    if not board.initial_hunter_count:return None
    if board.initial_hunter_count!=1:return 'guard_multiple_hunters_unimplemented'
    if not rules.allow_repeat_guard:return 'guard_no_repeat_unimplemented'
    hidden_hunter=len({w[3] for w in board.worlds})>1
    hidden_past_bite=any(not any(e.phase=='night' and e.day==night for e in board.history) for night in range(1,board.day))
    # Exact base cases: any successful night is followed by a terminal public
    # execution, so hidden bite knowledge cannot change a later wolf action.
    terminal_next_execution=(not board.initial_medium_count and not board.initial_seer_count and
                             (len(board.alive)<=3 and board.phase=='day' or
                              not hidden_past_bite and (len(board.alive)<=3 or
                              len(board.alive)==4 and board.phase=='day')))
    from .guard_history_prior import role_exchangeable
    closed_cast=not rules.allow_self_bite and not board.initial_medium_count and not board.initial_seer_count
    closed_history_case=closed_cast and (role_exchangeable(board) and not hidden_past_bite and
                        (len(board.alive)==5 and board.phase=='day' or len(board.alive)==4) or
                        latent_ready and (len(board.alive)<=3 or len(board.alive)==4 and board.phase=='day'))
    if hidden_hunter and (live_guard_mass(board) or hidden_past_bite) and not terminal_next_execution and not closed_history_case and (strategy is None or strategy.night!='random'):
        return 'guard_hidden_attack_max_unimplemented'
    return None


def guard_choices(board,actor,rules,position=('uniform',)):
    if tuple(position)!=('uniform',):raise ValueError('Unsupported ordered guard-position items')
    targets=guard_targets(board,actor,rules)
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


def condition_guard_observation(board,deaths,rules):
    """Ability likelihood only; never multiply by the wolf selection policy.

    A corpse identifies the bite, so its uniform guard-failure chance is known.
    No corpse identifies no bite target: retain Model A compatible role priors,
    requiring a guardian alive on that night, without inventing an attack prior.
    """
    if len(deaths)>1:raise ValueError('Multiple deaths unsupported')
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


def public_context(context):
    return context.public if isinstance(context,GuardContext) else context


def guarded_outcomes(frame,outcomes,engine):
    b=frame.board
    if not b.initial_hunter_count:return outcomes
    reason=scope_reason(b,engine.rules,engine.strategy,any(h.attacks for h in frame.after[0].hypotheses))
    if reason:raise engine.pending(reason)
    s,past,private,observer,physical=frame.after
    groups={};public={o.board.winner:o.context for o in outcomes};templates={o.board.winner:o.board for o in outcomes}
    success=None
    for h in private.hypotheses:
        actor=next((p for p in b.alive if h.roles[3]&(1<<(p-1))),None)
        choices=((None,F(1)),) if actor is None else guard_choices(b,actor,engine.rules,engine.strategy.guard_position)
        if actor is not None and isinstance(observer,GuardObserver) and observer.board==b:
            choices=((observer.target,F(1)),)
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
            if success is None:success=replace(condition_guard_observation(b,(),engine.rules),day=b.day+1,phase='day')
            if engine.strategy.night=='max' and len(b.alive)==4 and known_guardian(b) is None:
                success=replace(success,guard_prior_roster=(b.day,b.alive))
            child=success;template=success
        else:child=public[winner];template=templates[winner]
        own=replace(private,hypotheses=hs)
        physical_child=replace_worlds(template,public_worlds(hs),wolf_count=None)
        st=engine.project(s,child)
        if blocked and len(child.alive)<=3 and not b.initial_medium_count and not b.initial_seer_count:
            st=replace(st,hypotheses=normalize(tuple(replace(h,guards=(),attacks=()) for h in st.hypotheses)))
        if blocked and engine.strategy.night=='max' and len(child.alive)>3 and known_guardian(b) is None:
            from .guard_history_prior import extend_success
            st=extend_success(st,b.day,b.alive)
        result.append(FlowOutcome(mass,physical_child,GuardContext(child,own,st)))
    return tuple(result)
