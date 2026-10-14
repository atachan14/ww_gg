"""Separate Model A role mass from a supplied policy's physical owner law.

This enumerates an already selected information-set kernel; it neither selects
optimal actions nor supplies a policy or a counterfactual zero-support law.
The approved scope is one hunter, uniform nonself guards and repeat permission.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
from .guard_effect import GuardIntent,guard_blocks_attack
from .night_knowledge import WolfAttack,merge_night_records
from .seer_acquisition import normalize,Hypothesis
from .seer_future_uniform import FuturePending,TrueScanState,validate_roster


@dataclass(frozen=True)
class GuardHistoryMixture:
    role_prior: tuple
    role_support: tuple
    zero_support_roles: tuple
    public: TrueScanState | FuturePending
    physical: TrueScanState | FuturePending
    physical_mass: F

    def _owner_view(self,predicate):
        if isinstance(self.physical,FuturePending):return self.physical
        entries=tuple(h for h in self.physical.hypotheses if predicate(h))
        if not entries:return FuturePending('guard_private_history_zero_support')
        return replace(self.physical,hypotheses=normalize(entries))

    def wolf_view(self,mask,attacks):
        known=merge_night_records((),attacks)
        return self._owner_view(lambda h:h.roles[0]==mask and
                                merge_night_records((),h.attacks)==known)

    def hunter_view(self,actor,guards):
        if type(actor)is not int or actor<1:raise ValueError('Positive hunter actor required')
        known=merge_night_records((),guards)
        return self._owner_view(lambda h:bool(h.roles[3]&(1<<(actor-1))) and
                                merge_night_records((),h.guards)==known)


def enumerate_guard_history_mixture(source,role_prior,night,alive,policies,*,deaths=()):
    """Observe one night, preserving external public role mass exactly.

    `source` is the full physical world/history law, not a viewer restriction.
    Its current acquisition roster must already be present. Each supplied
    policy is keyed only by (initial wolf roster, that roster's attack history).
    A policy never receives a guardian position, guard intent or secret scan.
    `role_prior` comes from the separately updated public Board. Each supported
    world gets its conditional history law; any zero-support world makes the
    complete public mixture pending, without changing the requested role mass.
    """
    validate_roster(alive)
    alive_mask=sum(1<<(p-1) for p in alive)
    if type(night)is not int or night<1 or night>=len(source.rosters) or source.rosters[night]!=alive:
        raise ValueError('Current original acquisition roster required')
    if type(deaths)is not tuple or len(deaths)>1 or any(p not in alive for p in deaths):
        raise ValueError('Zero or one observed attack death required')
    prior=tuple(sorted(role_prior));weights={}
    for world in prior:
        if len(world)!=5:raise ValueError('Exact public role prior required')
        Hypothesis(world[:-1],(),world[-1])
        if world[:-1] in weights:raise ValueError('Duplicate public role world')
        weights[world[:-1]]=world[-1]
    if sum(weights.values(),F())!=1:raise ValueError('Normalized public role prior required')
    parent={};raw={};checked={}
    for h in source.hypotheses:
        if h.roles not in weights:continue  # Support removed by the public Board itself.
        parent[h.roles]=parent.get(h.roles,F())+h.mass
        if not h.roles[0]&alive_mask:raise ValueError('Living wolf required')
        if h.roles[3].bit_count()!=1:raise ValueError('Exactly one initial hunter required')
        if any(r.night==night for r in (*h.guards,*h.attacks)):
            raise ValueError('Night already recorded')
        info=(h.roles[0],h.attacks)
        if info not in checked:
            if info not in policies:raise ValueError('Missing explicit wolf information-set policy')
            policy=policies[info]
            if (not policy or len({p for p,q in policy})!=len(policy) or
                any(type(p)is not int or p not in alive or h.roles[0]&(1<<(p-1)) or
                    not isinstance(q,F) or q<=0 for p,q in policy) or
                sum((q for p,q in policy),F())!=1):
                raise ValueError('Normalized exact legal nonself-bite policy required')
            checked[info]=policy
        actor=next((p for p in alive if h.roles[3]&(1<<(p-1))),None)
        guards=((None,F(1)),) if actor is None else tuple((GuardIntent(night,actor,p),F(1,len(alive)-1))
                                                         for p in alive if p!=actor)
        for attack,qa in checked[info]:
            for intent,qg in guards:
                blocked=intent is not None and guard_blocks_attack(intent,attack)
                if deaths!=(() if blocked else (attack,)):continue
                recorded=replace(h,mass=h.mass*qa*qg,
                                 guards=h.guards+((intent,) if intent is not None else ()),
                                 attacks=h.attacks+(WolfAttack(night,attack),))
                raw.setdefault(h.roles,[]).append(recorded)
    totals={roles:sum((h.mass for h in raw.get(roles,())),F()) for roles in weights}
    zero=tuple(roles for roles in weights if not totals[roles])
    support=tuple((roles,totals[roles]/parent[roles] if parent.get(roles) else F()) for roles in weights)
    entries=tuple(h for hs in raw.values() for h in hs)
    mass=sum((h.mass for h in entries),F())
    physical=(replace(source,hypotheses=normalize(entries)) if mass else
              FuturePending('guard_physical_history_zero_support'))
    if zero:
        public=FuturePending('guard_public_history_zero_support')
    else:
        weighted=tuple(replace(h,mass=weights[roles]*h.mass/totals[roles])
                       for roles,hs in raw.items() for h in hs)
        public=replace(source,hypotheses=normalize(weighted))
        if public.public_roles!=prior:raise ValueError('Public role mass changed')
    return GuardHistoryMixture(prior,support,zero,public,physical,mass)
