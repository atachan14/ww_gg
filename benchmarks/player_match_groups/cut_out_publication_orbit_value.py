"""One owned publication boundary: P-stable orbits, scalar recursion, lazy labels.

Uniform/H0 only. Public generation remains Q-owned; chance coefficients and
conditional Q/P laws are separate. Default: one boundary. Explicit recursive
benchmark extension below; no ordinary factory dispatch.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from collections import Counter
from weakref import WeakKeyDictionary
from .cut_out_structural_publications import produce,mappings,restore
from .cut_out_joint_night_prototype import move_law,move_board
from .cut_out_day_night import point_fix
from .cut_out_initial_publications import InitialReferenceEngine
from .cut_out_uniform_game import OwnView
from werewolf.seer_intervention import SeerObserver
from werewolf.board_future import (remember,reconstruct_publication,PublicationEvidence,PublicReportEvidence,publication_key,kernel_snapshot,same_role_board)
from werewolf.evaluation_branch import physical_board,ContinuationInputs
from werewolf.morning_publications import public_report_branches
from werewolf.forecast_result import Forecast
from werewolf.model_a_public import horizon_for_action
from werewolf.information_set_forecast import Pending

_scopes=WeakKeyDictionary()


@dataclass(frozen=True,eq=False)
class MorningScope:
    graph:object
    builder:object
    request:object
    source:object
    groups:tuple
    group_ledger:object=None


def _context(scope):
    registry=getattr(scope.builder,'publication_groups',None) or scope.builder.inherited_groups
    return registry.require(scope.source.public,scope.source.public_state,scope.source.past)


def issue_scope(graph,builder,request,source):
    if request.origin is not graph.root.origin or request.roles()!=source:raise Pending('orbit_value_owned_source_required')
    provisional=MorningScope(graph,builder,request,source,())
    scope=replace(provisional,groups=_context(provisional).groups)
    _scopes[scope]=(graph.data,builder.rules,builder.strategy,tuple(vars(scope).values()))
    check_scope(scope);return scope


def check_scope(scope):
    if type(scope)is not MorningScope or scope not in _scopes:raise Pending('orbit_value_issued_scope_required')
    data,rules,strategy,fields=_scopes[scope]
    if scope.graph.data is not data or tuple(vars(scope).values())!=fields:raise Pending('orbit_value_owner_revision_changed')
    if (scope.builder.rules,scope.builder.strategy)!=(rules,strategy):raise Pending('orbit_value_config_changed')
    if scope.group_ledger is not None:
        source=scope.source
        groups=scope.group_ledger.groups_for(source.provenance,source.public,source)
        if groups is None or groups!=scope.groups:raise Pending('orbit_value_inherited_group_proof_changed')
        scope.group_ledger.stats['scope_parent_replays_avoided']+=1
        return source
    validator=getattr(scope.builder,'valid_owner',None)
    if validator is not None:validator()
    if _context(scope).groups!=scope.groups or scope.request.roles()!=scope.source:raise Pending('orbit_value_source_or_proof_changed')
    if (strategy.day,strategy.night,strategy.fake_reports)!=('random',)*3 or scope.source.public.initial_hunter_count:
        raise Pending('orbit_value_uniform_H0_only')
    if strategy.disclosure_for('seer')!='all' or tuple(strategy.seer_position)!=('unvisited','uniform'):
        raise Pending('orbit_value_future_policy_equivariance_unproved')
    return scope.source


def private_stabilizer(scope):
    source=check_scope(scope)
    if scope.group_ledger is not None:
        scope.group_ledger.stats['private_permutation_checks_avoided']+=sum(len(g)-1 for g in scope.groups)
        return scope.groups,()
    observer=source.observer;fixed=set()
    if observer is not None:
        if type(observer)is OwnView:fixed.add(observer.player)
        elif type(observer)is SeerObserver:fixed.update((observer.actor,observer.target))
        else:raise Pending('orbit_value_observer_transport_unproved')
        fixed.update(p for a in observer.acquisitions for p in (a.player,a.target))
    rosters={h.roles[0] for h in source.private.hypotheses}
    if len(rosters)==1:fixed.update(p for p in range(1,source.public.player_count+1) if next(iter(rosters))&(1<<(p-1)))
    groups=point_fix(scope.groups,*sorted(fixed));result=[];splits=[]
    for group in groups:
        okay=True
        for p in group[1:]:
            mapping=list(range(1,source.public.player_count+1));mapping[group[0]-1],mapping[p-1]=p,group[0];mapping=tuple(mapping)
            if any(h.guards for h in source.private.hypotheses) or move_law(source.private,mapping)!=source.private or not same_role_board(move_board(source.physical,source.private,mapping),source.physical):
                okay=False;break
        if okay:result.append(group)
        else:result.extend((p,) for p in group);splits.append(group)
    # All operations refine certified blocks; no newly inferred group joins.
    assert all(any(set(g)<=set(old) for old in scope.groups) for g in result)
    return tuple(result),tuple(splits)


class OrbitOracle(InitialReferenceEngine):
    """Independent labelled recursion; existing pattern restore at root only."""
    def __init__(self,scope):
        super().__init__(scope.graph);self.scope=scope;self.audit=Counter()
    def solve(self,*args,**kwargs):
        if not getattr(self,'_board_evidence_snapshot',False):self.audit['solve_requests']+=1
        return super().solve(*args,**kwargs)
    def generate_publications(self,b,s,past):
        source=self.scope.source
        if (b,s,past)==(source.public,source.public_state,source.past):
            check_scope(self.scope)
            proof=None if self.scope.group_ledger is None else (self.scope.group_ledger,source.provenance)
            patterns=produce(b,s,past,self.scope.groups,fake_policy=self.strategy.fake_seer_policy,_group_proof=proof)
            rows=public_report_branches(b,past,restore(patterns,b.player_count))
            self.audit['root_pattern_templates']+=len(patterns);self.audit['root_named_Boards']+=len(rows)
            return rows
        rows=super().generate_publications(b,s,past);self.audit['future_named_Boards']+=len(rows);return rows


@dataclass
class Representative:
    pattern:object
    q_per_label:F
    q_orbit:F
    p_orbit:F
    source:object
    request:object
    value:object=None
    forecast:object=None


def prepare(scope):
    groups,splits=private_stabilizer(scope);src=scope.source
    proof=None if scope.group_ledger is None else (scope.group_ledger,src.provenance)
    patterns=produce(src.public,src.public_state,src.past,groups,fake_policy=scope.builder.strategy.fake_seer_policy,_group_proof=proof)
    return groups,splits,patterns


def with_audited_groups(scope):
    """Single trusted adapter: audit first, then bind the exact source frame.

    This does not invent a root from a callback or from endpoint metadata.
    """
    from werewolf.acquisition_provenance import AcquisitionLedger
    try:audited=seed_structural(scope)
    except Pending as error:
        if error.reason in ('role_filter_seed_public_observer_only','role_filter_exact_immutable_carriers_required'):
            return scope  # Keep the ordinary full-check path for this source.
        raise
    ledger=AcquisitionLedger(scope.builder)
    scope.builder.acquisition_provenance=ledger
    source=audited.source
    receipt=ledger._register_audited_root(source.public,source,audited.groups,(scope.graph,scope.graph.data))
    if receipt is None:raise Pending('orbit_value_audited_root_not_supported')
    source=replace(source,provenance=receipt)
    result=MorningScope(scope.graph,scope.builder,scope.request,source,audited.groups,ledger)
    _scopes[result]=(scope.graph.data,scope.builder.rules,scope.builder.strategy,tuple(vars(result).values()))
    check_scope(result)
    return result


class PublicationOrbitValue:
    def __init__(self,scope,*,engine=None,prepared=None):
        self.scope=scope;self.engine=engine if engine is not None else OrbitOracle(scope);self.representatives=[];self.label_restorations=0
        self.groups,self.private_splits,patterns=prepare(scope) if prepared is None else prepared
        src=scope.source
        rows=[];by_observation={};self.public_representatives={}
        for pattern in patterns:
            q,b,s,past=public_report_branches(src.public,src.past,(pattern.branch,))[0]
            rows.append((q*pattern.multiplicity,b,s,past));by_observation[publication_key(b,past)]=pattern
            self.public_representatives[id(pattern)]=(q,b,s,past)
        self.patterns=patterns;self.representative_Boards=len(rows);self.named_Q_vectors=sum(p.multiplicity for p in patterns)
        # These coefficients are orbit chance integrals ONLY. The representative
        # conditional Q law is unchanged, not reweighted by physical P or size.
        weighted=self.engine.push(src.public_state,src.private,rows)
        remember(self.engine,scope.request,src)
        for p_mass,b,q_law,past,own in weighted:
            pattern=by_observation[publication_key(b,past)]
            self.engine.record_group_publication(src.public,src.public_state,src.past,b,q_law,past,'orbit')
            physical=physical_board(b,own,src.physical)
            child=reconstruct_publication(self.engine,src,b,q_law,past,own,physical,replay_unique=True)
            self.representatives.append(Representative(pattern,pattern.branch.probability,pattern.branch.probability*pattern.multiplicity,p_mass,child,child.board_data))
        self.p_zero_patterns=len(patterns)-len(self.representatives)
        if sum((r.p_orbit for r in self.representatives),F())!=1:raise Pending('orbit_value_physical_mass_incomplete')
    def check(self):
        check_scope(self.scope)
        if (self.engine.rules,self.engine.strategy)!=(self.scope.builder.rules,self.scope.builder.strategy):raise Pending('orbit_value_evaluator_config_changed')
    def value(self):
        self.check();result=F()
        for row in self.representatives:
            if row.value is None:row.value=self.engine.solve(*row.source,physical=row.source.physical)
            result+=row.p_orbit*row.value
        return result
    def forecast(self,row):
        self.check()
        if row.forecast is None:
            s=row.source
            value=self.engine.solve(*s,physical=s.physical)
            actions=tuple((p,self.engine.act(*s[:3],p,s.private,s.observer,physical=s.physical)) for p in s.public.alive)
            dawn=tuple((p,horizon_for_action(self.engine,s.public,s.public_state,s.past,p,s.private,observer=s.observer)) for p in s.public.alive)
            row.forecast=Forecast(value,actions,dawn)
        return row.forecast
    def labelled(self,row,mapping):
        self.check()
        if not any(row is r for r in self.representatives) or tuple(mapping) not in mappings(row.pattern,self.scope.source.public.player_count):raise Pending('orbit_value_mapping_not_certified')
        self.label_restorations+=1;s=row.source
        q=move_law(s.public_state,mapping);p=move_law(s.private,mapping)
        past=tuple(sorted(replace(r,player=mapping[r.player-1],target=mapping[r.target-1]) for r in s.past))
        child=ContinuationInputs(move_board(s.public,q,mapping),q,past,p,s.observer,move_board(s.physical,p,mapping))
        forecast=self.forecast(row)
        moved=Forecast(forecast.village_win,tuple(sorted((mapping[p-1],v) for p,v in forecast.action_values)),tuple(sorted((mapping[p-1],v) for p,v in forecast.by_dawn_values)))
        request=self.scope.request.child(PublicationEvidence(kernel_snapshot(self.engine),publication_key(child.public,past)),None)
        return row.q_per_label,row.p_orbit/row.pattern.multiplicity,child,moved,request

    def public_labelled(self,pattern,mapping):
        """Q-positive hypothetical detail, never an invented normalized P."""
        self.check()
        if not any(pattern is p for p in self.patterns) or tuple(mapping) not in mappings(pattern,self.scope.source.public.player_count):raise Pending('orbit_value_mapping_not_certified')
        q,b,s,past=self.public_representatives[id(pattern)]
        law=move_law(s,mapping);history=tuple(sorted(replace(r,player=mapping[r.player-1],target=mapping[r.target-1]) for r in past))
        board=move_board(b,law,mapping)
        child=ContinuationInputs(board,law,history,law,None,physical_board(board,law))
        request=self.scope.request.child(PublicReportEvidence(kernel_snapshot(self.engine),publication_key(board,history)),None)
        return q,child,request


def named_value(scope):
    source=check_scope(scope);engine=OrbitOracle(scope);remember(engine,scope.request,source)
    public=engine.morning(source.public,source.public_state,source.past);weighted=engine.push(source.public_state,source.private,public)
    result=F();children=[]
    for mass,b,s,past,own in weighted:
        child=reconstruct_publication(engine,source,b,s,past,own,physical_board(b,own,source.physical),replay_unique=True)
        value=engine.solve(*child,physical=child.physical);result+=mass*value;children.append((mass,child))
    return result,engine,public,weighted,children


# The recursive extension reuses the same proof, mass transfer and lazy detail
# implementation. Only the common morning policy hook is replaced.
from .cut_out_joint_night_forecast import FullRecordedPolicy
from .cut_out_inherited_groups import InheritedGroupRegistry,InheritedGroups
from werewolf.information_set_forecast import InformationSetForecast,InformationSetActionPolicy
from werewolf.board_future import register_origin


class RecursivePublicationPolicy(FullRecordedPolicy):
    def acquire(self,b,payload):
        if getattr(self.engine,'_board_evidence_snapshot',False):return InformationSetActionPolicy.acquire(self,b,payload)
        result=InformationSetActionPolicy.acquire(self,b,payload)
        self.engine.carry_proof('acquisition',b,payload.public_state,result.public_state,payload.past)
        return result
    def project(self,b,payload,outcome,target):
        if getattr(self.engine,'_board_evidence_snapshot',False):return InformationSetActionPolicy.project(self,b,payload,outcome,target)
        result=InformationSetActionPolicy.project(self,b,payload,outcome,target)
        self.engine.carry_proof('action',b,payload,result,target)
        return result
    def morning_value(self,payload):
        e=self.engine
        if getattr(e,'_board_evidence_snapshot',False):
            return super().morning_value(payload)
        return e.publication_value(payload)


class RecursivePublicationOracle(OrbitOracle):
    """Owned intermediate source only; ordinary targets, certified mornings.

    No canonical global state cache. A label frame persists along each
    representative path; later maps compose only on explicit detail readback.
    """
    def __init__(self,scope):
        super().__init__(scope)
        self.action_policy=RecursivePublicationPolicy(self)
        tracker=InheritedGroupRegistry.__new__(InheritedGroupRegistry)
        tracker.contexts={};tracker.by_board={};tracker.stats=Counter()
        src=check_scope(scope)
        tracker.install(InheritedGroups(src.public,src.public_state,src.past,scope.groups,event='owned-orbit-boundary'))
        self.inherited_groups=tracker
        self.plans=[];self.refusals=Counter();self.proof_losses=Counter();self.boundary_counts=Counter()

    def valid_owner(self):check_scope(self.scope)

    def record_group_publication(self,b,s,past,c,ns,history,kind):
        if getattr(self,'_board_evidence_snapshot',False):return
        self.carry_proof('publication',b,s,past,c,ns,history,kind)

    def carry_proof(self,kind,*args):
        try:return getattr(self.inherited_groups,kind)(*args)
        except Pending as error:
            # Only optional certificate propagation fails here. The completed
            # common transition is unchanged; later proof lookup will decline.
            self.proof_losses[error.reason]+=1
            return None

    def generate_publications(self,b,s,past):
        rows=InformationSetForecast.generate_publications(self,b,s,past)
        if not getattr(self,'_board_evidence_snapshot',False):self.audit['fallback_named_Boards']+=len(rows)
        return rows

    def publication_value(self,source):
        self.valid_owner()
        # Build a receipt for this exact private/physical continuation. Neither
        # missing inherited proof nor an unsupported policy authorizes merging.
        try:
            request=source.board_data or register_origin(self,source.public,source)
            cap=issue_scope(self.graph,self,request,source)
            prepared=prepare(cap)
        except Pending as error:
            # Preflight only: no mass transfer/continuation has occurred. Errors
            # in P support or later evaluation are never converted to fallback.
            self.refusals[error.reason]+=1
            return InformationSetActionPolicy.morning_value(self.action_policy,source)
        plan=PublicationOrbitValue(cap,engine=self,prepared=prepared)
        self.plans.append(plan)
        day=source.public.day
        self.boundary_counts[day,'boundaries']+=1
        self.boundary_counts[day,'named_Q']+=plan.named_Q_vectors
        self.boundary_counts[day,'representative_Q']+=plan.representative_Boards
        self.boundary_counts[day,'named_positive_P']+=sum(r.pattern.multiplicity for r in plan.representatives)
        self.boundary_counts[day,'representative_positive_P']+=len(plan.representatives)
        return plan.value()


def labelled_descendant(root_plan,root_row,mapping,request):
    """Compose a certified outer label frame with a requested descendant path.

    Ordinary Action/Publication evidence only. Unknown conditioning operations
    are explicitly refused; no synthetic transport evidence or hidden solve.
    """
    from .cut_out_joint_night_forecast_fixture import moved_source
    from werewolf.board_future import ActionEvidence,outcome_key
    from types import SimpleNamespace
    root_plan.check()
    if request.origin is not root_row.request.origin or request.history[:len(root_row.request.history)]!=root_row.request.history:
        raise Pending('orbit_value_descendant_prefix_required')
    suffix=request.history[len(root_row.request.history):]
    if any(type(op) not in (ActionEvidence,PublicationEvidence) for op in suffix):
        raise Pending('orbit_value_descendant_operation_transport_unproved')
    _,_,_,_,restored=root_plan.labelled(root_row,mapping)
    ordinary=InitialReferenceEngine(root_plan.scope.graph)
    prefix=root_row.request
    for op in suffix:
        prefix=prefix.child(op,None);expected=moved_source(prefix.roles(),mapping)
        if type(op)is ActionEvidence:
            alive=None if op.observed_alive is None else tuple(sorted(mapping[p-1] for p in op.observed_alive))
            moved=ActionEvidence(kernel_snapshot(ordinary),mapping[op.target-1],outcome_key(SimpleNamespace(board=expected.physical)),op.terminal_payoffs,alive)
        else:moved=PublicationEvidence(kernel_snapshot(ordinary),publication_key(expected.public,expected.past))
        restored=restored.child(moved,None)
    return restored


# A separate, narrow provenance experiment: no recursive evaluator adoption.
# Full joint symmetry is audited once at seed issuance. Only this module's
# typed transition constructors may mint children; no supplied posterior accepted.
_structural=WeakKeyDictionary()


@dataclass(frozen=True,eq=False)
class StructuralWitness:
    source:object
    groups:tuple
    owner:tuple
    parent:object=None
    selector:object=None
    private_mass:F=F(1)
    public_mass:F=F(1)
    choice_probability:object=None
    root_request:object=None


def _mint_structural(source,groups,owner,**kwargs):
    proof=StructuralWitness(source,groups,owner,**kwargs)
    _structural[proof]=tuple(vars(proof).values())
    return proof


def seed_structural(scope):
    """One full audit, including full public/private histories, before reuse."""
    from .cut_out_structural_publications import require_groups
    from werewolf.board_future import canonical_hypothesis
    from werewolf.seer_future_uniform import TrueScanState
    from werewolf.exact import Board
    source=check_scope(scope)
    if source.observer is not None:raise Pending('role_filter_seed_public_observer_only')
    if type(source.public)is not Board or type(source.physical)is not Board or any(type(law)is not TrueScanState or type(law.hypotheses)is not tuple or not all(canonical_hypothesis(h) for h in law.hypotheses) for law in (source.public_state,source.private)):
        raise Pending('role_filter_exact_immutable_carriers_required')
    groups,_=private_stabilizer(scope)
    require_groups(source.public,source.public_state,source.past,groups)
    owner=(scope.graph,scope.graph.data,scope.graph.engine,scope.graph.root,scope.builder,scope.builder.rules,scope.builder.strategy,scope.graph.engine.baseline,scope.graph.engine.baseline.rules,scope.graph.engine.baseline.strategy)
    return _mint_structural(source,groups,owner,root_request=scope.request)


def require_structural(proof):
    """Constant-field checks: no law hashing, equality, replay, or parent walk."""
    if type(proof)is not StructuralWitness or proof not in _structural:
        raise Pending('role_filter_minted_receipt_required')
    if any(a is not b for a,b in zip(tuple(vars(proof).values()),_structural[proof])):
        raise Pending('role_filter_receipt_changed')
    graph,data,engine,root,builder,rules,strategy,baseline,base_rules,base_strategy=proof.owner
    if graph.data is not data or graph.engine is not engine or graph.root is not root or builder.rules is not rules or builder.strategy is not strategy or engine.baseline is not baseline or baseline.rules is not base_rules or baseline.strategy is not base_strategy:
        raise Pending('role_filter_owner_or_configuration_changed')
    return proof.source


def condition_known_role(proof,player,role):
    """P restricted by role(player), Q unchanged; split only the named player.

    For every permutation fixing player, its role indicator commutes with the
    permutation. Restriction and separate P normalization preserve all remaining
    complete-history invariance. Marginalizing P gives equivariant physical
    weights. This theorem says nothing about arbitrary predicates or policies.
    """
    from werewolf.actor_information import condition_actor_state
    source=require_structural(proof)
    if type(player)is not int or player not in range(1,source.public.player_count+1) or type(role)is not str or role not in ('wolf','medium','seer','villager'):
        raise Pending('role_filter_explicit_supported_role_required')
    if source.observer is not None and source.observer!=OwnView(player,role):
        raise Pending('role_filter_new_or_changed_observer_unproved')
    observer=OwnView(player,role)
    mass=sum((h.mass for h in source.private.hypotheses if observer.accepts(h)),F())
    if not mass:raise Pending('role_filter_zero_private_support')
    private=condition_actor_state(source.private,observer.accepts)
    child=replace(source,private=private,observer=observer,physical=physical_board(source.public,private,source.physical),board_data=None)
    groups=point_fix(proof.groups,player)
    return _mint_structural(child,groups,proof.owner,parent=proof,selector=(player,role),private_mass=mass)


def structural_request(proof):
    """Ordinary cold evidence only when detail is explicitly requested."""
    from werewolf.board_future import condition_recipe
    source=require_structural(proof)
    if proof.parent is None:return proof.root_request
    parent=structural_request(proof.parent)
    if proof.selector[0]=='known-villager-death':
        from werewolf.board_future import ActionEvidence,outcome_key
        from types import SimpleNamespace
        _,target=proof.selector
        engine=InitialReferenceEngine(proof.owner[0])
        recipe=ActionEvidence(kernel_snapshot(engine),target,outcome_key(SimpleNamespace(board=source.physical)),False)
    else:
        recipe=condition_recipe(proof.parent.source,source)
        if recipe is None:raise Pending('role_filter_condition_receipt_unproved')
    return parent.child(recipe,None)


def known_villager_death(proof,target,*,stats=None):
    """Narrow certified common death kernel, or None for ordinary fallback.

    Five-alive Day1, W1/S1/V3/H0/M0, uniform strategy; target is a villager
    in BOTH complete Q/P supports. Daytime has no acquisition. The sole
    continuing death event has separate Q=P=1 chance; action choice is 1/5.
    Parent full histories are preserved by common projection. Fix target.
    """
    from time import perf_counter
    from werewolf.information_set_forecast import InformationSetForecast
    from werewolf.evaluation_branch import ActionInputs
    source=require_structural(proof);b=source.public
    metrics=stats if stats is not None else Counter()
    if (type(target)is not int or target not in b.alive or b.winner or b.phase!='day' or b.day!=1 or b.history or len(b.alive)!=5 or b.player_count!=5 or b.initial_medium_count or b.initial_hunter_count or b.initial_seer_count!=1 or 'medium' in b.claims):
        metrics['declined']+=1;return None
    rules,strategy=proof.owner[5:7]
    if (strategy.day,strategy.night,strategy.fake_reports)!=('random',)*3:
        metrics['declined']+=1;return None
    begin=perf_counter();bit=1<<(target-1)
    for law in (source.public_state,source.private):
        for h in law.hypotheses:
            metrics['preflight_hypothesis_visits']+=1
            if h.guards or h.roles[0].bit_count()!=1 or h.roles[2].bit_count()!=1 or h.roles[1] or h.roles[3] or any(m&bit for m in h.roles):
                metrics['declined']+=1;metrics['preflight_seconds']+=perf_counter()-begin;return None
    metrics['preflight_seconds']+=perf_counter()-begin
    # Reuse the pure common daytime resolution/projection kernels. Do not call
    # before_action/reconstruct_child: those attach evidence by replaying a
    # parent. Evidence is created only by structural_request on explicit read.
    begin=perf_counter()
    engine=InformationSetForecast(rules,strategy,exact_renaming=False,retire_uninformative_scans=False)
    engine.retain_joint_guard_history=True
    payload=ActionInputs(source.public_state,source.past,source.private,source.observer,source.physical)
    outcomes=engine.action_policy.outcomes(b,payload,target)
    if len(outcomes)!=1 or outcomes[0].probability!=1 or outcomes[0].board.winner is not None or outcomes[0].context is None:
        raise Pending('structural_known_villager_death_kernel_contract')
    child=engine.action_policy._project_roles(b,payload,outcomes[0],target)
    metrics['common_resolution_projection_seconds']+=perf_counter()-begin
    metrics['input_Q_hypotheses']+=len(source.public_state.hypotheses)
    metrics['input_P_hypotheses']+=len(source.private.hypotheses)
    metrics['output_Q_hypotheses']+=len(child.public_state.hypotheses)
    metrics['output_P_hypotheses']+=len(child.private.hypotheses)
    metrics['certified_deaths']+=1
    return _mint_structural(child,point_fix(proof.groups,target),proof.owner,parent=proof,selector=('known-villager-death',target),
        public_mass=F(1),private_mass=F(1),choice_probability=F(1,len(b.alive)))
