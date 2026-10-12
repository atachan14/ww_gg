"""Exact acquisition records, independent of public-only action selection.

No member is selected as a real world. Every entry remains a weighted hypothesis.
The caller owns public Board projection and the action/report policy.
"""
from dataclasses import dataclass
from fractions import Fraction
from itertools import product


@dataclass(frozen=True, order=True)
class Acquisition:
    """Result-slot day: 1 is initial; night N produces slot N+1.

    It is not a claim that publication occurred on that day.
    """
    day: int
    player: int
    target: int
    color: str

    def __post_init__(self):
        if any(type(v) is not int or v < 1 for v in (self.day,self.player,self.target)) or self.player == self.target or self.color not in ('white','black'):
            raise ValueError('Invalid seer acquisition')


@dataclass(frozen=True, order=True)
class SeerReport:
    acquired_day: int
    published_day: int
    player: int
    target: int
    color: str

    def __post_init__(self):
        Acquisition(self.acquired_day,self.player,self.target,self.color)
        if type(self.published_day) is not int or self.published_day < self.acquired_day:
            raise ValueError('Publication cannot precede acquisition')


@dataclass(frozen=True)
class Hypothesis:
    roles: tuple[int,int,int,int]
    acquisitions: tuple[Acquisition,...]
    mass: Fraction

    def __post_init__(self):
        if len(self.roles)!=4 or any(type(m) is not int or m<0 for m in self.roles) or any(a&b for i,a in enumerate(self.roles) for b in self.roles[i+1:]):
            raise ValueError('Invalid joint role masks')
        if not isinstance(self.mass,Fraction) or self.mass<=0:
            raise ValueError('Use positive exact mass')
        if len({(a.day,a.player) for a in self.acquisitions})!=len(self.acquisitions):
            raise ValueError('One acquisition per player and day')
        for a in self.acquisitions:
            if not self.roles[2] & (1<<(a.player-1)) or (a.color=='black') != bool(self.roles[0] & (1<<(a.target-1))):
                raise ValueError('Acquisition must agree with joint roles')


def normalize(entries):
    grouped={}
    for h in entries:
        key=(h.roles,h.acquisitions)
        grouped[key]=grouped.get(key,Fraction())+h.mass
    total=sum(grouped.values(),Fraction())
    if not total:raise ValueError('No compatible acquisition/report hypothesis')
    return tuple(Hypothesis(roles,records,q/total) for (roles,records),q in sorted(grouped.items()))


def from_board(board):
    return tuple(Hypothesis(world[:-1],(),world[-1]) for world in board.worlds)


def public_worlds(entries):
    """Marginalize secrets before public decision making, preserving role correlation."""
    grouped={}
    for h in entries:grouped[h.roles]=grouped.get(h.roles,Fraction())+h.mass
    return tuple((*roles,q) for roles,q in sorted(grouped.items()))


def acquire(entries, day, alive, targets):
    """Apply one already chosen common instruction; do not optimize inside worlds.

    targets supplies every possible live seer position, including latent ones.
    The visible action selector must supply it without inspecting entries.
    """
    if type(day) is not int or day<1 or len(set(alive))!=len(alive):raise ValueError('Invalid acquisition opportunity')
    possible={p for h in entries for p in alive if h.roles[2] & (1<<(p-1))}
    if not possible<=set(targets) or any(targets[p] not in alive or targets[p]==p for p in possible):
        raise ValueError('Target must be another player alive on that night')
    result=[]
    for h in entries:
        players=tuple(p for p in alive if h.roles[2] & (1<<(p-1)))
        if any(a.day==day and a.player in players for a in h.acquisitions):raise ValueError('Acquisition already recorded')
        records=tuple(Acquisition(day,p,targets[p],'black' if h.roles[0] & (1<<(targets[p]-1)) else 'white') for p in players)
        result.append(Hypothesis(h.roles,tuple(sorted(h.acquisitions+records)),h.mass))
    return normalize(result)


def initial_random_white(entries, alive):
    """Enumerate all independent uniform white-target draws jointly with roles.

    This reference kernel is deliberately unoptimized; callers must benchmark
    before using it for larger casts. No random generator is used.
    """
    result=[]
    for h in entries:
        players=tuple(p for p in alive if h.roles[2] & (1<<(p-1)))
        if any(a.day==1 for a in h.acquisitions):raise ValueError('Initial acquisition already recorded')
        choices=tuple(tuple(t for t in alive if t!=p and not h.roles[0] & (1<<(t-1))) for p in players)
        if any(not c for c in choices):raise ValueError('No other non-wolf initial target')
        count=1
        for options in choices:count*=len(options)
        for targets in product(*choices):
            records=tuple(Acquisition(1,p,t,'white') for p,t in zip(players,targets))
            result.append(Hypothesis(h.roles,tuple(sorted(h.acquisitions+records)),h.mass/count))
    return normalize(result)


def condition_publications(entries, reports):
    """Hand input is a truth-support filter; fake reporting policy is separate.

    Eligibility (CO, life, timing, permitted target) is the caller's concern.
    Reapply to an acquisition baseline for edits, never to a previous posterior.
    """
    keys=[(r.acquired_day,r.player) for r in reports]
    if len(set(keys))!=len(keys):raise ValueError('Duplicate acquisition report')
    compatible=[]
    for h in entries:
        known={(a.day,a.player):(a.target,a.color) for a in h.acquisitions}
        if all(not h.roles[2] & (1<<(r.player-1)) or known.get((r.acquired_day,r.player))==(r.target,r.color) for r in reports):
            compatible.append(h)
    return normalize(compatible)
