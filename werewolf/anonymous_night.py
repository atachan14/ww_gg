"""Group-native future choices, with an explicit named-prior/continuation adapter.

The input still contains existing named hypotheses. We read them once into
relational families; new choices use slots/counts, not named target products or
permutation verification. Q updates/publication and continuation remain the
shared exact named kernels. Named reconstruction is a separate boundary.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from .anonymous_relations import Cell,Person,Population,Scan,scans,attacks,alias
from .calculation_budget import tick
from .actor_information import WolfInformation
from .evaluation_branch import ActionInputs,physical_board
from .seer_acquisition import Acquisition
from .group_partition import _fix
from .board_future import outcome_key
from .joint_action_kernel import report_signature

ROLES=('wolf','seer','villager')

def role(h,p):
    return 'wolf' if h.roles[0]&(1<<(p-1)) else ('seer' if h.roles[2]&(1<<(p-1)) else 'villager')

@dataclass(frozen=True)
class Transport:
    people:tuple
    free:tuple
    def apply(self,bindings):
        people=list(self.people);free=[list(row) for row in self.free]
        for ref,index in bindings:
            if ref!=len(people):raise ValueError('Anonymous binder order changed')
            people.append(free[index].pop(0))
        return tuple(people)

def ingest(h,groups,alive):
    cells=[];free=[]
    for index,group in enumerate(groups):
        for r in ROLES:
            names=tuple(p for p in group if role(h,p)==r)
            cells.append(Cell(index,r,len(names),all(p in alive for p in group)));free.append(list(names))
    pop=Population(tuple(cells));people=[];lookup={}
    def bind(name):
        nonlocal pop
        if name not in lookup:
            index=next(i for i,row in enumerate(free) if name in row)
            pop,ref=pop.bind(index);lookup[name]=ref;people.append(name);free[index].remove(name)
        return lookup[name]
    # Ordered seer slots are distinguished individuals, never an observer's
    # knowledge of other seers. Actor policies still read the original Q.
    for group in groups:
        for name in group:
            if role(h,name)=='seer':bind(name)
    records=[]
    for a in sorted(h.acquisitions,key=lambda a:(a.day,lookup[a.player])):
        records.append(Scan(a.day,lookup[a.player],bind(a.target),a.color))
    old_attacks=tuple((a.night,bind(a.target)) for a in h.attacks)
    pop=replace(pop,scans=tuple(records),attacks=old_attacks)
    return pop,Transport(tuple(people),tuple(tuple(row) for row in free))

@dataclass(frozen=True)
class Symbol:
    index:int
    members:tuple
    def label(self):return str(self.members[0]) if len(self.members)==1 else '['+','.join(map(str,self.members))+'の'+alias(self.index)+']'

@dataclass(frozen=True)
class SymbolStep:
    kind:str
    actor:Symbol|None
    target:object
    actors:tuple=()
    public_fact:object=None
    @property
    def value(self):return self.target.index+1 if isinstance(self.target,Symbol) else self.target
    @property
    def visible_to(self):return (self.actor.index+1,) if self.actor else ()
    def label(self):
        if self.kind=='seer_target':return self.actor.label()+'が'+self.target.label()+'を占い'
        if self.kind=='seer_result':return {'white':'白','black':'黒'}[self.target]
        if self.kind=='wolf_target':
            grouped={}
            for symbol in self.actors:grouped.setdefault(symbol.members,[]).append(symbol)
            parts=[]
            for members,symbols in grouped.items():
                parts.append(symbols[0].label() if len(symbols)==1 else '['+','.join(map(str,members))+'の{'+','.join(alias(s.index) for s in symbols)+'}]')
            return ('狼集合' if len(self.actors)>1 else '')+'と'.join(parts)+'が'+self.target.label()+'を襲撃'
        if self.kind=='death_notice':
            names=self.target.members
            return '襲撃死：'+('['+','.join(('('+str(p)+')') if i==0 else str(p) for i,p in enumerate(names))+']' if len(names)>1 else str(names[0]))
        if self.kind=='publication':return str(self.target)
        raise ValueError('Unknown anonymous stage')

def symbolic_steps(path,groups):
    by_ref={};result=[]
    def symbol(ref,group=None):
        if ref not in by_ref:
            index=len(by_ref);g=path.population.people[ref].group if group is None else group
            by_ref[ref]=Symbol(index,groups[g])
        return by_ref[ref]
    for step in path.steps:
        if step.kind=='seer_target':result.append(SymbolStep(step.kind,symbol(step.actor),symbol(step.value)))
        elif step.kind=='seer_result':result.append(SymbolStep(step.kind,symbol(step.actor),step.value))
        else:
            bound,free=step.wolves
            owners=[symbol(ref) for ref in bound]
            for cell,count in free:
                owners.extend(symbol(('wolf',cell,index),path.population.cells[cell].group) for index in range(count))
            victim=symbol(step.value)
            result.extend((SymbolStep('wolf_target',None,victim,tuple(owners)),SymbolStep('death_notice',None,victim)))
    return tuple(result),tuple(by_ref.items())

@dataclass(frozen=True)
class Leaf:
    mass:F
    counter:F
    source:object
    steps:tuple
    information:object
    owner_index:int
    target:int
    outcome_index:int
    death_key:object
    report:object
    wolves:tuple
    scans:tuple
    groups:tuple
    multiplicity:int
    bindings:tuple
    selection:tuple
    correspondence:tuple
    belief:object=None

@dataclass(frozen=True)
class Branch:
    probability:F
    policy_probability:F
    counter_probability:F
    mass:F
    step:SymbolStep
    state:object
    images:tuple=()
    targets:tuple=()

class Stage:
    def __init__(self,program,leaves,prefix=()):
        self.program=program;self.leaves=tuple(leaves);self.prefix=prefix;self.public=program.source.public_state
        self.mass=sum((r.mass for r in leaves),F());self.counter=sum((r.counter for r in leaves),F());self._branches=None
    @property
    def terminal(self):return all(len(r.steps)==len(self.prefix) for r in self.leaves)
    @property
    def physical_atoms(self):
        from .seer_acquisition import normalize
        total=self.mass or self.counter
        return normalize(tuple(replace(h,mass=h.mass*(r.mass if self.mass else r.counter)/total) for r in self.leaves if (r.mass if self.mass else r.counter) for h in r.source.private.hypotheses))
    def actor_information(self,actor):
        return tuple((h.roles,tuple(a for a in h.acquisitions if a.player==actor),h.mass) for h in self.public.hypotheses)
    def branches(self):
        if self._branches is not None:return self._branches
        buckets={};index=len(self.prefix)
        for leaf in self.leaves:
            if index<len(leaf.steps):buckets.setdefault(leaf.steps[index],[]).append(leaf)
        rows=[]
        for step,leaves in buckets.items():
            mass=sum((r.mass for r in leaves),F());counter=sum((r.counter for r in leaves),F())
            rows.append(Branch(mass/self.mass if self.mass else counter/self.counter,mass/self.mass if self.mass else F(),counter/self.counter,mass,step,Stage(self.program,leaves,(*self.prefix,step))))
        self._branches=tuple(rows);return self._branches
    def outcomes(self):
        buckets={}
        for leaf in self.leaves:buckets.setdefault(leaf.source,[]).append(leaf)
        return tuple((sum((r.mass for r in rows),F()),sum((r.counter for r in rows),F()),rows[0],tuple((r,self.program.identity) for r in rows)) for rows in buckets.values())
    def value(self,engine):
        if self.terminal:
            total=self.mass or self.counter
            return sum(((mass if self.mass else counter)/total*self.program.continuation(engine,leaf) for mass,counter,leaf,images in self.outcomes()),F())
        return sum((b.probability*b.state.value(engine) for b in self.branches() if (b.policy_probability if self.mass else b.probability)),F())

class Program:
    method='anonymous-relational-v1'
    def __init__(self,source,groups,leaves,stats):
        self.source=source;self.groups=groups;self.leaves=tuple(leaves);self.identity=tuple(range(1,source.public.player_count+1));self.root=Stage(self,self.leaves);self.values={};self.stats=stats
    def continuation(self,engine,leaf):
        if leaf.source not in self.values:
            if leaf.belief is not None:self.values[leaf.source]=engine.anonymous_values.value(leaf.belief)
            else:
                with engine.group_scope(leaf.groups):self.values[leaf.source]=engine.solve(*leaf.source,physical=leaf.source.physical)
        return self.values[leaf.source]

def selection(h):return (h.roles,tuple((a.day,a.player,a.target,a.color) for a in h.acquisitions))

def compile_anonymous(engine,source,groups):
    # Native future-choice generator. Existing named priors, public Q updates,
    # morning publications and continuation are explicit compatibility boundaries.
    from .night_program import supported
    if not supported(engine,source) or not hasattr(engine,'aggregate_wolf') or engine.strategy.include_self_bite:return None
    b=source.public;groups=tuple(groups)+tuple((p,) for p in range(1,b.player_count+1) if not any(p in g for g in groups))
    key=(source,groups)
    cache=getattr(engine,'anonymous_programs',None)
    if cache is None:engine.anonymous_programs={};cache=engine.anonymous_programs
    if key in cache:return cache[key]
    belief=getattr(engine,'anonymous_beliefs',{}).get(source)
    if belief is not None:belief=belief.refine(groups)
    policies={};offsets={};offset=0;native_paths=0
    def commit(h):
        nonlocal offset
        info=WolfInformation.from_hypothesis(h)
        if info not in policies:
            if belief is not None:
                vector=tuple(sum(bool(info.initial_roster&(1<<(p-1))) for p in group) for group in groups)
                policy=engine.anonymous_values.wolf_policy(engine.anonymous_values.scalar(belief),vector)
                policies[info]={p:policy.get(index,F()) for index,group in enumerate(groups) for p in group if p in b.alive and not info.initial_roster&(1<<(p-1))}
            else:
                with engine.actor_scope(info):policies[info]=dict(engine.wolf_policy(b,source.public_state,source.past,info.initial_roster,info.attacks))
            offsets[info]=offset;offset+=len(policies[info])
        return info,policies[info]
    if belief is not None:
        from .anonymous_materialization import representative,expand
        def factory(atom):
            h,transport=representative(atom,groups);info,policy=commit(h)
            def committed(choice,bindings):
                extra=((choice.target,choice.fresh_cell),) if choice.fresh_cell is not None else ()
                names=transport.apply((*bindings,*extra));return policy.get(names[choice.target],F())
            return committed
        flow=belief.night(factory)
        public=replace(source.public_state,hypotheses=expand(flow.acquired_q,groups),rosters=source.public_state.rosters+(b.alive,))
        def futures():
            for row in flow.rows:
                h,transport=representative(row.before,groups)
                yield row.counter/row.path.counter,h,transport,row.path,row
        family_count=len(belief.p.rows)
    else:
        flow=None;families={}
        for h in source.private.hypotheses:
            tick();population,transport=ingest(h,groups,b.alive)
            if population not in families:families[population]=[F(),h,transport]
            families[population][0]+=h.mass
        public=engine.acquire(b,source.public_state)
        def futures():
            for population,(family_mass,h,transport) in families.items():
                info,policy=commit(h)
                for scan in scans(population,b.day+1):
                    def committed(choice):
                        extra=((choice.target,choice.fresh_cell),) if choice.fresh_cell is not None else ()
                        names=transport.apply((*scan.bindings,*extra));return policy.get(names[choice.target],F())
                    for path in attacks(scan,b.day,policy=committed):yield family_mass,h,transport,path,None
        family_count=len(families)
    leaves=[]
    for family_mass,h,transport,path,owned_row in futures():
        info,policy=commit(h)
        native_paths+=1;names=transport.apply(path.bindings);target=names[path.steps[-1].value]
        obtained=tuple(sorted(Acquisition(a.day,names[a.actor],names[a.target],a.color) for a in path.population.scans))
        own=replace(source.private,hypotheses=(replace(h,acquisitions=obtained,mass=F(1)),),rosters=source.private.rosters+(b.alive,))
        payload=ActionInputs(public,source.past,own,None,physical_board(b,own,source.physical))
        deaths=engine.action_policy.outcomes(b,payload,target)
        symbols,binding_map=symbolic_steps(path,groups)
        for index,death in enumerate(deaths):
            # Pure common Q/P projection; do not regenerate scans from
            # the representative's named action recipe here.
            child=engine.action_policy._project_roles(b,payload,death,target)
            reports=engine.report_children(child) if child.public.winner is None else ()
            rows=tuple((mass,after,report_signature(after)) for q,mass,after in reports) if reports else ((F(1),child,None),)
            for report_mass,after,report in rows:
                steps=tuple(replace(step,public_fact=child.public.winner) if step.kind=='death_notice' else step for step in symbols)
                if child.public.winner is None and any(claim in ('seer','medium') for claim in b.claims):
                    from .public_convergence import public_transport,transport_record
                    mapping=public_transport(source,after,groups)
                    published=[transport_record(r,mapping) for r in after.past if r not in source.past]
                    text='／'.join('Player'+str(r.player)+'：Player'+str(r.target)+('白' if r.color=='white' else '黒') for r in published)
                    steps=(*steps,SymbolStep('publication',None,text or '公開なし'))
                wolves=tuple(p for p in range(1,b.player_count+1) if h.roles[0]&(1<<(p-1)))
                acquired=tuple(sorted((a.player,a.target) for a in obtained if a.day==b.day+1))
                factor=family_mass*death.probability*report_mass
                leaf_h=after.private.hypotheses[0]
                named=[]
                for ref,symbol in binding_map:
                    if type(ref)is int:person=names[ref]
                    else:
                        _,cell,slot=ref;person=tuple(p for p in transport.free[cell] if p not in names)[slot]
                    named.append((symbol.index,person))
                leaf_belief=None
                if owned_row is not None:
                    from .anonymous_belief import Law
                    leaf_belief=replace(flow.branch(owned_row.observation,counter=True)[1],p=Law(((F(1),owned_row.atom),)))
                leaves.append(Leaf(factor*path.mass,factor*path.counter,replace(after,board_data=None,provenance=None),steps,info,offsets[info],target,index,outcome_key(death),report,wolves,acquired,_fix(groups,(*wolves,target,*(p for pair in acquired for p in pair))),path.multiplicity,binding_map,selection(leaf_h),tuple(named),leaf_belief))
    result=Program(source,groups,leaves,dict(named_prior_atoms=0 if belief is not None else len(source.private.hypotheses),relational_families=family_count,structural_joint_paths=native_paths,permutation_checks=0,belief_owned=belief is not None))
    result.belief=belief;result.belief_flow=flow
    cache[key]=result;return result


def shared_night(engine,source,groups):
    if getattr(engine,'anonymous_nights',False):
        program=compile_anonymous(engine,source,groups)
        if program is not None:return program
    from .night_program import compile_night
    return compile_night(engine,source,groups)
