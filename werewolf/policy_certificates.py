"""Bounded exact certificates under the EXISTING uniform-best-response rule.

This module never chooses a profile from an incomplete or ambiguous search.
It does not add arbitrary mixtures, off-path beliefs or new payoff models.
"""
from dataclasses import dataclass
from fractions import Fraction as F
from itertools import combinations,product
from .policy_choice import optimal_targets,uniform_policy
from .calculation_budget import calculation_budget,tick,CalculationBudgetExceeded
from .information_set_forecast import Pending


@dataclass(frozen=True)
class ProfileCertificate:
    profile: tuple
    scores: tuple


@dataclass(frozen=True)
class ProfileIssue:
    profile: tuple
    kind: str
    reason: str


@dataclass(frozen=True)
class ProfileSearch:
    status: str
    total: int
    evaluated: int
    certified: tuple = ()
    issues: tuple = ()
    reason: str | None = None
    proof: str = "exhaustive"

    @property
    def selected(self):
        # A proved candidate is not a license to fill undefined alternatives.
        return self.certified[0] if self.status=='unique' else None


def uniform_options(actions):
    actions=tuple(actions)
    if not actions or len(set(actions))!=len(actions):raise ValueError('Unique nonempty legal actions required')
    return tuple(uniform_policy(selected) for n in range(1,len(actions)+1)
                 for selected in combinations(actions,n))


def best_response_profile(legal,scores,*,maximize=False):
    if set(scores)!={info for info,actions in legal}:raise ValueError('Complete infoset scores required')
    rows=[];expected=[]
    for info,actions in legal:
        row=tuple(scores[info])
        if (len(row)!=len(actions) or len({a for a,v in row})!=len(row) or
            {a for a,v in row}!=set(actions) or
            any(type(v) not in (int,F) or not 0<=v<=1 for a,v in row)):
            raise ValueError('Complete exact legal score vectors required')
        values=dict(row);row=tuple((a,F(values[a])) for a in actions)
        rows.append((info,row))
        direction=maximize[info] if isinstance(maximize,dict) else maximize
        expected.append((info,uniform_policy(optimal_targets(row,maximize=direction))))
    return tuple(expected),tuple(rows)


def certify_uniform_profiles(legal,evaluate,*,maximize=False,max_profiles=4096,
                             max_work=250000,max_seconds=20):
    """Evaluate every complete profile and every legal deviation exactly.

    evaluate(profile) must use that SAME complete public profile for all rows.
    Undefined/unsupported candidates remain separate issues, never fake scores.
    """
    legal=tuple((info,tuple(actions)) for info,actions in legal)
    if not legal or len({i for i,a in legal})!=len(legal):raise ValueError('Unique nonempty infosets required')
    if type(max_profiles)is not int or max_profiles<1:raise ValueError('Positive profile limit required')
    total=1
    for info,actions in legal:
        if not actions or len(set(actions))!=len(actions):raise ValueError('Unique nonempty legal actions required')
        total*=(1<<len(actions))-1
    if total>max_profiles:return ProfileSearch('budget_unfinished',total,0,reason='profile_count_limit')
    if (type(maximize)is not bool and not isinstance(maximize,dict) or
        isinstance(maximize,dict) and (set(maximize)!={info for info,actions in legal} or
                                      any(type(v)is not bool for v in maximize.values()))):
        raise ValueError('Explicit objective for every infoset required')
    options=tuple(uniform_options(actions) for info,actions in legal)
    certificates=[];issues=[];evaluated=0
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            for choices in product(*options):
                tick();profile=tuple((info,choice) for (info,actions),choice in zip(legal,choices))
                try:
                    scores=evaluate(profile)
                except Pending as error:
                    kind=('undefined_observation' if error.reason in (
                        'public_generated_observation_zero_support','root_guard_profile_undefined_observations',
                        'public_continuation_zero_support','public_terminal_observation_zero_support',
                        'root_secret_public_history_zero_support',
                        'root_secret_physical_zero_support','root_secret_actor_belief_zero_support')
                        else 'unresolved_dependency')
                    issues.append(ProfileIssue(profile,kind,error.reason));evaluated+=1;continue
                expected,rows=best_response_profile(legal,scores,maximize=maximize)
                if expected==profile:certificates.append(ProfileCertificate(profile,rows))
                evaluated+=1
    except CalculationBudgetExceeded:
        return ProfileSearch('budget_unfinished',total,evaluated,tuple(certificates),tuple(issues),
                             reason='calculation_budget_exceeded')
    if any(i.kind=='unresolved_dependency' for i in issues):status='dependency_unfinished'
    elif any(i.kind=='undefined_observation' for i in issues):status='undefined_observations'
    elif len(certificates)>1:status='multiple'
    elif certificates:status='unique'
    else:status='no_admissible_profile'
    return ProfileSearch(status,total,evaluated,tuple(certificates),tuple(issues))
