"""Condition actor views and aggregate wolf information before policy choice.

No true guardian, other actor's scan or current observer intervention enters
the key. Public policy beliefs and actual branch masses remain separate inputs.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from .night_knowledge import WolfAttack,merge_night_records
from .seer_acquisition import normalize


def condition_actor_state(state,compatible,*,guards=(),attacks=()):
    """Condition an existing joint law; never generate missing history mass.

    Callers own the observation predicate and its support checks. All roles,
    scan results, other actors' records and state metadata survive. Explicit
    owner records are merged only after compatibility has been established.
    """
    entries=tuple(replace(h,
                  guards=merge_night_records(h.guards,guards) if guards else h.guards,
                  attacks=merge_night_records(h.attacks,attacks) if attacks else h.attacks)
                  for h in state.hypotheses if compatible(h))
    return replace(state,hypotheses=normalize(entries))


@dataclass(frozen=True)
class WolfInformation:
    initial_roster: int
    attacks: tuple = ()

    def __post_init__(self):
        if type(self.initial_roster)is not int or self.initial_roster<0:
            raise ValueError('Initial wolf mask required')
        if type(self.attacks)is not tuple or any(not isinstance(a,WolfAttack) for a in self.attacks):
            raise ValueError('Immutable wolf-owned attack records required')
        object.__setattr__(self,'attacks',merge_night_records((),self.attacks))

    @classmethod
    def from_hypothesis(cls,h):return cls(h.roles[0],h.attacks)

    def condition_public(self,state):
        known={a.night:a.target for a in self.attacks}
        compatible=lambda h:h.roles[0]==self.initial_roster and all(known.get(a.night)==a.target for a in h.attacks)
        if not any(compatible(h) for h in state.hypotheses):
            raise ValueError('Wolf information outside public support')
        return condition_actor_state(state,compatible,attacks=self.attacks)


def wolf_information_groups(state):
    """Return (owned information, actual mass, conditional branch law)."""
    groups={}
    for h in state.hypotheses:groups.setdefault(WolfInformation.from_hypothesis(h),[]).append(h)
    return tuple((info,sum((h.mass for h in hs),F()),replace(state,hypotheses=normalize(tuple(hs))))
                 for info,hs in groups.items())


def wolf_information_keys(state):
    """Owned keys only; fixed policies do not need conditional probability laws."""
    histories=dict.fromkeys((h.roles[0],h.attacks) for h in state.hypotheses)
    return tuple(dict.fromkeys(WolfInformation(mask,attacks) for mask,attacks in histories))


@dataclass(frozen=True)
class PersonalInformation:
    """Known owner role/results; no other actor's secret records."""
    actor:int
    role:str
    acquisitions:tuple=()

    def __post_init__(self):
        from .seer_acquisition import Acquisition
        if type(self.actor)is not int or self.actor<1 or self.role not in ('villager','medium','seer'):
            raise ValueError('Supported owner role and player required')
        if type(self.acquisitions)is not tuple or any(type(a)is not Acquisition or a.player!=self.actor for a in self.acquisitions):
            raise ValueError('Only owner acquisition records allowed')
        if self.acquisitions and self.role!='seer':raise ValueError('Only seer owns scan records')

    def __call__(self,h,state):
        bit=1<<(self.actor-1)
        owns=(not any(m&bit for m in h.roles)) if self.role=='villager' else bool(h.roles[{'medium':1,'seer':2}[self.role]]&bit)
        return owns and all(a in h.acquisitions for a in self.acquisitions)


def condition_personal(state,observation):
    """One semantic filtering pass, normalized complete histories and mass."""
    from .seer_intervention import SeerObserver
    if type(observation) not in (PersonalInformation,SeerObserver,WolfInformation):
        raise ValueError('Typed owner information required')
    if type(observation)is WolfInformation:
        known={a.night:a.target for a in observation.attacks}
        accepts=lambda h:h.roles[0]==observation.initial_roster and all(known.get(a.night)==a.target for a in h.attacks)
    else:accepts=lambda h:observation(h,state)
    entries=tuple(h for h in state.hypotheses if accepts(h))
    mass=sum((h.mass for h in entries),F())
    if not mass:raise ValueError('Owner information outside source support')
    if type(observation)is WolfInformation:
        entries=tuple(replace(h,attacks=merge_night_records(h.attacks,observation.attacks)) for h in entries)
    return mass,replace(state,hypotheses=normalize(entries))


def condition_wolf_choice(state,policies,target,*,compatible=lambda h:True):
    """Observed chosen target: retain actual w_I*q_I(t), then normalize P."""
    entries=tuple(replace(h,mass=h.mass*dict(policies[h.roles[0],h.attacks]).get(target,F()))
                  for h in state.hypotheses if compatible(h) and dict(policies[h.roles[0],h.attacks]).get(target,F())>0)
    mass=sum((h.mass for h in entries),F())
    if not mass:raise ValueError('Observed wolf choice outside support')
    return mass,replace(state,hypotheses=normalize(entries))


def wolf_information_orbits(state,partition):
    """Aggregate invariant wolf cells before building their conditional laws.

    Partitions are supplied only by the closed common generators. Recorded
    attack targets are fixed by them. Keep a complete representative joint
    law and sum actual mass over every image, never combine role marginals.
    """
    masks=tuple(sum(1<<(p-1) for p in group) for group in partition)
    buckets={}
    for h in state.hypotheses:
        mask=h.roles[0];key=(tuple((mask&part).bit_count() for part in masks),h.attacks)
        if key not in buckets:buckets[key]=[F(),mask,[]]
        row=buckets[key];row[0]+=h.mass
        if mask<row[1]:row[1]=mask;row[2]=[]
        if mask==row[1]:row[2].append(h)
    return tuple((WolfInformation(mask,attacks),mass,replace(state,hypotheses=normalize(tuple(entries))))
                 for (_,attacks),(mass,mask,entries) in buckets.items())


def information_positions(info,n):
    """Named owner evidence that a constructed partition must fix."""
    if type(info)is WolfInformation:
        return tuple(p for p in range(1,n+1) if info.initial_roster&(1<<(p-1)))+tuple(a.target for a in info.attacks)
    from .seer_intervention import SeerObserver
    return (info.actor,*(a.target for a in info.acquisitions),*((info.target,) if type(info)is SeerObserver else ()))
