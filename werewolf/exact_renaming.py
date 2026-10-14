"""Full-information scalar/action keys under exact player bijections.

Every candidate mapping is serialized with the entire public and private law.
Colors only reduce the search; they never establish equality by themselves.
No probability branches or policy rows are merged. Keys cache scalar payoffs;
callers keep original targets, tie multiplicities and exact chance masses.
Unknown record/observer shapes fail closed to the ordinary evaluator.
"""
from dataclasses import fields,is_dataclass
from fractions import Fraction as F
from itertools import permutations,product
from math import factorial
from .calculation_budget import tick

BOARD_FIELDS=frozenset(('player_count','alive','wolf_count','day','phase','history','belief',
 'initial_medium_count','claims','role_belief','initial_seer_count','initial_hunter_count',
 'world_belief','medium_opportunities','reports','report_resolved','guard_prior_roster'))
STATE_FIELDS=frozenset(('hypotheses','rosters','initial_rule','tracked','observed_prefix'))
LABELS=frozenset(('player','reporter','actor','target'))
RECORDS=frozenset(('PublicEvent','MediumReport','Acquisition','SeerReport','GuardIntent','WolfAttack'))

class Unsupported(Exception):pass

def record(r,ids):
    if (not is_dataclass(r) or type(r).__name__ not in RECORDS or
        any(f.name not in LABELS | {"day","phase","color","night","acquired_day","published_day"} for f in fields(r))):raise Unsupported()
    return (type(r).__name__,tuple((f.name,ids[getattr(r,f.name)-1] if f.name in LABELS
                                  else getattr(r,f.name)) for f in fields(r)))

def board_signature(b,ids,masks):
    if {f.name for f in fields(b)}!=BOARD_FIELDS:raise Unsupported()
    def triplets(xs):return tuple(sorted((d,ids[a-1],ids[t-1]) for d,a,t in xs))
    mapped={'alive':tuple(sorted(ids[p-1] for p in b.alive)),
      'claims':tuple(c for _,c in sorted((ids[p-1],c) for p,c in enumerate(b.claims,1))),
      'history':tuple(record(r,ids) for r in b.history),
      'belief':tuple(sorted((masks[w],q) for w,q in b.belief)),
      'role_belief':tuple(sorted((masks[w],masks[m],q) for w,m,q in b.role_belief)),
      'world_belief':tuple(sorted((*tuple(masks[m] for m in row[:-1]),row[-1]) for row in b.world_belief)),
      'medium_opportunities':triplets(b.medium_opportunities),
      'report_resolved':triplets(b.report_resolved),
      'reports':tuple(record(r,ids) for r in b.reports),
      'guard_prior_roster':None if b.guard_prior_roster is None else
          (b.guard_prior_roster[0],tuple(sorted(ids[p-1] for p in b.guard_prior_roster[1])))}
    return tuple((f.name,mapped.get(f.name,getattr(b,f.name))) for f in fields(b))

def state_signature(s,ids,masks):
    if {f.name for f in fields(s)}!=STATE_FIELDS:raise Unsupported()
    if any({f.name for f in fields(h)}!={"roles","acquisitions","mass","guards","attacks"} for h in s.hypotheses):raise Unsupported()
    hypotheses=tuple(sorted((tuple(masks[m] for m in h.roles),
         tuple(sorted(record(a,ids) for a in h.acquisitions)),
         tuple(record(g,ids) for g in h.guards),tuple(record(a,ids) for a in h.attacks),h.mass)
         for h in s.hypotheses))
    return (hypotheses,tuple(tuple(sorted(ids[p-1] for p in r)) for r in s.rosters),
            s.initial_rule,None if s.tracked is None else tuple(sorted(ids[p-1] for p in s.tracked)),
            s.observed_prefix)

def observer_signature(observer,ids,masks):
    if observer is None:return ('none',)
    if type(observer).__name__!='GuardObserver':raise Unsupported()
    return ('guard',board_signature(observer.board,ids,masks),ids[observer.actor-1],
            ids[observer.target-1],tuple(sorted(tuple(masks[m] for m in role) for role in observer.allowed_roles)))

def configuration(obj):
    # Current policy selectors contain symbolic items, never player IDs.
    expected={"Rules":{"allow_self_bite","initial_seer","allow_repeat_guard"},
              "Strategy":{"day","night","include_self_bite","fake_reports","disclosure_common","seer_disclosure","medium_disclosure","seer_position","fake_seer_policy","guard_position"}}
    if not is_dataclass(obj) or {f.name for f in fields(obj)}!=expected.get(type(obj).__name__):raise Unsupported()
    return tuple((f.name,getattr(obj,f.name)) for f in fields(obj))

def colors(b,s,private,target):
    def marginals(law):
        return tuple(tuple(sum((h.mass for h in law.hypotheses if h.roles[r]&(1<<(p-1))),F())
                           for r in range(4)) for p in range(1,b.player_count+1))
    public= marginals(s);own=marginals(private)
    return tuple((b.claims[p-1],p in b.alive,p==target,public[p-1],own[p-1],
                  tuple((e.day,e.phase) for e in b.history if e.target==p),
                  tuple(i for i,r in enumerate(s.rosters) if p in r),
                  tuple(i for i,r in enumerate(private.rosters) if p in r),
                  s.tracked is not None and p in s.tracked,
                  private.tracked is not None and p in private.tracked)
                 for p in range(1,b.player_count+1))

def canonical_key(b,s,past,private,observer,rules,strategy,*,target=None,physical=None,max_mappings=10000):
    """Return an exact payoff key, or None when safe search exceeds its cap."""
    if observer is not None and type(observer).__name__!='GuardObserver':return None
    groups={}
    for p,color in enumerate(colors(b,s,private,target),1):groups.setdefault(color,[]).append(p)
    blocks=tuple(tuple(groups[c]) for c in sorted(groups))
    count=1
    for block in blocks:count*=factorial(len(block))
    if count>max_mappings:return None
    try:base=(configuration(rules),configuration(strategy))
    except Unsupported:return None
    best=None;offsets=[];offset=0
    for block in blocks:offsets.append(tuple(range(offset+1,offset+len(block)+1)));offset+=len(block)
    try:
        for orders in product(*(permutations(block) for block in blocks)):
            tick()
            mapping={p:q for order,slots in zip(orders,offsets) for p,q in zip(order,slots)}
            ids=tuple(mapping[p] for p in range(1,b.player_count+1))
            masks=tuple(sum(1<<(ids[p]-1) for p in range(b.player_count) if m&(1<<p))
                        for m in range(1<<b.player_count))
            public=board_signature(b,ids,masks);law=state_signature(s,ids,masks)
            own=law if private==s else state_signature(private,ids,masks)
            actual=public if physical is None or physical==b else board_signature(physical,ids,masks)
            key=(base,public,law,tuple(record(r,ids) for r in past),own,
                 observer_signature(observer,ids,masks),actual,0 if target is None else ids[target-1])
            if best is None or key<best:best=key
    except Unsupported:return None
    return ('exact-full-renaming',best)
