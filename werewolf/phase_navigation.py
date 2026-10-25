"""Footer phase navigation over existing occurrence ancestry, not solver states."""
from collections import deque

def phase_targets(game):
    history=game.history;slots={}
    def slot(row):
        if row.key not in slots:
            b=history.state(row.key).source.public
            slots[row.key]=2*(b.day-1)+(b.phase=='night')
        return slots[row.key]
    current=game.occurrence;here=slot(current);previous=None
    for row in reversed(history.path(current.key)[:-1]):
        value=slot(row)
        if value==here-1:previous=row;break
        if value<here-1:break
    candidates=[];updates=[];pending=deque(history.children(current.key))
    while pending:
        row=pending.popleft();value=slot(row)
        if value not in (here,here+1):continue
        if value==here+1:
            candidates.append(row)
            if row.parent is not None and slot(history.occurrence(row.parent))==value and row.selector.get('kind') not in ('action','advance'):
                updates.append(row)
        pending.extend(history.children(row.key))
    # Occurrence IDs are validated append-order IDs on both creation/restore.
    following=max(updates or candidates,key=lambda row:int(row.key[1:]),default=None)
    def metadata(row):
        if row is None:return None
        b=history.state(row.key).source.public
        return dict(key=row.key,day=b.day,phase=b.phase)
    return dict(previous=metadata(previous),next=metadata(following))

def phase_back(game):
    previous=phase_targets(game)['previous']
    return game.move(previous['key']) if previous else game.occurrence

def phase_next(game,target,*,reuse_forward=True,outcome=None):
    following=phase_targets(game)['next']
    if reuse_forward and following:return game.move(following['key'])
    if reuse_forward:
        from .navigation_current import NavigationCurrent
        automatic=NavigationCurrent(game).automatic_update()
        if automatic:game.published(automatic['night'],automatic['route'])
    # Only the existing explicit action creates a missing next phase. Merely
    # asking for targets never builds/evaluates a future Board.
    return game.action(target,outcome=outcome)
