"""Small uniform complete-game comparison entry. No ordinary factory hookup."""
from collections import Counter
from dataclasses import dataclass,replace
from fractions import Fraction as F
from time import perf_counter
from .cut_out_saved_recipes import SavedCutOutGraph
from .cut_out_day_night import point_fix
from .partitioned_match_groups import UnsupportedPartition
from werewolf.information_set_forecast import InformationSetForecast,InformationSetActionPolicy,Pending
from werewolf.action_flow import action_flow
from werewolf.evaluation_branch import ActionInputs,ContinuationInputs,physical_board
from werewolf.actor_information import wolf_information_groups,condition_actor_state
from werewolf.board_future import calculation_origin,remember,condition_recipe
from werewolf.model_a_public import horizon_for_action
from werewolf.forecast_result import Forecast
from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded


@dataclass(frozen=True)
class OwnView:
    player:int
    role:str
    acquisitions:tuple=()

    def accepts(self,h):
        index={'wolf':0,'medium':1,'seer':2,'hunter':3}.get(self.role)
        owns=bool(h.roles[index]&(1<<(self.player-1))) if index is not None else not any(m&(1<<(self.player-1)) for m in h.roles)
        return owns and all(a in h.acquisitions for a in self.acquisitions)

    def __call__(self,h,state):return self.accepts(h)


class RecordedPolicy(InformationSetActionPolicy):
    def outcomes(self,b,payload,target):
        outcomes=super().outcomes(b,payload,target)
        if not getattr(self.engine,'_board_evidence_snapshot',False):
            self.engine.branch_records.append((b,payload.public_state,payload.private,payload.observer,target,
                tuple((o.probability,o.board) for o in outcomes)))
        if not getattr(self.engine,'_board_evidence_snapshot',False) and self.engine.capture_terminal:
            terminal=tuple(o for o in outcomes if o.board.winner is not None)
            if terminal:self.engine.terminal_records.append((b,payload,target,terminal))
        return outcomes

    def project(self,b,payload,outcome,target):
        start=perf_counter();result=super().project(b,payload,outcome,target)
        if not getattr(self.engine,'_board_evidence_snapshot',False):
            self.engine.costs['law_seconds']+=perf_counter()-start
            self.engine.projected.append(result)
        return result


class CutOutUniformEngine(InformationSetForecast):
    retain_joint_guard_history=True
    def __init__(self,graph,*,representatives=True,view=None):
        super().__init__(graph.engine.baseline.rules,graph.engine.baseline.strategy,
            max_work=1000000,exact_renaming=False,memoize_flows=True,retire_uninformative_scans=False)
        self.graph=graph;self.representatives=representatives;self.view=view
        self.costs=Counter();self.scalar_actions={};self.group_cache={};self.branch_records=[];self.projected=[];self.capture_terminal=False;self.terminal_records=[]
        self.action_policy=RecordedPolicy(self)

    def acquire(self,b,state):
        start=perf_counter();result=super().acquire(b,state)
        if not getattr(self,'_board_evidence_snapshot',False):
            self.costs['law_seconds']+=perf_counter()-start
            self.costs['acquisition_calls']+=1
        return result

    def morning(self,b,s,past):
        start=perf_counter();result=super().morning(b,s,past)
        if not getattr(self,'_board_evidence_snapshot',False):
            self.costs['law_seconds']+=perf_counter()-start
            self.costs['morning_calls']+=1
        return result

    def exchangeable(self,b):return False
    def value_law(self,state):return state
    def full_renamed_key(self,*args,**kwargs):return None
    def renamed_value_key(self,*args,**kwargs):return None
    def equivalent_targets(self,*args,**kwargs):return False
    def actor_equivalent_targets(self,*args,**kwargs):return False

    def groups(self,b,past,private):
        started=perf_counter()
        # Only previously proved groups and explicit observations are used.
        # Private branch law is NOT inspected for inferred secret endpoints.
        fixed={e.target for e in b.history}
        fixed.update(x for r in past for x in (r.player,r.target))
        fixed.update(x for r in b.reports for x in (r.reporter,r.target))
        if self.view is not None:
            fixed.add(self.view.player)
            fixed.update(x for a in self.view.acquisitions for x in (a.player,a.target))
        # A wolf actor conditions on its own roster, before choosing a bite.
        masks={h.roles[0] for h in private.hypotheses}
        if len(masks)==1:fixed.update(p for p in range(1,b.player_count+1) if next(iter(masks))&(1<<(p-1)))
        key=tuple(sorted(fixed))
        if key not in self.group_cache:
            self.group_cache[key]=point_fix(self.graph.engine.start().groups,*key)
            self.costs['cut_out_builds']+=1
        self.costs['cut_out_seconds']+=perf_counter()-started
        return self.group_cache[key]

    def act(self,b,s,past,target,private,observer,*,physical=None):
        physical=physical_board(b,private,physical)
        groups=self.groups(b,past,private)
        group=next(g for g in groups if target in g)
        representative=group[0] if self.representatives else target
        key_started=perf_counter()
        key=(b,s,past,private,observer,physical,representative)
        available=key in self.scalar_actions
        self.costs['key_seconds']+=perf_counter()-key_started
        self.costs['action_requests']+=1
        restore_started=perf_counter()
        if available:
            self.costs['representative_hits']+=1
            restored=self.scalar_actions[key]
            if representative!=target:
                self.costs['label_scalar_restores']+=1
                self.costs['label_restore_seconds']+=perf_counter()-restore_started
            return restored
        self.costs['action_evaluations']+=1
        start=perf_counter()
        value=action_flow(b,ActionInputs(s,past,private,observer,physical),representative,self.action_policy)
        self.costs['inclusive_action_seconds']+=perf_counter()-start
        key_started=perf_counter();self.scalar_actions[key]=value
        self.costs['key_seconds']+=perf_counter()-key_started
        return value

    def solve(self,b,s,past,private,observer,*,physical=None):
        if b.winner:return F(b.winner=='village')
        physical=physical_board(b,private,physical)
        key_started=perf_counter();key=(b,s,past,private,observer,physical)
        cached=self.values.get(key)
        self.costs['key_seconds']+=perf_counter()-key_started
        if cached is not None:return cached
        if b.phase=='day':
            groups=self.groups(b,past,private)
            choices=tuple(tuple(p for p in g if p in b.alive) for g in groups) if self.representatives else tuple((p,) for p in b.alive)
            value=sum((F(len(g),len(b.alive))*self.act(b,s,past,g[0],private,observer,physical=physical) for g in choices if g),F())
        elif b.phase=='night':
            value=F()
            for info,mass,own in wolf_information_groups(private):
                policy=dict(self.wolf_policy(b,s,past,info.initial_roster,info.attacks))
                groups=self.groups(b,past,own)
                choices=tuple(tuple(p for p in g if p in policy) for g in groups) if self.representatives else tuple((p,) for p in policy)
                for g in choices:
                    if g:value+=mass*sum((policy[p] for p in g),F())*self.act(b,s,past,g[0],own,observer,physical=physical_board(b,own,physical))
        else:raise Pending('cut_out_unknown_phase')
        key_started=perf_counter();self.values[key]=value
        self.costs['key_seconds']+=perf_counter()-key_started
        return value


class OfficialLabelledEngine(CutOutUniformEngine):
    # Independent OLD common recursion, with every target explicitly evaluated.
    # Avoid both exact-renaming and the experimental solve/group path.
    def groups(self,*args):raise AssertionError('reference cannot use cut-out groups')
    def solve(self,*args,**kwargs):return InformationSetForecast.solve(self,*args,**kwargs)
    def act(self,b,s,past,target,private,observer,*,physical=None):
        self.costs['action_requests']+=1
        key=(b,s,past,private,observer,physical,target)
        if key not in self.scalar_actions:
            self.costs['action_evaluations']+=1
            self.scalar_actions[key]=action_flow(b,ActionInputs(s,past,private,observer,
                physical_board(b,private,physical)),target,self.action_policy)
        return self.scalar_actions[key]


def _evaluate(graph,*,representatives=True,view=None,max_seconds=25,official_reference=False,capture_terminal=False):
    if type(graph) is not SavedCutOutGraph:return UnsupportedPartition('saved constructed graph required')
    if view is not None and (type(view) is not OwnView or view.role not in ('wolf','medium','seer','villager') or
        not 1<=view.player<=graph.engine.baseline.players or any(a.player!=view.player for a in view.acquisitions)):
        return UnsupportedPartition('explicit own role/results only')
    engine=(OfficialLabelledEngine if official_reference else CutOutUniformEngine)(graph,representatives=representatives,view=view)
    engine.capture_terminal=capture_terminal
    root=graph.origin();own=root.private
    if view is not None:
        if not any(view.accepts(h) for h in own.hypotheses):return UnsupportedPartition('own evidence has zero support')
        own=condition_actor_state(own,view.accepts)
    context=ContinuationInputs(root.public,root.public_state,root.past,own,view,physical_board(root.public,own,root.physical))
    request=graph.root
    if view is not None:
        recipe=condition_recipe(root,context)
        if recipe is None:return UnsupportedPartition('own evidence recipe unavailable')
        request=request.child(recipe,request.facts)
    start=perf_counter()
    with calculation_budget(1000000,max_seconds=max_seconds),calculation_origin(graph.data):
        remember(engine,request,context)
        value=engine.solve(*context,physical=context.physical)
        actions=tuple((p,engine.act(*context[:3],p,context.private,context.observer,physical=context.physical)) for p in root.public.alive)
        dawn=tuple((p,horizon_for_action(engine,root.public,root.public_state,root.past,p,own,observer=view)) for p in root.public.alive)
    engine.costs['total_seconds']=perf_counter()-start
    engine.costs['evaluation_other_seconds']=max(0,engine.costs['total_seconds']-engine.costs['law_seconds']-engine.costs['cut_out_seconds']-engine.costs['label_restore_seconds']-engine.costs['key_seconds'])
    engine.costs['saved_origins']=len({id(r.origin) for r in engine.board_sources.values()})
    engine.costs['generated_boards']=len(engine.board_sources)
    engine.costs['law_hypotheses_retained']=sum(len(key[1].hypotheses) for key in engine.values if hasattr(key[1],'hypotheses'))
    return Forecast(value,actions,dawn),engine


def evaluate(graph,*,representatives=True,view=None,max_seconds=25,official_reference=False,capture_terminal=False):
    if type(max_seconds) not in (int,float) or not 0<max_seconds<=25:
        return UnsupportedPartition('comparison entry requires a positive <=25s evaluation budget')
    try:
        return _evaluate(graph,representatives=representatives,view=view,max_seconds=max_seconds,official_reference=official_reference,capture_terminal=capture_terminal)
    except Pending as error:return UnsupportedPartition('common flow pending: '+error.reason)
    except CalculationBudgetExceeded:return UnsupportedPartition('comparison evaluation budget exhausted')
