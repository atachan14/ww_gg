"""Restore marginalized latent scan records for action display, never evaluation."""
from dataclasses import dataclass,replace
from .evaluation_branch import ContinuationInputs

@dataclass(frozen=True)
class FullTraceOrigin:
    original:object
    @property
    def game_data(self):return self.original.game_data
    def __call__(self):
        source=self.original()
        if source.past or any(c!='latent' for c in source.public.claims):
            raise ValueError('latent acquisition trace requires unchanged latent initial root')
        from .root_secret_flow import prepare_root_secrets
        from .seer_future_uniform import FuturePending
        full=prepare_root_secrets(source.public,self.original.rules)
        if isinstance(full,FuturePending):
            from .calculation_budget import budget_stop,CalculationBudgetExceeded
            stopped=budget_stop()
            if stopped:raise CalculationBudgetExceeded(kind=stopped['kind'])
            raise ValueError(full.reason)
        return ContinuationInputs(full.public,full.public_law,full.past,full.physical_law,source.observer,full.physical)

def trace_source(node):
    source=node.read()
    if source.private.tracked is None:return source,None
    tracked=sum(1<<(p-1) for p in source.private.tracked)
    roster=sum(1<<(p-1) for p in source.private.rosters[-1])
    if not any(h.roles[2]&roster&~tracked for h in source.private.hypotheses):return source,None
    request=node.export_request()
    if any(c!='latent' for c in request.origin.board_data.roles().board.claims):
        return source,'潜伏占いの取得履歴が集約済みのため一部未表示'
    full=replace(request,origin=FullTraceOrigin(request.origin)).roles()
    return full,None
