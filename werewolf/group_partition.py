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
    return _public_groups(groups,source.public,source.past)


def _public_groups(groups,board,past):
    records=[(r.player,('seer',r.acquired_day,r.published_day,'day',r.target,r.color)) for r in past]
    records.extend((r.reporter,('medium',r.day,r.day,'day',r.target,r.color)) for r in board.reports)
    records.extend((actor,('opportunity',day,day,'day',target,None)) for day,actor,target in getattr(board,'medium_opportunities',()))
    records.extend((actor,('resolved',day,day,'day',target,None)) for day,actor,target in board.report_resolved)
    fixed={record[4] for _,record in records}
    result=[]
    for group in _fix(groups,fixed):
        split={}
        for player in group:
            key=tuple(sorted((r for actor,r in records if actor==player),key=repr))
            split.setdefault(key,[]).append(player)
        result.extend(tuple(v) for v in split.values())
    return tuple(result)


def _frame_groups(groups,board,past,observer=None,*,target=None):
    """Monotone public/action/owner refinement at every scalar entry.

    Inputs are common generated frames, not marginally inferred automorphisms.
    No law scan, authentication or merging of previously separated classes.
    """
    from .actor_information import PersonalInformation,GuardInformation,GuardSelection,information_positions
    from .seer_intervention import SeerObserver
    if observer is not None and type(observer) not in (PersonalInformation,SeerObserver,GuardInformation,GuardSelection):return ()
    fixed={event.target for event in board.history}
    fixed.update(p for p in range(1,board.player_count+1) if p not in board.alive)
    if target is not None:fixed.add(target)
    if observer is not None:fixed.update(information_positions(observer,board.player_count))
    return _fix(_public_groups(groups,board,past),fixed)
