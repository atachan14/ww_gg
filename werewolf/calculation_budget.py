"""Per-evaluation work budget; complete exact cache values retain their meaning."""
from contextvars import ContextVar
from contextlib import contextmanager
from time import monotonic

class CalculationBudgetExceeded(Exception):pass
_current=ContextVar('wwgg_calculation_budget',default=None)

@contextmanager
def calculation_budget(max_work=None, *, max_seconds=None):
    if max_work is not None and (type(max_work)is not int or max_work<1):raise ValueError('Positive calculation budget required')
    if max_seconds is not None and (type(max_seconds) not in (int,float) or max_seconds<=0):raise ValueError('Positive calculation time budget required')
    parent=_current.get();deadline=parent[2] if parent is not None else None
    if max_seconds is not None:
        own=monotonic()+max_seconds;deadline=own if deadline is None else min(deadline,own)
    token=_current.set(None if max_work is None and deadline is None else [max_work,0,deadline])
    try:yield
    finally:_current.reset(token)

def tick(work=1):
    state=_current.get()
    if state is not None:
        state[1]+=work
        if state[2] is not None and monotonic()>=state[2]:raise CalculationBudgetExceeded('Exact public calculation time budget exceeded')
        if state[0] is not None and state[1]>state[0]:raise CalculationBudgetExceeded('Exact public calculation work budget exceeded')
