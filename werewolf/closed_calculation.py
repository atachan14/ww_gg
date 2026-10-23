"""Closed, snapshot-owned use of the shared fixed-CO H0 common kernels.

Public calls take saved BoardData or semantic actions/owner observations only.
No public call accepts a law, group, child frame, engine or cache. Input edits
open a fresh calculation. Nodes cannot be constructed or reassigned by callers.
There is no runtime provenance ledger, cache ticket or repeated owner/frame
validation; internal construction is the invariant. Cold recipes are exported
with a separate engine and never supply live calculation cache inputs.
"""
from dataclasses import dataclass
from contextlib import contextmanager
from fractions import Fraction as F
from .board_flow import BoardData
from .board_future import (SavedOrigin,GeneratedBoard,ActionEvidence,PublicationEvidence,
    OwnerInformationEvidence,ObservedActionEvidence,ObservedPublicationEvidence,outcome_key,publication_key,kernel_calculation)
from .information_set_forecast import InformationSetForecast,Pending
from .evaluation_branch import ActionInputs,ContinuationInputs,physical_board
from .actor_information import PersonalInformation,WolfInformation,WolfObserver,GuardInformation,GuardSelection,wolf_information_groups
from .seer_intervention import SeerObserver
from .exact import Strategy,ClaimPolicy,legal_targets
from .action_flow import resolve_action
from .forecast_result import Forecast
from .calculation_budget import calculation_budget,tick,DEFAULT_MAX_WORK,DEFAULT_MAX_SECONDS
from .model_a_public import horizon_for_action
from .group_partition import _fix,_report_groups,_frame_groups


from .actor_information import information_positions as _owner_positions


def _entry_origin(data,game,strategy):
    """Decode saved unchanged-public action observations; no hidden policy substitution."""
    history=game.get('history',())
    if not history:return data,()
    if len(history)>max(0,2*game['players']-2):raise ValueError('Too much history')
    for step in history:
        if (not isinstance(step,dict) or not {'target','policy','claims','claim_policy','seer_options'}<=step.keys()
            or set(step)-{'target','policy','claims','claim_policy','seer_options','reports','strategy_ui','result_disclosure_model','observation','deaths'}):
            raise ValueError('Invalid saved history')
        if type(step.get('target'))is not int or set(step)&{'observation','deaths'}:
            raise Pending('closed_saved_nonstandard_observation_pending')
    cp=ClaimPolicy(**game.get('claim_policy',{}))
    if (any(Strategy(**step.get('policy',{}))!=strategy
        or tuple(step.get('claims',()))!=tuple(game.get('claims',()))
        or ClaimPolicy(**step.get('claim_policy',{}))!=cp
        or step.get('result_disclosure_model')!=game.get('result_disclosure_model')
        or step.get('seer_options')!=game.get('seer_options') or step.get('reports') for step in history)
        or game.get('result_disclosure_model')!='full-observed-v1'
        or {r.get('reporter') for r in game.get('seer_inputs',()) if r.get('day')==1}!=set(p for p,c in enumerate(game.get('claims',()),1) if c=='seer')
        or any(r.get('target') is None or r.get('color') is None for r in game.get('seer_inputs',()))
        or 'filled' not in cp.conditions('seer')
        or tuple(game.get('claims',())).count('seer')<game.get('seers',0)
        or any(type(r.get('day'))is not int or not 1<=r['day']<=1+len(history)//2 for r in game.get('seer_inputs',()))):
        raise Pending('closed_saved_public_or_policy_change_pending')
    if any(type(r.get('day'))is not int or not 2<=r['day']<=1+len(history)//2 for r in game.get('reports',())):
        raise Pending('closed_saved_medium_timing_pending')
    if (any(r['day']>1 for r in game.get('seer_inputs',())) or game.get('reports')) and game.get('public_log'):
        raise Pending('closed_saved_report_public_log_pending')
    log=game.get('public_log',{})
    if any(b.get('slot',0)>0 for b in log.get('batches',())):
        raise Pending('closed_saved_late_public_event_pending')
    from types import SimpleNamespace
    from .result_disclosure import snapshot
    for slot in range(len(history)+1):
        claims,_=snapshot(game,SimpleNamespace(day=1+slot//2,phase='night' if slot%2 else 'day'),tuple(game['claims']))
        if claims!=tuple(game['claims']):raise Pending('closed_saved_late_public_event_pending')
    return data.updated(history=[],seer_inputs=[r for r in game.get('seer_inputs',()) if r['day']==1],reports=[]),tuple(step['target'] for step in history)


def _forecast_scope(source,engine):
    if source.public.winner is not None or len(source.public.alive)<=4:return
    if engine.strategy.include_self_bite:raise Pending('closed_forecast_self_bite_pending')
    reporters=sum(1<<(p-1) for p in source.public.alive if source.public.claims[p-1]=='seer')
    # Claims/roles cannot grow in this closed H0 flow; conditioning and deaths
    # preserve the selected zero/one-fake joint kernel at every later morning.
    tick(len(source.public_state.hypotheses)+len(source.past))
    declared=sum(1<<(p-1) for p in {r.player for r in source.past if r.acquired_day==1})
    if reporters & ~declared:raise Pending('closed_forecast_initial_report_pending')
    if any((reporters & ~h.roles[2]).bit_count()>1 for h in source.public_state.hypotheses):
        raise Pending('multiple_fake_report_correlation_unselected')


@dataclass(frozen=True)
class ActionBranch:
    probability:F
    node:object


@dataclass(frozen=True)
class ReportBranch:
    public_probability:object
    probability:F
    node:object


@dataclass(frozen=True)
class WolfChoice:
    information:WolfInformation
    information_mass:F
    target:int
    probability:F
    node:object

    @property
    def mass(self):return self.information_mass*self.probability


class ClosedCalculation:
    __slots__=('__data','__strategy','__engine','__root','__max_work','__max_seconds','__origin_data','__entry_probability')

    def __init__(self,data,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS,grouped=False,aggregate_wolf=False,aggregate_reports=False,anonymous=False):
        if type(data)is not BoardData:raise TypeError('Saved immutable BoardData required')
        if type(grouped)is not bool or type(aggregate_wolf)is not bool or type(aggregate_reports)is not bool:raise TypeError('Boolean representative mode required')
        if (aggregate_wolf or aggregate_reports) and not grouped:raise ValueError('Aggregation requires the grouped consumer')
        game=data.to_game();strategy=Strategy(**game['policy'])
        if game.get('hunters',0)>1:raise Pending('guard_multiple_hunters_unimplemented')
        if game.get('hunters',0) and (strategy.day,strategy.night,strategy.fake_reports)!=('random',)*3:
            raise Pending('closed_guard_stage_policy_unimplemented')
        if game.get('hunters',0):
            from .root_secret_flow import root_policy_supported
            if not root_policy_supported(strategy,hunters=game['hunters'],seers=game.get('seers',0),mediums=game.get('mediums',0)):
                raise Pending('closed_guard_policy_scope_unimplemented')
        if (game.get('model')!='group'
            or game.get('seers',0) and (game.get('seer_mode')!='information-fixed-v1'
                or game.get('seer_options',{}).get('likelihood')!='compatibility'
                or game.get('seer_options',{}).get('initial_rule')!='random_white')
            or ((strategy.day,strategy.night,strategy.fake_reports)!=('random',)*3
                and not (grouped and aggregate_reports and (strategy.day,strategy.night,strategy.fake_reports)==('max',)*3))
            or strategy.disclosure_for('seer')!='all' or strategy.disclosure_for('medium')!='all'):
            raise Pending('closed_initial_uniform_H0_snapshot_only')
        origin_data,saved_target=_entry_origin(data,game,strategy)
        object.__setattr__(self,'_ClosedCalculation__origin_data',origin_data)
        object.__setattr__(self,'_ClosedCalculation__entry_probability',F(1))
        object.__setattr__(self,'_ClosedCalculation__data',data)
        object.__setattr__(self,'_ClosedCalculation__strategy',strategy)
        object.__setattr__(self,'_ClosedCalculation__max_work',max_work)
        object.__setattr__(self,'_ClosedCalculation__max_seconds',max_seconds)
        from .grouped_forecast import GroupedForecast
        options={'aggregate_wolf':aggregate_wolf,'aggregate_reports':aggregate_reports} if grouped else {}
        if game.get('hunters',0):
            from .root_secret_flow import RootSecretEngine
            engine=RootSecretEngine(data.game_data.rules,strategy,exact_renaming=False,max_work=max_work)
        else:engine=(GroupedForecast if grouped else InformationSetForecast)(data.game_data.rules,strategy,exact_renaming=False,retire_uninformative_scans=False,max_work=max_work,**options)
        engine.retain_joint_guard_history=True
        engine.anonymous_nights=anonymous
        if anonymous:
            from .evaluation_graph import EvaluationGraph
            engine.evaluation_graph=EvaluationGraph(engine)
        if anonymous:
            from .anonymous_value import Evaluator
            engine.anonymous_values=Evaluator(strategy.day,strategy.night,strategy.win_cutoff)
        engine.retain_complete_abilities=aggregate_reports
        object.__setattr__(self,'_ClosedCalculation__engine',engine)
        with calculation_budget(max_work,max_seconds=max_seconds):
            tick(0);source=SavedOrigin(origin_data,engine.rules,strategy,project_public=False)()
            if source.public.day!=1 or source.public.phase!='day' or source.public.history:
                raise Pending('closed_initial_snapshot_required')
            # The initial saved group model is generated symmetrically within claim
            # classes; public report meanings refine them and fix targets. No arbitrary law or
            # caller-supplied partition can enter this constructor.
            classes={}
            for p,claim in enumerate(source.public.claims,1):classes.setdefault(claim,[]).append(p)
            groups=_report_groups(tuple(tuple(v) for v in classes.values()),source)
            from .action_tree_trace import FullTraceOrigin
            if aggregate_reports:
                full=FullTraceOrigin(SavedOrigin(origin_data,engine.rules,strategy,project_public=False))()
                root=self.__node(full,groups,(('full_trace',),))
            else:root=self.__node(source,groups,())
            # Rooted relational action orbits are not population partitions.
            from .public_relation_orbits import initial_orbits
            actual=root.read()
            engine.public_action_orbits={(actual.public,actual.public_state,actual.past):initial_orbits(origin_data.to_game())}
            engine.public_action_games={(actual.public,actual.public_state,actual.past):origin_data.to_game()}
            if anonymous and not source.public.winner and not engine.rules.allow_self_bite and not strategy.include_self_bite and not game.get('mediums',0) and not game.get('hunters',0) and all(c=='latent' for c in source.public.claims) and not source.past:
                from .anonymous_belief import Belief
                engine.anonymous_beliefs={root.read():Belief.initial(groups,dict(wolf=game['wolves'],seer=game.get('seers',0),villager=game['players']-game['wolves']-game.get('seers',0)),engine.rules.initial_seer)}
            else:engine.anonymous_beliefs={}
            probability=F(1)
            for target in saved_target:
                mass,root=root.observe(target)
                probability*=mass
                if root.read().public.phase=='day':
                    from .seer_acquisition import SeerReport
                    day=root.read().public.day
                    reports=tuple(SeerReport(day,day,r['reporter'],r['target'],r['color']) for r in game.get('seer_inputs',()) if r['day']==day)
                    from .exact import MediumReport
                    medium=tuple(MediumReport(**r) for r in game.get('reports',()) if r['day']==day)
                    mass,root=root.observe_reports(reports,medium)
                    probability*=mass
            object.__setattr__(self,'_ClosedCalculation__entry_probability',probability)
            object.__setattr__(self,'_ClosedCalculation__root',root)

    def __setattr__(self,name,value):raise AttributeError('Open a new calculation for changed inputs')
    @property
    def data(self):return self.__data
    @property
    def root(self):return self.__root
    @property
    def entry_probability(self):return self.__entry_probability

    def stats(self):
        e=self.__engine
        result=dict(values=len(e.values),actions=len(e.action_values),expansions=dict(e.expansions),
            acquired=len(e.acquired),mornings=len(e.mornings),publications=len(e.publication_values),policies=len(e.policies),
            saved_sources=len(e.board_sources),resolution_cache=len(e.board_action_kernels))
        if hasattr(e,'orbit_stats'):result['target_orbits']=dict(e.orbit_stats)
        if hasattr(e,'joint_stats'):result['joint_actions']=dict(e.joint_stats)
        if getattr(e,'aggregate_reports',False):result['report_vectors']=e.report_counts()
        return result

    @contextmanager
    def __kernel(self):
        with calculation_budget(self.__max_work,max_seconds=self.__max_seconds),kernel_calculation():
            tick(0)
            yield

    def __node(self,source,groups,path,view=None):
        node=object.__new__(_Node)
        object.__setattr__(node,'_Node__calculation',self)
        object.__setattr__(node,'_Node__source',source)
        object.__setattr__(node,'_Node__groups',_frame_groups(groups,source.public,source.past,source.observer))
        object.__setattr__(node,'_Node__path',path)
        object.__setattr__(node,'_Node__view',view)
        relation=None;orbits=None;relation_key=None
        if not source.public.history and source.observer is None and not any(op[0]=='physical' for op in path):
            from .public_relation_orbits import initial_orbits
            from .manual_public_input import initial_relation_game
            import json
            last=next((i for i in range(len(path)-1,-1,-1) if path[i][0]=='public_input'),None)
            relation=(initial_relation_game(self.__origin_data.to_game(),path[:last],path[last][1],source) if last is not None else self.__origin_data.to_game())
            orbits=initial_orbits(relation);relation_key=json.dumps(relation,sort_keys=True,separators=(',',':'))
        object.__setattr__(node,'_Node__relations',relation)
        object.__setattr__(node,'_Node__relation_key',relation_key)
        object.__setattr__(node,'_Node__orbits',orbits)
        return node



class _Node:
    __slots__=('__calculation','__source','__groups','__path','__view','__relations','__relation_key','__orbits')
    def __init__(self,*args,**kwargs):raise TypeError('Nodes are generated by a calculation')
    def __setattr__(self,name,value):raise AttributeError('Generated nodes are immutable')
    @property
    def data(self):return self.__calculation.data
    @property
    def solver_identity(self):return (self.__calculation.data.game_data.rules,self.__calculation._ClosedCalculation__strategy,self.__groups,self.__relation_key)
    @property
    def groups(self):return self.__groups
    def read(self):return self.__source
    @contextmanager
    def relation_scope(self):
        if self.__relations is None:
            yield;return
        engine=self.__calculation._ClosedCalculation__engine;s=self.__source
        key=(s.public,s.public_state,s.past);missing=object()
        orbits=engine.public_action_orbits.get(key,missing);game=engine.public_action_games.get(key,missing)
        engine.public_action_orbits[key]=self.__orbits;engine.public_action_games[key]=self.__relations
        try:yield
        finally:
            if orbits is missing:engine.public_action_orbits.pop(key,None)
            else:engine.public_action_orbits[key]=orbits
            if game is missing:engine.public_action_games.pop(key,None)
            else:engine.public_action_games[key]=game

    def personal(self,information):
        if type(information) not in (PersonalInformation,SeerObserver,WolfInformation,WolfObserver,GuardInformation,GuardSelection):raise ValueError('Typed owner information required')
        if type(information)is SeerObserver:
            from .seer_acquisition import Acquisition
            if type(information.acquisitions)is not tuple or any(type(a)is not Acquisition or a.player!=information.actor for a in information.acquisitions):
                raise ValueError('Only owner records allowed')
        s=self.__source
        # In this H0 generated-path scope every past bite is already recorded.
        # A personal observation cannot invent a future/missing action.
        if type(information)is WolfInformation and information.attacks!=s.private.hypotheses[0].attacks:
            raise ValueError('Use the generated past attack history')
        if type(information)is WolfObserver and any(a.night>=s.public.day for a in information.attacks):raise ValueError('Only past pack attacks allowed')
        view=('wolf',information.initial_roster) if type(information) in (WolfInformation,WolfObserver) else ('person',information.actor)
        if self.__view is not None and self.__view!=view:raise ValueError('Choose a personal view from the public root; do not combine owners')
        if type(information) in (PersonalInformation,SeerObserver,GuardInformation,GuardSelection):
            if type(information.actor)is not int or not 1<=information.actor<=s.public.player_count:raise ValueError('Owner outside original players')
            if type(information)is SeerObserver and (type(information.day)is not int or information.day<1 or type(information.target)is not int or not 1<=information.target<=s.public.player_count or information.target==information.actor):raise ValueError('Invalid owner scan intervention')
        if type(information) in (GuardInformation,GuardSelection):
            if any(g.night>=s.public.day for g in information.guards):raise ValueError('Only past guard records allowed')
            if type(information)is GuardSelection:
                if s.public.phase!='night' or information.night!=s.public.day:raise ValueError('Guard instruction belongs to current night')
                from .guard_model import guard_choices
                compatible=[h for h in s.private.hypotheses if information(h,s.private)]
                choices={tuple(p for p,q in guard_choices(s.public,information.actor,self.__calculation.data.game_data.rules,self.__calculation._ClosedCalculation__strategy.guard_position,guards=h.guards)) for h in compatible}
                if len(choices)!=1:raise Pending('guard_view_target_generation_support_unresolved')
                if information.target not in next(iter(choices)):raise ValueError('Illegal owner guard target')
        with self.__calculation._ClosedCalculation__kernel():mass,child=self.__calculation._ClosedCalculation__engine.personal_view(s,information)
        groups=_fix(self.__groups,_owner_positions(information,s.public.player_count))
        return mass,self.__calculation._ClosedCalculation__node(child,groups,(*self.__path,('owner',information,child.observer)),view)

    def _compositions(self):
        belief=getattr(self.__calculation._ClosedCalculation__engine,'anonymous_beliefs',{}).get(self.__source)
        if belief is not None:return belief.compositions()
        from .physical_selection import counts
        result={};tick(len(self.__source.private.hypotheses))
        for h in self.__source.private.hypotheses:
            key=counts(h,self.__source.public.alive);result[key]=result.get(key,F())+h.mass
        return tuple(sorted(result.items()))

    def _with_full_trace(self):
        if any(op[0]=='full_trace' for op in self.__path):return self
        from .action_tree_trace import trace_source
        source,pending=trace_source(self)
        if pending:raise ValueError(pending)
        if source is self.__source:return self
        return self.__calculation._ClosedCalculation__node(source,self.__groups,(('full_trace',),*self.__path),self.__view)

    def _select_physical(self,kind,selection):
        from .physical_selection import PhysicalSelectionEvidence,freeze
        selection=freeze(selection);source=PhysicalSelectionEvidence(kind,selection)(self.__source)
        groups=self.__groups
        e=self.__calculation._ClosedCalculation__engine
        belief=getattr(e,'anonymous_beliefs',{}).get(self.__source)
        if belief is not None and kind=='composition':
            from dataclasses import replace
            def living(atom):
                pop=atom.population
                count=lambda role:sum(p.alive and p.role==role for p in pop.people)+sum(c.count for c in pop.cells if c.alive and c.role==role)
                return count('wolf'),0,count('seer'),0,count('villager')
            e.anonymous_beliefs[source]=replace(belief,p=belief.p.condition(lambda atom:living(atom)==selection)[1])
        if kind=='joint':groups=_fix(groups,(*selection[1],*(p for pair in selection[2] for p in pair)))
        elif kind=='hypothesis':groups=tuple((p,) for group in groups for p in group)
        return self.__calculation._ClosedCalculation__node(source,groups,(*self.__path,('physical',kind,selection)),self.__view)

    def _public_night(self,source,target,public_digest,groups,prefix=(),counter=False):
        path=(*self.__path,('public_night',target,public_digest,tuple(groups),tuple(prefix),counter))
        return self.__calculation._ClosedCalculation__node(source,groups,path,self.__view)

    def _public_arrival(self,source,target,public_digest,groups,counter=False):
        path=(*self.__path,('public_arrival',target,public_digest,tuple(groups),counter))
        return self.__calculation._ClosedCalculation__node(source,groups,path,self.__view)

    def _evaluation_refinement(self,target=None):
        e=self.__calculation._ClosedCalculation__engine
        graph=getattr(e,'evaluation_graph',None)
        if graph is None:return None
        with self.__calculation._ClosedCalculation__kernel(),e.group_scope(self.__groups),self.relation_scope():
            return graph.refine(self.__source,self.__groups,target)

    def _night_program(self):
        from .anonymous_night import shared_night
        e=self.__calculation._ClosedCalculation__engine
        with self.__calculation._ClosedCalculation__kernel(),e.group_scope(self.__groups),self.relation_scope():
            return shared_night(e,self.__source,self.__groups)

    def _stage_child(self,leaf):
        from .board_future import publication_key
        path=(*self.__path,('owner',leaf.information,self.__source.observer),('action',leaf.target,leaf.death_key))
        if leaf.report is not None:path=(*path,('report',publication_key(leaf.source.public,leaf.source.past)))
        path=(*path,('physical','joint',(self.__source.public.day,leaf.wolves,leaf.scans)))
        if hasattr(leaf,'selection'):path=(*path,('physical','hypothesis',leaf.selection))
        return self.__calculation._ClosedCalculation__node(leaf.source,leaf.groups,path,self.__view)

    def _joint_actions(self):
        from .joint_action_kernel import supported,compile_actions
        e=self.__calculation._ClosedCalculation__engine
        with self.__calculation._ClosedCalculation__kernel(),e.group_scope(self.__groups),self.relation_scope():
            if not supported(e,self.__source):return None
            return compile_actions(e,self.__source,self.__groups)

    def _joint_child(self,plan,outcome):
        path=(*self.__path,('owner',plan.information,self.__source.observer),('action',plan.target,outcome.death_key))
        if outcome.report_index is not None:path=(*path,('report',publication_key(outcome.source.public,outcome.source.past)))
        return self.__calculation._ClosedCalculation__node(outcome.source,outcome.groups,path,self.__view)

    def selection_probability(self,target):
        s=self.__source;e=self.__calculation._ClosedCalculation__engine
        with self.__calculation._ClosedCalculation__kernel(),e.group_scope(self.__groups),self.relation_scope():
            if s.public.phase=='day':
                if e.strategy.day=='random':
                    targets=legal_targets(s.public,e.rules,e.strategy)
                    return F(1,len(targets)) if target in targets else F()
                graph=getattr(e,'evaluation_graph',None)
                decision=graph.day_decision(s,evaluate=True) if graph is not None else None
                if decision is not None:return dict(decision.policy).get(target,F())
                scores=dict(e.day_scores(s.public,s.public_state,s.past));best=max(scores.values())
                chosen=tuple(p for p,v in scores.items() if e.strategy.day=='random' or v==best)
                return F(1,len(chosen)) if target in chosen else F()
            return sum((choice.mass for choice in self.wolf_choices() if choice.target==target),F())

    def action_orbits(self):
        """Constructed action classes shared by scalar, Tree and navigation."""
        s=self.__source;e=self.__calculation._ClosedCalculation__engine
        legal=set(legal_targets(s.physical,e.rules,e.strategy))
        return tuple(tuple(p for p in group if p in legal) for group in (self.__orbits or self.__groups) if any(p in legal for p in group))

    def representative_action(self,target):
        """Canonical action and complete display lift, constructed by grouping."""
        from .navigation_history import NameMap
        source=self.__source;engine=self.__calculation._ClosedCalculation__engine
        groups=self.action_orbits()
        group=next((g for g in groups if target in g),None)
        if group is None:raise ValueError('Unknown action target')
        representative=group[0];n=source.public.player_count
        if representative==target:return representative,NameMap.identity(n)
        population=next(g for g in self.__groups if target in g)
        if representative in population:
            names=list(range(1,n+1));names[representative-1],names[target-1]=target,representative
        else:
            from .public_relation_orbits import initial_transport
            names=initial_transport(self.__relations,representative,target)
        return representative,NameMap(tuple(names))

    def action(self,target):
        s=self.__source;e=self.__calculation._ClosedCalculation__engine
        if s.public.winner is not None or type(target)is not int or target not in legal_targets(s.physical,e.rules,e.strategy):raise ValueError('Illegal action target')
        if s.public.phase=='day':
            recorded=self._evaluation_refinement(target)
            if recorded is not None:
                groups=_fix(self.__groups,(target,))
                return tuple(ActionBranch(edge.probability,self.__calculation._ClosedCalculation__node(edge.source,groups,(*self.__path,('action',target,edge.observation)),self.__view)) for edge in recorded.edges)
        payload=ActionInputs(s.public_state,s.past,s.private,s.observer,s.physical)
        with self.__calculation._ClosedCalculation__kernel():
            acquired,outcomes=resolve_action(s.public,payload,target,e.action_policy,terminal_payoffs=False)
            children=tuple((o,e.action_policy.project(s.public,acquired,o,target)) for o in outcomes)
        groups=_fix(self.__groups,(target,))
        belief=e.anonymous_beliefs.get(s) if getattr(e,'anonymous_nights',False) else None
        if belief is not None and s.public.phase=='day':
            owned={key:child for mass,key,child in belief.execute(target)}
            for outcome,child in children:e.anonymous_beliefs[child]=owned[child.public.winner].refine(groups)
        return tuple(ActionBranch(o.probability,self.__calculation._ClosedCalculation__node(c,groups,(*self.__path,('action',target,outcome_key(o))),self.__view)) for o,c in children)

    def observe(self,target):
        if self.__view is not None:raise ValueError('Observe saved public history before choosing a personal view')
        from .action_flow import observe_action
        s=self.__source
        with self.__calculation._ClosedCalculation__kernel():mass,child=observe_action(s,target,self.__calculation._ClosedCalculation__engine)
        return mass,self.__calculation._ClosedCalculation__node(child,_fix(self.__groups,(target,)),(*self.__path,('observe',target)),None)

    def observe_public_input(self,evidence):
        from .manual_public_input import condition_input
        from .exact import ClaimPolicy
        policy=ClaimPolicy(**self.__calculation.data.to_game().get('claim_policy',{}))
        with self.__calculation._ClosedCalculation__kernel():result=condition_input(self.__source,evidence,self.__calculation.data.game_data.rules,policy)
        groups=[]
        for group in self.__groups:
            split={}
            for player in group:split.setdefault(result.source.public.claims[player-1],[]).append(player)
            groups.extend(tuple(row) for row in split.values())
        child=self.__calculation._ClosedCalculation__node(result.source,_report_groups(tuple(groups),result.source),(*self.__path,('public_input',evidence,policy)),None)
        return result.public_mass,result.physical_mass,child

    def observe_reports(self,seer_reports,medium_reports=()):
        if self.__view is not None:raise ValueError('Observe public reports before choosing a personal view')
        from .report_publication import observe_public_reports
        with self.__calculation._ClosedCalculation__kernel():
            mass,child=observe_public_reports(self.__source,seer_reports,medium_reports,self.__calculation.data.game_data.rules)
        return mass,self.__calculation._ClosedCalculation__node(child,_report_groups(self.__groups,child),(*self.__path,('observed_reports',seer_reports,medium_reports)),None)

    def reports(self):
        s=self.__source
        with self.__calculation._ClosedCalculation__kernel():rows=self.__calculation._ClosedCalculation__engine.report_children(s)
        result=[]
        for q,p,c in rows:
            if c is s:result.append(ReportBranch(q,p,self));continue
            result.append(ReportBranch(q,p,self.__calculation._ClosedCalculation__node(c,_report_groups(self.__groups,c),(*self.__path,('report',publication_key(c.public,c.past))),self.__view)))
        return tuple(result)

    def wolf_choices(self):
        s=self.__source;e=self.__calculation._ClosedCalculation__engine
        if s.public.phase!='night':raise ValueError('Wolf choice requires night')
        result=[]
        with self.__calculation._ClosedCalculation__kernel():
            for info,mass,group in wolf_information_groups(s.private):
                child=ContinuationInputs(s.public,s.public_state,s.past,group,s.observer,physical_board(s.public,group,s.physical))
                owned=self.__calculation._ClosedCalculation__node(child,_fix(self.__groups,_owner_positions(info,s.public.player_count)),(*self.__path,('owner',info,s.observer)),self.__view)
                # Public Q only, independent of the personal-view branch P.
                for target,p in e.wolf_policy(s.public,s.public_state,s.past,info.initial_roster,info.attacks):
                    result.append(WolfChoice(info,mass,target,p,owned))
        return tuple(result)

    def win_certificate(self):
        from .win_certificate import certify
        s=self.__source;e=self.__calculation._ClosedCalculation__engine
        return certify(s.public,s.public_state,s.private,e.strategy,e.rules,s.observer)

    def forecast(self):
        e=self.__calculation._ClosedCalculation__engine;s=self.__source
        with self.__calculation._ClosedCalculation__kernel(),e.group_scope(self.__groups),self.relation_scope():
            _forecast_scope(s,e)
            belief=getattr(e,'anonymous_beliefs',{}).get(s)
            if belief is not None:return e.anonymous_values.forecast(belief)
            value=e.solve(*s,physical=s.physical);targets=legal_targets(s.physical,e.rules,e.strategy)
            orbits=e.target_orbits(targets)
            laws={g[0]:s.private for g in orbits}
            if s.public.phase=='night' and s.public.initial_hunter_count:
                # Same forced-target intervention as root_branch_forecast: retain Q,
                # restrict physical private worlds to legally compatible victims.
                from .belief_projection import project_private
                from .exact import forced_action_worlds,replace_worlds
                laws={g[0]:project_private(s.private,replace_worlds(s.physical,
                    forced_action_worlds(s.physical,g[0],e.rules,e.strategy)),marginalize_private=False) for g in orbits}
            values={g[0]:e.act(*s[:3],g[0],laws[g[0]],s.observer,physical=physical_board(s.public,laws[g[0]],s.physical)) for g in orbits}
            horizons={g[0]:horizon_for_action(e,s.public,s.public_state,s.past,g[0],laws[g[0]],observer=s.observer) for g in orbits}
            representatives={p:g[0] for g in orbits for p in g}
            actions=tuple((p,values[representatives[p]]) for p in targets)
            dawn=tuple((p,horizons[representatives[p]]) for p in targets)
        return Forecast(value,actions,dawn)

    def export_request(self):
        # Fresh replay engine/cache per exported recipe. Callers cannot mutate
        # the live calculation through exported evidence or its engine fields.
        if self.__calculation.data.game_data.hunters:
            from .root_secret_flow import RootSecretEngine
            e=RootSecretEngine(self.__calculation.data.game_data.rules,self.__calculation._ClosedCalculation__strategy,exact_renaming=False)
        else:e=InformationSetForecast(self.__calculation.data.game_data.rules,self.__calculation._ClosedCalculation__strategy,exact_renaming=False,retire_uninformative_scans=False)
        e.retain_joint_guard_history=True
        origin=SavedOrigin(self.__calculation._ClosedCalculation__origin_data,e.rules,e.strategy,project_public=False);request=GeneratedBoard(origin)
        if any(op[0]=='full_trace' for op in self.__path):
            from .action_tree_trace import FullTraceOrigin
            request=GeneratedBoard(FullTraceOrigin(origin))
        for operation in self.__path:
            if operation[0]=='full_trace':continue
            if operation[0]=='anonymous_owned':
                from .anonymous_owned import AnonymousProjectionEvidence
                step=AnonymousProjectionEvidence(operation[1])
            elif operation[0]=='physical':
                from .physical_selection import PhysicalSelectionEvidence
                step=PhysicalSelectionEvidence(operation[1],operation[2])
            elif operation[0]=='public_arrival':
                from .public_convergence import ArrivalObservationEvidence
                step=ArrivalObservationEvidence(e,*operation[1:])
            elif operation[0]=='public_night':
                from .public_convergence import NightObservationEvidence
                step=NightObservationEvidence(e,*operation[1:])
            elif operation[0]=='rename':
                from .public_convergence import TransportEvidence
                step=TransportEvidence(operation[1])
            elif operation[0]=='mixture':
                from .public_convergence import MixtureEvidence
                step=MixtureEvidence(tuple((node.export_request(),mapping,weight) for node,mapping,weight in operation[1]))
            elif operation[0]=='owner':step=OwnerInformationEvidence(operation[1],operation[2])
            elif operation[0]=='observe':step=ObservedActionEvidence(e,operation[1])
            elif operation[0]=='observed_reports':step=ObservedPublicationEvidence(e,operation[1],operation[2])
            elif operation[0]=='public_input':
                from .manual_public_input import PublicInputEvidence
                step=PublicInputEvidence(operation[1],e.rules,operation[2])
            elif operation[0]=='action':step=ActionEvidence(e,operation[1],operation[2],False)
            else:step=PublicationEvidence(e,operation[1])
            request=request.child(step,None)
        return request
