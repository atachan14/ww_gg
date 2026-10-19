"""Shared complete morning report generation; no continuation solver.

Generation receives the public joint prior, never viewer-conditioned evidence.
"""
from dataclasses import dataclass
from itertools import product,combinations,combinations_with_replacement
from collections import Counter
from math import factorial,prod
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
    multiplicity: int = 1


def fake_backlog_options(state,reporters,past):
    if len(reporters)>1:return FuturePending('multiple_fake_report_correlation_unselected')
    if not reporters:return (((),F(1)),)
    p=reporters[0];seen={(r.player,r.acquired_day) for r in past};plans=[]
    for day,roster in enumerate(state.rosters,1):
        if day==1 and state.initial_rule=='none' or p not in roster or (p,day) in seen:continue
        options=fake_uniform_options(state.rosters[0],p,past)
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
            groups.setdefault(reports,[]).append(Hypothesis(h.roles,h.acquisitions,h.mass*q,h.guards,h.attacks))
    result=[]
    for reports,entries in groups.items():
        tick(len(entries));mass=sum((h.mass for h in entries),F())
        result.append(GeneratedPublication(reports,mass,TrueScanState(normalize(entries),state.rosters,state.initial_rule,state.tracked,state.observed_prefix)))
    return tuple(sorted(result,key=lambda b:repr(b.reports)))



def _report_plans(reports,players):
    grouped={p:[] for p in players}
    for r in reports:grouped[r.player].append((r.acquired_day,r.published_day,r.target,r.color))
    return tuple((p,tuple(sorted(grouped[p]))) for p in players)


def compile_publications(state,past,morning_alive,claims,*,fake_policy=('noncontradictory','uniform'),seed=(),board=None):
    """Index the original joint truth/fake kernel; no independent marginals."""
    if tuple(fake_policy) not in (('uniform',),('noncontradictory','uniform')):raise ValueError('Unsupported fake seer policy')
    day=len(state.rosters)
    if day<2:return FuturePending('future_fake_law_does_not_specify_initial_declarations')
    generator=plausible_fake_options if 'noncontradictory' in fake_policy else fake_backlog_options
    reporters=tuple(sorted(p for p in morning_alive if claims[p-1]=='seer'))
    indexed={};fake_chances={};options={p:set() for p in reporters}
    for h in state.hypotheses:
        tick(1+len(h.acquisitions))
        fakes=tuple(p for p in reporters if not h.roles[2]&(1<<(p-1)))
        if fakes not in fake_chances:
            choices=generator(state,fakes,past)
            if isinstance(choices,FuturePending):return choices
            chances={}
            for reports,q in choices:
                key=_report_plans(reports,fakes);chances[key]=chances.get(key,F())+q
                for p,plan in key:options[p].add(plan)
            fake_chances[fakes]=chances
        truth=_report_plans(true_reports(h,past,morning_alive,claims,day),tuple(p for p in reporters if p not in fakes))
        indexed.setdefault(fakes,{}).setdefault(truth,[]).append(h)
        for p,plan in truth:options[p].add(plan)
    return CompiledPublications(state,board,past,reporters,indexed,fake_chances,options,seed)


def _plan_multisets(players,options):
    for plans in combinations_with_replacement(options,len(players)):
        tick()
        multiplicity=factorial(len(players))//prod(factorial(n) for n in Counter(plans).values())
        yield tuple(zip(players,plans)),multiplicity


class CompiledPublications:
    """Public-source-owned exact event cache and orderly reporter allocations."""
    def __init__(self,state,board,past,reporters,indexed,fake_chances,options,seed):
        self.state=state;self.board=board;self.past=past;self.reporters=reporters;self.indexed=indexed;self.fake_chances=fake_chances
        self.options={p:tuple(sorted(v)) for p,v in options.items()}
        self.events={};self.public_rows={}
        for q,child,law,history in seed:
            reports=tuple(history[len(past):])
            self.events[_report_plans(reports,reporters)]=GeneratedPublication(reports,q,law)
            self.public_rows[reports]=(child,history)
        self.stats={'candidates':0,'built_vectors':0,'emitted_vectors':0,'named_vectors_covered':0}

    def terminal_execution_value(self,private,targets,*,incomplete):
        """Joint report moments for final one-wolf execution, without posteriors.

        Choose each complete event's public face before weighting its private
        payoff. The original correlated truth/fake index supplies all masses.
        Named event/history caches remain untouched.
        """
        from .information_weights import observer_projection_ratios
        from .policy_choice import optimal_targets
        ratios=observer_projection_ratios(self.state,private,incomplete=incomplete)
        value=F();public_mass=F();private_mass=F()
        for selection in product(*(self.options[p] for p in self.reporters)):
            tick();plans=tuple(zip(self.reporters,selection))
            public={t:F() for t in targets};own={t:F() for t in targets}
            for fakes,chances in self.fake_chances.items():
                fake=tuple(pair for pair in plans if pair[0] in fakes)
                chance=chances.get(fake,F())
                if not chance:continue
                truth=tuple(pair for pair in plans if pair[0] not in fakes)
                for h in self.indexed[fakes].get(truth,()):
                    tick();mass=h.mass*chance
                    public_mass+=mass
                    private_mass+=mass*ratios.get((h.roles,h.acquisitions),F())
                    for t in targets:
                        if h.roles[0]&(1<<(t-1)):
                            public[t]+=mass
                            own[t]+=mass*ratios.get((h.roles,h.acquisitions),F())
            if any(public.values()):
                chosen=optimal_targets(tuple(public.items()),maximize=True)
                value+=sum((own[t] for t in chosen),F())/len(chosen)
        if public_mass!=1 or private_mass!=1:raise incomplete()
        return value

    def event(self,plans):
        if plans in self.events:return self.events[plans]
        entries=[]
        for fakes,chances in self.fake_chances.items():
            fake=tuple(pair for pair in plans if pair[0] in fakes);q=chances.get(fake,F())
            if not q:continue
            truth=tuple(pair for pair in plans if pair[0] not in fakes)
            entries.extend(Hypothesis(h.roles,h.acquisitions,h.mass*q,h.guards,h.attacks)
                           for h in self.indexed[fakes].get(truth,()))
        tick(1+len(entries))
        if not entries:result=None
        else:
            mass=sum((h.mass for h in entries),F())
            law=TrueScanState(normalize(entries),self.state.rosters,self.state.initial_rule,self.state.tracked,self.state.observed_prefix)
            reports=tuple(sorted(SeerReport(day,pub,p,target,color) for p,plan in plans for day,pub,target,color in plan))
            result=GeneratedPublication(reports,mass,law);self.stats['built_vectors']+=1
        self.events[plans]=result
        return result

    def branches(self,partition):
        generated=self.representatives(partition)
        if isinstance(generated,FuturePending):return generated
        result=[]
        for r in generated:
            if r.reports not in self.public_rows:
                self.public_rows[r.reports]=(replace_worlds(self.board,r.state.public_roles),self.past+r.reports)
            child,history=self.public_rows[r.reports]
            result.append((r.probability,child,r.state,history))
        return tuple(result)

    def representatives(self,partition):
        """Fix every target literally; permute only remaining reporter rows.

        Enumerate multisets before constructing report vectors. The marginal
        plan options only propose candidates: event() evaluates the correlated
        source hypotheses and the unchanged public fake kernel exactly.
        """
        targets={plan:frozenset(r[2] for r in plan) for options in self.options.values() for plan in options}
        universe=tuple(sorted(set().union(*targets.values()))) if targets else ()
        limit=min(len(universe),sum(max((len(plan) for plan in self.options[p]),default=0) for p in self.reporters))
        result=[]
        for width in range(limit+1):
            for selected in combinations(universe,width):
                tick();selected=frozenset(selected);blocks=[]
                for group in partition:
                    blocks.extend((p,) for p in group if p in selected)
                    rest=tuple(p for p in group if p not in selected)
                    if rest:blocks.append(rest)
                choices=[]
                for block in blocks:
                    options=tuple(plan for plan in self.options[block[0]] if targets[plan]<=selected)
                    if not options:break
                    choices.append(tuple(_plan_multisets(block,options)))
                else:
                    for selection in product(*choices):
                        tick();assignments=tuple(pair for plans,m in selection for pair in plans)
                        used=frozenset(t for p,plan in assignments for t in targets[plan])
                        if used!=selected:continue
                        plans=tuple(sorted(assignments))
                        self.stats['candidates']+=1;event=self.event(plans)
                        if event is None:continue
                        multiplicity=prod(m for plans,m in selection)
                        result.append(GeneratedPublication(event.reports,event.probability*multiplicity,event.state,multiplicity))
        if sum((r.probability for r in result),F())!=1:return FuturePending('report_orbit_public_mass_incomplete')
        self.stats['emitted_vectors']+=len(result)
        self.stats['named_vectors_covered']+=sum(r.multiplicity for r in result)
        return tuple(sorted(result,key=lambda b:repr(b.reports)))
