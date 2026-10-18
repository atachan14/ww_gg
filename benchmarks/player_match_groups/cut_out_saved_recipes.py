"""SavedOrigin-backed recipes for every labelled small cut-out branch.

No transported posterior is an origin. Observations are replayed from immutable
saved inputs; morning recipes contain only NEW reports, never the old prefix.
Normal Board/UI factories are not modified.
"""
from dataclasses import dataclass,field,replace
from collections import Counter
from fractions import Fraction as F
from hashlib import sha256
import json
from time import perf_counter
from .cut_out_model_a import adapt_model_a,adapt_six_model_a,ModelAInitialGroups,InitialModelASpec,source_game
from .cut_out_morning import CutOutMorning,MorningResult
from .cut_out_day_night import point_fix
from .partitioned_match_groups import UnsupportedPartition
from werewolf.board_flow import BoardData
from werewolf.board_future import (SavedOrigin,GeneratedBoard,ActionEvidence,completed_step,
    kernel_snapshot,same_role_board,reconstruction_kernel_reuse)
from werewolf.information_set_forecast import InformationSetForecast,Pending
from werewolf.exact import PublicEvent,action_outcomes,MediumReport
from werewolf.seer_acquisition import SeerReport
from werewolf.actor_information import wolf_information_groups
from werewolf.evaluation_branch import ContinuationInputs,physical_board
from werewolf.player_view import PlayerData,ReadMap,ViewScope,ResultFrame,PublicIndex,Declaration,freeze


@dataclass(frozen=True)
class InvalidatedBranch:
    reason: str


@dataclass(frozen=True)
class PathObservation:
    execution: int
    bite: int | None
    winner: str | None
    seers: tuple
    mediums: tuple


@dataclass(frozen=True)
class ObservedAction(ActionEvidence):
    def likelihood(self,source):
        b=source.public
        if b.phase=='day':
            matched=[o.probability for o in action_outcomes(b,self.target,self.engine.rules,self.engine.strategy)
                     if (o.board.alive,o.board.day,o.board.phase,o.board.winner,o.board.history)==self.observation]
            if len(matched)!=1:raise ValueError('execution observation lost support')
            return matched[0]
        # W1 + no hunter + uniform legal bites: casualty/winner conditional on
        # this bite is deterministic. Integrate OWNED policy over PUBLIC law.
        if b.wolf_count_distribution!={1:F(1)} or b.initial_hunter_count:
            raise ValueError('night likelihood outside one-wolf no-hunter proof')
        return sum((mass*dict(self.engine.wolf_policy(b,source.public_state,source.past,info.initial_roster,info.attacks)).get(self.target,F())
                    for info,mass,law in wolf_information_groups(source.public_state)),F())


@dataclass(frozen=True)
class MorningDeltaEvidence:
    engine: object
    seers: tuple
    mediums: tuple
    _completed: list=field(default_factory=list,init=False,compare=False,repr=False)

    def select(self,source):
        if source.public.winner is not None:raise ValueError('terminal branch cannot publish')
        branches=self.engine.push(source.public_state,source.private,
            self.engine.morning(source.public,source.public_state,source.past))
        selected=[row for row in branches
            if row[3][:len(source.past)]==source.past and row[3][len(source.past):]==self.seers
            and row[1].reports[:len(source.public.reports)]==source.public.reports
            and row[1].reports[len(source.public.reports):]==self.mediums]
        if len(selected)!=1:raise ValueError('new publication delta no longer uniquely supported')
        return selected[0]

    def likelihood(self,source):return self.select(source)[0]

    @completed_step
    def __call__(self,source):
        q,b,s,p,own=self.select(source)
        return ContinuationInputs(b,s,p,own,source.observer,physical_board(b,own,source.physical))


@dataclass(frozen=True,eq=False)
class BoardComparisonContext:
    request: GeneratedBoard
    inputs: ContinuationInputs
    groups: tuple
    scope: ViewScope
    frame: ResultFrame


@dataclass(frozen=True)
class BoundPlayerComparison:
    data: PlayerData
    context: BoardComparisonContext=field(repr=False)
    block: int

    @property
    def token(self):return self.context,self.block

    def valid_for(self,binding):return self.context.request is binding.request and self.context.scope==binding.scope


def equivalent(left,right):
    return (left.data.frame.scope==left.context.scope and right.data.frame.scope==right.context.scope
            and left.token==right.token)


class SavedBinding:
    def __init__(self,graph,observation,request,groups):
        self.graph,self.observation,self.request,self._groups=graph,observation,request,groups
        digest=sha256(graph.data.inputs.encode()).hexdigest()
        path_digest=sha256(repr(observation).encode()).hexdigest()
        branch_id=('cutout-saved',graph.data.facts.board_id,path_digest)
        self.scope=ViewScope(graph.data.runtime,branch_id,graph.data.to_game().get('revision',0),digest,evidence_digest=path_digest)
        self.frame=ResultFrame(self.scope,'roles',digest+':'+path_digest)
        self._context=None

    def read(self,*,reference=False):
        started=perf_counter();self.graph.stats['roles_reads']+=1
        try:
            with reconstruction_kernel_reuse(not reference):inputs=self.request.roles()
            if inputs.observer is not None:raise ValueError('public recipe acquired a private observer')
            if inputs.public_state!=inputs.private or not same_role_board(inputs.public,inputs.physical):
                raise ValueError('public physical-measure proof no longer applies')
            inputs=replace(inputs,board_data=self.request)
            if self._context is None or self._context.inputs!=inputs:
                self._context=BoardComparisonContext(self.request,inputs,self._groups,self.scope,self.frame)
            return self._context
        except (ValueError,Pending) as error:
            self.graph.stats['invalidated_reads']+=1
            return InvalidatedBranch(getattr(error,'reason',str(error)))
        finally:self.graph.stats['roles_seconds']+=perf_counter()-started

    def mass(self):
        """Conditional on choosing this execution target, not k/N class mass."""
        started=perf_counter();source=self.graph.origin();mass=F(1)
        try:
            for operation in self.request.history:
                chance=operation.likelihood(source)
                if chance<=0:raise ValueError('observed path has zero probability')
                source=operation(source);mass*=chance
            return mass
        except (ValueError,Pending) as error:return InvalidatedBranch(getattr(error,'reason',str(error)))
        finally:self.graph.stats['likelihood_seconds']+=perf_counter()-started

    def rows(self):
        context=self.read()
        if isinstance(context,InvalidatedBranch):return context
        b=context.inputs.public
        index=PublicIndex.from_board(self.graph.data)
        declarations=list(index.events)
        prefix=self.graph.engine.baseline.past
        # Existing input metadata is retained; generated reports are factual
        # read projections, not new saved user-input batches or CO timing rules.
        for kind,records in (('medium',b.reports),('seer',context.inputs.past[len(prefix):])):
            for offset,r in enumerate(records):
                p=r.reporter if kind=='medium' else r.player
                acquired=r.day if kind=='medium' else r.acquired_day
                published=r.day if kind=='medium' else r.published_day
                event=freeze(dict(kind=kind,player=p,target=r.target,day=acquired,color=r.color))
                declarations.append(Declaration(event,2*(published-1),self.scope.board_id,None,None,None,True,published,'day'))
        rows=[]
        for block,players in enumerate(context.groups):
            for p in players:
                q={role:b.role_probability(p,role) for role in ('wolf','medium','seer','hunter','villager')}
                # Role-stage PlayerData only. Missing action/horizon values stay
                # pending via the EXISTING ResultFrame/metric contract.
                legacy=ReadMap((('id',p),('wolf_probability',q['wolf']),('medium_probability',q['medium']),
                    ('citizen_probability',q['villager']),('village_probability',1-q['wolf']),
                    ('extra_probabilities',ReadMap((('seer',q['seer']),('hunter',q['hunter']))))))
                own=tuple(d for d in declarations if d.player==p)
                received=tuple(d for d in declarations if d.active and d.event['kind'] in ('seer','medium') and d.target==p)
                data=PlayerData(p,legacy,self.frame,own,received,b.claims[p-1],f'Player {p}',p in b.alive)
                rows.append(BoundPlayerComparison(data,context,block))
        return tuple(rows)


class SavedCutOutGraph:
    def __init__(self,engine,*,data=None,origin_factory=SavedOrigin):
        if type(engine) is not ModelAInitialGroups:raise TypeError('constructed formal adapter required')
        self.engine=engine
        self.data=BoardData.from_game(json.loads(engine.baseline.game_json)) if data is None else data
        expected=json.loads(engine.baseline.game_json);actual=self.data.to_game()
        if any(actual.get(k)!=v for k,v in expected.items() if k!='public_log'):
            raise ValueError('saved data is not the constructed initial semantic snapshot')
        if any(actual.get('public_log',{}).get(k)!=expected['public_log'].get(k) for k in ('version','base_claims','base_seer','base_medium','batches')):
            raise ValueError('arbitrary saved log is not an explicit initial snapshot')
        self.origin=origin_factory(self.data,engine.baseline.rules,engine.baseline.strategy,project_public=False)
        self.stats=Counter(roles_reads=0,invalidated_reads=0,recipe_branches=0,generator_checks=0,
            child_prior_reallocations=0,origin_gates=1)
        started=perf_counter();root=self.origin()
        if (not same_role_board(root.public,engine.baseline.board) or root.public_state!=engine.baseline.state
            or root.private!=engine.baseline.state or root.past!=engine.baseline.past or root.observer is not None
            or not same_role_board(root.physical,engine.baseline.board)):
            raise ValueError('SavedOrigin and constructed adapter disagree; no projection fallback')
        self.stats['origin_gate_seconds']=perf_counter()-started
        self.kernel=InformationSetForecast(engine.baseline.rules,engine.baseline.strategy,
            exact_renaming=False,memoize_flows=True,retire_uninformative_scans=False,max_work=100000)
        self.kernel.retain_joint_guard_history=True
        self.root=GeneratedBoard(self.origin,facts=(1,'day',engine.start().alive))
        self._days={};self._nights={};self._bindings={}

    def bind(self,observation):
        if type(observation) is not PathObservation:raise TypeError('closed labelled observation descriptor required')
        if type(observation.seers) is not tuple or any(type(r) is not SeerReport or r.published_day!=2 for r in observation.seers):
            raise ValueError('only generated first-morning seer deltas accepted')
        if type(observation.mediums) is not tuple or any(type(r) is not MediumReport or r.day!=2 for r in observation.mediums):
            raise ValueError('only generated first-morning medium deltas accepted')
        if observation.bite is None and observation.winner!='village':raise ValueError('day-only descriptor must be a terminal execution')
        if observation.winner is not None and (observation.seers or observation.mediums):raise ValueError('terminal descriptor cannot add reports')
        if observation in self._bindings:return self._bindings[observation]
        n=self.engine.baseline.players;p=observation.execution
        if type(p) is not int or not 1<=p<=n:raise ValueError('original execution target required')
        alive=tuple(x for x in range(1,n+1) if x!=p)
        day_winner=observation.winner if observation.bite is None else None
        day_history=(PublicEvent(1,'day',p),)
        day_key=(p,day_winner)
        if day_key not in self._days:
            obs=(alive,1,'day' if day_winner else 'night',day_winner,day_history)
            operation=ObservedAction(kernel_snapshot(self.kernel),p,obs,False)
            self._days[day_key]=self.root.child(operation,(1,obs[2],alive))
        request=self._days[day_key];groups=point_fix(self.engine.start().groups,p)
        if observation.bite is not None:
            target=observation.bite
            if type(target) is not int or target not in alive:raise ValueError('living bite target required')
            final_alive=tuple(x for x in alive if x!=target)
            day=1 if observation.winner else 2;phase='night' if observation.winner else 'day'
            history=(*day_history,PublicEvent(1,'night',target))
            key=(day_key,target,observation.winner)
            if key not in self._nights:
                obs=(final_alive,day,phase,observation.winner,history)
                operation=ObservedAction(kernel_snapshot(self.kernel),target,obs,False)
                self._nights[key]=request.child(operation,(day,phase,final_alive))
            request=self._nights[key];groups=point_fix(groups,target)
            if observation.winner is None:
                operation=MorningDeltaEvidence(kernel_snapshot(self.kernel),observation.seers,observation.mediums)
                request=request.child(operation,(day,phase,final_alive))
                fixed=[x for r in observation.seers for x in (r.player,r.target)]
                fixed.extend(x for r in observation.mediums for x in (r.reporter,r.target))
                groups=point_fix(groups,*fixed)
        binding=SavedBinding(self,observation,request,groups)
        self._bindings[observation]=binding;self.stats['recipe_branches']+=1
        return binding

    def register_all(self,runner,result):
        if type(runner) is not CutOutMorning or type(result) is not MorningResult or result.initial_context is not self.engine.start():
            raise ValueError('issued full public result required')
        prefix=self.engine.baseline.past;rows=[]
        for target in self.engine.start().alive:
            for bite,mass,child in runner.labelled_paths(result,target):
                if child.past[:len(prefix)]!=prefix:raise ValueError('source prefix changed')
                descriptor=PathObservation(target,bite,child.board.winner,child.past[len(prefix):],child.board.reports)
                rows.append((self.bind(descriptor),mass,child))
        return tuple(rows)

    def corrected(self,spec):
        if type(spec) is not InitialModelASpec:return UnsupportedPartition('explicit initial spec correction required')
        previous=self.engine.baseline.spec
        if any(getattr(previous,k)!=getattr(spec,k) for k in ('players','mediums','seers','rules','strategy','claim_policy')):
            return UnsupportedPartition('cast/rule/policy change requires a new graph, not retargeted history')
        engine=(adapt_six_model_a if spec.players==6 else adapt_model_a)(spec)
        if isinstance(engine,UnsupportedPartition):return engine
        game=source_game(spec,six=spec.players==6)
        changes={k:v for k,v in game.items() if k not in ('players','wolves','mediums','seers','hunters','rules')}
        changes['revision']=self.data.to_game().get('revision',0)+1
        data=self.data.updated(**changes) # existing immutable B-flow update API
        try:return SavedCutOutGraph(engine,data=data)
        except ValueError as error:return UnsupportedPartition('corrected SavedOrigin scope: '+str(error))