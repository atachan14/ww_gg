"""Closed, snapshot-owned use of the existing uniform H0 common kernels.

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
from .actor_information import PersonalInformation,WolfInformation,wolf_information_groups
from .seer_intervention import SeerObserver
from .exact import Strategy,ClaimPolicy,legal_targets
from .action_flow import resolve_action
from .forecast_result import Forecast
from .calculation_budget import calculation_budget,tick,DEFAULT_MAX_WORK,DEFAULT_MAX_SECONDS
from .model_a_public import horizon_for_action


def _fix(groups,positions):
    fixed=set(positions);out=[]
    for group in groups:
        out.extend((p,) for p in group if p in fixed)
        rest=tuple(p for p in group if p not in fixed)
        if rest:out.append(rest)
    return tuple(out)


def _report_groups(groups,source):
    """Refine inherited classes by complete public outgoing report meaning.

    Named report targets are fixed conservatively. Equal reporters from the
    same parent class remain one block; incoming information can never be
    hidden by equal outgoing declarations.
    """
    records=[(r.player,('seer',r.acquired_day,r.published_day,'day',r.target,r.color)) for r in source.past]
    records.extend((r.reporter,('medium',r.day,r.day,'day',r.target,r.color)) for r in source.public.reports)
    records.extend((actor,('resolved',day,day,'day',target,None)) for day,actor,target in source.public.report_resolved)
    fixed={record[4] for _,record in records}
    result=[]
    for group in _fix(groups,fixed):
        split={}
        for player in group:
            key=tuple(sorted((r for actor,r in records if actor==player),key=repr))
            split.setdefault(key,[]).append(player)
        result.extend(tuple(v) for v in split.values())
    return tuple(result)


def _owner_positions(info,n):
    if type(info)is WolfInformation:
        return tuple(p for p in range(1,n+1) if info.initial_roster&(1<<(p-1)))+tuple(a.target for a in info.attacks)
    return (info.actor,*(a.target for a in info.acquisitions),*((info.target,) if type(info)is SeerObserver else ()))


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

    def __init__(self,data,*,max_work=DEFAULT_MAX_WORK,max_seconds=DEFAULT_MAX_SECONDS):
        if type(data)is not BoardData:raise TypeError('Saved immutable BoardData required')
        game=data.to_game();strategy=Strategy(**game['policy'])
        if (game.get('hunters',0) or game.get('model')!='group'
            or game.get('seer_mode')!='information-fixed-v1'
            or game.get('seer_options',{}).get('likelihood')!='compatibility'
            or game.get('seer_options',{}).get('initial_rule')!='random_white'
            or (strategy.day,strategy.night,strategy.fake_reports)!=('random',)*3
            or strategy.disclosure_for('seer')!='all' or strategy.disclosure_for('medium')!='all'):
            raise Pending('closed_initial_uniform_H0_snapshot_only')
        origin_data,saved_target=_entry_origin(data,game,strategy)
        object.__setattr__(self,'_ClosedCalculation__origin_data',origin_data)
        object.__setattr__(self,'_ClosedCalculation__entry_probability',F(1))
        object.__setattr__(self,'_ClosedCalculation__data',data)
        object.__setattr__(self,'_ClosedCalculation__strategy',strategy)
        object.__setattr__(self,'_ClosedCalculation__max_work',max_work)
        object.__setattr__(self,'_ClosedCalculation__max_seconds',max_seconds)
        engine=InformationSetForecast(data.game_data.rules,strategy,exact_renaming=False,retire_uninformative_scans=False,max_work=max_work)
        engine.retain_joint_guard_history=True
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
            root=self.__node(source,groups,())
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
        return dict(values=len(e.values),actions=len(e.action_values),expansions=dict(e.expansions),
            acquired=len(e.acquired),mornings=len(e.mornings),publications=len(e.publication_values),policies=len(e.policies),
            saved_sources=len(e.board_sources),resolution_cache=len(e.board_action_kernels))

    @contextmanager
    def __kernel(self):
        with calculation_budget(self.__max_work,max_seconds=self.__max_seconds),kernel_calculation():
            tick(0)
            yield

    def __node(self,source,groups,path,view=None):
        node=object.__new__(_Node)
        object.__setattr__(node,'_Node__calculation',self)
        object.__setattr__(node,'_Node__source',source)
        object.__setattr__(node,'_Node__groups',groups)
        object.__setattr__(node,'_Node__path',path)
        object.__setattr__(node,'_Node__view',view)
        return node



class _Node:
    __slots__=('__calculation','__source','__groups','__path','__view')
    def __init__(self,*args,**kwargs):raise TypeError('Nodes are generated by a calculation')
    def __setattr__(self,name,value):raise AttributeError('Generated nodes are immutable')
    @property
    def groups(self):return self.__groups
    def read(self):return self.__source
    def personal(self,information):
        if type(information) not in (PersonalInformation,SeerObserver,WolfInformation):raise ValueError('Typed owner information required')
        if type(information)is SeerObserver:
            from .seer_acquisition import Acquisition
            if type(information.acquisitions)is not tuple or any(type(a)is not Acquisition or a.player!=information.actor for a in information.acquisitions):
                raise ValueError('Only owner records allowed')
        s=self.__source
        # In this H0 generated-path scope every past bite is already recorded.
        # A personal observation cannot invent a future/missing action.
        if type(information)is WolfInformation and information.attacks!=s.private.hypotheses[0].attacks:
            raise ValueError('Use the generated past attack history')
        view=('wolf',information.initial_roster) if type(information)is WolfInformation else ('person',information.actor)
        if self.__view is not None and self.__view!=view:raise ValueError('Choose a personal view from the public root; do not combine owners')
        if type(information) in (PersonalInformation,SeerObserver):
            if type(information.actor)is not int or not 1<=information.actor<=s.public.player_count:raise ValueError('Owner outside original players')
            if type(information)is SeerObserver and (type(information.day)is not int or information.day<1 or type(information.target)is not int or not 1<=information.target<=s.public.player_count or information.target==information.actor):raise ValueError('Invalid owner scan intervention')
        with self.__calculation._ClosedCalculation__kernel():mass,child=self.__calculation._ClosedCalculation__engine.personal_view(s,information)
        groups=_fix(self.__groups,_owner_positions(information,s.public.player_count))
        return mass,self.__calculation._ClosedCalculation__node(child,groups,(*self.__path,('owner',information,child.observer)),view)

    def action(self,target):
        s=self.__source;e=self.__calculation._ClosedCalculation__engine
        if s.public.winner is not None or type(target)is not int or target not in legal_targets(s.physical,e.rules,e.strategy):raise ValueError('Illegal action target')
        payload=ActionInputs(s.public_state,s.past,s.private,s.observer,s.physical)
        with self.__calculation._ClosedCalculation__kernel():
            acquired,outcomes=resolve_action(s.public,payload,target,e.action_policy,terminal_payoffs=False)
            children=tuple((o,e.action_policy.project(s.public,acquired,o,target)) for o in outcomes)
        groups=_fix(self.__groups,(target,))
        return tuple(ActionBranch(o.probability,self.__calculation._ClosedCalculation__node(c,groups,(*self.__path,('action',target,outcome_key(o))),self.__view)) for o,c in children)

    def observe(self,target):
        if self.__view is not None:raise ValueError('Observe saved public history before choosing a personal view')
        from .action_flow import observe_action
        s=self.__source
        with self.__calculation._ClosedCalculation__kernel():mass,child=observe_action(s,target,self.__calculation._ClosedCalculation__engine)
        return mass,self.__calculation._ClosedCalculation__node(child,_fix(self.__groups,(target,)),(*self.__path,('observe',target)),None)

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

    def forecast(self):
        e=self.__calculation._ClosedCalculation__engine;s=self.__source
        if s.public.winner is None and len(s.public.alive)>4:raise Pending('closed_forecast_four_alive_limit')
        with self.__calculation._ClosedCalculation__kernel():
            value=e.solve(*s,physical=s.physical);targets=legal_targets(s.physical,e.rules,e.strategy)
            actions=tuple((p,e.act(*s[:3],p,s.private,s.observer,physical=s.physical)) for p in targets)
            dawn=tuple((p,horizon_for_action(e,s.public,s.public_state,s.past,p,s.private,observer=s.observer)) for p in targets)
        return Forecast(value,actions,dawn)

    def export_request(self):
        # Fresh replay engine/cache per exported recipe. Callers cannot mutate
        # the live calculation through exported evidence or its engine fields.
        e=InformationSetForecast(self.__calculation.data.game_data.rules,self.__calculation._ClosedCalculation__strategy,exact_renaming=False,retire_uninformative_scans=False)
        e.retain_joint_guard_history=True
        origin=SavedOrigin(self.__calculation._ClosedCalculation__origin_data,e.rules,e.strategy,project_public=False);request=GeneratedBoard(origin)
        for operation in self.__path:
            if operation[0]=='owner':step=OwnerInformationEvidence(operation[1],operation[2])
            elif operation[0]=='observe':step=ObservedActionEvidence(e,operation[1])
            elif operation[0]=='observed_reports':step=ObservedPublicationEvidence(e,operation[1],operation[2])
            elif operation[0]=='action':step=ActionEvidence(e,operation[1],operation[2],False)
            else:step=PublicationEvidence(e,operation[1])
            request=request.child(step,None)
        return request
