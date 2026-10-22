"""Sufficient public roll bound; no recursive search and no policy fabrication.

Day invariant n-2|C|>=1 is preserved by executing C and at most one night death.
Only value is certified. Forced actions and complete MAX ties remain unknown.
"""
from dataclasses import dataclass
from .calculation_budget import tick

@dataclass(frozen=True)
class RollCertificate:
    candidates:tuple
    alive:int
    phase:str
    rule:str='public-roll-v1'

    def marker(self,day):
        # Worst-case one death per night; this is a roll budget, not a fake turn.
        executions=(self.alive-(1 if self.phase=='day' else 2))//2
        return dict(label=f'縄数{executions}狼位置数{len(self.candidates)}',
                    executions=executions,candidate_count=len(self.candidates),
                    day=day+(self.phase=='night'),phase='day')

def bound(candidates,alive,phase):
    candidates=tuple(sorted(candidates));n=len(alive)
    if phase not in ('day','night') or not candidates:return None
    if n < 2*len(candidates)+(1 if phase=='day' else 2):return None
    return RollCertificate(candidates,n,phase)

def certify(board,public,private,strategy,rules,observer=None):
    """Q determines policy; require full P support, including private relations.

    Fail closed for personal views, unsupported roles/rules or invalid mixtures.
    Historical policies are owned by the caller's immutable calculation.
    """
    if (not strategy.win_cutoff or strategy.day!='max' or observer is not None
        or board.winner is not None or board.initial_medium_count or board.initial_hunter_count
        or rules.allow_self_bite or strategy.include_self_bite):return None
    def key(h):return (h.roles,h.acquisitions,h.guards,h.attacks)
    tick(len(public.hypotheses))
    mask=0
    for h in public.hypotheses:
        if h.roles[1] or h.roles[3]:return None
        mask|=h.roles[0]
    result=bound((p for p in board.alive if mask&(1<<(p-1))),board.alive,board.phase)
    if result is None:return None
    tick(len(private.hypotheses))
    support={key(h) for h in public.hypotheses}
    return result if support and private.hypotheses and all(key(h) in support for h in private.hypotheses) else None

def certify_anonymous(b,enabled):
    if not enabled:return None
    tick(len(b.q.rows))
    candidates=set();living=set(p for g in b.groups for p in g)-{d.target for d in b.history}
    for mass,atom in b.q.rows:
        pop=atom.population;pin=dict(atom.pins);occupied=set(pin.values())
        if any(p.role not in ('wolf','seer','villager') for p in pop.people) or any(c.role not in ('wolf','seer','villager') for c in pop.cells):return None
        for name,ref in atom.pins:
            if name in living and pop.people[ref].role=='wolf':candidates.add(name)
        for index,group in enumerate(b.groups):
            possible=any(p.group==index and p.alive and p.role=='wolf' and ref not in occupied for ref,p in enumerate(pop.people)) or any(c.group==index and c.alive and c.role=='wolf' and c.count for c in pop.cells)
            if possible:candidates.update(p for p in group if p in living and p not in pin)
    result=bound(candidates,living,b.phase)
    if result is None:return None
    tick(len(b.p.rows))
    support={atom for mass,atom in b.q.rows}
    return result if support and b.p.rows and all(atom in support for mass,atom in b.p.rows) else None
