"""Opt-in diagnostic prototype: materialize branch details only on inspection.

No factory hookup. Full Q/P keys and SavedOrigin recipes remain authoritative.
Only recomputable terminal resolution memos and eager diagnostic copies change.
"""
from weakref import proxy
from .cut_out_initial_publications import InitialPublicationEngine,TrialPolicy
from .cut_out_uniform_game import CutOutUniformEngine
from .cut_out_joint_night_forecast import FullRecordedPolicy
from werewolf.information_set_forecast import InformationSetForecast,InformationSetActionPolicy,Pending


class ContinuingResolutionCache(dict):
    """Terminal payoffs have no child replay; a future miss resolves exactly."""
    def __init__(self):super().__init__();self.terminal_not_retained=0
    def __setitem__(self,key,value):
        if value[1] and all(o.board.winner is not None for o in value[1]):
            self.terminal_not_retained+=1
        else:super().__setitem__(key,value)


class DeferredRows:
    def __init__(self,ledger,kind):self.ledger=ledger;self.kind=kind
    def __len__(self):return self.ledger.terminal_count if self.kind=='terminal' else len(self.ledger.inputs)
    def __iter__(self):
        ledger=self.ledger
        # A fresh ordinary kernel uses the captured configuration and never
        # mutates the live engine or invokes a scalar continuation.
        fresh=InformationSetForecast(ledger.rules,ledger.strategy,exact_renaming=False,retire_uninformative_scans=False)
        fresh.retain_joint_guard_history=True
        for b,payload,target,has_terminal in ledger.inputs:
            if self.kind=='terminal' and not has_terminal:continue
            outcomes=InformationSetActionPolicy.outcomes(fresh.action_policy,b,payload,target)
            ledger.materialized+=1
            if self.kind=='branch':yield b,payload.public_state,payload.private,payload.observer,target,tuple((o.probability,o.board) for o in outcomes)
            elif self.kind=='terminal':yield b,payload,target,tuple(o for o in outcomes if o.board.winner is not None)
            else:yield b,payload,target,outcomes


class DeferredLedger:
    def __init__(self,engine):
        self.rules=engine.rules;self.strategy=engine.strategy;self.inputs=[];self.terminal_count=0;self.materialized=0
    def record(self,b,payload,target,outcomes):
        terminal=any(o.board.winner is not None for o in outcomes)
        self.inputs.append((b,payload,target,terminal));self.terminal_count+=terminal


class DeferredPolicy(TrialPolicy):
    def outcomes(self,b,payload,target):
        result=InformationSetActionPolicy.outcomes(self,b,payload,target)
        if not getattr(self.engine,'_board_evidence_snapshot',False):self.engine.deferred_ledger.record(b,payload,target,result)
        return result


class DeferredDiagnostics:
    def __init__(self,graph,**kwargs):
        super().__init__(graph,**kwargs)
        if graph.origin().public.initial_hunter_count or (self.strategy.day,self.strategy.night,self.strategy.fake_reports)!=('random',)*3:
            raise Pending('deferred_diagnostic_uniform_H0_only')
        self.deferred_ledger=DeferredLedger(self)
        self.branch_records=DeferredRows(self.deferred_ledger,'branch')
        self.full_branch_records=DeferredRows(self.deferred_ledger,'full')
        self.terminal_records=DeferredRows(self.deferred_ledger,'terminal')
        self.board_action_kernels=ContinuingResolutionCache()
        self.action_policy=DeferredPolicy(self)


class DeferredInitialEngine(DeferredDiagnostics,InitialPublicationEngine):pass


class EagerSmallEngine(CutOutUniformEngine):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.full_branch_records=[];self.action_policy=FullRecordedPolicy(self)


class DeferredSmallEngine(DeferredDiagnostics,EagerSmallEngine):pass
