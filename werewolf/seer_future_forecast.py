"""Fixed-policy PUBLIC continuation with generated seer disclosures.

Manual past evidence is a supplied prior. Future fake probabilities use the
uniform candidate law conditioned on public truth compatibility.
Multiple-fake correlation remains unselected.
"""
from dataclasses import dataclass
from itertools import product
from fractions import Fraction as F
from .exact import (replace_worlds,action_outcomes,legal_targets,report_actions,
                    random_report_outcomes,build_tree,evaluate_tree)
from .seer_acquisition import Hypothesis,SeerReport,normalize,public_worlds
from .seer_future_uniform import TrueScanState,FuturePending,acquire_uniform,true_reports
from .seer_fake_uniform import fake_joint_options,fake_uniform_options
from .calculation_budget import calculation_budget,tick,CalculationBudgetExceeded

@dataclass(frozen=True)
class GeneratedPublication:
    reports: tuple
    probability: F
    state: TrueScanState


def fake_backlog_options(state,reporters,past):
    if len(reporters)>1:return FuturePending('multiple_fake_report_correlation_unselected')
    if not reporters:return (((),F(1)),)
    p=reporters[0];seen={(r.player,r.acquired_day) for r in past};plans=[]
    for day,roster in enumerate(state.rosters,1):
        if day==1 and state.initial_rule=='none' or p not in roster or (p,day) in seen:continue
        options=fake_uniform_options(roster,p,past)
        if isinstance(options,FuturePending):return options
        plans.append(tuple((SeerReport(day,len(state.rosters),p,t,c),q) for (t,c),q in options))
    result=[]
    for selection in product(*plans):
        tick();q=F(1)
        for _,mass in selection:q*=mass
        result.append((tuple(r for r,_ in selection),q))
    return tuple(result)



def plausible_fake_options(state,reporters,past):
    """Filter using public support before simultaneous morning declarations.

    A candidate must be obtainable if its reporter were a true seer in at least
    one supported history. Do not inspect the actual truth owner's new report,
    teammate identities, or the actual private scan. Existing candidate weights
    are conditioned on this support, never weighted by hypothetical truth mass.
    An already exposed fake cannot regain truth status; retain its old noise law.
    """
    options=fake_backlog_options(state,reporters,past)
    if isinstance(options,FuturePending) or not reporters:return options
    player=reporters[0]
    possible=tuple(h for h in state.hypotheses if h.roles[2]&(1<<(player-1)))
    if not possible:return options
    seen={(r.player,r.acquired_day) for r in past}
    signatures=set()
    for h in possible:
        tick(1+len(h.acquisitions))
        signatures.add(tuple(sorted((a.day,a.target,a.color) for a in h.acquisitions
            if a.player==player and (player,a.day) not in seen)))
    kept=[]
    for reports,q in options:
        tick(1+len(reports))
        if tuple(sorted((r.acquired_day,r.target,r.color) for r in reports)) in signatures:
            kept.append((reports,q))
    total=sum((q for _,q in kept),F())
    if not total:return FuturePending('no_noncontradictory_fake_report')
    return tuple((reports,q/total) for reports,q in kept)


def future_publications(state,past,morning_alive,claims,*,fake_policy=('noncontradictory','uniform')):
    """Merge complete true/fake public vectors before any public action."""
    if tuple(fake_policy) not in (('uniform',),('noncontradictory','uniform')):raise ValueError('Unsupported fake seer policy')
    generator=plausible_fake_options if 'noncontradictory' in fake_policy else fake_backlog_options
    groups={};day=len(state.rosters);fake_options={}
    if day<2:return FuturePending('future_fake_law_does_not_specify_initial_declarations')
    for h in state.hypotheses:
        tick(1+len(h.acquisitions))
        fakes=tuple(p for p in morning_alive if claims[p-1]=='seer' and not h.roles[2]&(1<<(p-1)))
        if fakes not in fake_options:fake_options[fakes]=generator(state,fakes,past)
        choices=fake_options[fakes]
        if isinstance(choices,FuturePending):return choices
        truth=true_reports(h,past,morning_alive,claims,day)
        for fake_reports,q in choices:
            tick()
            reports=tuple(sorted(truth+fake_reports))
            groups.setdefault(reports,[]).append(Hypothesis(h.roles,h.acquisitions,h.mass*q))
    result=[]
    for reports,entries in groups.items():
        tick(len(entries));mass=sum((h.mass for h in entries),F())
        result.append(GeneratedPublication(reports,mass,TrueScanState(normalize(entries),state.rosters,state.initial_rule,state.tracked,state.observed_prefix)))
    return tuple(sorted(result,key=lambda b:repr(b.reports)))


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
                for branch in branches:
                    tick(len(branch.state.hypotheses))
                    public=replace_worlds(b,branch.state.public_roles)
                    total+=q*branch.probability*solve(public,branch.state,published+branch.reports)
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
