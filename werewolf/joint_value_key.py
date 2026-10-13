"""Exact scalar/action memo keys under latent-player renaming, never policies.

Fixed CO, one publishing seer, no hunter ability. Every role/scan correlation
relevant to public laws is retained; public and observer distributions remain
separate. A small (at most four labels) bijection is computational reuse only.
"""
from itertools import permutations
from functools import lru_cache


@lru_cache(maxsize=16)
def renamings(player_count,slots):
    """Public label bijections only; no belief, private state or strategy."""
    result=[]
    for order in permutations(slots):
        mapping=dict(zip(slots,order))
        ids=tuple(mapping.get(p,p) for p in range(1,player_count+1))
        masks=tuple(sum(1<<(ids[p]-1) for p in range(player_count) if mask&(1<<p))
                    for mask in range(1<<player_count))
        result.append((ids,masks))
    return tuple(result)


def public_variants(b,s,past):
    slots=tuple(p for p in range(1,b.player_count+1) if b.claims[p-1]=='latent')
    seers=tuple(p for p in b.alive if b.claims[p-1]=='seer')
    if not b.initial_seer_count or b.initial_hunter_count or len(seers)!=1 or len(slots)>4:return None
    medium=sum(1<<(p-1) for p in b.alive if b.claims[p-1]=='medium')
    seer=sum(1<<(p-1) for p in seers)
    supplied={(r.day,r.reporter,r.target) for r in b.reports}
    pending=tuple(o for o in b.medium_opportunities if o[0]>=b.day and
                  o not in b.report_resolved and o not in supplied and
                  not any(e.target==o[1] and e.day<o[0] for e in b.history))
    result=[]
    for ids,masks in renamings(b.player_count,slots):
        rename=lambda p:ids[p-1]
        triples=lambda entries:tuple(sorted((day,rename(owner),rename(target)) for day,owner,target in entries))
        board=(b.player_count,b.day,b.phase,tuple(b.claims),
               tuple(sorted(rename(p) for p in b.alive)),
               # Completed medium reports/history already conditioned the
               # joint law. Retain every still-pending report opportunity.
               triples(pending),
               tuple(sorted(b.initial_role_counts.items())))
        ledger=(s.initial_rule,s.observed_prefix,s.tracked,
                tuple(tuple(sorted(rename(p) for p in roster)) for roster in s.rosters),
                tuple((r.acquired_day,r.published_day,rename(r.player),rename(r.target),r.color) for r in past))
        public=joint_signature(s,masks,ids,medium,seer)
        result.append(((board,ledger,public),masks,ids,medium,seer))
    best=min(public for public,*_ in result)
    return tuple(item for item in result if item[0]==best)


def joint_signature(state,masks,ids,medium,seer):
    groups={}
    for h in state.hypotheses:
        scans=tuple((a.day,a.player,ids[a.target-1],a.color) for a in h.acquisitions
                    if seer&(1<<(a.player-1)))
        key=(masks[h.roles[0]],h.roles[1]&medium,h.roles[2]&seer,scans)
        groups[key]=groups[key]+h.mass if key in groups else h.mass
    return tuple(sorted(groups.items()))


def value_key(variants,private,target=None,*,public_same=False):
    if variants is None:return None
    return ('renamed-joint-value',min((public,public[2] if public_same else joint_signature(private,masks,ids,medium,seer),
                                     ids[target-1] if target is not None else 0)
                                    for public,masks,ids,medium,seer in variants))
