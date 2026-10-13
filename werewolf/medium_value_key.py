"""Scalar memo key for the fixed-CO medium model, not another solver.

Retain wolf information-set laws, medium truth correlations and pending target
truth. Only exchangeable non-CO locations and irrelevant completed history are
forgotten. Row IDs/policy vectors are never cached under this reduced key.
"""
from fractions import Fraction as F


def _party_descriptor(b,s,rules,strategy,pending,target):
    if any(b.claims[p-1]!='medium' for p in b.alive):return None
    if any((h.roles[0]|h.roles[1])&b.alive_mask!=b.alive_mask for h in s.hypotheses):return None
    eligible={o[1] for o in pending};masses={};lookup={}
    for h in s.hypotheses:
        info=(h.roles[0]&b.alive_mask,bool(target and h.roles[0]&(1<<(target-1))))
        lookup[h.roles[0]]=info;masses[info]=masses.get(info,F())+h.mass
    groups=[]
    for p in b.alive:
        matched=None
        for group in groups:
            q=group[0]
            if (p in eligible)!=(q in eligible):continue
            a=1<<(p-1);c=1<<(q-1)
            if all(masses.get((w^(a|c) if bool(w&a)!=bool(w&c) else w,t),F())==v
                   for (w,t),v in masses.items()):matched=group;break
        if matched is None:groups.append([p])
        else:matched.append(p)
    groups.sort(key=lambda g:(g[0] in eligible,b.wolf_probability(g[0]),len(g),g[0]))
    masks=tuple(sum(1<<(p-1) for p in group) for group in groups)
    def counts(w):return tuple((w&m).bit_count() for m in masks)
    public={};wl={}
    for full,(w,t) in lookup.items():wl[full]=(counts(w),t)
    for (w,t),q in masses.items():
        info=(counts(w),t);public[info]=public.get(info,F())+q
    prefix=('party-scalar',b.phase,tuple(len(g) for g in groups),tuple(g[0] in eligible for g in groups),
            b.initial_medium_count,b.initial_role_counts['wolf'],bool(target),rules,strategy,
            tuple(sorted(public.items())))
    return prefix,wl,None,None,b.alive_mask,tuple(tuple(g) for g in groups)


def public_descriptor(b,s,rules,strategy):
    if b.initial_seer_count or b.initial_hunter_count or len(s.rosters)!=b.day:return None
    if any(h.acquisitions for h in s.hypotheses):return None
    if strategy.disclosure_for('seer')=='all' and any(b.claims[p-1]=='seer' for p in b.alive):return None
    co=tuple(p for p in b.alive if b.claims[p-1]=='medium')
    other=tuple(p for p in b.alive if p not in co);ids=co+other;k=len(co)
    def living(mask):return sum(1<<i for i,p in enumerate(ids) if mask&(1<<(p-1)))
    def truth(mask):return sum(1<<i for i,p in enumerate(co) if mask&(1<<(p-1)))
    supplied={(r.day,r.reporter,r.target) for r in b.reports}
    pending=tuple(o for o in b.medium_opportunities if b.phase=='night' and
                  strategy.disclosure_for('medium')=='all' and o[0]==b.day+1 and o[1] in co
                  and o not in b.report_resolved and o not in supplied)
    targets=tuple(sorted({o[2] for o in pending}))
    if len(targets)>1:return None
    target=targets[0] if targets else None
    party=_party_descriptor(b,s,rules,strategy,pending,target)
    if party is not None:return party
    wolves={}
    for h in s.hypotheses:
        weights=wolves.setdefault(h.roles[0],{});m=truth(h.roles[1])
        weights[m]=weights.get(m,F())+h.mass
    lookup={};masses={}
    for w,weights in wolves.items():
        mass=sum(weights.values(),F());law=tuple((m,q/mass) for m,q in sorted(weights.items()))
        info=(living(w),bool(target and w&(1<<(target-1))),law)
        lookup[w]=info;masses[info]=masses.get(info,F())+mass
    # Check the complete actor-law distribution, not just wolf marginals.
    for j in range(k+1,len(ids)):
        a=1<<k;c=1<<j
        for (w,t,law),q in masses.items():
            swapped=w^(a|c) if bool(w&a)!=bool(w&c) else w
            if masses.get((swapped,t,law),F())!=q:return None
    low=(1<<k)-1;public={}
    for (w,t,law),q in masses.items():
        key=(w&low,(w>>k).bit_count(),t,law);public[key]=public.get(key,F())+q
    eligible=tuple(p in {o[1] for o in pending} for p in co)
    prefix=('medium-scalar',b.phase,k,len(other),b.initial_medium_count,b.initial_role_counts['wolf'],
            eligible,bool(target),rules,strategy,tuple(sorted(public.items())))
    return prefix,lookup,truth,low,k,co


def private_value_key(descriptor,private):
    if descriptor is None or any(h.acquisitions for h in private.hypotheses):return None
    prefix,lookup,truth,low,k,co=descriptor;own={}
    if prefix[0]=='party-scalar':
        for h in private.hypotheses:
            if h.roles[0] not in lookup or (h.roles[0]|h.roles[1])&k!=k:return None
            info=lookup[h.roles[0]];own[info]=own.get(info,F())+h.mass
        return prefix,tuple(sorted(own.items()))
    for h in private.hypotheses:
        if h.roles[0] not in lookup:return None
        w,t,law=lookup[h.roles[0]]
        key=(w&low,(w>>k).bit_count(),t,law,truth(h.roles[1]))
        own[key]=own.get(key,F())+h.mass
    return prefix,tuple(sorted(own.items()))


def private_action_key(descriptor,private,target):
    if descriptor is None or any(h.acquisitions for h in private.hypotheses):return None
    prefix,lookup,truth,low,k,co=descriptor;own={};bit=1<<(target-1)
    if prefix[0]=='party-scalar':
        for h in private.hypotheses:
            if h.roles[0] not in lookup or (h.roles[0]|h.roles[1])&k!=k:return None
            info=(*lookup[h.roles[0]],bool(h.roles[0]&bit));own[info]=own.get(info,F())+h.mass
        return 'party-action',prefix,next(i for i,g in enumerate(co) if target in g),tuple(sorted(own.items()))
    for h in private.hypotheses:
        if h.roles[0] not in lookup:return None
        w,t,law=lookup[h.roles[0]]
        key=(w&low,(w>>k).bit_count(),t,law,truth(h.roles[1]),bool(h.roles[0]&bit))
        own[key]=own.get(key,F())+h.mass
    return 'medium-action',prefix,(co.index(target) if target in co else -1),tuple(sorted(own.items()))
