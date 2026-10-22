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
    memories:tuple=()
    effects:tuple=()
    def bind_roles(self,roles):
        result=self
        for index,cell in enumerate(self.cells):
            if cell.role in roles:
                for _ in range(cell.count):result,_=result.bind(index)
        return result
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
    def bind_seers(self):return self.bind_roles(('seer',))

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
    from .anonymous_abilities import Context,run
    from .ability_adapters import Divination
    if initial_none:return (Path(population),)
    return run(population,(Divination(),),Context(day-1,day,initial_white=initial_white))


def attacks(path,night,*,include_self_bite=False,policy=None):
    from .anonymous_abilities import Context,choices,resolve
    from .ability_adapters import WolfAttack
    context=Context(night,night+1,include_self_bite=include_self_bite)
    committed=None if policy is None else lambda choice,bindings:policy(choice)
    rows=choices(path,WolfAttack(),None,context,committed)
    return tuple(resolve(row,context)[0] for row in rows)


def alias(index):
    text=''
    while True:
        text=chr(97+index%26)+text;index=index//26-1
        if index<0:return text

def person_label(population,index,groups):
    members=groups[population.people[index].group]
    return '['+','.join(map(str,members))+'の'+alias(index)+']'
