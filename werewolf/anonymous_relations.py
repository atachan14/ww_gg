"""Anonymous finite populations: fresh binders, relational history, exact slot mass.

No named assignments, permutations, swap tests, or payoff comparisons occur here.
The owner supplies constructed exchangeability cells and a committed policy.
A binder is an individual, not a role marginal; reusing it asserts equality.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from .calculation_budget import tick

@dataclass(frozen=True,order=True)
class Cell:
    group:int
    role:str
    count:int
    alive:bool=True
    def __post_init__(self):
        if type(self.count)is not int or self.count<0:raise ValueError('Nonnegative exact population count required')

@dataclass(frozen=True,order=True)
class Person:
    group:int
    role:str
    alive:bool=True

@dataclass(frozen=True,order=True)
class Scan:
    day:int
    actor:int
    target:int
    color:str

@dataclass(frozen=True)
class Population:
    cells:tuple
    people:tuple=()
    scans:tuple=()
    attacks:tuple=()
    def bind(self,index):
        cell=self.cells[index]
        if not cell.count:raise ValueError('Empty anonymous class')
        cells=list(self.cells);cells[index]=replace(cell,count=cell.count-1)
        return replace(self,cells=tuple(cells),people=(*self.people,Person(cell.group,cell.role,cell.alive))),len(self.people)
    def choices(self,*,actor=None,unvisited=False,nonwolf=False):
        seen={s.target for s in self.scans if s.actor==actor} if unvisited else set()
        rows=[]
        for target,person in enumerate(self.people):
            if person.alive and target!=actor and target not in seen and (not nonwolf or person.role!='wolf'):
                rows.append(Choice(self,target,None,1))
        for index,cell in enumerate(self.cells):
            if cell.alive and cell.count and (not nonwolf or cell.role!='wolf'):
                child,target=self.bind(index);rows.append(Choice(child,target,index,cell.count))
        return tuple(rows)
    def acquire(self,day,actor,target):
        if actor==target or not self.people[actor].alive or not self.people[target].alive:raise ValueError('Scan requires two distinct night-start living individuals')
        if self.people[actor].role!='seer':raise ValueError('Only a true seer acquires a result')
        color='black' if self.people[target].role=='wolf' else 'white'
        return replace(self,scans=(*self.scans,Scan(day,actor,target,color))),color
    def death(self,target,night):
        if not self.people[target].alive:raise ValueError('Already dead target')
        people=list(self.people);people[target]=replace(people[target],alive=False)
        return replace(self,people=tuple(people),attacks=(*self.attacks,(night,target)))
    def wolves(self):
        return (tuple(i for i,p in enumerate(self.people) if p.alive and p.role=='wolf'),
                tuple((i,c.count) for i,c in enumerate(self.cells) if c.alive and c.role=='wolf' and c.count))
    def bind_seers(self):
        result=self
        for index,cell in enumerate(self.cells):
            if cell.role=='seer':
                for _ in range(cell.count):result,_=result.bind(index)
        return result

@dataclass(frozen=True)
class Choice:
    population:Population
    target:int
    fresh_cell:int|None
    multiplicity:int

@dataclass(frozen=True)
class Step:
    kind:str
    actor:int|None
    value:object
    wolves:tuple=()

@dataclass(frozen=True)
class Path:
    population:Population
    mass:F=F(1)
    multiplicity:int=1
    steps:tuple=()
    counter:F=F(1)
    bindings:tuple=() # (new binder, originating cell); existing binders keep identity

def scans(population,day,*,initial_white=False,initial_none=False):
    actors=tuple(i for i,p in enumerate(population.people) if p.role=='seer' and p.alive)
    rows=(Path(population),)
    if initial_none:return rows
    for actor in actors:
        generated=[]
        for row in rows:
            # Only this actor's previous targets affect legal choice. Other
            # actors' new private results never condition this choice policy.
            options=row.population.choices(actor=actor,unvisited=not initial_white,nonwolf=initial_white)
            total=sum(c.multiplicity for c in options)
            if not total:raise ValueError('no_legal_true_seer_target')
            for choice in options:
                tick();child,color=choice.population.acquire(day,actor,choice.target)
                bindings=row.bindings+(((choice.target,choice.fresh_cell),) if choice.fresh_cell is not None else ())
                generated.append(Path(child,row.mass*F(choice.multiplicity,total),row.multiplicity*choice.multiplicity,
                    (*row.steps,Step('seer_target',actor,choice.target),Step('seer_result',actor,color)),row.mass*F(choice.multiplicity,total),bindings))
        rows=tuple(generated)
    return rows

def attacks(path,night,*,include_self_bite=False,policy=None):
    """policy(choice) is per-slot mass committed at night start from actor Q.

    Default is uniform. Never normalize a supplied policy using the physical
    role partition or a newly revealed result: it may include zero-mass rows.
    """
    options=path.population.choices(nonwolf=not include_self_bite)
    total=sum(c.multiplicity for c in options)
    if not total:return ()
    rows=[]
    for choice in options:
        tick();weight=F(1,total) if policy is None else policy(choice)
        if not isinstance(weight,F) or weight<0:raise ValueError('Exact nonnegative committed policy required')
        bindings=path.bindings+(((choice.target,choice.fresh_cell),) if choice.fresh_cell is not None else ())
        rows.append(Path(choice.population.death(choice.target,night),path.mass*choice.multiplicity*weight,
            path.multiplicity*choice.multiplicity,(*path.steps,Step('wolf_target',None,choice.target,choice.population.wolves())),path.mass*F(choice.multiplicity,total),bindings))
    return tuple(rows)

def alias(index):
    text=''
    while True:
        text=chr(97+index%26)+text;index=index//26-1
        if index<0:return text

def person_label(population,index,groups):
    members=groups[population.people[index].group]
    return '['+','.join(map(str,members))+'の'+alias(index)+']'
