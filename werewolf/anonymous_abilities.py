"""Shared anonymous ability scheduler. Gameplay rules live in adapters.

Policies are committed from the pre-stage state. Private observations are typed
relations between binders; effects resolve only after all independent choices.
No named target products, permutation tests or value-based equivalence occur.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from typing import Protocol
from .calculation_budget import tick

@dataclass(frozen=True,order=True)
class Memory:
    kind:str
    day:int
    actor:int|None
    participants:tuple=()
    value:object=None
    visible_to:tuple=()

@dataclass(frozen=True)
class Effect:
    kind:str
    participants:tuple
    day:int

@dataclass(frozen=True)
class Context:
    day:int
    acquisition_day:int
    initial_white:bool=False
    initial_none:bool=False
    allow_repeat_guard:bool=True
    include_self_bite:bool=False
    execution:int|None=None

class Ability(Protocol):
    key:str
    roles:tuple
    def actors(self,population):...
    def choices(self,population,actor,context):...
    def apply(self,path,actor,choice,context):...


def slots(population,predicate):
    """One existing binder or one fresh count-class representative per choice."""
    from .anonymous_relations import Choice
    rows=[]
    for ref,person in enumerate(population.people):
        if predicate(person,ref):rows.append(Choice(population,ref,None,1))
    for index,cell in enumerate(population.cells):
        if cell.count and predicate(cell,None):
            child,ref=population.bind(index);rows.append(Choice(child,ref,index,cell.count))
    return tuple(rows)


def choices(path,ability,actor,context,committed=None):
    options=ability.choices(path.population,actor,context)
    total=sum(c.multiplicity for c in options)
    if not total:raise ValueError('no_legal_'+ability.key+'_target')
    rows=[]
    for choice in options:
        tick();per_slot=F(1,total) if committed is None else committed(choice,path.bindings)
        if not isinstance(per_slot,F) or per_slot<0:raise ValueError('Exact nonnegative committed policy required')
        bindings=path.bindings+(((choice.target,choice.fresh_cell),) if choice.fresh_cell is not None else ())
        after=ability.apply(replace(path,population=choice.population),actor,choice,context)
        rows.append(replace(after,mass=path.mass*choice.multiplicity*per_slot,
            counter=path.counter*F(choice.multiplicity,total),multiplicity=path.multiplicity*choice.multiplicity,bindings=bindings))
    return tuple(rows)


def dead_stage_kinds(present,living,stages):
    """An absent role and an inactive observation are not a dead holder."""
    return tuple(stages) if present and not living else ()


def run(population,abilities,context,policy_factory=None):
    from .anonymous_relations import Path,Step
    roles=tuple(dict.fromkeys(role for ability in abilities for role in ability.roles))
    population=population.bind_roles(roles)
    schedule=[]
    for ability in abilities:
        actors=ability.actors(population)
        if actors:schedule.extend((ability,actor) for actor in actors)
        elif dead_stage_kinds(any(p.role in ability.roles for p in population.people),actors,getattr(ability,'stages',())):schedule.append((ability,'dead'))
    schedule=tuple(schedule)
    # Factories see only the initial state, before any stage result is obtained.
    policies={(ability.key,actor):None if actor=='dead' or policy_factory is None else policy_factory(ability,actor,population) for ability,actor in schedule}
    rows=(Path(population),)
    for ability,actor in schedule:
        following=[]
        for path in rows:
            if actor=='dead':following.append(replace(path,steps=(*path.steps,*(Step('ability_dead',None,kind) for kind in ability.stages))))
            elif getattr(ability,'observation_only',False):following.append(ability.observe(path,actor,context))
            else:following.extend(choices(path,ability,actor,context,policies[ability.key,actor]))
        rows=tuple(following)
    return rows


def resolve(path,context):
    """Simultaneous cancellation/death effects; no role or policy inspection."""
    pop=path.population;blocked={e.participants[0] for e in pop.effects if e.kind=='protect' and e.day==context.day}
    victims=tuple(dict.fromkeys(e.participants[0] for e in pop.effects if e.kind=='attack' and e.day==context.day and e.participants[0] not in blocked))
    people=list(pop.people)
    for ref in victims:
        if not people[ref].alive:raise ValueError('Simultaneous effect targets an earlier death')
        people[ref]=replace(people[ref],alive=False)
    return replace(path,population=replace(pop,people=tuple(people),effects=tuple(e for e in pop.effects if e.day!=context.day))),victims
