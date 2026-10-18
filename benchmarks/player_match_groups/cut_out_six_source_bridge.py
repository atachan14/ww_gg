"""Issued current-source witnesses for fixed-CO six-player first-night replay."""
from dataclasses import dataclass
from collections import Counter
from weakref import WeakKeyDictionary
from hashlib import sha256
from functools import partial
from .cut_out_inherited_groups import InheritedGroups,InheritedGroupRegistry
from .cut_out_day_night import point_fix
from .cut_out_uniform_game import CutOutUniformEngine
from .partitioned_match_groups import UnsupportedPartition
from werewolf.information_set_forecast import Pending
from werewolf.evaluation_branch import ContinuationInputs
from werewolf.calculation_budget import CalculationBudgetExceeded

_issued=WeakKeyDictionary()


@dataclass(frozen=True,eq=False)
class SourceWitness:
    source:object
    contexts:tuple
    replay_branches:tuple
    origin:object
    inputs_digest:str
    revision:int
    owner_key:tuple


def _scope(registry):
    from .cut_out_six_registry import SixInputRegistry
    from .cut_out_six_inherited import initial_shape_reason
    from .cut_out_model_a import InitialModelASpec
    from werewolf.board_future import SavedOrigin
    from werewolf.exact import Strategy,ClaimPolicy
    from werewolf.seer_acquisition import SeerReport
    from werewolf.report_publication import publication_slot
    if type(registry)is not SixInputRegistry or getattr(registry,'problem','uninitialized') is not None:
        raise Pending('source_bridge_registry_required')
    if type(registry.base)is not InitialModelASpec:raise Pending('source_bridge_initial_spec_required')
    data=registry.data;g=data.to_game();reason=initial_shape_reason(registry.base)
    if (data.game_data.players,data.game_data.wolves,data.game_data.mediums,data.game_data.seers,data.game_data.hunters,data.game_data.rules)!=(6,1,registry.base.mediums,1,0,registry.base.rules):
        raise Pending('source_bridge_common_data_mismatch')
    if reason:raise Pending(reason)
    if g.get('model')!='group' or g.get('seer_mode')!='information-fixed-v1' or g.get('board_flow') is not None:
        raise Pending('source_bridge_model_unproved')
    if (type(registry.origin)is not SavedOrigin or registry.origin.board_data is not data
        or registry.origin.project_public is not False or registry.root.origin is not registry.origin or registry.root.history
        or registry.origin.rules!=registry.base.rules or registry.origin.strategy!=registry.base.strategy):
        raise Pending('source_bridge_origin_unbound')
    history=g.get('history',())
    if len(history)!=2 or any(type(s.get('target'))is not int or 'observation' in s or 'deaths' in s for s in history):
        raise Pending('source_bridge_first_night_only')
    frames=(*history,g);claims=registry.base.claims
    if any(s.get('seer_options')!={'initial_rule':registry.base.rules.initial_seer,'likelihood':'compatibility'} or s.get('result_disclosure_model')!='full-observed-v1' for s in frames):
        raise Pending('source_bridge_observation_configuration_unproved')
    if any(tuple(s.get('claims',()))!=claims for s in frames):raise Pending('source_bridge_unknown_CO')
    if any(Strategy(**s.get('policy',{}))!=registry.base.strategy or ClaimPolicy(**s.get('claim_policy',{}))!=registry.base.claim_policy for s in frames):
        raise Pending('source_bridge_step_configuration_changed')
    log=g.get('public_log',{});graph=log.get('board_graph',{});bid=graph.get('current');node=graph.get('nodes',{}).get(bid,{})
    if any(e.get('kind') not in ('co','seer','medium') for b in log.get('batches',()) for e in b.get('events',())):
        raise Pending('source_bridge_log_operation_unproved')
    if any(e.get('kind')=='co' for b in log.get('batches',()) for e in b.get('events',())):
        raise Pending('source_bridge_unknown_CO')
    if any(tuple(c)!=claims for c in log.get('base_claims',())):raise Pending('source_bridge_unknown_CO')
    revision=g.get('revision',0)
    if (type(revision)is not int or revision<0 or any(type(node.get(k))is not int or node[k]<0 for k in ('revision','input_revision','generation'))
        or revision!=node.get('input_revision') or type(graph.get('generation',0))is not int or graph.get('generation',0)<0):raise Pending('source_bridge_invalid_revision')
    if (node.get('active') is not True or type(log.get('branch_id'))is not int or log['branch_id']<1 or node.get('slot')!=2 or node.get('day')!=2 or node.get('phase')!='day'
        or data.facts.board_id!=bid or log.get('board_id')!=bid or node.get('branch')!=log.get('branch_id')):raise Pending('source_bridge_owner_mismatch')
    from werewolf.board_owned_log import path,signature
    lineage=path(graph)
    if len(lineage)!=3 or any(signature(graph['nodes'][lineage[i+1]]['edge'])!=signature(step) for i,step in enumerate(history)):
        raise Pending('source_bridge_owner_path_mismatch')
    initial_reports=tuple(SeerReport(r['day'],1,r['reporter'],r['target'],r['color']) for r in g.get('seer_inputs',()) if publication_slot(g,'seer',r)==0)
    if initial_reports!=registry.base.reports:raise Pending('source_bridge_initial_reports_changed')
    owner_key=(bid,node['revision'],node['input_revision'],node['generation'],graph.get('generation',0),log.get('branch_id'))
    return g,revision,owner_key,sha256(data.inputs.encode()).hexdigest()


class _ReplayGroups:
    def __init__(self,groups,claims):self.initial_groups=groups;self.claims=claims;self.contexts=[];self.branches=[];self.finished=False

    def record(self,event,branch,detail):
        b=branch.public
        if b.claims!=self.claims:raise Pending('source_bridge_replay_CO_unproved')
        parent=self.contexts[-1] if self.contexts else None;fixed=set()
        if event=='initial':
            if parent is not None or b.history or b.day!=1 or b.phase!='day':raise Pending('source_bridge_initial_receipt_required')
        elif parent is None:raise Pending('source_bridge_replay_parent_missing')
        elif event=='snapshot':
            if b.history!=parent.board.history or b.alive!=parent.board.alive or branch.past[:len(parent.past)]!=parent.past or b.reports[:len(parent.board.reports)]!=parent.board.reports:
                raise Pending('source_bridge_snapshot_delta_unproved')
            for r in branch.past[len(parent.past):]:fixed.update((r.player,r.target))
            for r in b.reports[len(parent.board.reports):]:fixed.update((r.reporter,r.target))
            for day,player,target in set(b.report_resolved)-set(parent.board.report_resolved):fixed.update((player,target))
        elif event=='observed-action':
            index,target=detail
            if (len(b.history)!=len(parent.board.history)+1 or b.history[:-1]!=parent.board.history
                or b.history[-1].target!=target or b.history[-1].phase!=parent.board.phase
                or b.alive!=tuple(p for p in parent.board.alive if p!=target)):
                raise Pending('source_bridge_observed_action_unproved')
            fixed.add(target)
        elif event=='finished':
            if b.history!=parent.board.history or b.day!=2 or b.phase!='day':raise Pending('source_bridge_final_receipt_unproved')
            self.finished=True
        else:raise Pending('source_bridge_replay_event_unknown')
        groups=self.initial_groups if parent is None else point_fix(parent.groups,*sorted(fixed))
        context=InheritedGroups(b,branch.public_law,branch.past,groups,parent,'saved-'+event,tuple(sorted(fixed)),0 if parent is None else parent.depth+1)
        self.contexts.append(context);self.branches.append(branch)


def issue(registry):
    from .cut_out_model_a import adapt_six_model_a
    from werewolf.root_secret_flow import replay_root_secrets
    from werewolf.seer_future_uniform import FuturePending
    try:
        game,revision,owner_key,digest=_scope(registry)
        initial=adapt_six_model_a(registry.base)
        if isinstance(initial,UnsupportedPartition):return initial
        collector=_ReplayGroups(initial.start().groups,registry.base.claims)
        source=registry.origin()
        if source.public.day!=2 or source.public.phase!='day' or len(source.public.history)!=2 or source.observer is not None:
            raise Pending('source_bridge_current_source_shape_unproved')
        branch=replay_root_secrets(game,source.public,registry.base.rules,registry.base.strategy,max_work=1000000,max_seconds=25,_group_observer=collector)
        if isinstance(branch,FuturePending):raise Pending(branch.reason)
        expected=ContinuationInputs(branch.public,branch.public_law,branch.past,branch.physical_law,None,branch.physical)
        if not collector.finished or source!=expected:raise Pending('source_bridge_complete_source_mismatch')
        witness=SourceWitness(source,tuple(collector.contexts),tuple(collector.branches),registry.origin,digest,revision,owner_key)
        # Identity-led issuance rejects unbound constructors and dataclass copies.
        _issued[witness]=(registry,registry.data,registry.base,witness.source,witness.contexts,witness.replay_branches,witness.origin,digest,revision,owner_key)
        return witness
    except CalculationBudgetExceeded:return UnsupportedPartition('source_bridge_budget_exhausted')
    except (Pending,ValueError,KeyError,TypeError) as error:return UnsupportedPartition(getattr(error,'reason','source_bridge_invalid_input:'+str(error)))


def require_bound(registry,witness,*,source=None):
    if type(witness)is not SourceWitness or witness not in _issued:raise Pending('source_bridge_witness_not_issued')
    record=_issued[witness]
    game,revision,owner_key,digest=_scope(registry)
    if (record[0] is not registry or record[1] is not registry.data or record[2]!=registry.base
        or witness.origin is not registry.origin or record[6] is not witness.origin
        or witness.source is not record[3] or witness.contexts is not record[4] or witness.replay_branches is not record[5]
        or (digest,revision,owner_key)!=(witness.inputs_digest,witness.revision,witness.owner_key)
        or (digest,revision,owner_key)!=record[7:]):raise Pending('source_bridge_snapshot_binding_mismatch')
    actual=registry.origin() if source is None else source
    if actual!=witness.source:raise Pending('source_bridge_complete_source_mismatch')
    return witness


class _CurrentGroups(InheritedGroupRegistry):
    def __init__(self,witness):
        self.contexts={};self.by_board={};self.stats=Counter(issued_current_source=1,root_group_reads=0)
        for context in witness.contexts:self.install(context)


class CurrentSourceEngine(CutOutUniformEngine):
    def __init__(self,graph,*,witness,**kwargs):self.source_witness=witness;super().__init__(graph,**kwargs)
    def make_group_registry(self,graph):return _CurrentGroups(require_bound(graph,self.source_witness))
    def groups(self,*args,**kwargs):
        if self.inherited_groups is None:raise Pending('source_bridge_missing_group_no_fallback')
        return super().groups(*args,**kwargs)


def screen(registry,*,witness=None,view=None,official_reference=False):
    from .cut_out_six_registry import current_screen
    try:
        require_bound(registry,witness)
        return current_screen(registry,view=view,official_reference=official_reference,
            _engine_class=None if official_reference else partial(CurrentSourceEngine,witness=witness))
    except CalculationBudgetExceeded:return UnsupportedPartition('source_bridge_budget_exhausted')
    except (Pending,ValueError,KeyError,TypeError) as error:return UnsupportedPartition(getattr(error,'reason','source_bridge_invalid_input:'+str(error)))


def read_action(registry,*,witness=None,target,view=None,winner=None):
    from .cut_out_six_registry import OwnEvidence
    from werewolf.exact import action_outcomes
    from werewolf.board_future import ActionEvidence,kernel_snapshot,outcome_key
    from werewolf.calculation_budget import calculation_budget
    try:
        require_bound(registry,witness);source=registry.origin();request=registry.root
        engine=CurrentSourceEngine(registry,witness=witness,view=view)
        if view is not None:
            own=OwnEvidence(view);source=own(source);request=request.child(own,None)
        if type(target)is not int or target not in source.public.alive:raise Pending('source_bridge_illegal_action')
        outcomes=[o for o in action_outcomes(source.physical,target,registry.base.rules,registry.base.strategy) if o.board.winner==winner]
        if len(outcomes)!=1:raise Pending('source_bridge_action_observation_missing')
        outcome=outcomes[0]
        request=request.child(ActionEvidence(kernel_snapshot(engine),target,outcome_key(outcome),False),None)
        with calculation_budget(1000000,max_seconds=25):child=request.roles()
        return child,outcome.probability,request
    except CalculationBudgetExceeded:return UnsupportedPartition('source_bridge_budget_exhausted')
    except (Pending,ValueError,KeyError,TypeError) as error:return UnsupportedPartition(getattr(error,'reason','source_bridge_invalid_input:'+str(error)))
