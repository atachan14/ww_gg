"""Unpublished true-seer kernel. No public route, fake policy, or win solver.

Generation probabilities here are distinct from manual compatibility filtering.
Acquisition roster is before night casualties; publication roster is morning.
"""
from .calculation_budget import DEFAULT_MAX_WORK, DEFAULT_MAX_SECONDS
from dataclasses import dataclass
from fractions import Fraction as F
from itertools import product
from .seer_acquisition import Acquisition, SeerReport, Hypothesis, normalize, public_worlds
from .calculation_budget import calculation_budget, tick, CalculationBudgetExceeded

@dataclass(frozen=True)
class FuturePending:
    reason: str

@dataclass(frozen=True)
class TrueScanState:
    hypotheses: tuple
    rosters: tuple = ()
    initial_rule: str = "random_white"
    tracked: tuple | None = None
    observed_prefix: int = 0 # User-Board ledger uses currently active declarations only.
    def __post_init__(self):
        if type(self.observed_prefix)is not int or not 0<=self.observed_prefix<=len(self.rosters):raise ValueError("Invalid observed acquisition prefix")
        if self.initial_rule not in ("normal","random_white","none"):raise ValueError("Initial GameRule required")
        if not self.hypotheses or any(not isinstance(h,Hypothesis) for h in self.hypotheses) or sum((h.mass for h in self.hypotheses),F())!=1:
            raise ValueError('Complete normalized joint hypotheses are required')
        if self.tracked is not None:validate_roster(self.tracked)
        for i,alive in enumerate(self.rosters):
            validate_roster(alive)
            if i and not set(alive)<=set(self.rosters[i-1]):raise ValueError('Acquisition roster cannot resurrect players')
        for h in self.hypotheses:
            for record in (*h.guards,*h.attacks):
                if record.night>=len(self.rosters) or record.target not in self.rosters[record.night]:
                    raise ValueError('Private night record lacks its acquisition roster')
                if hasattr(record,'actor') and record.actor not in self.rosters[record.night]:
                    raise ValueError('Guardian was not alive on the recorded night')
            for a in h.acquisitions:
                if self.tracked is not None and a.player not in self.tracked:raise ValueError('Acquisition owner is marginalized, not tracked')
                if a.day==1 and (self.initial_rule=='none' or self.initial_rule=='random_white' and a.color!='white'):raise ValueError('Initial acquisition violates GameRule')
                if a.day>len(self.rosters) or a.player not in self.rosters[a.day-1] or a.target not in self.rosters[a.day-1]:raise ValueError('Acquisition owner and target must be alive at night start')
            for day,alive in enumerate(self.rosters,1):
                expected={p for p in alive if h.roles[2]&(1<<(p-1)) and (self.tracked is None or p in self.tracked)} if day!=1 or self.initial_rule!='none' else set()
                actual={a.player for a in h.acquisitions if a.day==day}
                if day>self.observed_prefix and expected!=actual:raise ValueError('Missing own acquisition history cannot become unvisited')
        from .joint_value_sharing import share_hypothesis_tuple
        shared=share_hypothesis_tuple(self.hypotheses)
        if shared is not self.hypotheses:object.__setattr__(self,'hypotheses',shared)
    def __hash__(self):
        cached=self.__dict__.get('_hash_cache')
        if cached is not None:return cached
        value=hash((self.hypotheses,self.rosters,self.initial_rule,self.tracked,self.observed_prefix))
        # Frozen containers can still be constructed from mutable/subclass
        # inputs. Cache only the exact deeply immutable value representation.
        from .guard_effect import GuardIntent
        from .night_knowledge import WolfAttack
        immutable=(type(self)is TrueScanState and type(self.hypotheses)is tuple and
            type(self.rosters)is tuple and all(type(r)is tuple for r in self.rosters) and
            type(self.initial_rule)is str and (self.tracked is None or type(self.tracked)is tuple) and
            all(type(h)is Hypothesis and type(h.roles)is tuple and type(h.mass)is F and
                type(h.acquisitions)is tuple and type(h.guards)is tuple and type(h.attacks)is tuple and
                all(type(a)is Acquisition and type(a.color)is str for a in h.acquisitions) and
                all(type(g)is GuardIntent for g in h.guards) and all(type(a)is WolfAttack for a in h.attacks)
                for h in self.hypotheses))
        if immutable:object.__setattr__(self,'_hash_cache',value)
        return value
    def __getstate__(self):
        # Python string hashes differ between processes; never persist this
        # derived cache through pickle/copy. All mathematical fields survive.
        return {key:value for key,value in self.__dict__.items() if key!='_hash_cache'}
    @property
    def public_roles(self):
        cached=self.__dict__.get('_public_roles_cache')
        if cached is not None:return cached
        result=public_worlds(self.hypotheses)
        # Retain full immutable hypotheses; cache only this derived exact sum.
        # Noncanonical mutable caller inputs keep the uncached behavior.
        if type(self.hypotheses)is tuple and all(type(h)is Hypothesis and type(h.roles)is tuple
                                                for h in self.hypotheses):
            object.__setattr__(self,'_public_roles_cache',result)
        return result

def validate_roster(alive):
    if not isinstance(alive,tuple) or len(set(alive))!=len(alive) or any(type(p)is not int or not 1<=p<=9 for p in alive):raise ValueError('Explicit unique 1-9 player roster required')

def candidates(h,player,players):
    """Prefer own unvisited targets within the supplied night-start roster."""
    legal=tuple(sorted(p for p in players if p!=player))
    visited={a.target for a in h.acquisitions if a.player==player}
    preferred=tuple(p for p in legal if p not in visited)
    return preferred or legal

def acquire_uniform(state,alive,*,max_work=DEFAULT_MAX_WORK,position=('unvisited','uniform')):
    """Slot1: uniform nonwolf white; later slots: own-unvisited uniform targets.

    Every live true seer, including latent true seers, independently scans.
    No world is sampled and no instruction uses teammate private information.
    """
    if tuple(position)!=('unvisited','uniform'):raise ValueError('Unsupported ordered scan-position filters')
    validate_roster(alive)
    if state.rosters and not set(alive)<=set(state.rosters[-1]):raise ValueError('Acquisition roster cannot resurrect players')
    day=len(state.rosters)+1;entries=[];targets_roster=alive
    try:
        with calculation_budget(max_work):
            from .night_abilities import seer_paths
            for h in state.hypotheses:
                tick()
                try:rows=seer_paths(h,alive,day,state.initial_rule,position,tracked=state.tracked)
                except ValueError as error:return FuturePending(str(error))
                entries.extend(row.hypothesis for row in rows)
            tick(len(entries))
            return TrueScanState(normalize(entries),state.rosters+(alive,),state.initial_rule,state.tracked,state.observed_prefix)
    except CalculationBudgetExceeded:return FuturePending('true_scan_generation_budget_exceeded')

def true_reports(h,published,morning_alive,claims,day):
    """All unpublished obtained results of surviving true-seer CO players.

    This is a truth-side payload, never a complete public vector with fakes.
    """
    seen={(r.player,r.acquired_day) for r in published}
    return tuple(SeerReport(a.day,day,a.player,a.target,a.color) for a in h.acquisitions if a.player in morning_alive and claims[a.player-1]=='seer' and (a.player,a.day) not in seen)

@dataclass(frozen=True)
class TruthPublication:
    reports: tuple
    probability: F
    state: TrueScanState

def truth_only_publications(state,morning_alive,claims,published=(),*,max_work=DEFAULT_MAX_WORK):
    """Exact public outcomes only when no possible fake reporter is involved.

    Any possible fake keeps the whole result Pending, including multiple wolves;
    no independent coin, joint coordination, or knowledge set is assumed.
    """
    validate_roster(morning_alive)
    if not state.rosters:return FuturePending('acquisition_history_required')
    if not set(morning_alive)<=set(state.rosters[-1]):raise ValueError('Morning survivors must come from the night roster')
    if not isinstance(claims,tuple) or not 1<=len(claims)<=9 or len(claims)<max(morning_alive,default=0) or any(c not in ('latent','villager','seer','medium','hunter','wolf') for c in claims):raise ValueError('Public claims required')
    if not isinstance(published,tuple) or any(not isinstance(r,SeerReport) or r.published_day>len(state.rosters) for r in published):raise ValueError('Past publication records required')
    if len({(r.player,r.acquired_day) for r in published})!=len(published):raise ValueError('Duplicate published acquisition')
    for h in state.hypotheses:
        for report in published:
            # Past reports are already-observed evidence in the supplied prior.
            # A dead past fake does not require a retroactive generation policy.
            if not h.roles[2]&(1<<(report.player-1)):continue
            known=next((a for a in h.acquisitions if a.day==report.acquired_day and a.player==report.player),None)
            if known is None or (known.target,known.color)!=(report.target,report.color):raise ValueError('Past true publication must already be conditioned into the state')
        if any(claims[p-1]=='seer' and not h.roles[2]&(1<<(p-1)) for p in morning_alive):return FuturePending('fake_target_color_policy_and_wolf_shared_information_unselected')
    groups={}
    try:
        with calculation_budget(max_work):
            for h in state.hypotheses:
                tick(1+len(h.acquisitions))
                reports=true_reports(h,published,morning_alive,claims,len(state.rosters))
                groups.setdefault(reports,[]).append(h)
            result=[]
            for reports,entries in groups.items():
                tick(len(entries))
                mass=sum((h.mass for h in entries),F())
                result.append(TruthPublication(reports,mass,TrueScanState(normalize(entries),state.rosters,state.initial_rule,state.tracked,state.observed_prefix)))
            return tuple(sorted(result,key=lambda b:repr(b.reports)))
    except CalculationBudgetExceeded:return FuturePending('truth_publication_generation_budget_exceeded')
