"""Six-player input snapshots and semantic, lazy generated-Board registry."""
from dataclasses import dataclass,replace,field
from types import SimpleNamespace
from fractions import Fraction as F
from time import perf_counter
from .cut_out_model_a import source_game,adapt_six_model_a,InitialModelASpec
from .cut_out_saved_recipes import SavedCutOutGraph,InvalidatedBranch,MorningDeltaEvidence,ObservedAction
from .cut_out_day_night import point_fix
from .partitioned_match_groups import UnsupportedPartition
from .cut_out_uniform_game import OwnView
from werewolf.board_flow import BoardData
from werewolf.board_future import (SavedOrigin,GeneratedBoard,ActionEvidence,PublicationEvidence,ConditionEvidence,ContextEvidence,
    kernel_snapshot,same_role_board,completed_step)
from werewolf.evaluation_branch import ContinuationInputs,physical_board
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.actor_information import condition_actor_state
from werewolf.public_log import migrate,transaction
from werewolf.public_log_changes import upgrade,project_changes
from werewolf.board_owned_log import commit_owned_change
from werewolf.report_publication import publication_slot
from werewolf.seer_acquisition import SeerReport,Acquisition


@dataclass(frozen=True)
class OwnEvidence:
    view:OwnView
    @completed_step
    def __call__(self,source):
        if type(self.view) is not OwnView or type(self.view.player) is not int or not 1<=self.view.player<=6 or self.view.role not in ('wolf','seer','medium','villager') or type(self.view.acquisitions) is not tuple or any(type(a) is not Acquisition or a.player!=self.view.player for a in self.view.acquisitions):
            raise ValueError('only own role and own acquisition records are allowed')
        own=condition_actor_state(source.private,self.view.accepts)
        return ContinuationInputs(source.public,source.public_state,source.past,own,self.view,physical_board(source.public,own,source.physical))
    _completed:list=field(default_factory=list,init=False,compare=False,repr=False)


@dataclass(frozen=True)
class WolfEvidence:
    mask:int
    source_kind:str="private"
    physical_source:str="physical"
    observer_override:object=None
    preserve_observer:bool=True
    @completed_step
    def __call__(self,source):
        if self.source_kind not in ('public','private') or self.physical_source not in ('physical','intervention'):raise ValueError('unknown conditional law source')
        law=source.public_state if self.source_kind=='public' else source.private
        own=condition_actor_state(law,lambda h:h.roles[0]==self.mask)
        observer=source.observer if self.preserve_observer else self.observer_override
        return ContinuationInputs(source.public,source.public_state,source.past,own,observer,physical_board(source.public,own,source.physical if self.physical_source=='physical' else None))
    def likelihood(self,source):
        return sum((h.mass for h in source.private.hypotheses if h.roles[0]==self.mask),F())
    _completed:list=field(default_factory=list,init=False,compare=False,repr=False)


@dataclass(frozen=True)
class RegistryAction(ObservedAction):
    def likelihood(self,source):
        from werewolf.action_flow import resolve_action
        from werewolf.evaluation_branch import ActionInputs
        from werewolf.board_future import outcome_key
        acquired,outcomes=resolve_action(source.public,ActionInputs(source.public_state,source.past,source.private,source.observer,source.physical),self.target,self.engine.action_policy,terminal_payoffs=False)
        chance=sum((o.probability for o in outcomes if outcome_key(o)==self.observation),F())
        if source.public.phase=='night':
            from werewolf.actor_information import wolf_information_groups
            chance*=sum((mass*dict(self.engine.wolf_policy(source.public,source.public_state,source.past,info.initial_roster,info.attacks)).get(self.target,F()) for info,mass,law in wolf_information_groups(source.private)),F())
        return chance


@dataclass(frozen=True)
class RecipeDescriptor:
    operations:tuple


class LazyBinding:
    def __init__(self,registry,descriptor):
        self.registry,self.descriptor=registry,descriptor;self._request=None;self.reads=0
    def request(self):
        if self._request is None:
            current=self.registry.root
            for kind,args in self.descriptor.operations:
                if kind=='action':
                    target,observation=args;operation=RegistryAction(kernel_snapshot(self.registry.kernel),target,observation,False)
                elif kind=='morning':operation=MorningDeltaEvidence(kernel_snapshot(self.registry.kernel),*args)
                elif kind=='own':operation=OwnEvidence(args)
                elif kind=='wolf':operation=WolfEvidence(*args) if type(args) is tuple else WolfEvidence(args)
                else:raise ValueError('unknown semantic recipe')
                current=current.child(operation,None)
            self._request=current
        return self._request
    def read(self):
        self.reads+=1
        if self.registry.problem:return self.registry.problem
        try:return self.request().roles()
        except (ValueError,Pending) as error:return InvalidatedBranch(getattr(error,'reason',str(error)))
    def mass(self):
        if self.registry.problem:return self.registry.problem
        if any(kind=='wolf' and type(args) is tuple and args[1]=='public' for kind,args in self.descriptor.operations):
            return InvalidatedBranch('public-belief cache bridge has no standalone physical path mass')
        try:
            state=self.registry.origin();mass=F(1)
            for operation in self.request().history:
                if hasattr(operation,'likelihood'):
                    chance=operation.likelihood(state)
                    if chance<=0:raise ValueError('semantic path has zero mass')
                    mass*=chance
                state=operation(state)
            return mass
        except (ValueError,Pending) as error:return InvalidatedBranch(getattr(error,'reason',str(error)))


class SixInputRegistry(SavedCutOutGraph):
    """Only built from an explicit six-player saved timeline; no law ingestion."""
    def __init__(self,base,data,*,shape=None):
        self.base,self.data=base,data;self.problem=None;self.bindings={};self.stats={}
        self.origin=SavedOrigin(data,base.rules,base.strategy,project_public=False)
        self.kernel=InformationSetForecast(base.rules,base.strategy,exact_renaming=False,memoize_flows=True,retire_uninformative_scans=False,max_work=1000000)
        self.kernel.retain_joint_guard_history=True
        self.root=GeneratedBoard(self.origin,facts=None)
        try:
            root=self.origin();self._shape=root.public
            g=data.to_game();claims=tuple(g['history'][0]['claims'] if g['history'] else g['claims'])
            reports=tuple(SeerReport(r['day'],1,r['reporter'],r['target'],r['color']) for r in g['seer_inputs'] if publication_slot(g,'seer',r)==0)
            initial=adapt_six_model_a(replace(base,claims=claims,reports=reports))
            if isinstance(initial,UnsupportedPartition):raise ValueError(initial.reason)
            groups=initial.start().groups
            fixed={e.target for e in root.public.history}
            fixed.update(x for r in root.past for x in (r.player,r.target))
            fixed.update(x for r in root.public.reports for x in (r.reporter,r.target))
            fixed.update(e['player'] for b in g['public_log']['batches'] for e in b['events'])
            groups=point_fix(groups,*fixed)
            baseline=SimpleNamespace(players=6,rules=base.rules,strategy=base.strategy,spec=base,
                board=root.public,state=root.public_state,past=root.past)
            self.engine=SimpleNamespace(baseline=baseline,start=lambda:SimpleNamespace(groups=groups))
        except (ValueError,Pending) as error:
            self.problem=InvalidatedBranch(getattr(error,'reason',str(error)));self._shape=shape
            self.engine=None
    @classmethod
    def create(cls,base,targets=(),reports=(),medium_reports=()):
        initial=adapt_six_model_a(base)
        if isinstance(initial,UnsupportedPartition):return initial
        if type(targets) is not tuple or len(targets) not in (0,2):raise ValueError('six-player Day1/Day2 input snapshot only; explicit night edits unsupported')
        g=source_game(base,six=True);g.pop('public_log')
        step={k:g[k] for k in ('claims','claim_policy','policy','seer_options','result_disclosure_model')}
        g['history']=[dict(step,target=p) for p in targets]
        all_reports=base.reports+tuple(reports)
        if any(r.published_day!=r.acquired_day for r in all_reports):raise ValueError('use existing transaction for late publication ownership')
        g['seer_inputs']=[dict(day=r.acquired_day,reporter=r.player,target=r.target,color=r.color) for r in all_reports]
        g['reports']=[dict(day=r.day,reporter=r.reporter,target=r.target,color=r.color) for r in medium_reports]
        g['public_log']=upgrade(migrate(g));g=project_changes(g,g['public_log'])
        return cls(base,BoardData.from_game(g))
    def read(self):return self.problem or self.origin()
    def corrected_root(self,base,reports=(),medium_reports=()):
        if type(base) is not InitialModelASpec:return InvalidatedBranch('explicit initial input spec required')
        if any(getattr(base,k)!=getattr(self.base,k) for k in ('players','mediums','seers','rules','strategy','claim_policy')):
            return InvalidatedBranch('root correction cannot change cast/rule/policy')
        targets=tuple(step['target'] for step in self.data.to_game()['history'])
        candidate=SixInputRegistry.create(base,targets,reports,medium_reports)
        if isinstance(candidate,UnsupportedPartition):return candidate
        game=candidate.data.to_game();game['revision']=self.data.to_game().get('revision',0)+1
        data=self.data.updated(**{k:v for k,v in game.items() if k not in ('players','wolves','mediums','seers','hunters','rules')})
        return SixInputRegistry(base,data,shape=self._shape)
    def edited(self,payload):
        if type(payload) is not dict:return InvalidatedBranch('existing public-log transaction object required')
        before=self.data.to_game()
        try:
            after=transaction(before,self._shape,payload)
            after=commit_owned_change(before,after);after['revision']=before.get('revision',0)+1
            changes={k:v for k,v in after.items() if k not in ('players','wolves','mediums','seers','hunters','rules')}
            return SixInputRegistry(self.base,self.data.updated(**changes),shape=self._shape)
        except (ValueError,Pending) as error:return InvalidatedBranch(getattr(error,'reason',str(error)))
    def register(self,request):
        if request.origin is not self.origin:raise ValueError('request must belong to this saved origin')
        state=self.origin();items=[]
        for operation in request.history:
            result=operation(state)
            if isinstance(operation,ActionEvidence):items.append(('action',(operation.target,operation.observation)))
            elif isinstance(operation,MorningDeltaEvidence):items.append(('morning',(operation.seers,operation.mediums)))
            elif isinstance(operation,OwnEvidence):items.append(('own',operation.view))
            elif isinstance(operation,WolfEvidence):items.append(('wolf',(operation.mask,operation.source_kind,operation.physical_source,operation.observer_override,operation.preserve_observer)))
            elif isinstance(operation,PublicationEvidence):
                if result.past[:len(state.past)]!=state.past:raise ValueError('publication replaced prefix')
                items.append(('morning',(result.past[len(state.past):],result.public.reports[len(state.public.reports):])))
            elif isinstance(operation,ConditionEvidence):
                if operation.identity:pass
                elif result.observer!=state.observer and type(result.observer) is OwnView:items.append(('own',result.observer))
                elif len({h.roles[0] for h in result.private.hypotheses})==1:items.append(('wolf',(result.private.hypotheses[0].roles[0],operation.source_kind,operation.physical_source,operation.observer,False)))
                else:raise ValueError('condition lacks supported semantic role/roster descriptor')
            elif isinstance(operation,ContextEvidence):
                if result!=state:raise ValueError('nonidentity context projection outside retained-law registry')
            else:raise ValueError('unregistered recipe type '+type(operation).__name__)
            state=result
        binding=self.bind_descriptor(RecipeDescriptor(tuple(items)))
        rebuilt=binding.read()
        if isinstance(rebuilt,InvalidatedBranch) or (rebuilt.public_state,rebuilt.private,rebuilt.past,rebuilt.observer)!=(state.public_state,state.private,state.past,state.observer):
            raise ValueError('semantic registration does not reproduce complete input law')
        if not same_role_board(rebuilt.public,state.public) or not same_role_board(rebuilt.physical,state.physical):raise ValueError('semantic registry Board mismatch')
        return binding
    def bind_descriptor(self,descriptor):
        if type(descriptor) is not RecipeDescriptor:raise TypeError('semantic descriptor required')
        if descriptor not in self.bindings:self.bindings[descriptor]=LazyBinding(self,descriptor)
        return self.bindings[descriptor]
    def rebind(self,binding):
        if any(kind=='wolf' and type(args) is tuple and args[1]=='public' for kind,args in binding.descriptor.operations):
            return InvalidatedBranch('public-belief cache bridge is snapshot-local; reissue from the new evaluation')
        return self.bind_descriptor(binding.descriptor)
    def bind(self,observation):raise ValueError('use preview_action or bind_descriptor for a saved current Board')
    def corrected(self,spec):raise ValueError('use corrected_root with explicit current reports, or edited for the current owner')
    def register_all(self,*args):raise ValueError('request individual branches lazily; global terminal trees are verification work')

@dataclass(frozen=True)
class CurrentScreen:
    forecast:object
    table:object
    public_joint:object
    own_belief:object
    physical_joint:object
    engine:object
    timings:object
    primary:object=None
    cumulative:object=None
    def pair(self,left,left_role,right,right_role,*,own=False):
        if any(type(p) is not int or not 1<=p<=6 for p in (left,right)) or any(r not in ('wolf','medium','seer','hunter','villager') for r in (left_role,right_role)):raise ValueError('explicit original players and role names required')
        law=self.own_belief if own else self.public_joint
        def has(h,p,role):
            index={'wolf':0,'medium':1,'seer':2,'hunter':3}.get(role)
            return bool(h.roles[index]&(1<<(p-1))) if index is not None else not any(m&(1<<(p-1)) for m in h.roles)
        return sum((h.mass for h in law.hypotheses if has(h,left,left_role) and has(h,right,right_role)),F())


def current_screen(registry,*,view=None,official_reference=False):
    from .cut_out_uniform_game import evaluate
    from werewolf.player_view import build_public_view,ViewScope,ResultFrame,private_api_rows
    from werewolf.exact import replace_worlds,Values
    started=perf_counter();evaluated=evaluate(registry,view=view,official_reference=official_reference)
    if isinstance(evaluated,UnsupportedPartition):return evaluated
    forecast,engine=evaluated;eval_seconds=perf_counter()-started
    root=registry.origin();belief=root.public_state;physical=root.private
    if view is not None:
        belief=condition_actor_state(belief,view.accepts);physical=condition_actor_state(physical,view.accepts)
    board=replace_worlds(root.public,belief.public_roles)
    marginals=[{r:board.role_probability(p,r) for r in ('wolf','medium','seer','hunter','villager')} for p in range(1,7)]
    started=perf_counter();primary=Values(forecast.village_win,1-forecast.village_win)
    cumulative=registry.data.roles().progress.total_values(primary) if view is None else None
    if view is None:
        roles=SimpleNamespace(probabilities=lambda p:marginals[p-1])
        table=build_public_view(registry.data,roles,board,ResultFrame(ViewScope.public(registry.data),'complete','screen-prototype'),
            state=registry.data.to_game(),event_history=board.history,alive=board.alive,
            action_values={p:Values(v,1-v) for p,v in forecast.action_values},by_dawn_values=dict(forecast.by_dawn_values),manual=True)
    else:table=private_api_rows(marginals,targets=dict(forecast.action_values),final_values=dict(forecast.action_values),dawn_for=dict(forecast.by_dawn_values).get)
    return CurrentScreen(forecast,table,root.public_state,belief,physical,engine,
        dict(evaluation_seconds=eval_seconds,table_seconds=perf_counter()-started),primary,cumulative)


def preview_action(registry,target,*,winner=None,view=None):
    """Literal individual label, materialized only when its branch is opened."""
    from werewolf.exact import action_outcomes
    from werewolf.board_future import outcome_key
    if registry.problem:return registry.problem
    source=registry.origin()
    if source.public.phase!='day':return InvalidatedBranch('day-action preview only; night requires an explicit actor observation')
    if type(target) is not int or target not in source.public.alive:return InvalidatedBranch('living action label required')
    physical=source.physical
    prefix=()
    if view is not None:
        try:source=OwnEvidence(view)(source)
        except ValueError as error:return InvalidatedBranch(str(error))
        physical=source.physical;prefix=(('own',view),)
    matches=[o for o in action_outcomes(physical,target,registry.base.rules,registry.base.strategy) if o.board.winner==winner]
    if len(matches)!=1:return InvalidatedBranch('requested individual action observation has zero support')
    descriptor=RecipeDescriptor(prefix+(('action',(target,outcome_key(matches[0]))),))
    return registry.bind_descriptor(descriptor)
