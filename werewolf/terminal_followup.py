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


@dataclass(frozen=True)
class TerminalPhysicalInput:
    source: object
    entries: tuple


def terminal_physical_input(state):
    """Sum equal physical inputs, retaining the exact source and its ledgers.

    This is only a scalar-integral plan. Physical transitions read roles and
    guards; scans and attacks remain untouched in source and every caller.
    """
    from .calculation_budget import tick
    grouped={}
    for h in state.hypotheses:
        tick();key=(h.roles,h.guards)
        if key in grouped:
            original,mass=grouped[key];grouped[key]=(original,mass+h.mass)
        else:grouped[key]=(h,h.mass)
    return TerminalPhysicalInput(state,tuple(grouped.values()))


def terminal_physical_measures(board,state,engine,target,*,physical_input=None):
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
    if physical_input is None:physical_input=terminal_physical_input(state)
    if physical_input.source is not state:raise ValueError('Exact physical input source required')
    groups={};templates={}
    for h,input_mass in physical_input.entries:
        tick()
        for q,child,guards in physical_hypothesis_outcomes(board,h,engine,target):
            branch=(child.alive,child.day,child.phase,child.history,child.winner)
            roles=groups.setdefault(branch,{})
            roles[h.roles]=roles.get(h.roles,F())+input_mass*q;templates[branch]=child
    result=[]
    for branch,roles in groups.items():
        mass=sum(roles.values(),F())
        worlds=tuple((*role,q/mass) for role,q in sorted(roles.items()))
        child=replace_worlds(templates[branch],worlds,wolf_count=None)
        result.append((mass,child,TerminalRoleMeasure(worlds)))
    return tuple(result)


def _cached_terminal_table(board,engine):
    cache=getattr(engine,'terminal_tables',None)
    if cache is None:cache={};engine.terminal_tables=cache
    key=(board,engine.rules,engine.strategy)
    if key not in cache:
        value=terminal_payoff_table(board,engine.rules,engine.strategy)
        if len(cache)>=16:cache.pop(next(iter(cache)))
        cache[key]=value
    return cache[key]


def uniform_terminal_action_value(board,state,private,engine,target,*,observer=None,physical=None):
    """Exact scalar backup through existing kernels; no replacement joint law.

    A day cut requires every execution to end physically. A uniform night cut
    additionally requires the next unobserved scan to have no strategic or
    reporting effect. Replay and actual observation paths are never shortened.
    """
    if board.winner is not None or observer is not None or len(board.alive)!=3:return None
    if state.public_roles!=tuple(sorted(board.worlds)):return None
    from .calculation_budget import tick
    roles=private.public_roles
    if not {w[:-1] for w in roles}<={w[:-1] for w in board.worlds}:return None
    if physical is not None and replace_worlds(board,roles,wolf_count=None)!=physical:return None
    if board.phase=='day':
        table=_cached_terminal_table(board,engine)
        if table is None:return None
        tick(len(roles))
        return sum((w[-1]*table[w[:-1]][target] for w in roles),F())
    if (not engine.rules.allow_self_bite or not engine.strategy.include_self_bite) and any(
        w[0]&(1<<(target-1)) for w in roles):return None
    if (board.phase!='night' or len(board.alive)!=3 or engine.strategy.night!='random' or
        engine.strategy.guard_position!=('uniform',) or len(state.rosters)!=board.day or
        any(board.claims[p-1]==role and engine.strategy.disclosure_for(role)!='none'
            for p in board.alive for role in ('seer','medium'))):return None
    table=_cached_terminal_table(board,engine)
    if table is None:return None
    plans=getattr(engine,'terminal_inputs',None)
    if plans is None:plans={};engine.terminal_inputs=plans
    def plan(source):
        key=id(source)  # Cached plans hold strong source references.
        if key not in plans:
            value=terminal_physical_input(source)
            if len(plans)>=16:plans.pop(next(iter(plans)))
            plans[key]=value
        return plans[key]
    actual=terminal_physical_measures(board,private,engine,target,physical_input=plan(private))
    if actual is None:return None
    supported=()
    if any(child.winner is None for mass,child,measure in actual):
        supports=getattr(engine,'terminal_uniform_support',None)
        if supports is None:supports={};engine.terminal_uniform_support=supports
        key=(board,state,engine.rules,engine.strategy)
        if key not in supports:
            from .fixed_actor_continuation import physical_hypothesis_outcomes
            possible=set()
            for h,mass in plan(state).entries:
                for bite in board.alive:
                    if not engine.strategy.include_self_bite and h.roles[0]&(1<<(bite-1)):continue
                    tick()
                    if any(child.winner is None for q,child,guards in
                           physical_hypothesis_outcomes(board,h,engine,bite)):
                        possible.add(h.roles);break
            if len(supports)>=16:supports.pop(next(iter(supports)))
            supports[key]=tuple(sorted(possible))
        supported=supports[key]
        if not supported:return None  # Ordinary flow owns zero-support refusal.
    value,reads=terminal_followup_value(board,supported,actual,table,engine.strategy)
    return value
