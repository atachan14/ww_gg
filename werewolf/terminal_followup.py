"""A proved terminal follow-up cut over the existing physical action kernel.

No replacement joint law is returned. Callers retain every original ledger and
supply complete physical outcomes; only already-terminal payoffs are compiled.
Public ranking uses Model-A Q before selection, and actor payoffs use P.
"""
from dataclasses import replace,dataclass
from fractions import Fraction as F
from .exact import action_outcomes,replace_worlds,legal_targets
from .policy_choice import optimal_targets,uniform_policy


def terminal_payoff_table(board,rules,strategy):
    day=replace(board,day=board.day+int(board.phase=='night'),phase='day')
    table={}
    for world in board.worlds:
        single=replace_worlds(day,((*world[:-1],F(1)),),wolf_count=None)
        row=[]
        for target in legal_targets(single,rules,strategy):
            outcomes=action_outcomes(single,target,rules,strategy)
            if any(o.board.winner is None for o in outcomes):return None
            row.append((target,sum((o.probability*F(o.board.winner=='village') for o in outcomes),F())))
        if tuple(p for p,v in row)!=day.alive:return None
        table[world[:-1]]=dict(row)
    return table


def terminal_followup_value(board,supported_roles,physical_outcomes,table,strategy):
    # Q retains its original relative role weights on positive generated
    # support. Generation likelihoods do not reweight those roles.
    if all(child.winner is not None for mass,child,joint in physical_outcomes):
        return sum((mass*F(child.winner=='village') for mass,child,joint in physical_outcomes),F()),0
    weights=tuple((w[:-1],w[-1]) for w in board.worlds if w[:-1] in supported_roles)
    if not weights:raise ValueError('Positive physical continuation requires public support')
    total=sum((q for role,q in weights),F())
    scores=tuple((p,sum((q*table[role][p] for role,q in weights),F())/total) for p in board.alive)
    chosen=board.alive if strategy.day=='random' else optimal_targets(scores,maximize=True)
    policy=uniform_policy(chosen);value=F();reads=0
    for mass,child,joint in physical_outcomes:
        if child.winner is not None:value+=mass*F(child.winner=='village')
        else:
            if child.phase!='day' or child.alive!=board.alive:raise ValueError('Nonterminal follow-up outside proof')
            reads=1
            value+=mass*sum((role[-1]*sum((q*table[role[:-1]][p] for p,q in policy),F())
                             for role in joint.public_roles),F())
    return value,reads


@dataclass(frozen=True)
class TerminalRoleMeasure:
    public_roles: tuple


def terminal_physical_measures(board,state,engine,target):
    """Integrate only an unused FUTURE scan kernel at a proved terminal cut.

    Every existing acquisition/guard/attack record remains in the input. The
    next unobserved scan sums to one and cannot affect the physical kernel or
    the following terminal execution. No shortened joint state is constructed
    or returned to history/replay/observer callers.
    """
    if (board.phase!='night' or len(board.alive)!=3 or len(state.rosters)!=board.day or
        state.rosters and not set(board.alive)<=set(state.rosters[-1]) or
        tuple(engine.strategy.seer_position)!=('unvisited','uniform') or
        any(board.claims[p-1]==role and engine.strategy.disclosure_for(role)!='none'
            for p in board.alive for role in ('seer','medium'))):return None
    from .fixed_actor_continuation import physical_hypothesis_outcomes
    from .calculation_budget import tick
    plans={};groups={};templates={}
    for h in state.hypotheses:
        tick();key=(h.roles,h.guards)
        if key not in plans:plans[key]=physical_hypothesis_outcomes(board,h,engine,target)
        for q,child,guards in plans[key]:
            branch=(child.alive,child.day,child.phase,child.history,child.winner)
            roles=groups.setdefault(branch,{})
            roles[h.roles]=roles.get(h.roles,F())+h.mass*q;templates[branch]=child
    result=[]
    for branch,roles in groups.items():
        mass=sum(roles.values(),F())
        worlds=tuple((*role,q/mass) for role,q in sorted(roles.items()))
        child=replace_worlds(templates[branch],worlds,wolf_count=None)
        result.append((mass,child,TerminalRoleMeasure(worlds)))
    return tuple(result)
