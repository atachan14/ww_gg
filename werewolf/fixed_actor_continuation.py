"""Physical chance backup until a decision needs a public/unknown-role law.

This is a dependency cut, not a substitute public belief. Call it only with an
actor law derived from the complete public input, never a viewer restriction.
Unknown roles are integrated BEFORE any max. When all other choices are
fixed and only this actor has information-dependent decisions, its carried
law conditions on the observed physical outcomes and its own actions. This
never installs a replacement PUBLIC belief. None requests the ordinary evaluator.
"""
from dataclasses import replace
from fractions import Fraction as F
from .exact import replace_worlds,action_outcomes
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
        from .guard_model import GuardObserver
        if (isinstance(observer,GuardObserver) and observer.actor==actor and
                observer.board.day==b.day and observer.target in {g for g,q in choices}):
            choices=((observer.target,F(1)),)
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
