"""Opt-in terminal-only scalar Board deferral; no ordinary factory hookup."""
from .cut_out_deferred_diagnostics import DeferredInitialEngine,DeferredSmallEngine,DeferredPolicy
from werewolf.terminal_outcome import terminal_death_outcomes,TerminalOutcome
from werewolf.information_set_forecast import InformationSetActionPolicy


class TerminalPolicy(DeferredPolicy):
    def terminal_outcomes(self,board,payload,target):
        if board.phase=='night' and getattr(self.night_outcomes,'__func__',None) is not InformationSetActionPolicy.night_outcomes:return None
        rows=terminal_death_outcomes(board,payload,target,self.engine)
        if rows is not None and not getattr(self.engine,'_board_evidence_snapshot',False):
            self.engine.terminal_compact_actions+=1
            self.engine.deferred_ledger.record(board,payload,target,rows)
        return rows
    def project(self,b,payload,outcome,target):
        if isinstance(outcome,TerminalOutcome):outcome=outcome.materialize()
        return super().project(b,payload,outcome,target)


class CompactTerminal:
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.terminal_compact_actions=0;self.action_policy=TerminalPolicy(self)


class CompactTerminalInitialEngine(CompactTerminal,DeferredInitialEngine):pass
class CompactTerminalSmallEngine(CompactTerminal,DeferredSmallEngine):pass
