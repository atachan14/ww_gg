"""Fixed-policy PUBLIC continuation with generated seer disclosures.

Manual past evidence is a supplied prior. Future fake probabilities use the
uniform candidate law conditioned on public truth compatibility.
Multiple-fake correlation remains unselected.
"""
from dataclasses import dataclass
from fractions import Fraction as F
from .exact import (replace_worlds,action_outcomes,legal_targets,report_actions,
                    random_report_outcomes,build_tree,evaluate_tree)
from .seer_acquisition import Hypothesis,normalize
from .seer_future_uniform import TrueScanState,FuturePending,acquire_uniform,true_reports
from .calculation_budget import calculation_budget,tick,CalculationBudgetExceeded

# Compatibility exports retain existing callers and historical tests.
from .morning_publications import (GeneratedPublication, fake_backlog_options,
    plausible_fake_options, future_publications, public_report_branches)


def project_private(state,board,*,marginalize_private=False):
    old=dict((r[:-1],r[-1]) for r in state.public_roles)
    new=dict((r[:-1],r[-1]) for r in board.worlds)
    tracked=tuple(p for p in board.alive if board.claims[p-1]=='seer' and (state.tracked is None or p in state.tracked)) if marginalize_private else state.tracked
    entries=tuple(Hypothesis(h.roles,tuple(a for a in h.acquisitions if not marginalize_private or a.player in tracked),h.mass*new[h.roles]/old[h.roles]) for h in state.hypotheses if h.roles in new)
    return TrueScanState(normalize(entries),state.rosters,state.initial_rule,tracked,state.observed_prefix)

@dataclass(frozen=True)
class Forecast:
    village_win: F
    action_values: tuple
    by_dawn_values: tuple = ()

class Unresolved(Exception):
    def __init__(self,pending):self.pending=pending


def forecast(board,state,past,rules,strategy,*,max_work=250000,trace=None,marginalize_known_fake=True,marginalize_private=True):
    """Fixed CO; existing public day/night choices; no private-world maximization.

    Truth acquisitions occur on the night roster before casualties. Survivors
    publish at morning. Existing medium report policy is preserved; its fixed
    instruction is chosen before generated seer disclosure and public decisions.
    """
    if state.public_roles!=tuple(sorted(board.worlds)):raise ValueError('Private joint marginal must match the public Board')
    if board.winner is not None:return Forecast(F(int(board.winner=='village')),())
    if len(state.rosters)!=board.day:raise ValueError('Complete acquisition ledger through current day required')
    memo={};action_memo={};acquired_memo={}
    def checked(value):
        if isinstance(value,FuturePending):raise Unresolved(value)
        return value
    def morning(child,private,published):
        actions=report_actions(child) if strategy.disclosure_for('medium')=='all' else ()
        if not actions:
            groups=((F(1),child),)
            choices=(groups,)
        elif strategy.fake_reports=='random':choices=(tuple((o.probability,o.board) for o in random_report_outcomes(child)),)
        else:choices=tuple(tuple((o.probability,o.board) for o in a.outcomes) for a in actions)
        values=[]
        for outcomes in choices:
            total=F()
            for q,b in outcomes:
                p=project_private(private,b,marginalize_private=marginalize_private)
                co=tuple(i for i in b.alive if b.claims[i-1]=='seer')
                fake_sets=tuple(tuple(i for i in co if not h.roles[2]&(1<<(i-1))) for h in p.hypotheses)
                if any(len(fakes)>1 for fakes in fake_sets):raise Unresolved(FuturePending('multiple_fake_report_correlation_unselected'))
                known_fake=tuple(i for i in co if all(i in fakes for fakes in fake_sets))
                if marginalize_known_fake and len(known_fake)==1:
                    # Its approved uniform law ignores roles. Marginalize this
                    # public noise: own fake history never affects truth scans,
                    # and CO/public action policies are fixed in this forecast.
                    groups={}
                    for h in p.hypotheses:
                        tick(1+len(h.acquisitions));r=true_reports(h,published,b.alive,b.claims,len(p.rosters));groups.setdefault(r,[]).append(h)
                    branches=tuple(GeneratedPublication(r,sum((h.mass for h in hs),F()),TrueScanState(normalize(hs),p.rosters,p.initial_rule,p.tracked,p.observed_prefix)) for r,hs in groups.items())
                    if trace is not None:trace['known_single_fake_noise_marginalized']=trace.get('known_single_fake_noise_marginalized',0)+1
                else:branches=checked(future_publications(p,published,b.alive,b.claims,fake_policy=strategy.fake_seer_policy))
                if trace is not None:
                    trace['morning_public_vectors']=trace.get('morning_public_vectors',0)+len(branches)
                    trace['max_acquisition_day']=max(trace.get('max_acquisition_day',0),len(p.rosters))
                if sum(branch.probability for branch in branches)!=1:raise ValueError('Incomplete generated public branch set')
                for probability, public, joint, reports in public_report_branches(b,published,branches):
                    tick(len(joint.hypotheses))
                    total+=q*probability*solve(public,joint,reports)
            values.append(total)
        return sum(values,F())/len(values) if strategy.fake_reports=='random' else min(values)
    def action_value(b,s,published,target):
        tick(len(s.hypotheses));total=F()
        for o in action_outcomes(b,target,rules,strategy):
            if o.board.winner is not None:value=F(int(o.board.winner=='village'))
            else:
                private=s
                if b.phase=='night':
                    key=(b,s)
                    if key not in acquired_memo:
                        private=checked(acquire_uniform(s,b.alive,max_work=max_work,position=strategy.seer_position));tick(len(private.hypotheses));acquired_memo[key]=private
                        if trace is not None:trace['night_acquisition_calls']=trace.get('night_acquisition_calls',0)+1
                    private=acquired_memo[key]
                next_private=project_private(private,o.board,marginalize_private=marginalize_private)
                value=morning(o.board,next_private,published) if b.phase=='night' else solve(o.board,next_private,published)
            total+=o.probability*value
        return total
    def no_future_information(b,s):
        co=tuple(p for p in b.alive if b.claims[p-1]=='seer')
        return not co or marginalize_known_fake and len(co)==1 and not any(h.roles[2]&(1<<(co[0]-1)) for h in s.hypotheses)
    def values_for(b,s,published):
        key=(b,s,published)
        if key in action_memo:return action_memo[key]
        if no_future_information(b,s):
            root=build_tree(b,rules,strategy);evaluation=evaluate_tree(root,strategy)
            values=tuple((p,evaluation.action_value(root,p).village_win) for p in legal_targets(b,rules,strategy))
        else:values=tuple((target,action_value(b,s,published,target)) for target in legal_targets(b,rules,strategy))
        action_memo[key]=values
        return values
    def solve(b,s,published):
        tick(len(s.hypotheses))
        if b.winner is not None:return F(int(b.winner=='village'))
        key=(b,s,published)
        if key in memo:return memo[key]
        mode=strategy.day if b.phase=='day' else strategy.night
        if mode=='max' and not no_future_information(b,s):
            numbers=[]
            for target in legal_targets(b,rules,strategy):
                value=action_value(b,s,published,target);numbers.append(value)
                if value==(1 if b.phase=='day' else 0):
                    # Absolute probability bound establishes the complete scalar
                    # optimum. No partial action table is cached or returned.
                    memo[key]=value
                    return value
            values=tuple(zip(legal_targets(b,rules,strategy),numbers))
        else:values=values_for(b,s,published)
        if not values:raise ValueError('No legal public continuation')
        numbers=tuple(v for _,v in values)
        mode=strategy.day if b.phase=='day' else strategy.night
        value=sum(numbers,F())/len(numbers) if mode=='random' else max(numbers) if b.phase=='day' else min(numbers)
        memo[key]=value
        return value
    try:
        with calculation_budget(max_work):
            value=solve(board,state,past)
            actions=() if board.winner is not None else values_for(board,state,past)
            from .by_dawn import action_by_dawn
            horizon=tuple((target,action_by_dawn(board,target,rules,strategy,
                lambda b: values_for(b,project_private(state,b,marginalize_private=marginalize_private),past))) for target,_ in actions)
            return Forecast(value,actions,horizon)
    except CalculationBudgetExceeded:return FuturePending('future_public_continuation_budget_exceeded')
    except Unresolved as exc:return exc.pending
