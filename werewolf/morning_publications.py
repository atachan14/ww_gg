"""Shared complete morning report generation; no continuation solver.

Generation receives the public joint prior, never viewer-conditioned evidence.
"""
from dataclasses import dataclass
from itertools import product
from fractions import Fraction as F
from .seer_acquisition import Hypothesis,SeerReport,normalize
from .seer_future_uniform import TrueScanState,FuturePending,true_reports
from .seer_fake_uniform import fake_uniform_options
from .calculation_budget import tick
from .exact import replace_worlds


def public_report_branches(board, past, generated):
    """Apply generated public vectors before the next public decision.

    Both continuations use this boundary; actor ranking and observer weighting
    belong to their callers. Acquisition records are retained in branch.state.
    """
    return tuple((branch.probability, replace_worlds(board, branch.state.public_roles),
                  branch.state, past + branch.reports) for branch in generated)

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

