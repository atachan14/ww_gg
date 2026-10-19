"""Constructed player partitions; no law scans or runtime certificates."""
def _fix(groups,positions):
    fixed=set(positions);out=[]
    for group in groups:
        out.extend((p,) for p in group if p in fixed)
        rest=tuple(p for p in group if p not in fixed)
        if rest:out.append(rest)
    return tuple(out)


def _report_groups(groups,source):
    """Refine inherited classes by complete public outgoing report meaning.

    Named report targets are fixed conservatively. Equal reporters from the
    same parent class remain one block; incoming information can never be
    hidden by equal outgoing declarations.
    """
    records=[(r.player,('seer',r.acquired_day,r.published_day,'day',r.target,r.color)) for r in source.past]
    records.extend((r.reporter,('medium',r.day,r.day,'day',r.target,r.color)) for r in source.public.reports)
    records.extend((actor,('resolved',day,day,'day',target,None)) for day,actor,target in source.public.report_resolved)
    fixed={record[4] for _,record in records}
    result=[]
    for group in _fix(groups,fixed):
        split={}
        for player in group:
            key=tuple(sorted((r for actor,r in records if actor==player),key=repr))
            split.setdefault(key,[]).append(player)
        result.extend(tuple(v) for v in split.values())
    return tuple(result)
