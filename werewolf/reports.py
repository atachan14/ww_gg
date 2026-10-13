"""Exact future medium disclosures on sufficient public joint states.

Marginalize only role distinctions with no future effect: keep live wolf masks,
true-medium masks for CO/reporters, and the executed target's correlated color.
"""
from fractions import Fraction as F
from functools import lru_cache
from itertools import product
from .calculation_budget import tick


def delete_bit(mask,index):
    return (mask&((1<<index)-1))|((mask>>(index+1))<<index)


def normalize(entries):
    groups={}
    for w,m,t,q in entries:groups[w,m,t]=groups.get((w,m,t),F())+q
    mass=sum(groups.values(),F())
    return tuple((*key,q/mass) for key,q in sorted(groups.items()))


def swap(mask,a,b):
    return mask ^ ((1<<a)|(1<<b)) if bool(mask&(1<<a))!=bool(mask&(1<<b)) else mask


def same_action(a,b,co,eligible,entries):
    if bool(co&(1<<a))!=bool(co&(1<<b)) or bool(eligible&(1<<a))!=bool(eligible&(1<<b)):return False
    original={(w,m,t):q for w,m,t,q in entries}
    return all(original.get((swap(w,a,b),swap(m,a,b),t))==q for w,m,t,q in entries)


def winning(n,w):
    return 1 if w==0 else 0 if w>=n-w else None


def transition(n,phase,co,eligible,entries,target,strategy):
    tick(len(entries))
    counts={}
    for w,m,t,q in entries:counts[w.bit_count()]=counts.get(w.bit_count(),F())+q
    normalizers={}
    if phase=='night' and not strategy.include_self_bite:
        for w,m,t,q in entries:
            if not w&(1<<target):normalizers[w.bit_count()]=normalizers.get(w.bit_count(),F())+q
        if set(normalizers)!=set(counts):return None
    continuing=[];village=F()
    for w,m,t,q in entries:
        if phase=='night' and not strategy.include_self_bite:
            if w&(1<<target):continue
            q*=counts[w.bit_count()]/normalizers[w.bit_count()]
        remaining=delete_bit(w,target);truth=bool(w&(1<<target)) if phase=='day' else t
        result=winning(n-1,remaining.bit_count())
        if result==1:village+=q
        elif result is None:continuing.append((remaining,delete_bit(m,target),int(truth),q))
    mass=sum((x[-1] for x in continuing),F())
    if mass:
        new_co=delete_bit(co,target)
        new_eligible=new_co if phase=='day' else delete_bit(eligible,target)
        child=normalize(continuing)
        if phase=='night' and new_eligible:
            continuation=disclosure(n-1,new_co,new_eligible,child,strategy)
        else:
            continuation=solve_reports(n-1,'night' if phase=='day' else 'day',new_co,new_eligible if phase=='day' else 0,child,strategy)
        village+=mass*continuation
    return village


@lru_cache(maxsize=32768)
def disclosure(n,co,eligible,entries,strategy):
    tick(len(entries))
    reporters=tuple(i for i in range(n) if eligible&(1<<i))
    fake_positions=tuple(i for i in reporters if any(w&(1<<i) for w,m,t,q in entries))
    if strategy.fake_reports=='random':
        # The random instruction is private. Merge all paths to one public
        # report vector BEFORE optimizing any subsequent public action.
        groups={};normalizer=1<<len(fake_positions)
        for colors in product((0,1),repeat=len(fake_positions)):
            tick(len(entries))
            instructions=dict(zip(fake_positions,colors))
            for w,m,t,q in entries:
                pattern=sum(1<<i for i in reporters if (t if m&(1<<i) else instructions[i]))
                groups.setdefault(pattern,[]).append((w,m,0,q/normalizer))
        return sum((sum(x[-1] for x in group)*solve_reports(n,'day',co,0,normalize(group),strategy) for group in groups.values()),F())
    values=[]
    for colors in product((0,1),repeat=len(fake_positions)):
        tick(len(entries))
        instructions=dict(zip(fake_positions,colors));groups={}
        for w,m,t,q in entries:
            pattern=sum(1<<i for i in reporters if (t if m&(1<<i) else instructions[i]))
            groups.setdefault(pattern,[]).append((w,m,0,q))
        value=F()
        for group in groups.values():
            mass=sum((x[-1] for x in group),F())
            value+=mass*solve_reports(n,'day',co,0,normalize(group),strategy)
        values.append(value)
    return sum(values,F())/len(values) if strategy.fake_reports=='random' else min(values)


@lru_cache(maxsize=32768)
def solve_reports(n,phase,co,eligible,entries,strategy):
    tick(len(entries))
    winners={winning(n,w.bit_count()) for w,m,t,q in entries}
    if len(winners)==1 and None not in winners:return F(next(iter(winners)))
    representatives=[];values=[]
    for target in range(n):
        representative=next((i for i in representatives if same_action(target,i,co,eligible,entries)),None)
        if representative is not None:
            value=values[representative]
        else:
            value=transition(n,phase,co,eligible,entries,target,strategy)
            representatives.append(target)
        values.append(value)
    candidates=[value for value in values if value is not None]
    if not candidates:raise ValueError('No legal public action')
    mode=strategy.day if phase=='day' else strategy.night
    return sum(candidates,F())/len(candidates) if mode=='random' else max(candidates) if phase=='day' else min(candidates)


def compact(board,reveal_now=False):
    ids=board.alive;co=sum(1<<j for j,i in enumerate(ids) if board.claims[i-1]=='medium')
    report_day=board.day if reveal_now else board.day+1 if board.phase=='night' else None
    supplied={(r.day,r.reporter,r.target) for r in board.reports}
    opportunities=tuple(o for o in board.medium_opportunities if o[0]==report_day and o[1] in ids and o not in board.report_resolved and o not in supplied)
    eligible=sum(1<<j for j,i in enumerate(ids) if any(o[1]==i for o in opportunities))
    targets={o[2] for o in opportunities}
    if len(targets)>1:raise ValueError('One execution per simultaneous report opportunity')
    target=next(iter(targets),None)
    entries=[]
    # Other village roles have no abilities; wolf/medium joint projection is sufficient.
    for w,m,q in board.role_belief:
        wm=sum(1<<j for j,i in enumerate(ids) if w&(1<<(i-1)))
        mm=sum(1<<j for j,i in enumerate(ids) if m&(1<<(i-1)))&(co|eligible)
        entries.append((wm,mm,int(bool(w&(1<<(target-1)))) if target else 0,q))
    return len(ids),co,eligible,normalize(entries)


def public_value(board,strategy,reveal_now=False):
    if strategy.disclosure_for('medium')=='none':
        from .exact import solve,marginal_state
        return solve(len(board.alive),board.phase,marginal_state(board),strategy).village_win
    n,co,eligible,entries=compact(board,reveal_now)
    tick(len(entries))
    if reveal_now and eligible:return disclosure(n,co,eligible,entries,strategy)
    return solve_reports(n,board.phase,co,eligible,entries,strategy)
