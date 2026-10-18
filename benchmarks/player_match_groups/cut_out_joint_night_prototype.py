"""Unconnected uniform joint-night orbit prototype: certified first-night only."""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from weakref import WeakKeyDictionary
from .cut_out_user_seven_source import *
from .cut_out_user_seven_source_fixture import ok
from werewolf.actor_information import condition_actor_state
from werewolf.evaluation_branch import physical_board,ActionInputs
from werewolf.seer_acquisition import Hypothesis,normalize
from werewolf.information_set_forecast import InformationSetForecast
from werewolf.action_flow import resolve_action

_caps=WeakKeyDictionary()

@dataclass(frozen=True,eq=False)
class NightCertificate:
    registry:object
    witness:object
    source:object
    groups:tuple
    physical_weights:tuple

@dataclass(frozen=True)
class JointOrbit:
    roster:int
    target:int
    seer_block:tuple
    target_block:tuple
    multiplicity:int
    public_mass:F
    physical_mass:F

@dataclass(frozen=True)
class NightLeaf:
    public:object
    public_state:object
    public_measure:object
    private:object
    physical:object
    past:tuple
    q:F
    p:F


def make_case(executed=3,physical_weights=None):
    """One fixed observed death; optional invariant P mixture, not a new policy."""
    from werewolf.board_future import calculation_origin,remember
    if type(executed)is not int or executed not in (1,3):raise Pending('prototype_fixed_prefix_only')
    prepared=ok(prepare(comparison_game()[1]));r=ok(from_game(prepared.data.to_game(),prepared));w=ok(issue(r));e=SevenInitialEngine(r,witness=w)
    source=replace(w.source,physical=physical_board(w.source.public,w.source.private,w.source.physical))
    with calculation_budget(100000,max_seconds=2),calculation_origin(r.data):
        remember(e,r.root,source);payload=ActionInputs(source.public_state,source.past,source.private,None,source.physical)
        acquired,outcomes=resolve_action(source.public,payload,executed,e.action_policy)
        if len(outcomes)!=1:raise Pending('prototype_death_branch_unproved')
        source=e.action_policy.project(source.public,acquired,outcomes[0],executed)
    groups=e.inherited_groups.require(source.public,source.public_state,source.past).groups
    weights=(F(1,2),F(1,2)) if physical_weights is None else tuple(physical_weights)
    if len(weights)!=2 or any(type(x)is not F or x<=0 for x in weights) or sum(weights)!=1:raise Pending('prototype_positive_exact_class_weights_required')
    if executed==3 and weights!=(F(1,2),F(1,2)):raise Pending('prototype_P_breaks_seer_block')
    # Weight whole invariant role classes; never a viewer fact into policy choice.
    hs=tuple(replace(h,mass=weights[0 if h.roles[0]&1 else 1]/3) for h in source.private.hypotheses)
    private=replace(source.private,hypotheses=normalize(hs))
    source=replace(source,private=private,physical=physical_board(source.public,private,source.physical))
    cap=NightCertificate(r,w,source,groups,weights);_caps[cap]=(r,w,source,groups,weights)
    return cap


def require(cap,source=None):
    if type(cap)is not NightCertificate or cap not in _caps:raise Pending('prototype_issued_certificate_required')
    expected=_caps[cap]
    if (cap.registry,cap.witness,cap.source,cap.groups,cap.physical_weights)!=expected:raise Pending('prototype_certificate_changed')
    require_bound(cap.registry,cap.witness)
    if source is not None and source!=cap.source:raise Pending('prototype_Q_P_substitution_refused')
    strategy=cap.registry.engine.baseline.strategy
    if (strategy.day,strategy.night,strategy.fake_reports)!=('random','random','random') or strategy.include_self_bite or cap.source.public.initial_hunter_count:raise Pending('prototype_uniform_no_hunter_no_self_bite_only')
    return cap.source


def produce(cap,*,source=None):
    """Block occupancy + legal target blocks. No literal info/action product."""
    x=require(cap,source);b=x.public;result=[]
    seer_blocks=[tuple(p for p in g if p in (1,2)) for g in cap.groups];seer_blocks=[g for g in seer_blocks if g]
    citizens=(5,6,7)
    for seers in seer_blocks:
        wolf_seer=seers[0];roster=(1<<(wolf_seer-1))|(1<<4)
        qm=sum((h.mass for h in x.public_state.hypotheses if h.roles[0]==roster),F())
        pm=sum((h.mass for h in x.private.hypotheses if h.roles[0]==roster),F())
        info_mult=len(seers)*len(citizens)
        legal=tuple(p for p in b.alive if not roster&(1<<(p-1)))
        for group in cap.groups:
            candidates=tuple(p for p in group if p in legal)
            if not candidates:continue
            n=info_mult*len(candidates)
            result.append(JointOrbit(roster,candidates[0],seers,group,n,qm*n/len(legal),pm*n/len(legal)))
    assert sum((o.public_mass for o in result),F())==sum((o.physical_mass for o in result),F())==1
    return tuple(result)


def labels(cap,orbit):
    """Restore literal labels lazily, without generating their continuations."""
    x=require(cap)
    if orbit not in produce(cap):raise Pending('prototype_foreign_orbit')
    emitted=0
    for seer in orbit.seer_block:
        for citizen in (5,6,7):
            roster=(1<<(seer-1))|(1<<(citizen-1))
            for target in orbit.target_block:
                if target not in x.public.alive or roster&(1<<(target-1)):continue
                original_seer=1 if orbit.roster&1 else 2
                constraints={original_seer:seer,5:citizen,orbit.target:target}
                mapping={}
                for group in cap.groups:
                    selected={a:b for a,b in constraints.items() if a in group}
                    if len(set(selected.values()))!=len(selected) or any(b not in group for b in selected.values()):raise Pending('prototype_transport_conflict')
                    selected.update(zip((p for p in group if p not in selected),(p for p in group if p not in selected.values())))
                    mapping.update(selected)
                emitted+=1;yield roster,target,tuple(mapping[p] for p in range(1,8))
    assert emitted==orbit.multiplicity


def simulate(cap,roster,target):
    """One common physical/acquisition/publication flow; no value recursion."""
    x=require(cap);b=x.public
    if type(roster)is not int or roster not in {h.roles[0] for h in x.public_state.hypotheses}:raise Pending('prototype_unknown_wolf_information')
    if type(target)is not int or target not in b.alive or roster&(1<<(target-1)):raise Pending('prototype_illegal_bite')
    e=InformationSetForecast(cap.registry.engine.baseline.rules,cap.registry.engine.baseline.strategy,exact_renaming=False,retire_uninformative_scans=False)
    e.retain_joint_guard_history=True
    def forbidden(*args,**kwargs):raise AssertionError('prototype cannot call solve/act')
    e.solve=e.act=forbidden
    qown=condition_actor_state(x.public_state,lambda h:h.roles[0]==roster)
    pown=condition_actor_state(x.private,lambda h:h.roles[0]==roster)
    payload=ActionInputs(x.public_state,x.past,pown,None,physical_board(b,pown,x.physical))
    acquired,outcomes=resolve_action(b,payload,target,e.action_policy)
    leaves=[]
    for outcome in outcomes:
        child=e.action_policy._project_roles(b,acquired,outcome,target)
        # Supported invariant P changes only info-class masses, so conditional
        # Q/P at a fixed roster are identical; assert rather than approximate.
        if qown!=pown:raise Pending('prototype_within_info_Q_P_likelihood_difference_unproved')
        published=e.morning(child.public,child.public_state,child.past)
        qbranches=e.push(child.public_state,child.private,published)
        pbranches=e.push(child.public_state,child.private,published)
        for (q,c,ns,past,qmeasure),(p,pc,pns,ppast,private) in zip(qbranches,pbranches):
            assert (c,ns,past)==(pc,pns,ppast)
            leaves.append(NightLeaf(c,ns,qmeasure,private,physical_board(c,private,child.physical),past,outcome.probability*q,outcome.probability*p))
    assert sum((v.q for v in leaves),F())==sum((v.p for v in leaves),F())==1
    return tuple(leaves)


def move_law(law,mapping):
    def player(p):return mapping[p-1]
    def mask(m):return sum(1<<(player(p)-1) for p in range(1,8) if m&(1<<(p-1)))
    hs=tuple(Hypothesis(tuple(mask(m) for m in h.roles),tuple(sorted(replace(a,player=player(a.player),target=player(a.target)) for a in h.acquisitions)),h.mass,(),tuple(replace(a,target=player(a.target)) for a in h.attacks)) for h in law.hypotheses)
    return replace(law,hypotheses=normalize(hs),rosters=tuple(tuple(sorted(player(p) for p in r)) for r in law.rosters),tracked=None if law.tracked is None else tuple(sorted(player(p) for p in law.tracked)))


def move_board(b,law,mapping):
    from werewolf.exact import replace_worlds
    player=lambda p:mapping[p-1]
    claims=['']*7
    for p in range(1,8):claims[player(p)-1]=b.claims[p-1]
    return replace_worlds(b,law.public_roles,wolf_count=None,alive=tuple(sorted(player(p) for p in b.alive)),claims=tuple(claims),
        history=tuple(replace(v,target=player(v.target)) for v in b.history),
        medium_opportunities=tuple(sorted((d,player(p),player(t)) for d,p,t in b.medium_opportunities)),
        reports=tuple(sorted((replace(v,reporter=player(v.reporter),target=player(v.target)) for v in b.reports),key=lambda v:(v.day,v.reporter,v.target,v.color))),
        report_resolved=tuple(sorted((d,player(p),player(t)) for d,p,t in b.report_resolved)))


def restore(leaf,mapping):
    q=move_law(leaf.public_state,mapping);measure=move_law(leaf.public_measure,mapping);p=move_law(leaf.private,mapping)
    past=tuple(sorted(replace(v,player=mapping[v.player-1],target=mapping[v.target-1]) for v in leaf.past))
    return NightLeaf(move_board(leaf.public,q,mapping),q,measure,p,move_board(leaf.physical,p,mapping),past,leaf.q,leaf.p)


def probability_table(leaf):
    """Labelled probability rows; no win/action-value Forecast in this prototype."""
    roles=('wolf','medium','seer','hunter','villager')
    return tuple((p,tuple(leaf.public.role_probability(p,r) for r in roles),tuple(leaf.physical.role_probability(p,r) for r in roles)) for p in range(1,8))