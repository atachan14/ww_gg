"""Physical chance backup until a decision needs a public/unknown-role law.

This is a dependency cut, not a substitute public belief. Call it only with an
actor law derived from the complete public input, never a viewer restriction.
Unknown roles are integrated BEFORE any max. Future actor max is evaluated
here only when that actor already knows the complete role assignment and all
other value-relevant choices are fixed. None requests the ordinary evaluator.
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


def fixed_actor_value(board,public_law,engine,*,info,target=None):
    if public_law.public_roles!=tuple(sorted(board.worlds)):
        raise ValueError('Complete public input required for actor continuation')
    law=info.condition_public(public_law)
    if len(law.rosters)!=board.day:
        return None  # Input is before this night's acquisition, not after it.
    cache={}
    strategy=engine.strategy;rules=engine.rules
    # Public reporting choices are left to their existing common flow.
    if any(board.claims[p-1]==role and strategy.disclosure_for(role)!='none'
           for p in board.alive for role in ('seer','medium')):
        return None

    def actions(b,s,p):
        acquired=engine.acquire(b,s) if b.phase=='night' else s
        grouped={};templates={}
        for h in acquired.hypotheses:
            tick()
            single=replace_worlds(b,((*h.roles,F(1)),),wolf_count=None)
            actor=next((a for a in b.alive if h.roles[3]&(1<<(a-1))),None)
            if b.phase=='night' and actor is not None:
                choices=guard_choices(b,actor,rules,strategy.guard_position,guards=h.guards)
                if not choices:raise engine.pending('guard_no_legal_target_unselected')
                resolved=tuple((q,resolve_fixed_guard_night(single,GuardIntent(b.day,actor,g),p,rules,
                                previous=previous_guard(h.guards,actor,b.day))[0].board,
                                h.guards+(GuardIntent(b.day,actor,g),)) for g,q in choices)
            else:
                resolved=tuple((o.probability,o.board,h.guards) for o in action_outcomes(single,p,rules,strategy))
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
        key=(b,s,forced)
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
            if strategy.night=='max' and len({h.roles for h in s.hypotheses})!=1:
                return None
            scores=tuple((p,act(b,group,p)) for p in targets)
            if any(v is None for p,v in scores):return None
            chosen=targets if strategy.night=='random' else optimal_targets(scores,maximize=False)
            value=sum((q*dict(scores)[p] for p,q in uniform_policy(chosen)),F())
        if value is not None:cache[key]=value
        return value

    return solve(board,law,target)
