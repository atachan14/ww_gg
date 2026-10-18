"""One owned publication boundary: P-stable orbits, scalar recursion, lazy labels.

Uniform/H0 only. Public generation remains Q-owned; chance coefficients and
conditional Q/P laws are separate. No ordinary factory or recursive dispatch.
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
    validator=getattr(scope.builder,'valid_owner',None)
    if validator is not None:validator()
    if _context(scope).groups!=scope.groups or scope.request.roles()!=scope.source:raise Pending('orbit_value_source_or_proof_changed')
    if (strategy.day,strategy.night,strategy.fake_reports)!=('random',)*3 or scope.source.public.initial_hunter_count:
        raise Pending('orbit_value_uniform_H0_only')
    if strategy.disclosure_for('seer')!='all' or tuple(strategy.seer_position)!=('unvisited','uniform'):
        raise Pending('orbit_value_future_policy_equivariance_unproved')
    return scope.source


def private_stabilizer(scope):
    source=check_scope(scope);observer=source.observer;fixed=set()
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
            patterns=produce(b,s,past,self.scope.groups,fake_policy=self.strategy.fake_seer_policy)
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


class PublicationOrbitValue:
    def __init__(self,scope):
        self.scope=scope;self.engine=OrbitOracle(scope);self.representatives=[];self.label_restorations=0
        self.groups,self.private_splits=private_stabilizer(scope)
        src=scope.source
        patterns=produce(src.public,src.public_state,src.past,self.groups,fake_policy=self.engine.strategy.fake_seer_policy)
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
