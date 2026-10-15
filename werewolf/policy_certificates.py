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
                             max_work=250000,max_seconds=20,stop_on_undefined=False):
    """Evaluate every complete profile and every legal deviation exactly.

    evaluate(profile) must use that SAME complete public profile for all rows.
    Undefined/unsupported candidates remain separate issues, never fake scores.
    stop_on_undefined permits early REFUSAL from a witnessed required candidate;
    its proof metadata/evaluated count never claim the other profiles finished.
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
                    issues.append(ProfileIssue(profile,kind,error.reason));evaluated+=1
                    if stop_on_undefined and kind=='undefined_observation':
                        # One required but undefined candidate is enough to
                        # refuse a numeric result. This is witness evidence,
                        # not a claim to have classified every other profile.
                        return ProfileSearch('undefined_observations',total,evaluated,
                            tuple(certificates),tuple(issues),reason='undefined_candidate_witness',
                            proof='undefined_witness')
                    continue
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


def certify_support_profiles(legal,evaluate,contributions,forced,*,maximize=False,
                             max_profiles=4096,max_work=250000,max_seconds=20):
    """Exact quotient of ALL uniform profiles by a proved OR-support signature.

    Caller proves complete candidate scores depend only on this signature.
    Every local uniform policy must be supplied. DP retains its multiplicity
    and a complete witness. A class has at most one admissible profile: its
    uniform best response, which must map back to that same class.
    """
    legal=tuple((i,tuple(actions)) for i,actions in legal);total=1
    if not legal or len({i for i,a in legal})!=len(legal):raise ValueError('Unique nonempty infosets required')
    if type(max_profiles)is not int or max_profiles<1:raise ValueError('Positive profile limit required')
    if (type(maximize)is not bool and not isinstance(maximize,dict) or
        isinstance(maximize,dict) and (set(maximize)!={info for info,actions in legal} or
                                      any(type(v)is not bool for v in maximize.values()))):
        raise ValueError('Explicit objective for every infoset required')
    tables={};options={};dimensions=len(forced)
    if not dimensions or any(type(x)is not int or x<0 for x in forced):
        raise ValueError('Nonnegative complete support signature required')
    for info,actions in legal:
        policies=uniform_options(actions);total*=len(policies)
        rows=contributions[info]
        if (len(rows)!=len(policies) or {p for p,delta in rows}!=set(policies) or
            any(len(delta)!=dimensions or any(type(x)is not int or x<0 for x in delta)
                for policy,delta in rows)):
            raise ValueError('Every legal uniform policy contribution required')
        tables[info]=dict(rows);grouped={}
        for policy,delta in rows:
            count,witness=grouped.get(delta,(0,policy));grouped[delta]=(count+1,witness)
        options[info]=tuple((delta,count,policy) for delta,(count,policy) in grouped.items())
    if set(contributions)!={i for i,a in legal}:raise ValueError('Complete infoset contributions required')
    def signature(profile):
        key=forced
        for info,policy in profile:
            key=tuple(a|b for a,b in zip(key,tables[info][policy]))
        return key
    evaluated=0;certificates=[];issues=[]
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            states={forced:(1,())}
            for info,actions in legal:
                following={}
                for key,(count,witness) in states.items():
                    for delta,multiplicity,policy in options[info]:
                        tick();updated=tuple(a|b for a,b in zip(key,delta))
                        old_count,old_witness=following.get(updated,(0,witness+((info,policy),)))
                        following[updated]=(old_count+count*multiplicity,old_witness)
                if len(following)>max_profiles:
                    return ProfileSearch('budget_unfinished',total,0,reason='support_partition_limit',
                                         proof='support_partition')
                states=following
            if sum(count for count,witness in states.values())!=total:
                raise ValueError('Incomplete support partition')
            for key,(count,witness) in states.items():
                tick()
                try:scores=evaluate(witness)
                except Pending as error:
                    undefined=error.reason in ('public_generated_observation_zero_support',
                        'root_guard_profile_undefined_observations','public_continuation_zero_support',
                        'public_terminal_observation_zero_support','root_secret_public_history_zero_support',
                        'root_secret_physical_zero_support','root_secret_actor_belief_zero_support')
                    issues.append(ProfileIssue(witness,'undefined_observation' if undefined else
                        'unresolved_dependency',error.reason));evaluated+=count
                    return ProfileSearch('undefined_observations' if undefined else 'dependency_unfinished',
                        total,evaluated,tuple(certificates),tuple(issues),reason=error.reason,
                        proof='support_partition')
                expected,rows=best_response_profile(legal,scores,maximize=maximize)
                if signature(expected)==key:certificates.append(ProfileCertificate(expected,rows))
                evaluated+=count
    except CalculationBudgetExceeded:
        return ProfileSearch('budget_unfinished',total,evaluated,tuple(certificates),tuple(issues),
                             reason='calculation_budget_exceeded',proof='support_partition')
    status='multiple' if len(certificates)>1 else 'unique' if certificates else 'no_admissible_profile'
    return ProfileSearch(status,total,evaluated,tuple(certificates),proof='support_partition')


def certify_dependency_profiles(legal,evaluate_rows,dependencies,*,maximize=False,
                                max_profiles=4096,max_work=250000,max_seconds=20):
    """Eliminate necessary best-response equations without restricting profiles.

    Caller proves each COMPLETE row depends only on the listed policy rows.
    SCCs are processed after their dependencies. In each SCC an independent
    block is uniquely forced by the remaining assignment; asymmetric responses
    stay separate. All legal candidates of each retained profile are computed.
    """
    legal=tuple((i,tuple(a)) for i,a in legal);infos=tuple(i for i,a in legal)
    if not legal or len(set(infos))!=len(infos) or set(dependencies)!=set(infos):
        raise ValueError('Complete unique dependency inputs required')
    if type(max_profiles)is not int or max_profiles<1:raise ValueError('Positive profile limit required')
    if any(not set(d)<=set(infos) for d in dependencies.values()):raise ValueError('Unknown dependency')
    if (type(maximize)is not bool and not isinstance(maximize,dict) or isinstance(maximize,dict) and
        (set(maximize)!=set(infos) or any(type(v)is not bool for v in maximize.values()))):
        raise ValueError('Explicit objective for every infoset required')
    options={i:uniform_options(a) for i,a in legal};total=1
    for choices in options.values():total*=len(choices)
    # Tarjan emits a component only after its outgoing dependencies.
    indices={};low={};stack=[];active=set();components=[]
    def visit(i):
        indices[i]=low[i]=len(indices);stack.append(i);active.add(i)
        for d in infos:
            if d not in dependencies[i]:continue
            if d not in indices:visit(d);low[i]=min(low[i],low[d])
            elif d in active:low[i]=min(low[i],indices[d])
        if low[i]==indices[i]:
            members=set()
            while True:
                d=stack.pop();active.remove(d);members.add(d)
                if d==i:break
            components.append(tuple(d for d in infos if d in members))
    for i in infos:
        if i not in indices:visit(i)
    def subset_legal(members):return tuple((i,a) for i,a in legal if i in members)
    def direction(members):return {i:maximize[i] for i in members} if isinstance(maximize,dict) else maximize
    states=[({}, {})];work=0
    try:
        with calculation_budget(max_work,max_seconds=max_seconds):
            for component in components:
                blocks=[()]
                for seed in component:
                    if seed in dependencies[seed]:continue
                    block=[seed]
                    for i in component:
                        if i not in block and not set(dependencies[i])&set((*block,i)) and all(i not in dependencies[d] for d in block):block.append(i)
                    blocks.append(tuple(block))
                def size(block):
                    n=1
                    for i in block:n*=len(options[i])
                    return n
                eliminated=max(blocks,key=size);feedback=tuple(i for i in component if i not in eliminated)
                count=1
                for i in feedback:count*=len(options[i])
                if work+count*len(states)>max_profiles:
                    return ProfileSearch('budget_unfinished',total,0,reason='dependency_feedback_limit',proof='dependency_elimination')
                following=[]
                for assigned,known_scores in states:
                    for choices in product(*(options[i] for i in feedback)):
                        tick();work+=1
                        values={i:uniform_policy(a) for i,a in legal};values.update(assigned)
                        values.update(zip(feedback,choices));profile=tuple((i,values[i]) for i in infos)
                        if eliminated:
                            scores=evaluate_rows(profile,eliminated)
                            forced,_=best_response_profile(subset_legal(eliminated),scores,maximize=direction(eliminated))
                            values.update(forced)
                        profile=tuple((i,values[i]) for i in infos)
                        scores=evaluate_rows(profile,component)
                        expected,rows=best_response_profile(subset_legal(component),scores,maximize=direction(component))
                        if all(values[i]==p for i,p in expected):
                            accepted=dict(assigned);accepted.update((i,values[i]) for i in component)
                            complete=dict(known_scores);complete.update(rows);following.append((accepted,complete))
                states=following
                if not states:break
    except Pending as error:
        undefined=error.reason in ('public_generated_observation_zero_support','root_guard_profile_undefined_observations',
            'public_continuation_zero_support','public_terminal_observation_zero_support',
            'root_secret_public_history_zero_support','root_secret_physical_zero_support','root_secret_actor_belief_zero_support')
        return ProfileSearch('undefined_observations' if undefined else 'dependency_unfinished',total,0,
            issues=(ProfileIssue(profile,'undefined_observation' if undefined else 'unresolved_dependency',error.reason),),
            reason=error.reason,proof='dependency_elimination')
    except CalculationBudgetExceeded:
        return ProfileSearch('budget_unfinished',total,0,reason='calculation_budget_exceeded',proof='dependency_elimination')
    certificates=tuple(ProfileCertificate(tuple((i,values[i]) for i in infos),tuple((i,scores[i]) for i in infos))
                       for values,scores in states)
    status='multiple' if len(certificates)>1 else 'unique' if certificates else 'no_admissible_profile'
    return ProfileSearch(status,total,total,certificates,proof='dependency_elimination')
