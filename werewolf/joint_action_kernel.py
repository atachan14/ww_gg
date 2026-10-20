"""Joint night actions over constructed player partitions, with named transports.

Only existing conditional-policy, acquisition, death and publication generators
produce laws. An orbit retains a full representative Q/P state plus its named
images; a representative wolf is a coordinate, never a globally selected world.
"""
from dataclasses import dataclass,asdict,replace
from fractions import Fraction as F
from .actor_information import WolfInformation,wolf_information_keys
from .evaluation_branch import ActionInputs,ContinuationInputs,physical_board
from .action_flow import resolve_action
from .group_partition import _fix,_frame_groups
from .board_future import outcome_key
from .calculation_budget import tick


def supported(engine,source):
    b=source.public
    if (engine.strategy.day=='max' and not engine.max_grouped):return False
    if (b.phase!='night' or b.winner or b.initial_hunter_count or source.observer is not None
        or engine.acquisition_provenance is not None or engine.trace is not None
        or engine.retire_uninformative_scans
        or any(engine.strategy.disclosure_for(r)!='all' for r in ('seer','medium'))):return False
    actors={p for p in b.alive if b.role_probability(p,'seer')}
    if not actors or actors!={p for p in b.alive if b.claims[p-1]=='seer'}:return False
    if any(b.role_probability(p,'seer')!=1 for p in actors):return False
    return all(law.tracked is None or actors<=set(law.tracked) for law in (source.public_state,source.private))


def report_signature(source,mapping=None):
    def moved(record):
        row=asdict(record)
        if mapping:
            for k in ('player','reporter','target'):
                if k in row:row[k]=mapping[row[k]-1]
        return row
    return {'seer':sorted((moved(r) for r in source.past),key=lambda r:(r['acquired_day'],r['player'],r['published_day'],r['target'],r['color'])),
            'medium':sorted((moved(r) for r in source.public.reports),key=lambda r:(r['day'],r['reporter'],r['target'],r['color']))}


@dataclass(frozen=True)
class NamedAction:
    information:object
    owner_index:int
    target:int
    mapping:tuple
    policy_mass:F
    fallback_mass:F


@dataclass(frozen=True)
class ActionPlan:
    information:object
    source:object
    groups:tuple
    target:int
    policy_mass:F
    fallback_mass:F
    members:tuple


@dataclass(frozen=True)
class ActionGroup:
    targets:tuple
    plans:tuple
    policy_mass:F
    fallback_mass:F


@dataclass(frozen=True)
class JointOutcome:
    probability:F
    source:object
    groups:tuple
    outcome_index:int
    report_index:object
    death_key:object
    images:tuple = ()


def mapping_for(groups,n,original,other,target,victim):
    """One constructed bijection between equal owner/victim classes; no search."""
    mapping=list(range(1,n+1))
    for group in groups:
        for wolf in (False,True):
            left=[p for p in group if bool(original&(1<<(p-1)))==wolf]
            right=[p for p in group if bool(other&(1<<(p-1)))==wolf]
            if target in left:
                mapping[target-1]=victim;left.remove(target);right.remove(victim)
            for a,b in zip(left,right):mapping[a-1]=b
    return tuple(mapping)


def compile_actions(engine,source,groups):
    """Plan actor/target orbits before constructing physical or report children."""
    b=source.public;n=b.player_count
    groups=tuple(groups)+tuple((p,) for p in range(1,n+1) if not any(p in g for g in groups))
    cache_key=(source,groups)
    if cache_key in engine.joint_actions:return engine.joint_actions[cache_key]
    cells=engine.wolf_cells(source.private)
    def owner_key(info):
        counts=tuple(sum(bool(info.initial_roster&(1<<(p-1))) for p in g) for g in groups)
        return (counts,info.attacks) if engine.aggregate_wolf else (info.initial_roster,info.attacks)
    plans={};owners={};offset=0
    for info,mass,law in cells:
        tick()
        with engine.actor_scope(info):
            policy=dict(engine.wolf_policy(b,source.public_state,source.past,info.initial_roster,info.attacks))
            legal=tuple(p for p in b.alive if engine.strategy.include_self_bite or not info.initial_roster&(1<<(p-1)))
            orbits=engine.target_orbits(legal)
            actor_groups=engine.groups
        owners[owner_key(info)]=(info,mass,law,policy,legal,orbits,actor_groups)
    named={}
    for h in source.private.hypotheses:
        info=WolfInformation.from_hypothesis(h);named[info]=named.get(info,F())+h.mass
    indices={}
    for info in wolf_information_keys(source.private):
        indices[info]=offset;offset+=len(owners[owner_key(info)][3])
    for key,(info,mass,law,policy,legal,orbits,actor_groups) in owners.items():
        own=ContinuationInputs(b,source.public_state,source.past,law,source.observer,physical_board(b,law,source.physical))
        for orbit in orbits:
            target=orbit[0];members=[]
            for named_info,named_mass in named.items():
                if owner_key(named_info)!=key:continue
                base=mapping_for(groups,n,info.initial_roster,named_info.initial_roster,None,None)
                for victim in tuple(base[p-1] for p in orbit):
                    mapping=mapping_for(groups,n,info.initial_roster,named_info.initial_roster,target,victim)
                    members.append(NamedAction(named_info,indices[named_info],victim,mapping,named_mass*policy.get(target,F()),named_mass/F(len(legal))))
            plan=ActionPlan(info,own,_fix(actor_groups,(target,)),target,mass*sum((policy.get(p,F()) for p in orbit),F()),mass*F(len(orbit),len(legal)),tuple(members))
            family=next(g for g in groups if target in g)
            plans.setdefault(family,[]).append(plan)
    result=tuple(ActionGroup(tuple(sorted({m.target for p in ps for m in p.members})),tuple(ps),sum((p.policy_mass for p in ps),F()),sum((p.fallback_mass for p in ps),F())) for ps in plans.values())
    engine.joint_stats['compiled_kernels']+=1
    engine.joint_stats['representative_actions']+=sum(len(g.plans) for g in result)
    engine.joint_stats['named_actions']+=sum(len(p.members) for g in result for p in g.plans)
    engine.joint_actions[cache_key]=result
    return result


def observation_map(source,groups):
    """Canonical target slots for fixed reporters, using constructed classes.

    Multiple exchangeable reporters conservatively retain named outcomes. No
    permutation search or value comparison establishes this quotient.
    """
    n=source.public.player_count;identity=tuple(range(1,n+1))
    records=tuple(source.past)+tuple(source.public.reports)
    owner=lambda r:r.player if hasattr(r,'player') else r.reporter
    if any(any(owner(r) in g and len(g)>1 for g in groups) for r in records):return identity
    mapping={};used=set()
    for record in records:
        player=record.target
        if player in mapping:continue
        group=next((g for g in groups if player in g),(player,))
        target=next(p for p in group if p not in used)
        mapping[player]=target;used.add(target)
    for group in groups:
        for player,target in zip((p for p in group if p not in mapping),(p for p in group if p not in used)):
            mapping[player]=target
    return tuple(mapping.get(p,p) for p in range(1,n+1))


def compose(first,second):
    return tuple(second[p-1] for p in first)


def resolve_outcomes(engine,source,target,groups):
    key=(source,target,groups)
    if key in engine.joint_outcomes:return engine.joint_outcomes[key]
    b=source.public
    acquired,deaths=resolve_action(b,ActionInputs(source.public_state,source.past,source.private,source.observer,source.physical),target,engine.action_policy,terminal_payoffs=False)
    result=[]
    for index,death in enumerate(deaths):
        tick();child=engine.action_policy.project(b,acquired,death,target)
        reports=engine.report_children(child) if child.public.winner is None else ()
        rows=tuple((mass,c,i) for i,(q,mass,c) in enumerate(reports)) if reports else ((F(1),child,None),)
        for mass,c,report in rows:
            result.append(JointOutcome(death.probability*mass,c,_frame_groups(groups,c.public,c.past,c.observer),index,report,outcome_key(death)))
    buckets={}
    for outcome in result:
        mapping=observation_map(outcome.source,groups)
        signature=report_signature(outcome.source,mapping)
        board=outcome.source.public
        facts=(outcome.outcome_index,board.winner,repr(signature),tuple(sorted((d,mapping[a-1],mapping[t-1]) for d,a,t in board.report_resolved)))
        if facts not in buckets:buckets[facts]=[outcome,mapping,[]]
        representative,first,images=buckets[facts]
        inverse=tuple(mapping.index(p)+1 for p in range(1,len(mapping)+1))
        images.append((outcome.probability,compose(first,inverse),outcome.report_index))
    reduced=[]
    for representative,mapping,images in buckets.values():
        mass=sum((q for q,m,i in images),F())
        reduced.append(replace(representative,probability=mass,images=tuple((q/mass,m,i) for q,m,i in images)))
    engine.joint_stats['resolved_actions']+=1
    engine.joint_stats['named_outcomes']+=len(result)
    engine.joint_stats['outcome_representatives']+=len(reduced)
    engine.joint_outcomes[key]=tuple(reduced)
    return tuple(reduced)


def group_outcomes(engine,group):
    normalizer=group.policy_mass or group.fallback_mass
    return tuple((plan,(plan.policy_mass if group.policy_mass else plan.fallback_mass)/normalizer,outcome)
        for plan in group.plans if (plan.policy_mass if group.policy_mass else plan.fallback_mass)
        for outcome in resolve_outcomes(engine,plan.source,plan.target,plan.groups))


def continuation_value(engine,outcomes):
    value=F()
    for probability,outcome in outcomes:
        with engine.group_scope(outcome.groups):
            value+=probability*engine.solve(*outcome.source,physical=outcome.source.physical)
    return value
