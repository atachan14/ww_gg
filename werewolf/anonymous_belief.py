"""Exact count-native beliefs; names are public pins, never role assignments.

Q uses public observation compatibility. P additionally carries the committed
actor policy. Publicly unknown people remain anonymous across acquisitions and
deaths; their directed private histories are part of each immutable atom.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from math import factorial
from .anonymous_relations import Cell,Person,Population,scans,attacks
from .calculation_budget import tick

# Named role keys belong to the rules/schema boundary, not the count algebra.

def allocations(total,counts):
    if len(counts)==1:
        if total<=counts[0]:yield (total,)
        return
    for n in range(min(total,counts[0])+1):
        for rest in allocations(total-n,counts[1:]):yield (n,*rest)

def multinomial(counts):
    result=factorial(sum(counts))
    for n in counts:result//=factorial(n)
    return result

@dataclass(frozen=True)
class Atom:
    population:Population
    pins:tuple=() # (public name, anonymous person); no hidden role truth in names
    def pin(self,name,groups):
        known=dict(self.pins)
        if name in known:return ((F(1),self,known[name]),)
        group=next(i for i,g in enumerate(groups) if name in g)
        occupied=set(known.values());options=[]
        for ref,person in enumerate(self.population.people):
            if person.group==group and ref not in occupied:options.append((1,self.population,ref))
        for index,cell in enumerate(self.population.cells):
            if cell.group==group and cell.count:
                child,ref=self.population.bind(index);options.append((cell.count,child,ref))
        total=sum(n for n,p,ref in options)
        if not total:raise ValueError('Public name has no anonymous slot')
        return tuple((F(n,total),Atom(pop,tuple(sorted((*self.pins,(name,ref))))),ref) for n,pop,ref in options)
    def publish_identity(self,ref,groups):
        known={r:n for n,r in self.pins}
        if ref in known:return known[ref],self
        group=groups[self.population.people[ref].group];used={n for n,r in self.pins}
        name=next(n for n in group if n not in used)
        return name,replace(self,pins=tuple(sorted((*self.pins,(name,ref)))))

@dataclass(frozen=True)
class Law:
    rows:tuple # (normalized exact weight, Atom)
    @classmethod
    def weighted(cls,rows):
        buckets={}
        for weight,atom in rows:
            tick()
            if weight<0:raise ValueError('Negative belief mass')
            if weight:buckets[atom]=buckets.get(atom,F())+weight
        total=sum(buckets.values(),F())
        if not total:raise ValueError('Anonymous observation has zero support')
        return total,cls(tuple((q/total,atom) for atom,q in buckets.items()))
    def acquire(self,day,initial_rule=None):
        rows=[]
        for mass,atom in self.rows:
            pop=atom.population
            if initial_rule is not None:pop=pop.bind_seers()
            for path in scans(pop,day,initial_white=initial_rule=='random_white',initial_none=initial_rule=='none'):
                rows.append((mass*path.mass,replace(atom,population=path.population)))
        return Law.weighted(rows)[1]
    def condition(self,predicate):return Law.weighted((mass,atom) for mass,atom in self.rows if predicate(atom))
    def marginal(self,name,groups,role):
        return sum((mass*weight for mass,atom in self.rows for weight,child,ref in atom.pin(name,groups)
                    if child.population.people[ref].role==role),F())
    def refine(self,old,new):
        # Refinement distinguishes coordinates, never guesses symmetry from a
        # payoff/law comparison. Pin all but one residual subgroup by construction.
        law=self
        for group in old:
            parts=[tuple(p for p in g if p in group) for g in new];parts=[g for g in parts if g]
            if not parts:raise ValueError('Partition lost people')
            residual=max(parts,key=len)
            for name in (p for part in parts if part!=residual for p in part):
                law=Law.weighted((mass*q,child) for mass,atom in law.rows for q,child,ref in atom.pin(name,old))[1]
        result=[]
        for mass,atom in law.rows:
            by_name={ref:name for name,ref in atom.pins};used={name for name,ref in atom.pins}
            def residual_group(index):
                names=[p for p in old[index] if p not in used]
                if not names:return next(i for i,g in enumerate(new) if any(p in g for p in old[index]))
                return next(i for i,g in enumerate(new) if all(p in g for p in names))
            people=tuple(replace(person,group=next(i for i,g in enumerate(new) if by_name[ref] in g) if ref in by_name else residual_group(person.group)) for ref,person in enumerate(atom.population.people))
            cells=tuple(replace(cell,group=residual_group(cell.group)) for cell in atom.population.cells)
            result.append((mass,replace(atom,population=replace(atom.population,people=people,cells=cells))))
        return Law.weighted(result)[1]

def initial_law(groups,counts,initial_rule='random_white'):
    roles=tuple(counts)
    counts=tuple(counts[role] for role in roles)
    if sum(counts)!=sum(map(len,groups)):raise ValueError('Role counts do not fill population')
    denominator=multinomial(counts);rows=[]
    def visit(index,left,cells,ways):
        if index==len(groups):
            if not any(left):rows.append((F(ways,denominator),Atom(Population(cells))))
            return
        for chosen in allocations(len(groups[index]),left):
            tick();visit(index+1,tuple(a-b for a,b in zip(left,chosen)),(*cells,*(Cell(index,role,n) for role,n in zip(roles,chosen))),ways*multinomial(chosen))
    visit(0,counts,(),1)
    return Law.weighted(rows)[1].acquire(1,initial_rule)

def winner(pop):
    wolves=sum(c.count for c in pop.cells if c.alive and c.role=='wolf')+sum(p.alive and p.role=='wolf' for p in pop.people)
    others=sum(c.count for c in pop.cells if c.alive and c.role!='wolf')+sum(p.alive and p.role!='wolf' for p in pop.people)
    return 'village' if not wolves else ('wolf' if wolves>=others else None)

@dataclass(frozen=True)
class Death:
    day:int
    phase:str
    target:int

@dataclass(frozen=True)
class Belief:
    groups:tuple
    q:Law
    p:Law
    day:int=1
    phase:str='day'
    history:tuple=()
    @classmethod
    def initial(cls,groups,counts,initial_rule='random_white'):
        law=initial_law(groups,counts,initial_rule);return cls(groups,law,law)
    def refine(self,groups):
        groups=tuple(groups)
        return self if groups==self.groups else replace(self,groups=groups,q=self.q.refine(self.groups,groups),p=self.p.refine(self.groups,groups))
    def execute(self,name):
        if self.phase!='day':raise ValueError('Execution requires day')
        if any(winner(atom.population) is not None for mass,atom in self.p.rows):raise ValueError('Terminal belief has no actions')
        def branches(law):
            rows={}
            for mass,atom in law.rows:
                for weight,child,ref in atom.pin(name,self.groups):
                    person=child.population.people[ref]
                    if not person.alive:raise ValueError('Execution target already dead')
                    people=list(child.population.people);people[ref]=replace(person,alive=False)
                    child=replace(child,population=replace(child.population,people=tuple(people)))
                    rows.setdefault(winner(child.population),[]).append((mass*weight,child))
            return {key:Law.weighted(values) for key,values in rows.items()}
        q,p=branches(self.q),branches(self.p)
        return tuple((mass,key,replace(self,q=q[key][1],p=law,phase='night',history=(*self.history,Death(self.day,'day',name)))) for key,(mass,law) in p.items())
    def compositions(self):
        rows={}
        for mass,atom in self.p.rows:
            pop=atom.population
            count=lambda role:sum(p.alive and p.role==role for p in pop.people)+sum(c.count for c in pop.cells if c.alive and c.role==role)
            key=tuple(count(role) for role in ('wolf','medium','seer','hunter','villager'));rows[key]=rows.get(key,F())+mass
        return tuple(sorted(rows.items()))
    def night(self,policy_factory=None,*,acquire=True):return NightFlow(self,policy_factory,acquire=acquire)

@dataclass(frozen=True)
class NightRow:
    mass:F
    counter:F
    atom:Atom
    steps:tuple
    observation:tuple # public victim representative, winner
    before:Atom
    path:object

class NightFlow:
    def __init__(self,before,policy_factory=None,*,acquire=True):
        if before.phase!='night':raise ValueError('Night transition requires night')
        if any(winner(atom.population) is not None for mass,atom in before.p.rows):raise ValueError('Terminal belief has no actions')
        self.before=before;rows=[]
        for mass,atom in before.p.rows:
            # Called before any new acquisition. Later stages cannot alter it.
            committed=None if policy_factory is None else policy_factory(atom)
            from .anonymous_relations import Path
            for scan in (scans(atom.population,before.day+1) if acquire else (Path(atom.population),)):
                policy=None if committed is None else lambda choice:committed(choice,scan.bindings)
                for path in attacks(scan,before.day,policy=policy):
                    victim=path.steps[-1].value
                    after=replace(atom,population=path.population)
                    name,after=after.publish_identity(victim,before.groups)
                    from .anonymous_night import symbolic_steps
                    steps,bindings=symbolic_steps(path,before.groups)
                    result=winner(path.population)
                    steps=tuple(replace(step,public_fact=result) if step.kind=='death_notice' else step for step in steps)
                    rows.append(NightRow(mass*path.mass,mass*path.counter,after,steps,(name,result),atom,path))
        self.rows=tuple(rows);self.acquired_q=before.q.acquire(before.day+1) if acquire else before.q;self._branches={}
    def branch(self,observation,prefix=(),counter=False):
        name,result=observation
        def matching(row):return row.observation==observation and row.steps[:len(prefix)]==tuple(prefix)
        mass,p=Law.weighted(((row.counter if counter else row.mass),row.atom) for row in self.rows if matching(row))
        if observation not in self._branches:
            public=[]
            for weight,atom in self.acquired_q.rows:
                for q,child,ref in atom.pin(name,self.before.groups):
                    if child.population.people[ref].role=='wolf':continue
                    pop=child.population.death(ref,self.before.day)
                    if winner(pop)==result:public.append((weight*q,replace(child,population=pop)))
            self._branches[observation]=Law.weighted(public)[1]
        child=replace(self.before,q=self._branches[observation],p=p,day=self.before.day+1,phase='day',history=(*self.before.history,Death(self.before.day,'night',name)))
        return mass,child
    def observations(self):return tuple(dict.fromkeys(row.observation for row in self.rows))
