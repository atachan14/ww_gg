"""Evidence replay for generated Boards in stages 1/2/3a/3b.

A generated child stores an action/observation recipe, not a parent's computed
posterior. Its role state is reconstructed from the calculation's origin and
all recorded recipes. The existing kernels define the recipes' semantics.
"""
from .calculation_budget import DEFAULT_MAX_WORK, DEFAULT_MAX_SECONDS
from dataclasses import dataclass,replace,field
from contextvars import ContextVar
from contextlib import contextmanager
from copy import copy

_rebuilding=ContextVar('board_role_rebuilding',default=False)
_active_origin=ContextVar('board_calculation_origin',default=None)
_reuse_kernels=ContextVar('board_reconstruction_kernel_reuse',default=True)


def completed_step(method):
    """One completed deterministic step, verified by all reconstructed inputs.

    This is an optional internal reuse; disabling it executes the complete
    reference recipe. It is not a cache of a Board's authoritative input.
    """
    def run(self,source):
        memo=self._completed
        if _reuse_kernels.get() and memo and source==memo[0]:
            memo[2]+=1
            return memo[1]
        result=method(self,source)
        if _reuse_kernels.get():memo[:]=(source,result,0)
        return result
    return run


@dataclass(frozen=True)
class GeneratedBoard:
    origin:object
    history:tuple=()
    facts:object=None

    def child(self,recipe,facts):return GeneratedBoard(self.origin,(*self.history,recipe),facts)

    @property
    def game_data(self):return self.origin.game_data

    def roles(self):
        from .board_roles import reconstruct_roles
        return reconstruct_roles(self)

    def _reconstruct(self):
        from .calculation_budget import tick
        tick(0)
        token=_rebuilding.set(True)
        try:
            state=self.origin()
            for operation in self.history:state=GeneratedBoard.replay_operation(operation,state)
            return state
        finally:_rebuilding.reset(token)

    @staticmethod
    def replay_operation(operation,state):return operation(state)

@dataclass(frozen=True)
class ActionEvidence:
    engine:object
    target:int
    observation:tuple
    terminal_payoffs:bool=True
    observed_alive:object=None

    _completed:list=field(default_factory=list,init=False,compare=False,hash=False,repr=False)

    @completed_step
    def __call__(self,source):
        from .action_flow import resolve_action
        from .evaluation_branch import ActionInputs
        b=source.public
        acquired,outcomes=resolve_action(b,ActionInputs(source.public_state,source.past,
            source.private,source.observer,source.physical),self.target,self.engine.action_policy,
            terminal_payoffs=self.terminal_payoffs,observed_alive=self.observed_alive)
        matches=[o for o in outcomes if outcome_key(o)==self.observation]
        if len(matches)!=1:raise ValueError('Generated Board observation is not uniquely reconstructible')
        return self.engine.action_policy.project(b,acquired,matches[0],self.target)

@dataclass(frozen=True)
class PublicationEvidence:
    engine:object
    observation:tuple

    _completed:list=field(default_factory=list,init=False,compare=False,hash=False,repr=False)

    @completed_step
    def __call__(self,source):
        from .evaluation_branch import ContinuationInputs,physical_board
        b,s,past,private,observer=self.engine.continuation_context(*source)
        branches=self.engine.push(s,private,self.engine.morning(b,s,past))
        selected=[(c,ns,p,own) for q,c,ns,p,own in branches
                  if publication_key(c,p)==self.observation]
        if len(selected)!=1:raise ValueError('Generated publication is not uniquely reconstructible')
        c,ns,p,own=selected[0]
        return ContinuationInputs(c,ns,p,own,observer,physical_board(c,own,source.physical))


def outcome_key(outcome):
    b=outcome.board
    return (b.alive,b.day,b.phase,b.winner,b.history)


def publication_key(board,past):
    return (board.alive,board.day,board.phase,board.claims,board.reports,board.report_resolved,past)


def kernel_snapshot(engine):
    # Freeze policy/proof configuration at this event. A later counterfactual
    # must not change the policy that generated an earlier observation.
    frozen=copy(engine)
    frozen._board_evidence_snapshot=True
    # Runtime acquisition receipts belong to their live engine, not replay.
    if hasattr(frozen,'acquisition_provenance'):frozen.acquisition_provenance=None
    for key,value in vars(engine).items():
        if key in ('night_kernels','night_sources','candidate_rule_cache'):
            setattr(frozen,key,value.copy())
    # The recipe owns this snapshot. Its policy only borrows it; a strong
    # back-reference would retain every completed recipe until cyclic GC.
    from weakref import proxy
    frozen.action_policy=type(engine.action_policy)(proxy(frozen))
    frozen.board_sources={}
    frozen.trace=None
    if not _reuse_kernels.get():frozen.memoize_flows=False
    return frozen


class EvidenceKey:
    """Cached structural hash; equality still compares every immutable input."""
    __slots__=('values','fingerprint')
    def __init__(self,values,hashes):
        self.values=values
        self.fingerprint=hash(tuple(hashes))
    def __hash__(self):return self.fingerprint
    def __eq__(self,other):
        return isinstance(other,EvidenceKey) and self.values==other.values


def evidence_key(engine,values):
    hashes=[]
    for value in values:
        item=engine.board_key_hashes.get(id(value))
        if item is None or item[0] is not value:
            item=(value,hash(value));engine.board_key_hashes[id(value)]=item
        hashes.append(item[1])
    return EvidenceKey(values,hashes)


def source_key(board,payload,engine):
    return evidence_key(engine,(board,payload.public_state,payload.past,payload.private,payload.observer,payload.physical))


def public_source_key(engine,board,state,past):return evidence_key(engine,(board,state,past))


def remember(engine,request,state):
    key=evidence_key(engine,(state.public,state.public_state,state.past,state.private,state.observer,state.physical))
    engine.board_sources[key]=request
    context=_active_origin.get()
    if context is not None:
        context[1][key]=request
        public_key=public_source_key(engine,state.public,state.public_state,state.past)
        context[2][public_key]=(request,state)
        point=(state.public.day,state.public.phase,state.public.alive,state.public.history)
        context[3].setdefault(point,{})[public_key]=(request,state)
    return request


def register_origin(engine,board,payload):
    from .evaluation_branch import ContinuationInputs
    key=source_key(board,payload,engine)
    if key in engine.board_sources:return engine.board_sources[key]
    root=ContinuationInputs(board,payload.public_state,payload.past,payload.private,
                            payload.observer,payload.physical)
    context=_active_origin.get()
    if context is not None:
        # The active evaluation call owns its engine. Its action adapter only
        # borrows it, so a completed evaluation cannot retain the entire recipe
        # graph in an engine -> policy -> engine cycle until cyclic GC.
        from weakref import proxy,ProxyTypes
        if type(engine) not in ProxyTypes and engine.action_policy.engine is engine:
            engine.action_policy.engine=proxy(engine)
        if key in context[1]:return remember(engine,context[1][key],root)
        known=context[2].get(public_source_key(engine,board,payload.public_state,payload.past))
        if known is not None:
            parent,source=known
            operation=condition_recipe(source,root)
            if operation is not None:
                request=parent.child(operation,(board.day,board.phase,board.alive))
                return remember(engine,request,root)
        # Existing exact information retirement is an explicit recipe too;
        # it must not silently become a new origin at a computed child.
        point=(board.day,board.phase,board.alive,board.history)
        for parent,source in tuple(context[3].get(point,{}).values()):
            if (source.public.day,source.public.phase,source.public.alive,source.public.history)!=(
                    board.day,board.phase,board.alive,board.history):continue
            view=None
            if source.observer is not None and payload.observer is None:
                view=PublicViewEvidence()
                source=view(source)
            projection=ContextEvidence(kernel_snapshot(engine))
            projected=projection(source)
            if (projected.public,projected.public_state,projected.past)!=(board,payload.public_state,payload.past):continue
            operation=condition_recipe(projected,root)
            if operation is None:continue
            request=parent
            if view is not None:request=request.child(view,(board.day,board.phase,board.alive))
            request=request.child(projection,(board.day,board.phase,board.alive))
            if not operation.identity:request=request.child(operation,request.facts)
            return remember(engine,request,root)
        # A production origin is always rebuilt from saved evidence. Kernel
        # clients without a GameData record may explicitly supply an initial
        # joint law; that compatibility input is not a parent-update route.
        origin=SavedOrigin(context[0],engine.rules,engine.strategy,payload.observer is None)
        token=_rebuilding.set(True)
        try:source=origin()
        finally:_rebuilding.reset(token)
        if (source.public,source.public_state,source.past)!=(board,payload.public_state,payload.past):
            from .information_set_forecast import Pending
            raise Pending('board_future_origin_not_reconstructible')
        operation=condition_recipe(source,root)
        if operation is None:
            from .information_set_forecast import Pending
            raise Pending('board_future_view_not_reconstructible')
        request=GeneratedBoard(origin,() if operation.identity else (operation,),
                               (board.day,board.phase,board.alive))
    else:
        from .board_flow import GameData
        counts=board.initial_role_counts
        common=GameData(board.player_count,counts['wolf'],counts['medium'],counts['seer'],counts['hunter'],engine.rules)
        request=GeneratedBoard(KernelOrigin(root,common),facts=(board.day,board.phase,board.alive))
    return remember(engine,request,root)


def reconstruct_child(engine,board,payload,outcome,target,legacy):
    if _rebuilding.get():return legacy()
    ledger=getattr(engine,'acquisition_provenance',None)
    evidence=None
    state=None
    if _reuse_kernels.get() and ledger is not None and id(outcome) in ledger._deaths:
        state=legacy()  # Pure canonical projection precedes the single boundary check.
        evidence=ledger.death_boundary(board,payload,outcome,target,state,require_request=True)
    if evidence is not None:
        receipt,parent,frame=evidence
        from .evaluation_branch import ContinuationInputs
        b,q,past,p,observer,physical=frame
        parent_state=ContinuationInputs(b,q,past,p,observer,physical)
        options=engine.board_action_options.get((source_key(board,payload,engine),target),(True,None))
        operation=ActionEvidence(kernel_snapshot(engine),target,outcome_key(outcome),*options)
        state=replace(state,provenance=receipt)
        operation._completed[:]=(parent_state,state,0)
        request=parent.child(operation,(outcome.board.day,outcome.board.phase,outcome.board.alive))
        ledger._attach_generated_request(receipt,request)
        ledger.stats['death_parent_replays_avoided']+=1
        remember(engine,request,state)
        return replace(state,board_data=request)
    if ledger is not None:ledger.stats['death_ordinary_fallbacks']+=1
    parent=register_origin(engine,board,payload)
    options=engine.board_action_options.get((source_key(board,payload,engine),target),(True,None))
    request=parent.child(ActionEvidence(kernel_snapshot(engine),target,outcome_key(outcome),*options),
                         (outcome.board.day,outcome.board.phase,outcome.board.alive))
    state=request.roles()
    if not same_role_board(state.physical,outcome.board):
        raise ValueError('Reconstructed physical Board differs from observed outcome')
    # Preserve the actual physical branch carrier, after checking equivalence.
    state=replace(state,physical=outcome.board)
    if engine.trace is not None and board.phase=='night':
        engine.trace.setdefault('public_updates',[]).append({'history':board.history,'target':target,
            'prior_counts':board.wolf_count_distribution,'child_counts':state.public.wolf_count_distribution})
    remember(engine,request,state)
    if ledger is not None:
        receipt=ledger.finish_death(board,payload,outcome,target,state)
        if receipt is not None:
            state=replace(state,provenance=receipt)
            ledger._attach_request(receipt,request)
    return replace(state,board_data=request)


def reconstruct_publication(engine,payload,child,public,past,private,physical,*,replay_unique=False):
    from .evaluation_branch import ContinuationInputs,physical_board
    if _rebuilding.get():return ContinuationInputs(child,public,past,private,payload.observer,physical)
    ledger=getattr(engine,'acquisition_provenance',None)
    completed=ContinuationInputs(child,public,past,private,payload.observer,physical)
    boundary=None if not (_reuse_kernels.get() and replay_unique and ledger is not None) else ledger.report_boundary(payload,completed,require_request=True)
    if boundary is not None:
        receipt,source=boundary
        operation=PublicationEvidence(kernel_snapshot(engine),publication_key(child,past))
        completed=replace(completed,provenance=receipt)
        operation._completed[:]=(payload,completed,0)
        request=source.child(operation,(child.day,child.phase,child.alive))
        ledger._attach_generated_request(receipt,request)
        ledger.stats['report_parent_replays_avoided']+=1
        remember(engine,request,completed)
        return replace(completed,board_data=request)
    if ledger is not None:ledger.stats['report_ordinary_fallbacks']+=1
    source=payload.board_data
    if source is None:
        from .evaluation_branch import ActionInputs
        source=register_origin(engine,payload.public,ActionInputs(payload.public_state,payload.past,
            payload.private,payload.observer,payload.physical))
    operation=PublicationEvidence(kernel_snapshot(engine),publication_key(child,past))
    if _reuse_kernels.get() and replay_unique:
        # The normal flow already generated this unique publication event.
        # Reuse it only when full reconstructed source inputs compare equal.
        completed=ContinuationInputs(child,public,past,private,payload.observer,physical)
        operation._completed[:]=(payload,completed,0)
    request=source.child(operation,(child.day,child.phase,child.alive))
    result=request.roles()
    if same_role_board(result.physical,physical):result=replace(result,physical=physical)
    remember(engine,request,result)
    if ledger is not None:
        receipt=ledger.finish_report(payload,result)
        if receipt is not None:
            result=replace(result,provenance=receipt)
            ledger._attach_request(receipt,request)
    return replace(result,board_data=request)


def before_action(policy,board,payload):
    if _rebuilding.get() or not hasattr(policy,'engine') or not hasattr(payload,'public_state'):
        return None
    return register_origin(policy.engine,board,payload)


def after_acquisition(policy,board,acquired,source,*,target=None,terminal_payoffs=False,observed_alive=None):
    if source is not None:
        policy.engine.board_sources[source_key(board,acquired,policy.engine)]=source
        policy.engine.board_action_options[(source_key(board,acquired,policy.engine),target)]=(terminal_payoffs,observed_alive)


@contextmanager
def calculation_origin(board):
    token=_active_origin.set((board,{},{},{}))
    try:yield
    finally:_active_origin.reset(token)


def active_calculation_data():
    context=_active_origin.get()
    return None if context is None else context[0]

@dataclass(frozen=True)
class SavedOrigin:
    board_data:object
    rules:object
    strategy:object
    project_public:bool=True
    _completed:list=field(default_factory=list,init=False,compare=False,hash=False,repr=False)

    @property
    def game_data(self):return self.board_data.game_data

    def __call__(self):
        # This origin owns one immutable complete input snapshot. Reuse only
        # its completed reconstruction; reference mode always rebuilds it.
        if _reuse_kernels.get() and self._completed:return self._completed[0]
        result=self._reconstruct()
        if _reuse_kernels.get():self._completed[:]=(result,)
        return result

    def _reconstruct(self):
        from .board_roles import prepare_evaluation
        from .evaluation_branch import ContinuationInputs,physical_board
        from .seer_future_uniform import FuturePending
        roles=self.board_data.roles()
        b=roles.board
        kind,value=prepare_evaluation(self.board_data.to_game(),b,self.rules,self.strategy)
        if isinstance(value,FuturePending):
            from .information_set_forecast import Pending
            raise Pending(value.reason)
        if kind=='root':
            return ContinuationInputs(value.public,value.public_law,value.past,
                                      value.physical_law,None,value.physical)
        if kind=='exchangeable':
            from .public_prior import _complete_prior,public_history_key
            value=_complete_prior.__wrapped__(public_history_key(self.board_data.to_game()),b,
                self.rules,False,DEFAULT_MAX_WORK)
            kind='prior'
        if kind=='prior':
            from .guard_history_prior import seed_history
            from .evaluation_projection import project_evaluation
            state,past=value
            if self.strategy.night=='max' and b.initial_hunter_count:state=seed_history(b,state)
            if self.project_public:b,state=project_evaluation(b,state,self.strategy)
            return ContinuationInputs(b,state,past,state,None,physical_board(b,state))
        from .information_set_forecast import Pending
        raise Pending('board_future_origin_scope')


def canonical_hypothesis(h):
    # Preserve compatibility behavior for mutable or subclass records.
    from .seer_acquisition import Hypothesis,Acquisition
    from .guard_effect import GuardIntent
    from .night_knowledge import WolfAttack
    return (type(h)is Hypothesis and type(h.roles)is tuple and
        type(h.acquisitions)is tuple and all(type(a)is Acquisition for a in h.acquisitions) and
        type(h.guards)is tuple and all(type(g)is GuardIntent for g in h.guards) and
        type(h.attacks)is tuple and all(type(a)is WolfAttack for a in h.attacks))


def identity(h):
    # Mass-free comparison key, not a second hypothesis/role distribution.
    # Include all compared fields so new secret-history fields cannot disappear.
    from .seer_acquisition import Hypothesis
    from fractions import Fraction
    if type(h)is Hypothesis:
        # Noncanonical compatibility inputs keep their old validation, but
        # equal tuple subclasses still share the same semantic key.
        source=h if canonical_hypothesis(h) else replace(h,mass=Fraction(1))
        return (type(source),*(getattr(source,name) for name in identity_fields(type(source))))
    return replace(h,mass=Fraction(1))


from functools import lru_cache
@lru_cache(maxsize=16)
def identity_fields(kind):
    from dataclasses import fields
    return tuple(f.name for f in fields(kind) if f.compare and f.name!='mass')


def weighted_hypothesis(h,mass):
    # Already validated canonical immutable records need no reconstruction
    # when even the mass is unchanged. Subclasses/mutable inputs keep validation.
    return h if canonical_hypothesis(h) and h.mass==mass else replace(h,mass=mass)

@dataclass(frozen=True)
class ConditionEvidence:
    source_kind:str
    mapping:tuple
    metadata:tuple
    observer:object
    physical_source:str='physical'
    identity:bool=False

    _completed:list=field(default_factory=list,init=False,compare=False,hash=False,repr=False)

    @completed_step
    def __call__(self,source):
        if self.identity:return source
        from .seer_acquisition import normalize
        from .evaluation_branch import ContinuationInputs,physical_board
        law=source.public_state if self.source_kind=='public' else source.private
        mapping=dict(self.mapping)
        entries=tuple(weighted_hypothesis(mapping[key],h.mass)
                      for h in law.hypotheses if (key:=identity(h)) in mapping)
        own=replace(law,hypotheses=normalize(entries),**dict(self.metadata))
        return ContinuationInputs(source.public,source.public_state,source.past,own,
            self.observer,physical_board(source.public,own,
                source.physical if self.physical_source=='physical' else None))


def condition_recipe(source,target):
    from dataclasses import fields
    from .seer_acquisition import normalize
    metadata=tuple((f.name,getattr(target.private,f.name)) for f in fields(target.private)
                   if f.name!='hypotheses')
    targets=target.private.hypotheses
    # Exact structural index narrows candidates; guard/attack compatibility
    # and unique-match requirements remain unchanged.
    candidates={}
    for t in targets:candidates.setdefault((t.roles,t.acquisitions),[]).append(t)
    for kind,law in (('private',source.private),('public',source.public_state)):
        mapping=[]
        for h in law.hypotheses:
            key=identity(h)
            compatible=[t for t in candidates.get((h.roles,h.acquisitions),())
                        if set(h.guards)<=set(t.guards) and set(h.attacks)<=set(t.attacks)]
            if len(compatible)==1:mapping.append((key,compatible[0]))
        if not mapping:continue
        by_key=dict(mapping)
        entries=tuple(weighted_hypothesis(by_key[key],h.mass)
                      for h in law.hypotheses if (key:=identity(h)) in by_key)
        rebuilt=replace(law,hypotheses=normalize(entries),**dict(metadata))
        if rebuilt==target.private:
            from .evaluation_branch import physical_board
            for physical_kind,base in (('physical',source.physical),('intervention',None)):
                try:candidate=physical_board(source.public,rebuilt,base)
                except ValueError:continue
                if not same_role_board(candidate,target.physical):continue
                return ConditionEvidence(kind,tuple(mapping),metadata,target.observer,physical_kind,
                    identity=(source.private==target.private and source.observer==target.observer
                              and source.physical==target.physical))
    return None


@dataclass(frozen=True)
class ContextEvidence:
    engine:object

    _completed:list=field(default_factory=list,init=False,compare=False,hash=False,repr=False)

    @completed_step
    def __call__(self,source):
        from .evaluation_branch import ContinuationInputs,physical_board
        b,s,past,private,observer=self.engine.continuation_context(*source)
        return ContinuationInputs(b,s,past,private,observer,
                                  physical_board(b,private,source.physical))


@dataclass(frozen=True)
class KernelOrigin:
    state:object
    game_data:object

    def __call__(self):return self.state


def same_role_board(left,right):
    """Compare semantic role laws across the existing sparse/full encodings."""
    if left is right:return True
    if type(left) is not type(right):return False
    if tuple(sorted(left.worlds))!=tuple(sorted(right.worlds)):return False
    # Compare validated immutable facts directly; constructing a throwaway
    # Board here would repeat all normalization/count checks for equality.
    return all(getattr(left,name)==getattr(right,name)
        for name,descriptor in left.__dataclass_fields__.items()
        if descriptor.compare and name not in ('belief','role_belief','world_belief'))


@contextmanager
def kernel_calculation():
    """Run common numeric kernels when the caller owns the evidence path.

    Used by saved reconstruction and closed calculation-local generation.
    No nested origin lookup, publication recording or live Board replay.
    """
    token=_rebuilding.set(True)
    try:yield
    finally:_rebuilding.reset(token)


# Existing 3a callers share the same context; no second execution mode.
evidence_reconstruction=kernel_calculation

def reconstruction_reuse_enabled():return _reuse_kernels.get()


@contextmanager
def reconstruction_kernel_reuse(enabled):
    """Test oracle switch; both modes replay the same complete evidence."""
    token=_reuse_kernels.set(enabled)
    try:yield
    finally:_reuse_kernels.reset(token)


@dataclass(frozen=True)
class PublicReportEvidence:
    """Public-policy hypothetical branch, never the observer's physical P."""
    engine:object
    observation:tuple
    provider:str='morning'

    _completed:list=field(default_factory=list,init=False,compare=False,hash=False,repr=False)

    @completed_step
    def __call__(self,source):
        from .evaluation_branch import ContinuationInputs,physical_board
        branches=getattr(self.engine,self.provider)(source.public,source.public_state,source.past)
        selected=[(b,s,p) for q,b,s,p in branches if publication_key(b,p)==self.observation]
        if len(selected)!=1:raise ValueError('Public report observation is not uniquely reconstructible')
        b,s,p=selected[0]
        return ContinuationInputs(b,s,p,s,None,physical_board(b,s))


def record_publications(engine,board,state,past,branches,provider='morning'):
    if _rebuilding.get() or branches==((1,board,state,past),):return branches
    from .evaluation_branch import ActionInputs,ContinuationInputs,physical_board
    base=physical_board(board,state)
    source=register_origin(engine,board,ActionInputs(state,past,state,None,base))
    for q,child,law,history in branches:
        request=source.child(PublicReportEvidence(kernel_snapshot(engine),publication_key(child,history),provider),
                             (child.day,child.phase,child.alive))
        remember(engine,request,ContinuationInputs(child,law,history,law,None,physical_board(child,law)))
    return branches


@dataclass(frozen=True)
class PublicViewEvidence:
    _completed:list=field(default_factory=list,init=False,compare=False,hash=False,repr=False)

    @completed_step
    def __call__(self,source):
        from .evaluation_branch import ContinuationInputs,physical_board
        return ContinuationInputs(source.public,source.public_state,source.past,
            source.public_state,None,physical_board(source.public,source.public_state))

@dataclass(frozen=True)
class MediumInstructionEvidence:
    engine:object
    fake_colors:tuple
    reports:tuple
    resolved:tuple

    _completed:list=field(default_factory=list,init=False,compare=False,hash=False,repr=False)

    @completed_step
    def __call__(self,source):
        from .exact import report_actions
        from .evaluation_branch import ContinuationInputs,physical_board
        action=next(a for a in report_actions(source.public) if a.fake_colors==self.fake_colors)
        outcome=next(o for o in action.outcomes if (o.board.reports,o.board.report_resolved)==(self.reports,self.resolved))
        law=self.engine.project(source.public_state,outcome.board)
        return ContinuationInputs(outcome.board,law,source.past,law,None,physical_board(outcome.board,law))


def record_medium_instruction(engine,board,state,past,outcome,fake_colors,*,law=None):
    if _rebuilding.get():return
    from .evaluation_branch import ActionInputs,ContinuationInputs,physical_board
    source=register_origin(engine,board,ActionInputs(state,past,state,None,physical_board(board,state)))
    child=outcome.board
    if law is None:law=engine.project(state,child)
    if fake_colors is None:
        from .exact import report_actions
        fake_colors=next(a.fake_colors for a in report_actions(board)
            if any((o.board.reports,o.board.report_resolved)==(child.reports,child.report_resolved)
                   for o in a.outcomes))
    request=source.child(MediumInstructionEvidence(kernel_snapshot(engine),fake_colors,
        child.reports,child.report_resolved),(child.day,child.phase,child.alive))
    remember(engine,request,ContinuationInputs(child,law,past,law,None,physical_board(child,law)))


def resolution_key(policy,board,payload,target,terminal_payoffs,observed_alive):
    if not hasattr(policy,'engine') or not hasattr(payload,'public_state'):return None
    e=policy.engine
    if not hasattr(e,'board_action_kernels'):return None
    sources=getattr(e,'night_sources',None)
    before=sources.get((board,payload.public_state,payload.past),payload.public_state) if sources is not None else payload.public_state
    kernels=getattr(e,'night_kernels',None)
    selected=kernels.get((board,before,payload.past)) if kernels is not None else None
    kernel=None if selected is None else frozenset(selected.items())
    functions=[]
    for owner,names in ((policy,('acquire','outcomes','night_outcomes','terminal_outcomes')),
                         (e,('public_children','physical_children','acquire','project','public_night_policies'))):
        for name in names:
            method=getattr(owner,name,None);functions.append(getattr(method,'__func__',method))
    config=(type(policy),e.rules,e.strategy,getattr(e,'candidate_profiles',()),
            getattr(e,'candidate_contexts',()),getattr(e,'verifying_actor_mask',None),
            policy.terminal_preflight_safe,kernel,tuple(functions))
    try:
        return evidence_key(e,(board,payload.public_state,payload.past,payload.private,
            payload.observer,payload.physical,target,terminal_payoffs,observed_alive,config))
    except TypeError:return None


def reuse_resolution(policy,board,payload,target,terminal_payoffs,observed_alive):
    # Reuse only an entire pure event with exactly the reconstructed inputs.
    # A calculated parent posterior is never accepted as authoritative input.
    if not _rebuilding.get() or not _reuse_kernels.get():return None
    key=resolution_key(policy,board,payload,target,terminal_payoffs,observed_alive)
    if key is None:return None
    e=policy.engine
    e.board_replay_stats['requests']+=1
    result=e.board_action_kernels.get(key)
    if result is not None:e.board_replay_stats['hits']+=1
    return result


def remember_resolution(policy,board,payload,target,terminal_payoffs,observed_alive,result):
    if not _reuse_kernels.get():return
    key=resolution_key(policy,board,payload,target,terminal_payoffs,observed_alive)
    if key is not None:policy.engine.board_action_kernels[key]=result


@dataclass(frozen=True)
class OwnerInformationEvidence:
    information:object
    observer:object

    def __call__(self,source):
        from .actor_information import condition_personal
        from .evaluation_branch import ContinuationInputs,physical_board
        mass,own=condition_personal(source.private,self.information)
        return ContinuationInputs(source.public,source.public_state,source.past,own,self.observer,
            physical_board(source.public,own,source.physical))


def reconstruct_information(engine,source,child,information,mass):
    """Generated semantic filter, no reconstructed-law comparison to certify it."""
    if _rebuilding.get():return child
    ledger=getattr(engine,'acquisition_provenance',None)
    boundary=None if ledger is None else ledger.information_boundary(source,child,information,mass,require_request=True)
    receipt,parent=(None,None) if boundary is None else boundary
    operation=OwnerInformationEvidence(information,child.observer)
    if parent is not None and _reuse_kernels.get():
        child=replace(child,provenance=receipt)
        request=parent.child(operation,(child.public.day,child.public.phase,child.public.alive))
        ledger._attach_generated_request(receipt,request)
        ledger.stats['information_parent_replays_avoided']+=1
        remember(engine,request,child)
        return replace(child,board_data=request)
    if ledger is not None:ledger.stats['information_ordinary_fallbacks']+=1
    parent=source.board_data
    if parent is None:
        from .evaluation_branch import ActionInputs
        parent=register_origin(engine,source.public,ActionInputs(source.public_state,source.past,source.private,source.observer,source.physical))
    request=parent.child(operation,(child.public.day,child.public.phase,child.public.alive))
    result=request.roles()
    remember(engine,request,result)
    return replace(result,board_data=request)


@dataclass(frozen=True)
class ObservedActionEvidence:
    engine:object
    target:int

    def __call__(self,source):
        from .action_flow import observe_action
        return observe_action(source,self.target,self.engine)[1]


@dataclass(frozen=True)
class ObservedPublicationEvidence:
    engine:object
    seer_reports:tuple
    medium_reports:tuple

    def __call__(self,source):
        from .report_publication import observe_public_reports
        return observe_public_reports(source,self.seer_reports,self.medium_reports,self.engine.rules)[1]
