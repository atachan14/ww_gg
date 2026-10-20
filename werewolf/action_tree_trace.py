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
        if source.public.day!=1 or source.public.phase!='day' or source.public.history:
            raise ValueError('Complete ability origin requires an initial saved root')
        from .night_abilities import complete_initial
        from .evaluation_branch import physical_board
        q=complete_initial(source.public_state,source.public.alive)
        p=q if source.private==source.public_state else complete_initial(source.private,source.public.alive)
        return replace(source,public_state=q,private=p,physical=physical_board(source.public,p,source.physical))

def trace_source(node):
    source=node.read()
    if source.private.tracked is None:return source,None
    tracked=sum(1<<(p-1) for p in source.private.tracked)
    roster=sum(1<<(p-1) for p in source.private.rosters[-1])
    if not any(h.roles[2]&roster&~tracked for h in source.private.hypotheses):return source,None
    request=node.export_request()
    full=replace(request,origin=FullTraceOrigin(request.origin)).roles()
    return full,None
