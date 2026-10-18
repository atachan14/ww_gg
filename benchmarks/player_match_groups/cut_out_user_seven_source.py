"""Typed7/W2 uniform adapter + issued sources; evaluation only at <=3 alive."""
from dataclasses import dataclass
from types import SimpleNamespace
from collections import Counter
from copy import deepcopy
from weakref import WeakKeyDictionary
from hashlib import sha256
from functools import partial
from .cut_out_user_seven_uniform_preparation import PreparedSeven,prepare,comparison_game,CLAIMS
from .cut_out_inherited_groups import InheritedGroups,InheritedGroupRegistry
from .cut_out_day_night import point_fix
from .cut_out_uniform_game import CutOutUniformEngine,OwnView,evaluate as common_evaluate
from .cut_out_saved_recipes import SavedCutOutGraph
from .partitioned_match_groups import UnsupportedPartition
from werewolf.board_flow import BoardData
from werewolf.board_future import SavedOrigin,GeneratedBoard
from werewolf.exact import Rules,Strategy,ClaimPolicy
from werewolf.evaluation_branch import ContinuationInputs
from werewolf.information_set_forecast import Pending
from werewolf.calculation_budget import CalculationBudgetExceeded,calculation_budget

_issued=WeakKeyDictionary()
ROOT_GROUPS=((1,2),(3,),(4,),(5,6,7))


@dataclass(frozen=True)
class SevenCast:
    players:int=7
    wolves:int=2
    mediums:int=1
    seers:int=1
    hunters:int=0


@dataclass(frozen=True)
class SevenBaseline:
    cast:SevenCast
    rules:object
    strategy:object
    claim_policy:object
    board:object
    state:object
    past:tuple
    @property
    def players(self):return self.cast.players
    @property
    def wolves(self):return self.cast.wolves


@dataclass(frozen=True,eq=False)
class SevenUniformAdapter:
    data:object
    initial:object
    baseline:object
    def __init__(self,data,initial,source):
        game=data.to_game();object.__setattr__(self,'data',data);object.__setattr__(self,'initial',initial)
        object.__setattr__(self,'baseline',SevenBaseline(SevenCast(),Rules(**game['rules']),Strategy(**game['policy']),ClaimPolicy(**game['claim_policy']),source.public,source.public_state,source.past))
    def start(self):raise Pending('seven_issued_context_required_no_legacy_root')


def _metadata(data,initial):
    from .cut_out_user_seven_uniform_preparation import _scope as initial_scope
    from werewolf.public_log_changes import declarations
    from werewolf.board_owned_log import path,signature
    if type(initial)is not PreparedSeven:raise Pending('seven_initial_descriptor_required')
    initial_game=initial.data.to_game();initial_scope(initial_game)
    if initial.groups!=ROOT_GROUPS:raise Pending('seven_initial_groups_unproved')
    g=data.to_game()
    if tuple(g.get(k) for k in ('players','wolves','mediums','seers','hunters'))!=(7,2,1,1,0):raise Pending('seven_cast_mismatch')
    for k in ('model','rules','seer_mode','seer_options','result_disclosure_model','claim_policy'):
        if g.get(k)!=initial_game.get(k):raise Pending('seven_configuration_changed:'+k)
    if g.get('board_flow') is not None:raise Pending('seven_board_flow_unproved')
    history=g.get('history',())
    if len(history) not in (0,2,4):raise Pending('seven_saved_prefix_scope')
    removed=[]
    for step in history:
        target=step.get('target')
        if type(target)is not int or target not in range(1,8) or target in removed or 'observation' in step or 'deaths' in step:raise Pending('seven_saved_action_unproved')
        removed.append(target)
    for frame in (*history,g):
        if tuple(frame.get('claims',()))!=CLAIMS:raise Pending('seven_unknown_CO')
        if Strategy(**frame.get('policy',{}))!=Strategy(**initial_game['policy']) or ClaimPolicy(**frame.get('claim_policy',{}))!=ClaimPolicy(**initial_game['claim_policy']):raise Pending('seven_uniform_configuration_required')
        if frame.get('seer_options')!=initial_game['seer_options'] or frame.get('result_disclosure_model')!=initial_game['result_disclosure_model']:raise Pending('seven_observation_configuration_changed')
    log=g.get('public_log',{});graph=log.get('board_graph',{});bid=graph.get('current');node=graph.get('nodes',{}).get(bid,{})
    if log.get('version')!=2:raise Pending('seven_log_layout_unproved')
    root_batch=initial_game['public_log']['batches'][0]
    if next((b for b in log.get('batches',()) if b['id']==root_batch['id']),None)!=root_batch:raise Pending('seven_initial_batch_changed')
    active,known=declarations(log);initial_ids={e['id'] for e in root_batch['events'] if e['kind']=='co'}
    if {eid for eid,(slot,e) in known.items() if e['kind']=='co'}!=initial_ids:raise Pending('seven_unknown_CO')
    revision=g.get('revision',0)
    if (type(revision)is not int or revision<0 or any(type(node.get(k))is not int or node[k]<0 for k in ('revision','input_revision','generation'))
        or revision!=node.get('input_revision') or type(graph.get('generation',0))is not int or graph.get('generation',0)<0):raise Pending('seven_invalid_revision')
    lineage=path(graph)
    if (len(lineage)!=len(history)+1 or node.get('active')is not True or node.get('slot')!=len(history)
        or node.get('day')!=1+len(history)//2 or node.get('phase')!='day' or log.get('board_id')!=bid
        or data.facts.board_id!=bid or type(log.get('branch_id'))is not int or log['branch_id']<1 or type(node.get('branch'))is not int or node.get('branch')!=log.get('branch_id')):raise Pending('seven_owner_mismatch')
    if any(signature(graph['nodes'][lineage[i+1]]['edge'])!=signature(step) for i,step in enumerate(history)):raise Pending('seven_owner_path_mismatch')
    for batch in log.get('batches',()):
        slot=batch.get('slot')
        if batch.get('mode') not in ('single','simultaneous'):raise Pending('seven_batch_mode_unproved')
        if type(slot)is not int or slot not in range(len(lineage)) or batch.get('board_id')!=lineage[slot]:raise Pending('seven_batch_owner_mismatch')
        for event in batch.get('events',()):
            if batch['id']==root_batch['id']:continue
            if event.get('kind') not in ('seer','medium') or CLAIMS[event['player']-1]!=event['kind'] or event.get('day')!=1+slot//2 or slot%2:raise Pending('seven_report_operation_unproved')
    # Initial acquired reports must still belong to the original root batch.
    for player in (1,2):
        slot,e=active.get(('seer',1,player),(None,{}))
        if slot!=0 or (e.get('target'),e.get('color'))!=(4,'white'):raise Pending('seven_initial_report_changed')
    owner=(bid,node['revision'],node['input_revision'],node['generation'],graph.get('generation',0),log.get('branch_id'))
    return g,revision,owner,sha256(data.inputs.encode()).hexdigest()


class SevenRegistry(SavedCutOutGraph):
    def __init__(self,data,initial):
        _metadata(data,initial);self.data=data;self.initial=initial;self.problem=None;self.stats={}
        g=data.to_game();self.origin=SavedOrigin(data,Rules(**g['rules']),Strategy(**g['policy']),False)
        self.root=GeneratedBoard(self.origin);source=self.origin()
        self.engine=SevenUniformAdapter(data,initial,source)
    def edited(self,payload):
        from werewolf.public_log import transaction
        from werewolf.board_owned_log import commit_owned_change,check_item_owner
        try:
            before=self.data.to_game();check_item_owner(before,payload)
            after=commit_owned_change(before,transaction(before,self.origin().public,payload));after['revision']=before.get('revision',0)+1
            data=BoardData.from_game(after,game_data=self.data.game_data,runtime=self.data.runtime)
            return SevenRegistry(data,self.initial)
        except (Pending,ValueError,KeyError,TypeError) as error:return _unsupported(error)


def _unsupported(error):return UnsupportedPartition(getattr(error,'reason','seven_invalid_input:'+str(error)))


def from_game(game,initial):
    if type(initial)is not PreparedSeven:return UnsupportedPartition('seven_initial_descriptor_required')
    try:return SevenRegistry(BoardData.from_game(game,game_data=initial.data.game_data,runtime=initial.data.runtime),initial)
    except (Pending,ValueError,KeyError,TypeError) as error:return _unsupported(error)


def synthetic_registry(*,endgame=False):
    """Explicit test observations, never the actual user's unprovided history."""
    from werewolf.board_owned_log import prepare as owned_prepare,commit_owned_change
    from werewolf.public_log_changes import project_changes
    from werewolf.public_log import transaction
    initial=prepare(comparison_game()[1])
    if isinstance(initial,UnsupportedPartition):return initial
    g=deepcopy(initial.data.to_game())
    def extend(targets):
        nonlocal g
        for target in targets:g['history'].append({k:deepcopy(g[k]) for k in ('claims','claim_policy','policy','seer_options','result_disclosure_model')}|{'target':target})
        g=project_changes(g,owned_prepare(g,g['public_log']))
    def report(day,target,color):
        nonlocal g
        events=[dict(kind='seer',player=p,day=day,target=target,color=color) for p in (1,2)]+[dict(kind='medium',player=3,day=day,target=target,color=color)]
        # v2 declaration transaction validates history/owners without needing a
        # prematurely prepared (report-incomplete) role source.
        before=g;g=commit_owned_change(before,transaction(before,None,{'mode':'simultaneous','events':events}));g['revision']=before.get('revision',0)+1
    extend((7,6));report(2,7,'white')
    if endgame:extend((5,4));report(3,5,'black')
    return from_game(g,initial)


@dataclass(frozen=True,eq=False)
class SevenWitness:
    source:object
    contexts:tuple
    replay_branches:tuple
    origin:object
    inputs_digest:str
    revision:int
    owner_key:tuple


class _BatchReplay:
    def __init__(self,initial,game):
        from werewolf.public_log_changes import declarations
        self.groups=ROOT_GROUPS;self.contexts=[];self.branches=[];self.finished=False
        self.active,_=declarations(game['public_log']);self.origins={}
        for batch in game['public_log']['batches']:
            for e in batch['events']:self.origins[e['id']]=(batch['id'],batch['board_id'],batch['slot'],batch['mode'])
    def _receipt(self,kind,row):
        key=('seer',row.acquired_day,row.player) if kind=='seer' else ('medium',row.day,row.reporter,row.target)
        slot,e=self.active.get(key,(None,{}));origin=self.origins.get(e.get('id'))
        owner=row.player if kind=='seer' else row.reporter
        day=row.acquired_day if kind=='seer' else row.day
        if (e.get('player'),e.get('target'),e.get('color'),e.get('day'))!=(owner,row.target,row.color,day):return None
        return origin if origin is not None and origin[2]==slot and origin[3]=='simultaneous' else None
    def record(self,event,branch,detail):
        b=branch.public;parent=self.contexts[-1] if self.contexts else None;fixed=set();shared=False
        if b.claims!=CLAIMS:raise Pending('seven_replay_CO_changed')
        if event=='initial':
            if parent is not None or b.history:raise Pending('seven_replay_initial_unproved')
        elif parent is None:raise Pending('seven_replay_parent_missing')
        elif event=='snapshot':
            if b.history!=parent.board.history or branch.past[:len(parent.past)]!=parent.past:raise Pending('seven_snapshot_delta_unproved')
            # Existing Board.reports carries current-day medium rows; older
            # evidence remains in the saved log and inherited parent proof.
            retired=set(parent.board.reports)-set(b.reports)
            if any(r.day>=b.day for r in retired):raise Pending('seven_medium_history_rewrite_unproved')
            reports=branch.past[len(parent.past):];mediums=tuple(r for r in b.reports if r not in parent.board.reports)
            rows={r.player:r for r in reports}
            if len(rows)==len(reports) and set(rows)=={1,2}:
                a,c=rows[1],rows[2];oa,oc=self._receipt('seer',a),self._receipt('seer',c)
                shared=(oa is not None and oa==oc and (a.acquired_day,a.published_day,a.target,a.color)==(c.acquired_day,c.published_day,c.target,c.color))
            for r in reports:
                fixed.add(r.target)
                if not shared:fixed.add(r.player)
            for r in mediums:fixed.update((r.reporter,r.target))
            for day,player,target in set(b.report_resolved)-set(parent.board.report_resolved):fixed.update((player,target))
        elif event=='observed-action':
            i,target=detail
            if b.history[:-1]!=parent.board.history or len(b.history)!=len(parent.board.history)+1 or b.history[-1].target!=target or b.alive!=tuple(p for p in parent.board.alive if p!=target):raise Pending('seven_observed_action_unproved')
            fixed.add(target)
        elif event=='finished':
            if b.history!=parent.board.history or b.phase!='day':raise Pending('seven_finished_unproved')
            self.finished=True
        else:raise Pending('seven_replay_event_unknown')
        groups=ROOT_GROUPS if parent is None else point_fix(parent.groups,*sorted(fixed))
        context=InheritedGroups(b,branch.public_law,branch.past,groups,parent,'seven-'+event+('-shared-batch' if shared else ''),tuple(sorted(fixed)),0 if parent is None else parent.depth+1)
        self.contexts.append(context);self.branches.append(branch)


def _source_handle(registry,game,source):
    if (type(registry.origin)is not SavedOrigin or registry.origin.project_public is not False
        or registry.origin.board_data is not registry.data or type(registry.root)is not GeneratedBoard or registry.root.origin is not registry.origin or registry.root.history
        or registry.origin.rules!=Rules(**game['rules']) or registry.origin.strategy!=Strategy(**game['policy'])
        or registry.engine.data is not registry.data or registry.engine.initial is not registry.initial):raise Pending('seven_origin_unbound')
    expected=SevenBaseline(SevenCast(),Rules(**game['rules']),Strategy(**game['policy']),ClaimPolicy(**game['claim_policy']),source.public,source.public_state,source.past)
    if registry.engine.baseline!=expected:raise Pending('seven_adapter_binding_mismatch')


def issue(registry):
    from werewolf.root_secret_flow import replay_root_secrets,RootSecretBranch
    from werewolf.seer_future_uniform import FuturePending
    try:
        if type(registry)is not SevenRegistry or type(registry.engine)is not SevenUniformAdapter:raise Pending('seven_registry_required')
        game,revision,owner,digest=_metadata(registry.data,registry.initial)
        source=registry.origin();_source_handle(registry,game,source)
        if game['history']:
            collector=_BatchReplay(registry.initial,game)
            branch=replay_root_secrets(game,source.public,registry.origin.rules,registry.origin.strategy,max_work=300000,max_seconds=10,_group_observer=collector)
            if isinstance(branch,FuturePending):raise Pending(branch.reason)
            expected=ContinuationInputs(branch.public,branch.public_law,branch.past,branch.physical_law,None,branch.physical)
            if not collector.finished or source!=expected:raise Pending('seven_complete_source_mismatch')
            contexts=tuple(collector.contexts);branches=tuple(collector.branches)
        else:
            fresh=prepare(game)
            if isinstance(fresh,UnsupportedPartition) or source!=fresh.source:raise Pending('seven_initial_source_mismatch')
            contexts=(InheritedGroups(source.public,source.public_state,source.past,ROOT_GROUPS,event='seven-initial-shared-batch'),)
            branches=(RootSecretBranch(source.public,source.public_state,source.physical,source.private,source.past),)
        w=SevenWitness(source,contexts,branches,registry.origin,digest,revision,owner)
        _issued[w]=(registry,registry.data,registry.initial,registry.engine,w.source,w.contexts,w.replay_branches,w.origin,digest,revision,owner)
        return w
    except CalculationBudgetExceeded:return UnsupportedPartition('seven_bridge_budget_exhausted')
    except (Pending,ValueError,KeyError,TypeError) as error:return _unsupported(error)


def require_bound(registry,witness,*,source=None):
    if type(witness)is not SevenWitness or witness not in _issued:raise Pending('seven_witness_not_issued')
    if type(registry)is not SevenRegistry or type(registry.engine)is not SevenUniformAdapter:raise Pending('seven_registry_required')
    record=_issued[witness];game,revision,owner,digest=_metadata(registry.data,registry.initial)
    _source_handle(registry,game,witness.source)
    if (any(a is not b for a,b in zip(record[:4],(registry,registry.data,registry.initial,registry.engine)))
        or registry.origin is not witness.origin or record[7]is not witness.origin or registry.root.origin is not registry.origin or registry.origin.board_data is not registry.data
        or witness.source is not record[4] or witness.contexts is not record[5] or witness.replay_branches is not record[6]
        or (digest,revision,owner)!=(witness.inputs_digest,witness.revision,witness.owner_key) or (digest,revision,owner)!=record[8:]):raise Pending('seven_snapshot_binding_mismatch')
    if (registry.origin() if source is None else source)!=witness.source:raise Pending('seven_complete_source_mismatch')
    return witness


class _IssuedGroups(InheritedGroupRegistry):
    def __init__(self,witness):
        self.contexts={};self.by_board={};self.stats=Counter(seven_issued_source=1,root_group_reads=0)
        for c in witness.contexts:self.install(c)


class SevenSourceEngine(CutOutUniformEngine):
    def __init__(self,graph,*,witness,**kwargs):self.source_witness=witness;super().__init__(graph,**kwargs)
    def make_group_registry(self,graph):return _IssuedGroups(require_bound(graph,self.source_witness))
    def solve(self,b,*args,**kwargs):
        if not b.winner and len(b.alive)>3:raise Pending('seven_full_forecast_not_enabled')
        return super().solve(b,*args,**kwargs)
    def act(self,b,*args,**kwargs):
        if not b.winner and len(b.alive)>3:raise Pending('seven_full_action_value_not_enabled')
        return super().act(b,*args,**kwargs)
    def groups(self,*args,**kwargs):
        if self.inherited_groups is None:raise Pending('seven_missing_group_no_fallback')
        return super().groups(*args,**kwargs)


def evaluate_small(registry,*,witness=None,view=None,official_reference=False):
    try:
        w=require_bound(registry,witness)
        if len(w.source.public.alive)>3:return UnsupportedPartition('seven_full_forecast_not_enabled')
        return common_evaluate(registry,view=view,official_reference=official_reference,
            engine_class=None if official_reference else partial(SevenSourceEngine,witness=w))
    except (Pending,ValueError,KeyError,TypeError) as error:return _unsupported(error)


def read_action(registry,*,witness=None,target,view=None,winner=None):
    from werewolf.exact import action_outcomes
    from werewolf.actor_information import condition_actor_state
    from werewolf.evaluation_branch import physical_board
    from werewolf.board_future import condition_recipe,ActionEvidence,kernel_snapshot,outcome_key
    try:
        require_bound(registry,witness);source=registry.origin();request=registry.root
        e=SevenSourceEngine(registry,witness=witness,view=view)
        if view is not None:
            if type(view)is not OwnView or view.role not in ('seer','medium','wolf','villager') or not 1<=view.player<=7 or any(a.player!=view.player for a in view.acquisitions):raise Pending('seven_own_information_only')
            own=condition_actor_state(source.private,view.accepts);next_source=ContinuationInputs(source.public,source.public_state,source.past,own,view,physical_board(source.public,own,source.physical))
            recipe=condition_recipe(source,next_source)
            if recipe is None:raise Pending('seven_own_recipe_unproved')
            request=request.child(recipe,None);source=next_source
        if type(target)is not int or target not in source.public.alive:raise Pending('seven_illegal_action')
        outcomes=[o for o in action_outcomes(source.physical,target,e.rules,e.strategy) if o.board.winner==winner]
        if len(outcomes)!=1:raise Pending('seven_observation_unavailable')
        o=outcomes[0];request=request.child(ActionEvidence(kernel_snapshot(e),target,outcome_key(o),False),None)
        with calculation_budget(300000,max_seconds=10):child=request.roles()
        return child,o.probability,request
    except CalculationBudgetExceeded:return UnsupportedPartition('seven_bridge_budget_exhausted')
    except (Pending,ValueError,KeyError,TypeError) as error:return _unsupported(error)
