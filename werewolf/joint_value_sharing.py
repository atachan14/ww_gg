"""Opt-in owner-scoped exact sharing of immutable joint-law components.

Full hypotheses include exact mass and every private record. Law containers,
metadata, origin evidence and policy snapshots are never interned or omitted.
"""
from contextvars import ContextVar
from contextlib import contextmanager
from fractions import Fraction
from weakref import WeakValueDictionary
from collections import Counter

_active=ContextVar('wwgg_immutable_joint_scope',default=None)


class JointPoolOwnerChanged(ValueError):pass


class JointValuePool:
    def __init__(self,owner):
        self.owner=owner;self.data=owner.data;self.active=True
        self.records=WeakValueDictionary();self.hypotheses=WeakValueDictionary();self.counts=Counter();self.closed_live_counts=None
    def check(self):
        if not self.active or self.owner.data is not self.data:raise JointPoolOwnerChanged('immutable_joint_pool_owner_revision_changed')
    def record(self,r):
        from .seer_acquisition import Acquisition
        from .guard_effect import GuardIntent
        from .night_knowledge import WolfAttack
        if type(r)is Acquisition and all(type(x)is int for x in (r.day,r.player,r.target)) and type(r.color)is str:key=(Acquisition,r.day,r.player,r.target,r.color)
        elif type(r)is GuardIntent and all(type(x)is int for x in (r.night,r.actor,r.target)):key=(GuardIntent,r.night,r.actor,r.target)
        elif type(r)is WolfAttack and all(type(x)is int for x in (r.night,r.target)):key=(WolfAttack,r.night,r.target)
        else:return r
        self.counts['record_requests']+=1;old=self.records.get(key)
        if old is not None:self.counts['record_hits']+=1;return old
        self.records[key]=r;return r
    def components(self,acquisitions,guards,attacks):
        self.check()
        result=[]
        for rows in (acquisitions,guards,attacks):
            if type(rows)is not tuple:result.append(rows);continue
            shared=tuple(self.record(r) for r in rows)
            result.append(rows if all(a is b for a,b in zip(rows,shared)) else shared)
        return tuple(result)
    def joint(self,entries):
        from .seer_acquisition import Hypothesis,Acquisition
        from .guard_effect import GuardIntent
        from .night_knowledge import WolfAttack
        self.check()
        if type(entries)is not tuple:return entries
        result=[]
        for h in entries:
            canonical=(type(h)is Hypothesis and type(h.roles)is tuple and type(h.mass)is Fraction and
                all(type(v)is int for v in h.roles) and type(h.acquisitions)is tuple and type(h.guards)is tuple and type(h.attacks)is tuple and
                all(type(a)is Acquisition and type(a.color)is str for a in h.acquisitions) and all(type(g)is GuardIntent for g in h.guards) and all(type(a)is WolfAttack for a in h.attacks))
            if not canonical:result.append(h);self.counts['uncanonical_hypotheses']+=1;continue
            # Equality of the entire tuple, not a digest or marginal signature,
            # resolves hash collisions and retains full role/history coupling.
            key=(h.roles,h.acquisitions,h.mass,h.guards,h.attacks)
            self.counts['hypothesis_requests']+=1;old=self.hypotheses.get(key)
            if old is not None:self.counts['hypothesis_hits']+=1;result.append(old)
            else:self.hypotheses[key]=h;result.append(h)
        return entries if all(a is b for a,b in zip(entries,result)) else tuple(result)
    def close(self):
        self.closed_live_counts=dict(records=len(self.records),hypotheses=len(self.hypotheses))
        self.records.clear();self.hypotheses.clear();self.active=False;self.owner=None;self.data=None


@contextmanager
def share_joint_values(owner):
    pool=JointValuePool(owner);token=_active.set(pool)
    try:yield pool
    finally:_active.reset(token);pool.close()


@contextmanager
def independent_joint_values():
    token=_active.set(None)
    try:yield
    finally:_active.reset(token)


def share_hypothesis_records(h):
    pool=_active.get()
    if pool is None:return
    # Constructor-time replacement only; validated equal immutable records.
    # No already-published Hypothesis object is mutated by the pool.
    values=pool.components(h.acquisitions,h.guards,h.attacks)
    for name,value in zip(('acquisitions','guards','attacks'),values):
        if value is not getattr(h,name):object.__setattr__(h,name,value)


def share_hypothesis_tuple(entries):
    pool=_active.get()
    return entries if pool is None else pool.joint(entries)
