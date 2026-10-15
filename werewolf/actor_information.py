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
