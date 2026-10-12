"""Per-evaluation work budget; complete exact cache values retain their meaning."""
from contextvars import ContextVar
from contextlib import contextmanager

class CalculationBudgetExceeded(Exception):pass
_current=ContextVar('wwgg_calculation_budget',default=None)

@contextmanager
def calculation_budget(max_work=None):
    if max_work is not None and (type(max_work)is not int or max_work<1):raise ValueError('Positive calculation budget required')
    token=_current.set(None if max_work is None else [max_work,0])
    try:yield
    finally:_current.reset(token)

def tick(work=1):
    state=_current.get()
    if state is not None:
        state[1]+=work
        if state[1]>state[0]:raise CalculationBudgetExceeded('Exact public calculation work budget exceeded')
