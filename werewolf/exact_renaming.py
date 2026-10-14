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

def field_names(value,cache=None):
    key=('fields',type(value))
    if cache is not None and key in cache:return cache[key]
    result=frozenset(f.name for f in fields(value))
    if cache is not None:cache[key]=result
    return result


def record(r,ids,cache=None):
    key=None
    if cache is not None:
        try:
            key=(r,ids)
            if key in cache:return cache[key]
        except TypeError:key=None
    if (not is_dataclass(r) or type(r).__name__ not in RECORDS or
        not field_names(r,cache)<=LABELS | {"day","phase","color","night","acquired_day","published_day"}):raise Unsupported()
    result=(type(r).__name__,tuple((f.name,ids[getattr(r,f.name)-1] if f.name in LABELS
                                  else getattr(r,f.name)) for f in fields(r)))
    if cache is not None and key is not None and len(cache)<8192:cache[key]=result
    return result


def board_signature(b,ids,masks,record_cache=None):
    if {f.name for f in fields(b)}!=BOARD_FIELDS:raise Unsupported()
    def triplets(xs):return tuple(sorted((d,ids[a-1],ids[t-1]) for d,a,t in xs))
    mapped={'alive':tuple(sorted(ids[p-1] for p in b.alive)),
      'claims':tuple(c for _,c in sorted((ids[p-1],c) for p,c in enumerate(b.claims,1))),
      'history':tuple(record(r,ids,record_cache) for r in b.history),
      'belief':tuple(sorted((masks[w],q) for w,q in b.belief)),
      'role_belief':tuple(sorted((masks[w],masks[m],q) for w,m,q in b.role_belief)),
      'world_belief':tuple(sorted((*tuple(masks[m] for m in row[:-1]),row[-1]) for row in b.world_belief)),
      'medium_opportunities':triplets(b.medium_opportunities),
      'report_resolved':triplets(b.report_resolved),
      'reports':tuple(record(r,ids,record_cache) for r in b.reports),
      'guard_prior_roster':None if b.guard_prior_roster is None else
          (b.guard_prior_roster[0],tuple(sorted(ids[p-1] for p in b.guard_prior_roster[1])))}
    return tuple((f.name,mapped.get(f.name,getattr(b,f.name))) for f in fields(b))

def state_signature(s,ids,masks,record_cache=None):
    if {f.name for f in fields(s)}!=STATE_FIELDS:raise Unsupported()
    if any(field_names(h,record_cache)!={"roles","acquisitions","mass","guards","attacks"} for h in s.hypotheses):raise Unsupported()
    hypotheses=tuple(sorted((tuple(masks[m] for m in h.roles),
         tuple(sorted(record(a,ids,record_cache) for a in h.acquisitions)),
         tuple(record(g,ids,record_cache) for g in h.guards),tuple(record(a,ids,record_cache) for a in h.attacks),h.mass)
         for h in s.hypotheses))
    return (hypotheses,tuple(tuple(sorted(ids[p-1] for p in r)) for r in s.rosters),
            s.initial_rule,None if s.tracked is None else tuple(sorted(ids[p-1] for p in s.tracked)),
            s.observed_prefix)

def observer_signature(observer,ids,masks,record_cache=None):
    if observer is None:return ('none',)
    if type(observer).__name__!='GuardObserver':raise Unsupported()
    return ('guard',board_signature(observer.board,ids,masks,record_cache),ids[observer.actor-1],
            ids[observer.target-1],tuple(sorted(tuple(masks[m] for m in role) for role in observer.allowed_roles)))

def configuration(obj):
    # Current policy selectors contain symbolic items, never player IDs.
    expected={"Rules":{"allow_self_bite","initial_seer","allow_repeat_guard"},
              "Strategy":{"day","night","include_self_bite","fake_reports","disclosure_common","seer_disclosure","medium_disclosure","seer_position","fake_seer_policy","guard_position"}}
    if not is_dataclass(obj) or {f.name for f in fields(obj)}!=expected.get(type(obj).__name__):raise Unsupported()
    return tuple((f.name,getattr(obj,f.name)) for f in fields(obj))

def colors(b,s,private,target,*,marginal_cache=None):
    def marginals(law):
        key=(law,b.player_count)
        if marginal_cache is not None and key in marginal_cache:return marginal_cache[key]
        totals=[[F() for _ in range(4)] for _ in range(b.player_count)]
        for h in law.hypotheses:
            for r,mask in enumerate(h.roles):
                while mask:
                    bit=mask&-mask;totals[bit.bit_length()-1][r]+=h.mass;mask-=bit
        result=tuple(tuple(row) for row in totals)
        if marginal_cache is not None:marginal_cache[key]=result
        return result
    public=marginals(s);own=public if private is s else marginals(private)
    return tuple((b.claims[p-1],p in b.alive,p==target,public[p-1],own[p-1],
                  tuple((e.day,e.phase) for e in b.history if e.target==p),
                  tuple(i for i,r in enumerate(s.rosters) if p in r),
                  tuple(i for i,r in enumerate(private.rosters) if p in r),
                  s.tracked is not None and p in s.tracked,
                  private.tracked is not None and p in private.tracked)
                 for p in range(1,b.player_count+1))

def canonical_key(b,s,past,private,observer,rules,strategy,*,target=None,physical=None,max_mappings=10000,prune_automorphisms=True,marginal_cache=None):
    """Return an exact payoff key, or None when safe search exceeds its cap."""
    if observer is not None and type(observer).__name__!='GuardObserver':return None
    groups={}
    for p,color in enumerate(colors(b,s,private,target,marginal_cache=marginal_cache),1):groups.setdefault(color,[]).append(p)
    blocks=tuple(tuple(groups[c]) for c in sorted(groups))
    count=1
    for block in blocks:count*=factorial(len(block))
    if count>max_mappings:return None
    try:base=(configuration(rules),configuration(strategy))
    except Unsupported:return None
    best=None;offsets=[];offset=0
    for block in blocks:offsets.append(tuple(range(offset+1,offset+len(block)+1)));offset+=len(block)
    def masks_for(ids):
        return tuple(sum(1<<(ids[p]-1) for p in range(b.player_count) if m&(1<<p))
                     for m in range(1<<b.player_count))
    record_cache={}  # Per-key, immutable record serialization only.
    def snapshot(ids,masks):
        public=board_signature(b,ids,masks,record_cache);law=state_signature(s,ids,masks,record_cache)
        own=law if private==s else state_signature(private,ids,masks,record_cache)
        actual=public if physical is None or physical==b else board_signature(physical,ids,masks,record_cache)
        return (base,public,law,tuple(record(r,ids,record_cache) for r in past),own,
                observer_signature(observer,ids,masks,record_cache),actual,0 if target is None else ids[target-1])
    try:
        # Prove automorphisms against the ENTIRE input, not just colors. The
        # swaps (leader,other) generate every permutation inside a block. If
        # each preserves the snapshot, all its orders serialize identically
        # under every mapping of the other blocks; keep one representative.
        identity=tuple(range(1,b.player_count+1));original=None;orders_by_block=[]
        for block in blocks:
            symmetric=prune_automorphisms and len(block)>=3
            if symmetric:
                if original is None:original=snapshot(identity,tuple(range(1<<b.player_count)))
                for other in block[1:]:
                    tick();ids=list(identity);a=block[0]-1;c=other-1;ids[a],ids[c]=ids[c],ids[a]
                    ids=tuple(ids)
                    if snapshot(ids,masks_for(ids))!=original:
                        symmetric=False;break
            orders_by_block.append((block,) if symmetric else permutations(block))
        for orders in product(*orders_by_block):
            tick()
            mapping={p:q for order,slots in zip(orders,offsets) for p,q in zip(order,slots)}
            ids=tuple(mapping[p] for p in range(1,b.player_count+1))
            key=snapshot(ids,masks_for(ids))
            if best is None or key<best:best=key
    except Unsupported:return None
    return ('exact-full-renaming',best)
