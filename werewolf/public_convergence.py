"""Public-observation convergence with weighted hidden continuations.

Construct one name transport inside inherited public classes, never search for
swaps or merge by payoff. A public key includes Q and all public history. P is
mixed with actual reach mass; it is never fed back into public/actor beliefs.
"""
from dataclasses import dataclass,replace,fields
from fractions import Fraction as F
from hashlib import sha256
from .evaluation_branch import ContinuationInputs,physical_board
from .seer_acquisition import normalize

LABELS=frozenset(('player','reporter','actor','target'))

def transport_record(record,mapping):
    return replace(record,**{f.name:mapping[getattr(record,f.name)-1] for f in fields(record) if f.name in LABELS})

def transport_source(source,mapping):
    if source.observer is not None:raise ValueError('Public convergence excludes personal observers')
    if mapping==tuple(range(1,source.public.player_count+1)):return source
    def mask(value):return sum(1<<(mapping[p]-1) for p in range(len(mapping)) if value&(1<<p))
    def board(b):
        from .exact import replace_worlds
        triplets=lambda rows:tuple(sorted((d,mapping[a-1],mapping[t-1]) for d,a,t in rows))
        return replace_worlds(b,tuple(sorted((*tuple(mask(m) for m in w[:-1]),w[-1]) for w in b.worlds)),
            alive=tuple(sorted(mapping[p-1] for p in b.alive)),claims=tuple(c for p,c in sorted((mapping[p-1],c) for p,c in enumerate(b.claims,1))),
            history=tuple(transport_record(r,mapping) for r in b.history),reports=tuple(transport_record(r,mapping) for r in b.reports),
            medium_opportunities=triplets(b.medium_opportunities),report_resolved=triplets(b.report_resolved),
            guard_prior_roster=None if b.guard_prior_roster is None else (b.guard_prior_roster[0],tuple(sorted(mapping[p-1] for p in b.guard_prior_roster[1]))))
    def law(s):
        hypotheses=normalize(tuple(replace(h,roles=tuple(mask(m) for m in h.roles),acquisitions=tuple(sorted(transport_record(a,mapping) for a in h.acquisitions)),
            guards=tuple(transport_record(g,mapping) for g in h.guards),attacks=tuple(transport_record(a,mapping) for a in h.attacks)) for h in s.hypotheses))
        return replace(s,hypotheses=hypotheses,rosters=tuple(tuple(sorted(mapping[p-1] for p in row)) for row in s.rosters),tracked=None if s.tracked is None else tuple(sorted(mapping[p-1] for p in s.tracked)))
    return ContinuationInputs(board(source.public),law(source.public_state),tuple(sorted(transport_record(r,mapping) for r in source.past)),law(source.private),None,board(source.physical))

def public_transport(before,after,groups):
    # Bind observable new corpse/report positions in event order. Remaining
    # names fill residual slots monotonically. Private results play no part.
    chosen={};used=set()
    records=tuple(after.public.history[len(before.public.history):])+tuple(r for r in after.past if r not in before.past)+tuple(r for r in after.public.reports if r not in before.public.reports)
    for record in records:
        for field in ('player','reporter','target'):
            if not hasattr(record,field):continue
            person=getattr(record,field)
            if person in chosen:continue
            group=next((g for g in groups if person in g),(person,))
            target=next(p for p in group if p not in used);chosen[person]=target;used.add(target)
    for group in groups:
        for person,target in zip((p for p in group if p not in chosen),(p for p in group if p not in used)):
            chosen[person]=target;used.add(target)
    return tuple(chosen.get(p,p) for p in range(1,before.public.player_count+1))

def canonical_board(board):
    # Only probability tables are unordered. Histories, names, public timing and
    # private directed memories retain their full original meaning.
    updates={name:tuple(sorted(getattr(board,name))) for name in ('belief','role_belief','world_belief') if tuple(sorted(getattr(board,name)))!=getattr(board,name)}
    return replace(board,**updates) if updates else board


def state_key(source):
    return (canonical_board(source.public),source.public_state,source.past,source.private,source.observer,canonical_board(source.physical))


def public_key(source):return canonical_board(source.public),source.public_state,source.past

def legacy_digest(source):return sha256(repr((source.public,source.public_state,source.past)).encode()).hexdigest()[:24]

def matches_digest(source,value):return value in (digest(source),legacy_digest(source))

def digest(source):return sha256(repr(public_key(source)).encode()).hexdigest()[:24]

def mix(weighted):
    rows=tuple((weight,source) for weight,source in weighted if weight>0)
    total=sum((weight for weight,source in rows),F())
    if not total:raise ValueError('No positive physical component mass')
    first=rows[0][1];key=public_key(first)
    if any(public_key(source)!=key for weight,source in rows):raise ValueError('Different public posterior/history cannot converge')
    atoms=normalize(tuple(replace(h,mass=h.mass*weight/total) for weight,source in rows for h in source.private.hypotheses))
    own=replace(first.private,hypotheses=atoms)
    return replace(first,private=own,physical=physical_board(first.public,own,first.physical),board_data=None,provenance=None)

@dataclass(frozen=True)
class TransportEvidence:
    mapping:tuple
    def __call__(self,source):return transport_source(source,self.mapping)

@dataclass(frozen=True)
class MixtureEvidence:
    components:tuple # (fresh reconstructible request, deterministic map, mass)
    def __call__(self,source):return mix(tuple((weight,transport_source(request.roles(),mapping)) for request,mapping,weight in self.components))


def observation_branches(engine,source,target,*,counter=False,publish=True):
    from .actor_information import wolf_information_keys,condition_wolf_choice
    from .evaluation_branch import ActionInputs
    b=source.public;policies={}
    for info in wolf_information_keys(source.private):
        if counter:
            legal=tuple(p for p in b.alive if engine.strategy.include_self_bite or not info.initial_roster&(1<<(p-1)))
            policies[info.initial_roster,info.attacks]=tuple((p,F(1,len(legal))) for p in legal)
        else:
            with engine.actor_scope(info):policies[info.initial_roster,info.attacks]=engine.wolf_policy(b,source.public_state,source.past,info.initial_roster,info.attacks)
    try:mass,own=condition_wolf_choice(source.private,policies,target)
    except ValueError:return ()
    from .action_flow import resolve_action
    payload,outcomes=resolve_action(b,ActionInputs(source.public_state,source.past,own,None,physical_board(b,own,source.physical)),target,engine.action_policy)
    rows=[]
    for death in outcomes:
        child=engine.action_policy._project_roles(b,payload,death,target)
        reports=engine.report_children(child) if publish and child.public.winner is None else ()
        for weight,after in (tuple((p,c) for q,p,c in reports) if reports else ((F(1),child),)):
            rows.append((mass*death.probability*weight,replace(after,board_data=None,provenance=None)))
    return tuple(rows)

def public_observation_orbits(engine,source,target,groups,*,counter=False,publish=True):
    buckets={}
    for weight,after in observation_branches(engine,source,target,counter=counter,publish=publish):
        mapping=public_transport(source,after,groups);moved=transport_source(after,mapping)
        buckets.setdefault(public_key(moved),[]).append((weight,moved))
    return tuple((sum((w for w,s in rows),F()),mix(rows)) for rows in buckets.values())

def public_night_observations(engine,source,groups,*,counter=False,publish=True):
    """Integrate unobserved bites too, notably every bite behind a guard success."""
    buckets={}
    # Named-Q boundary: a prevented attack leaves its target unobserved.
    # Integrate every name instead of pinning an invisible representative.
    target_groups=tuple((p,) for p in source.public.alive) if source.public.initial_hunter_count else groups
    for group in target_groups:
        living=tuple(p for p in group if p in source.public.alive)
        if not living:continue
        target=living[0]
        for mass,after in public_observation_orbits(engine,source,target,groups,counter=counter,publish=publish):
            buckets.setdefault(public_key(after),[]).append((mass*len(living),after,target))
    return tuple((sum(mass for mass,after,target in rows),mix(tuple((mass,after) for mass,after,target in rows)),rows[0][2]) for rows in buckets.values())


def prefix_likelihood(h,before,after,groups,prefix):
    """Bind a visible anonymous relation pattern against an existing named atom.

    This is an evidence predicate, not generation of named future actions or
    a swap-safety test. Seer slot order is an anonymous coordinate gauge.
    Unvisited/random acquisition and policy masses are already in h.mass.
    """
    from .anonymous_night import SymbolStep
    if not prefix:return F(1)
    day=before.public.day+1;records={a.player:a for a in h.acquisitions if a.day==day}
    living=before.public.alive;wolves={p for p in living if h.roles[0]&(1<<(p-1))}
    victim=next((a.target for a in h.attacks if a.night==before.public.day),None)
    rows=[({},(),F(1))]
    def bind(mapping,symbol,name):
        if name not in symbol.members:return None
        if symbol.index in mapping:return mapping if mapping[symbol.index]==name else None
        if name in mapping.values():return None
        return {**mapping,symbol.index:name}
    for step in prefix:
        next_rows=[]
        for mapping,actors,weight in rows:
            if step.kind=='ability_dead':
                role={'medium_result':1,'seer_target':2,'seer_result':2,'guard_target':3}[step.target]
                if h.roles[role] and not any(h.roles[role]&(1<<(p-1)) for p in living):next_rows.append((mapping,actors,weight))
            elif step.kind=='seer_target':
                group_index=groups.index(step.actor.members)
                earlier={p for group in groups[:group_index] for p in group}
                if any(p in earlier and p not in actors for p in records):continue
                candidates=(mapping[step.actor.index],) if step.actor.index in mapping else tuple(p for p in records if p in step.actor.members and p not in actors)
                slots=sum(p in step.actor.members for p in records)-sum(p in step.actor.members for p in actors)
                if not slots:continue
                for actor in candidates:
                    if actor in actors or actor not in records:continue
                    chosen=bind(mapping,step.actor,actor)
                    if chosen is None:continue
                    chosen=bind(chosen,step.target,records[actor].target)
                    if chosen is not None:next_rows.append((chosen,(*actors,actor),weight/F(slots)))
            elif step.kind=='seer_result':
                actor=mapping.get(step.actor.index)
                if actor in records and records[actor].color==step.target:next_rows.append((mapping,actors,weight))
            elif step.kind=='wolf_target':
                if len(actors)!=len(records) or step.target.index in {s.index for s in step.actors}:continue
                allocated={mapping[s.index] for s in step.actors if s.index in mapping}
                if not allocated<=wolves:continue
                expected={};actual={}
                for symbol in step.actors:expected[symbol.members]=expected.get(symbol.members,0)+1
                for group in groups:
                    count=len(wolves&set(group))
                    if count:actual[tuple(group)]=count
                if expected!=actual:continue
                chosen=bind(mapping,step.target,victim)
                if chosen is not None:next_rows.append((chosen,actors,weight))
            elif step.kind=='death_notice':
                if step.public_fact!=after.public.winner:continue
                chosen=bind(mapping,step.target,victim)
                if chosen is not None:next_rows.append((chosen,actors,weight))
            elif step.kind=='publication':
                text='／'.join('Player'+str(r.player)+'：Player'+str(r.target)+('白' if r.color=='white' else '黒') for r in after.past if r not in before.past) or '公開なし'
                from .tree_public_updates import publication_label
                if step.target in (text,publication_label(before,after)):next_rows.append((mapping,actors,weight))
        rows=next_rows
    return sum((weight for mapping,actors,weight in rows),F())

def condition_prefix(source,before,groups,prefix):
    atoms=[];mass=F()
    for h in source.private.hypotheses:
        likelihood=prefix_likelihood(h,before,source,groups,prefix)
        if likelihood:atoms.append(replace(h,mass=h.mass*likelihood));mass+=h.mass*likelihood
    if not mass:raise ValueError('Anonymous relation evidence has zero support')
    own=replace(source.private,hypotheses=normalize(tuple(atoms)))
    return mass,replace(source,private=own,physical=physical_board(source.public,own,source.physical),board_data=None,provenance=None)

@dataclass(frozen=True)
class NightObservationEvidence:
    engine:object
    target:int
    public_digest:str
    groups:tuple
    prefix:tuple=()
    counter:bool=False
    def __call__(self,source):
        graph=getattr(self.engine,'evaluation_graph',None)
        projection=graph.public_projection(source,self.groups,evaluate=True,counter=self.counter) if graph is not None else None
        rows=tuple((e.probability,e.source,e.target) for e in projection.edges) if projection is not None else public_night_observations(self.engine,source,self.groups,counter=self.counter)
        selected=next((after for weight,after,target in rows if matches_digest(after,self.public_digest)),None)
        if selected is None:raise ValueError('Public night observation unavailable')
        return condition_prefix(selected,source,self.groups,self.prefix)[1] if self.prefix else selected


@dataclass(frozen=True)
class ArrivalObservationEvidence:
    engine:object
    target:int
    public_digest:str
    groups:tuple
    counter:bool=False
    def __call__(self,source):
        graph=getattr(self.engine,'evaluation_graph',None)
        projection=graph.public_projection(source,self.groups,evaluate=True,counter=self.counter) if graph is not None else None
        rows=tuple((e.probability,e.source,e.target) for e in projection.arrivals) if projection is not None else public_night_observations(self.engine,source,self.groups,counter=self.counter,publish=False)
        selected=next((after for weight,after,target in rows if matches_digest(after,self.public_digest)),None)
        if selected is None:raise ValueError('Pre-report public arrival unavailable')
        return selected
