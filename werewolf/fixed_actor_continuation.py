"""Physical chance backup until a decision needs a public/unknown-role law.

This is a dependency cut, not a substitute public belief. Call it only with an
actor law derived from the complete public input, never a viewer restriction.
Unknown roles are integrated BEFORE any max. When all other choices are
fixed and only this actor has information-dependent decisions, its carried
law conditions on the observed physical outcomes and its own actions. This
never installs a replacement PUBLIC belief. None requests the ordinary evaluator.
"""
from dataclasses import replace,dataclass
from fractions import Fraction as F
from .exact import replace_worlds,action_outcomes,legal_targets,winner_for
from .seer_acquisition import normalize,public_worlds
from .guard_model import guard_choices
from .guard_history_prior import previous_guard
from .guard_effect import GuardIntent
from .guard_night import resolve_fixed_guard_night
from .night_knowledge import WolfAttack
from .actor_information import wolf_information_groups
from .policy_choice import optimal_targets,uniform_policy
from .calculation_budget import tick


def fixed_actor_value(board,public_law,engine,*,info,target=None,measure=None,allow_actor_only=False):
    if public_law.public_roles!=tuple(sorted(board.worlds)):
        raise ValueError('Complete public input required for actor continuation')
    law=info.condition_public(public_law)
    strategy=engine.strategy;rules=engine.rules
    actor_only=(allow_actor_only and strategy.day=="random" and strategy.guard_position==("uniform",) and
                board.initial_hunter_count<=1 and not board.initial_seer_count and
                not board.initial_medium_count)
    if measure is not None:
        # Payoff may use P, but no extra viewer fact may change actor choices.
        signature=lambda h:(h.roles,h.acquisitions,h.guards,h.attacks)
        def conditional(state):
            totals={}
            for h in state.hypotheses:totals[h.roles]=totals.get(h.roles,F())+h.mass
            return {signature(h):h.mass/totals[h.roles] for h in state.hypotheses}
        metadata=lambda state:(state.rosters,state.initial_rule,state.tracked,state.observed_prefix)
        if metadata(measure)!=metadata(law) or conditional(measure)!=conditional(law):
            return None
        if len({h.roles for h in law.hypotheses})>1:
            def role_mass(state):
                totals={}
                for h in state.hypotheses:totals[h.roles]=totals.get(h.roles,F())+h.mass
                return totals
            if not actor_only or role_mass(measure)!=role_mass(law):return None
        law=measure  # Unknown-role choices require the SAME belief/payoff law.
    if len(law.rosters)!=board.day:
        return None  # Input is before this night's acquisition, not after it.
    # Complete physical-law scalar cache shared across candidate/infoset calls.
    # Keep the dependency-cut mode separate: a proposal must never become a
    # known-role certificate merely because its Board and history coincide.
    cache=getattr(engine,'actor_continuation_values',None)
    if cache is None:
        cache={};engine.actor_continuation_values=cache
    # Public reporting choices are left to their existing common flow.
    if any(board.claims[p-1]==role and strategy.disclosure_for(role)!='none'
           for p in board.alive for role in ('seer','medium')):
        return None

    def actions(b,s,p):return physical_actor_outcomes(b,s,engine,p)

    def act(b,s,p):
        value=F()
        for q,child,st in actions(b,s,p):
            v=solve(child,st)
            if v is None:return None
            value+=q*v
        return value

    def solve(b,s,forced=None):
        b=replace_worlds(b,s.public_roles,wolf_count=None)
        if b.winner is not None:return F(b.winner=='village')
        key=(rules,strategy,actor_only,b,s,forced)
        if key in cache:return cache[key]
        tick(len(s.hypotheses))
        if forced is not None:value=act(b,s,forced)
        elif b.phase=='day':
            if strategy.day!='random':return None
            values=tuple(act(b,s,p) for p in b.alive)
            if any(v is None for v in values):return None
            value=sum(values,F())/len(values)
        else:
            groups=wolf_information_groups(s)
            if len(groups)!=1:return None
            info,mass,group=groups[0]
            targets=tuple(p for p in b.alive if strategy.include_self_bite or
                          not info.initial_roster&(1<<(p-1)))
            if strategy.night=='max' and len({h.roles for h in s.hypotheses})!=1 and not actor_only:
                return None
            scores=tuple((p,act(b,group,p)) for p in targets)
            if any(v is None for p,v in scores):return None
            chosen=targets if strategy.night=='random' else optimal_targets(scores,maximize=False)
            value=sum((q*dict(scores)[p] for p,q in uniform_policy(chosen)),F())
        if value is not None:cache[key]=value
        return value

    return solve(board,law,target)


def physical_hypothesis_outcomes(b,h,engine,p,observer=None):
    """Existing physical kernel; no acquisition, belief or policy selection."""
    rules=engine.rules
    single=replace_worlds(b,((*h.roles,F(1)),),wolf_count=None)
    actor=next((a for a in b.alive if h.roles[3]&(1<<(a-1))),None)
    if b.phase=='night' and actor is not None:
        choices=guard_choices(b,actor,rules,engine.strategy.guard_position,guards=h.guards)
        from .guard_model import selected_guard
        selected=selected_guard(observer,b,actor,choices)
        if selected is not None:choices=((selected,F(1)),)
        if not choices:raise engine.pending('guard_no_legal_target_unselected')
        resolved=tuple((q,resolve_fixed_guard_night(single,GuardIntent(b.day,actor,g),p,rules,
                        previous=previous_guard(h.guards,actor,b.day))[0].board,
                        h.guards+(GuardIntent(b.day,actor,g),)) for g,q in choices)
    else:
        resolved=tuple((o.probability,o.board,h.guards) for o in action_outcomes(single,p,rules,engine.strategy))
    return resolved


def physical_actor_outcomes(b,s,engine,p,*,acquire=True,observer=None):
    strategy=engine.strategy;rules=engine.rules
    acquired=engine.acquire(b,s) if acquire and b.phase=='night' else s
    grouped={};templates={};physical={}
    for h in acquired.hypotheses:
        tick()
        # Within this fixed Board/action, casualties depend on roles and the
        # full guard history, never scans, attack memories or hypothesis mass.
        # Reuse physical construction only; append each ORIGINAL joint record
        # below so no private history is marginalized or used for selection.
        physics=(h.roles,h.guards)
        if physics not in physical:
            resolved=physical_hypothesis_outcomes(b,h,engine,p,observer)
            physical[physics]=resolved
        resolved=physical[physics]
        for q,child,guards in resolved:
            key=(child.alive,child.day,child.phase,child.history,child.winner)
            record=replace(h,mass=h.mass*q,guards=guards,
                attacks=h.attacks+((WolfAttack(b.day,p),) if b.phase=='night' else ()))
            grouped.setdefault(key,[]).append(record);templates[key]=child
    result=[]
    for key,hs in grouped.items():
        mass=sum((h.mass for h in hs),F());joint=replace(acquired,hypotheses=normalize(tuple(hs)))
        child=replace_worlds(templates[key],public_worlds(joint.hypotheses),wolf_count=None)
        result.append((mass,child,joint))
    return tuple(result)


@dataclass(frozen=True)
class UniformPhysicalInput:
    """Arguments of the pure physical kernel, never a joint belief/state."""
    roles: tuple
    guards: tuple


def fixed_uniform_action_value(board,source,private,engine,target,*,observer=None,physical=None,past=()):
    """Linear backup of fixed uniform choices through the SAME physical kernel.

    Complete source/private ledgers remain at the caller. Future unobserved
    scans integrate to one only when no later choice or report can read them.
    Public Q is never replaced by a chosen physical world. No max is performed
    inside worlds: this cut accepts fixed uniform day/night/guard policies only.
    """
    strategy=engine.strategy;rules=engine.rules
    from .exact_renaming import configuration,Unsupported
    try:configuration(rules);configuration(strategy)
    except Unsupported:return None
    if (strategy.day!='random' or strategy.night!='random' or observer is not None or
        engine.trace is not None or hasattr(engine,'fixed_profile') or
        getattr(engine,'verifying_actor_mask',None) is not None or strategy.guard_position!=('uniform',) or
        tuple(strategy.seer_position)!=('unvisited','uniform') or board.initial_hunter_count>1 or
        strategy.include_self_bite and not rules.allow_self_bite or
        len(source.rosters)!=board.day or len(private.rosters)!=board.day or not source.rosters or
        not set(board.alive)<=set(source.rosters[-1]) or
        source.public_roles!=tuple(sorted(board.worlds)) or
        any(board.claims[p-1]==role and strategy.disclosure_for(role)!='none'
            for p in board.alive for role in ('seer','medium'))):return None
    metadata=lambda x:(x.rosters,x.initial_rule,x.tracked,x.observed_prefix)
    if metadata(source)!=metadata(private):return None
    if any(winner_for(len(board.alive),(w[0]&board.alive_mask).bit_count()) is not None
           for w in private.public_roles):return None
    if physical is not None and replace_worlds(board,private.public_roles,wolf_count=None)!=physical:return None
    if target is not None and board.phase=='night' and not strategy.include_self_bite and any(
        w[0]&(1<<(target-1)) for w in private.public_roles):return None
    supports=getattr(engine,'uniform_source_support',None)
    if supports is None:supports={};engine.uniform_source_support=supports
    identity=(id(source),board,rules,strategy)
    signature=lambda h:(h.roles,h.acquisitions,h.guards,h.attacks)
    if identity not in supports:
        from .guard_history_prior import guard_history_ready,public_history_ready
        from .guard_model import scope_reason
        ready=(public_history_ready(board,source) if rules.allow_repeat_guard else guard_history_ready(board,source))
        if scope_reason(board,rules,strategy,ready,joint_max=getattr(engine,'joint_guard_max',False)):return None
        tick(len(source.hypotheses))
        value=(source,frozenset(signature(h) for h in source.hypotheses))
        if len(supports)>=16:supports.pop(next(iter(supports)))
        supports[identity]=value
    allowed=supports[identity][1]
    projections=getattr(engine,'uniform_physical_inputs',None)
    if projections is None:projections={};engine.uniform_physical_inputs=projections
    projection_key=(board,rules,strategy,id(source),id(private))
    if projection_key not in projections:
        grouped={}
        for h in private.hypotheses:
            tick()
            if signature(h) not in allowed:return None
            hunter=next((p for p in board.alive if h.roles[3]&(1<<(p-1))),None)
            previous=previous_guard(h.guards,hunter,board.day) if hunter is not None else None
            if hunter is not None and not rules.allow_repeat_guard and board.day>1 and previous is None:return None
            identity=(h.roles[0],h.roles[3],None if rules.allow_repeat_guard or previous is None else previous.target)
            if identity in grouped:
                mass,original=grouped[identity];grouped[identity]=(mass+h.mass,original)
            else:grouped[identity]=(h.mass,UniformPhysicalInput(h.roles,h.guards))
        value=(source,private,tuple(grouped.values()))
        if len(projections)>=16:projections.pop(next(iter(projections)))
        projections[projection_key]=value
    else:tick()
    entries=projections[projection_key][2]
    cache=getattr(engine,'uniform_physical_values',None)
    if cache is None:cache={};engine.uniform_physical_values=cache
    def key(b,h,forced):
        actor=next((p for p in b.alive if h.roles[3]&(1<<(p-1))),None)
        previous=(previous_guard(h.guards,actor,b.day) if actor is not None and
                  not rules.allow_repeat_guard else None)
        # S/M cannot affect any accepted selector or physical transition. Their
        # original masks stay in the kernel input; this caches a scalar only.
        return (rules,strategy,b.alive,b.phase,h.roles[0],h.roles[3],
                None if previous is None else previous.target,forced)
    def solve(b,h):
        if b.winner is not None:return F(b.winner=='village')
        identity=key(b,h,None)
        if identity in cache:tick();return cache[identity]
        actions=legal_targets(b,rules,strategy)
        value=sum((act(b,h,p)[0] for p in actions),F())/len(actions)
        if len(cache)<16384:cache[identity]=value
        return value
    def act(b,h,p):
        identity=key(b,h,p)
        if identity in cache:tick();return cache[identity]
        tick();value=village=wolf=F()
        for mass,child,guards in physical_hypothesis_outcomes(b,h,engine,p):
            next_input=UniformPhysicalInput(h.roles,guards)
            value+=mass*solve(child,next_input)
            if child.winner is not None:
                village+=mass*F(child.winner=='village');wolf+=mass*F(child.winner=='wolf')
            elif b.phase=='day':
                bites=legal_targets(child,rules,strategy)
                village+=mass*sum((act(child,next_input,bite)[1] for bite in bites),F())/len(bites)
                wolf+=mass*sum((act(child,next_input,bite)[2] for bite in bites),F())/len(bites)
        result=(value,village,wolf)
        if len(cache)<16384:cache[identity]=result
        return result
    value=village=wolf=F()
    for mass,h in entries:
        tick()
        single=replace_worlds(board,((*h.roles,F(1)),),wolf_count=None)
        if target is None:value+=mass*solve(single,h)
        else:
            result=act(single,h,target)
            value+=mass*result[0];village+=mass*result[1];wolf+=mass*result[2]
    if target is not None:
        horizons=getattr(engine,'uniform_action_horizons',None)
        if horizons is None:horizons={};engine.uniform_action_horizons=horizons
        identity=(board,rules,strategy,past,id(source),id(private),target)
        if len(horizons)>=32:horizons.pop(next(iter(horizons)))
        horizons[identity]=(source,private,(village,wolf))
    return value
