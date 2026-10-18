"""Comparison-only bounded full-input key planning. Never selected by app factories.

Only local plan exhaustion becomes a missing key. Request cancellation/budget
exceptions propagate; no unfinished key or numerical value is cached here.
"""
from dataclasses import dataclass,field
from math import factorial
from time import monotonic
import inspect
from werewolf import exact_renaming as original
from werewolf.exact import Board
from werewolf.seer_future_uniform import TrueScanState
from werewolf.actor_information import WolfInformation
from werewolf.guard_model import GuardObserver
from werewolf.seer_intervention import SeerObserver

class PlanExhausted(Exception):pass

@dataclass
class KeyReusePlan:
    max_source_cells:int=4096
    max_serialized_cells:int=32768
    max_snapshots:int=16
    max_swaps:int=8
    max_seconds:float=.05
    source_cells:int=field(default=0,init=False)
    serialized_cells:int=field(default=0,init=False)
    snapshots:int=field(default=0,init=False)
    swaps:int=field(default=0,init=False)
    residual_count:int=field(default=1,init=False)
    certified_blocks:list=field(default_factory=list,init=False,repr=False)
    reason:str=field(default='new',init=False)
    started:float=field(default=0,init=False,repr=False)

    def __post_init__(self):
        if any(type(v)is not int or v<1 for v in(self.max_source_cells,self.max_serialized_cells,self.max_snapshots,self.max_swaps)):
            raise ValueError('Positive integer plan bounds required')
        if type(self.max_seconds)not in(int,float)or self.max_seconds<=0:raise ValueError('Positive local time bound required')

    def stop(self,reason):
        self.reason=reason;raise PlanExhausted()

    def check(self):
        # Keep request-owned work/cancellation semantics even during preflight.
        original.tick()
        if monotonic()-self.started>=self.max_seconds:self.stop('plan_time_limit')

    def admit(self,b,s,past,private,physical,profiles,observer):
        self.started=monotonic();self.check()
        if observer is not None and type(observer)not in(GuardObserver,SeerObserver):self.stop('unsupported_observer')
        if type(past)is not tuple:self.stop('record_shape')
        boards=[b];laws=[s,private]
        if physical is not None:boards.append(physical)
        if type(profiles)is not tuple or len(profiles)>8:self.stop('profile_context_limit')
        if any(type(row)is not tuple or len(row)!=4 for row in profiles):self.stop('profile_context_shape')
        cells=len(past)*7
        if observer is not None:
            if type(b)is not Board:self.stop('prototype_scope')
            if any(type(v)is not int or not 1<=v<=b.player_count for v in(observer.actor,observer.target)):self.stop('observer_shape')
            if type(observer)is SeerObserver:
                if type(observer.acquisitions)is not tuple or len(observer.acquisitions)>32:self.stop('observer_limit')
                cells+=7*len(observer.acquisitions)
            else:
                if type(observer.allowed_roles)is not tuple or len(observer.allowed_roles)>128:self.stop('observer_limit')
                if any(type(row)is not tuple or len(row)!=4 for row in observer.allowed_roles):self.stop('observer_shape')
                boards.append(observer.board);cells+=4*len(observer.allowed_roles)
        if len(past)>32:self.stop('record_limit')
        for source,law,reports,profile in profiles:
            if type(reports)is not tuple or type(profile)is not tuple:self.stop('profile_context_shape')
            if len(reports)>32 or len(profile)>16:self.stop('profile_context_limit')
            if any(type(row)is not tuple or len(row)!=2 or type(row[0])is not WolfInformation or type(row[1])is not tuple for row in profile):self.stop('profile_context_shape')
            boards.append(source);laws.append(law);cells+=len(reports)*7
            for info,policy in profile:
                if len(info.attacks)>32 or len(policy)>6:self.stop('profile_context_limit')
                cells+=len(info.attacks)*3+len(policy)*2+1
        for board in boards:
            if type(board)is not Board or not 1<=board.player_count<=6:self.stop('prototype_scope')
            if any(len(xs)>32 for xs in(board.history,board.reports,board.medium_opportunities,board.report_resolved)):
                self.stop('record_limit')
            if len(board.worlds)>128:self.stop('world_limit')
            cells+=len(board.worlds)*5+len(board.claims)+7*(len(board.history)+len(board.reports))+3*(len(board.medium_opportunities)+len(board.report_resolved))
        for law in laws:
            if type(law)is not TrueScanState or len(law.hypotheses)>128 or len(law.rosters)>32:self.stop('law_limit')
            cells+=sum(len(r)for r in law.rosters)
            for h in law.hypotheses:
                if max(len(h.acquisitions),len(h.guards),len(h.attacks))>32:self.stop('record_limit')
                cells+=5+7*(len(h.acquisitions)+len(h.guards)+len(h.attacks))
                if cells>self.max_source_cells:self.stop('source_cell_limit')
        self.source_cells=cells
        if cells>self.max_source_cells:self.stop('source_cell_limit')
        self.check()

    def snapshot(self):
        self.check()
        if self.snapshots>=self.max_snapshots:self.stop('snapshot_limit')
        if self.serialized_cells+self.source_cells>self.max_serialized_cells:self.stop('serialized_cell_limit')
        self.snapshots+=1;self.serialized_cells+=self.source_cells

    def swap(self):
        self.check()
        if self.swaps>=self.max_swaps:self.stop('swap_limit')
        self.swaps+=1

    def block(self,block,symmetric):
        if symmetric:self.certified_blocks.append(block)
        else:self.residual_count*=factorial(len(block))

    def summary(self):
        # No identities, law contents, observer or policy details in telemetry.
        return dict(reason=self.reason,source_cells=self.source_cells,serialized_cells=self.serialized_cells,
                    snapshots=self.snapshots,swaps=self.swaps,residual_count=self.residual_count,
                    certified_block_sizes=[len(b)for b in self.certified_blocks])

_SOURCE=inspect.getsource(original.canonical_key)
_CHANGES=(
 ("    if observer is not None and type(observer).__name__ not in ('GuardObserver','SeerObserver'):return None",
  "    proof_plan.admit(b,s,past,private,physical,wolf_profiles,observer)\n    if observer is not None and type(observer).__name__ not in ('GuardObserver','SeerObserver'):return None"),
 ('    if count>max_mappings:return None','    # Comparison-only: cap the residual search after complete proofs.'),
 ('    def snapshot(ids,masks):','    def snapshot(ids,masks):\n        proof_plan.snapshot()'),
 ('                    tick();ids=list(identity);','                    proof_plan.swap();tick();ids=list(identity);'),
 ('            orders_by_block.append((block,) if symmetric else permutations(block))',
  '            proof_plan.block(block,symmetric)\n            orders_by_block.append((block,) if symmetric else permutations(block))'),
 ('        for orders in product(*orders_by_block):',
  "        if proof_plan.residual_count>max_mappings:proof_plan.stop('residual_mapping_limit')\n        for orders in product(*orders_by_block):"),
)
for before,after in _CHANGES:
    if _SOURCE.count(before)!=1:raise RuntimeError('Canonical source changed; revalidate bounded plan adapter')
    _SOURCE=_SOURCE.replace(before,after)
_CODE=compile(_SOURCE,original.__file__,'exec')

def planned_key(b,s,past,private,observer,rules,strategy,*,plan=None,**kwargs):
    """Exact original key or None; a fresh request-local plan is single-use."""
    plan=KeyReusePlan()if plan is None else plan
    if plan.reason!='new':raise ValueError('A key plan is single-use')
    plan.reason='running'
    namespace=dict(vars(original));namespace['proof_plan']=plan
    exec(_CODE,namespace)
    try:
        key=namespace['canonical_key'](b,s,past,private,observer,rules,strategy,**kwargs)
    except PlanExhausted:return None
    plan.reason='complete'if key is not None else'unsupported'
    return key