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
    guards: tuple = ()
    attacks: tuple = ()

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
        from .guard_effect import GuardIntent
        from .night_knowledge import WolfAttack
        if type(self.guards)is not tuple or type(self.attacks)is not tuple:
            raise ValueError('Immutable private night records required')
        for g in self.guards:
            if (not isinstance(g,GuardIntent) or any(type(x)is not int or x<1 for x in (g.night,g.actor,g.target))
                    or g.actor==g.target or not self.roles[3]&(1<<(g.actor-1))):
                raise ValueError('Guard history must belong to the true guardian')
        if any(not isinstance(a,WolfAttack) for a in self.attacks):raise ValueError('Invalid attack records')
        if len({g.night for g in self.guards})!=len(self.guards) or len({a.night for a in self.attacks})!=len(self.attacks):
            raise ValueError('One personal action per night')
        from .joint_value_sharing import share_hypothesis_records
        share_hypothesis_records(self)


def normalize(entries):
    from .guard_effect import GuardIntent
    from .night_knowledge import WolfAttack
    grouped={};originals={}
    for h in entries:
        key=(h.roles,h.acquisitions,h.guards,h.attacks)
        grouped[key]=grouped.get(key,Fraction())+h.mass;originals.setdefault(key,h)
    total=sum(grouped.values(),Fraction())
    if not total:raise ValueError('No compatible acquisition/report hypothesis')
    result=[]
    for key,q in sorted(grouped.items()):
        roles,records,guards,attacks=key;mass=q/total;original=originals[key]
        # Already-validated immutable data need no second constructor pass when
        # normalization changes NOTHING. Unknown/subclass/mutable inputs keep
        # the original full validation; no history or positive mass is invented.
        reusable=(type(original)is Hypothesis and type(mass)is Fraction and
            type(original.mass)is Fraction and mass==original.mass and
            type(roles)is tuple and type(records)is tuple and type(guards)is tuple and type(attacks)is tuple and
            all(type(a)is Acquisition and type(a.color)is str for a in records) and
            all(type(g)is GuardIntent for g in guards) and all(type(a)is WolfAttack for a in attacks))
        result.append(original if reusable else Hypothesis(roles,records,mass,guards,attacks))
    return tuple(result)


def from_board(board):
    return tuple(Hypothesis(world[:-1],(),world[-1]) for world in board.worlds)


def public_worlds(entries):
    """Marginalize secrets before public decision making, preserving role correlation."""
    grouped={}
    for h in entries:grouped[h.roles]=grouped.get(h.roles,Fraction())+h.mass
    return tuple((*roles,q) for roles,q in sorted(grouped.items()))


def acquire(entries, day, alive, targets, *, target_players=None):
    """Apply one already chosen common instruction; do not optimize inside worlds.

    targets supplies every possible live seer position, including latent ones.
    The visible action selector must supply it without inspecting entries.
    """
    if type(day) is not int or day<1 or len(set(alive))!=len(alive):raise ValueError('Invalid acquisition opportunity')
    legal=tuple(alive)if target_players is None else tuple(target_players)
    if any(type(p)is not int or p<1 for p in legal)or len(set(legal))!=len(legal):raise ValueError('Original target roster required')
    possible={p for h in entries for p in alive if h.roles[2] & (1<<(p-1))}
    if not possible<=set(targets) or any(targets[p] not in legal or targets[p]==p for p in possible):
        raise ValueError('Target must be another original player; corpses are legal')
    result=[]
    for h in entries:
        players=tuple(p for p in alive if h.roles[2] & (1<<(p-1)))
        if any(a.day==day and a.player in players for a in h.acquisitions):raise ValueError('Acquisition already recorded')
        records=tuple(Acquisition(day,p,targets[p],'black' if h.roles[0] & (1<<(targets[p]-1)) else 'white') for p in players)
        result.append(Hypothesis(h.roles,tuple(sorted(h.acquisitions+records)),h.mass,h.guards,h.attacks))
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
            result.append(Hypothesis(h.roles,tuple(sorted(h.acquisitions+records)),h.mass/count,h.guards,h.attacks))
    return normalize(result)


def publication_support(entries, reports):
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
    return tuple(compatible)


def condition_publications(entries,reports):
    return normalize(publication_support(entries,reports))
