"""Finite, request-owned exact evaluation budgets; no game inputs in diagnostics."""
from contextvars import ContextVar
from contextlib import contextmanager
from time import monotonic
import logging

DEFAULT_MAX_WORK=4000000
DEFAULT_MAX_SECONDS=270
_current=ContextVar('wwgg_calculation_budget',default=None)
_last_stop=ContextVar('wwgg_budget_stop',default=None)
_cancelled=ContextVar('wwgg_calculation_cancelled',default=None)
_log=logging.getLogger('wwgg.budget')

class CalculationCancelled(Exception):pass

@contextmanager
def cancellation_scope(event):
    token=_cancelled.set(event)
    try:yield
    finally:_cancelled.reset(token)

class CalculationBudgetExceeded(Exception):
    def __init__(self,message='Exact calculation budget exceeded',*,kind=None):
        super().__init__(message);self.kind=kind

def reset_diagnostics():_last_stop.set(None)
def budget_stop():return _last_stop.get()
def stop_message(kind=None):
    stop=budget_stop()
    if kind is not None:stop={'kind':kind}
    if stop and stop['kind']=='time':return '計算時間の上限に達しました。結果は未計算です。'
    if stop and stop['kind']=='work':return '計算作業量の上限に達しました。結果は未計算です。'
    return '計算予算に達しました。結果は未計算です。'

@contextmanager
def calculation_budget(max_work=None,*,max_seconds=None):
    if max_work is not None and (type(max_work)is not int or max_work<1):raise ValueError('Positive calculation budget required')
    if max_seconds is not None and (type(max_seconds) not in (int,float) or max_seconds<=0):raise ValueError('Positive calculation time budget required')
    parent=_current.get();deadline=parent[2] if parent else None;started=parent[4] if parent else None
    if max_seconds is not None:
        now=monotonic();own=now+max_seconds;deadline=own if deadline is None else min(deadline,own)
        if started is None:started=now
    token=_current.set(None if max_work is None and deadline is None and parent is None else [max_work,0,deadline,parent,started])
    try:yield
    finally:_current.reset(token)

def check_cancelled():
    """Poll cooperative stop without charging work or altering budget identity."""
    cancelled=_cancelled.get()
    if cancelled is not None and cancelled.is_set():raise CalculationCancelled()

def tick(work=1):
    check_cancelled()
    state=_current.get()
    if state is None:return
    now=monotonic() if state[2] is not None else None
    # Every active owner receives the work; nested calls cannot reset a request's
    # work ceiling. Child scopes may impose a stricter local ceiling.
    cursor=state
    while cursor is not None:
        cursor[1]+=work
        kind='time' if cursor[2] is not None and now>=cursor[2] else 'work' if cursor[0] is not None and cursor[1]>cursor[0] else None
        if kind:
            if now is None:now=monotonic()
            detail={'kind':kind,'work':cursor[1],'max_work':cursor[0],
                    'elapsed_seconds':round(now-cursor[4],6) if cursor[4] is not None else None}
            _last_stop.set(detail)
            _log.warning('wwgg_budget_stop kind=%s work=%s max_work=%s elapsed_seconds=%s',kind,detail['work'],detail['max_work'],detail['elapsed_seconds'])
            raise CalculationBudgetExceeded('Exact calculation '+kind+' budget exceeded',kind=kind)
        cursor=cursor[3]


def budget_usage():
    state=_current.get()
    if state is None:return None
    while state[3] is not None:state=state[3]
    return {'work':state[1],'max_work':state[0],
            'elapsed_seconds':round(monotonic()-state[4],6) if state[4] is not None else None}

def peak_memory_mb():
    try:
        import resource
        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,3)
    except ImportError:return None

def log_result(endpoint,status,kind=None):
    usage=budget_usage()
    if usage is None:return
    # Counts, duration and process high-water only; no game/session/secret data.
    _log.warning('wwgg_budget_result endpoint=%s status=%s work=%s max_work=%s elapsed_seconds=%s process_peak_mb=%s stop=%s',
                 endpoint,status,usage['work'],usage['max_work'],usage['elapsed_seconds'],peak_memory_mb(),kind or (budget_stop() or {}).get('kind','complete'))
