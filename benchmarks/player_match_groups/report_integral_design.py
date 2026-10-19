"""Development math/oracle only; no production evaluator or runtime certificate."""
from fractions import Fraction as F
from collections import defaultdict
from itertools import product
from math import prod
from dataclasses import replace
import json,hashlib,time
from pathlib import Path
from werewolf.calculation_budget import tick


class Undefined(Exception):
    pass


def full(h):return (h.roles,h.acquisitions,h.guards,h.attacks)
def projection(h):return (h.roles,h.acquisitions)
def sig(plan):return tuple(sorted((r.acquired_day,r.target,r.color) for r in plan))
def normalized(rows):
    total=sum(rows.values(),F());assert total>0
    return {key:q/total for key,q in rows.items() if q}


def factor_slots(state,past,player):
    # Independent transcription of the specified factor law, not calls to
    # fake_uniform_options/backlog/plausible/generator/normalizer.
    from werewolf.seer_acquisition import SeerReport
    seen={(r.player,r.acquired_day) for r in past}
    days=tuple(day for day,roster in enumerate(state.rosters,1) if player in roster and (player,day) not in seen and not (day==1 and state.initial_rule=='none'))
    if not days:return ()
    legal=tuple(p for p in state.rosters[0] if p!=player)
    visited={r.target for r in past if r.player==player}
    targets=tuple(p for p in legal if p not in visited) or legal
    if not targets:raise Undefined('no_legal_fake_report_target')
    slots=[]
    for day in days:
        slots.append(tuple((SeerReport(day,len(state.rosters),player,t,c),F(1,2*len(targets))) for t in targets for c in ('white','black')))
    return tuple(slots)


def truth_plan(h,past,alive,claims,day):
    from werewolf.seer_acquisition import SeerReport
    seen={(r.player,r.acquired_day) for r in past}
    return tuple(sorted(SeerReport(a.day,day,a.player,a.target,a.color) for a in h.acquisitions
        if a.player in alive and claims[a.player-1]=='seer' and (a.player,a.day) not in seen))


def factor_check(state,past,alive,claims,weights=None,*,plausible=True):
    """Only normalizers/support; never enumerate a fake Cartesian product."""
    if len(state.rosters)<2:raise Undefined('future_fake_law_does_not_specify_initial_declarations')
    weights=weights or {full(h):h.mass for h in state.hypotheses}
    hs=tuple(h for h in state.hypotheses if weights.get(full(h),0)>0)
    families={tuple(p for p in alive if claims[p-1]=='seer' and not h.roles[2]&(1<<(p-1))) for h in hs}
    seen={(r.player,r.acquired_day) for r in past};result={}
    for fakes in sorted(families):
        if len(fakes)>1:raise Undefined('multiple_fake_report_correlation_unselected')
        if not fakes:
            result[fakes]=dict(raw_plans=1,kept_plans=1,Z=F(1),factor_slots=(),signatures=None);continue
        p=fakes[0];slots=factor_slots(state,past,p)
        slot_maps=[{(r.acquired_day,r.target,r.color):q for r,q in options} for options in slots]
        possible=tuple(h for h in hs if h.roles[2]&(1<<(p-1))) if plausible else ()
        if not possible:
            # Complete independent factor product is row-stochastic. Its
            # cardinality is counted without constructing report vectors.
            result[fakes]=dict(raw_plans=prod(map(len,slots)),kept_plans=prod(map(len,slots)),Z=F(1),factor_slots=slots,signatures=None);continue
        signatures={tuple(sorted((a.day,a.target,a.color) for a in h.acquisitions if a.player==p and (p,a.day) not in seen)) for h in possible}
        kept={}
        for signature in signatures:
            tick()
            if len(signature)!=len(slot_maps):continue
            q=F(1)
            for entry,options in zip(signature,slot_maps):q*=options.get(entry,F())
            if q:kept[signature]=q
        Z=sum(kept.values(),F())
        if not Z:raise Undefined('no_noncontradictory_fake_report')
        result[fakes]=dict(raw_plans=prod(map(len,slots)),kept_plans=len(kept),Z=Z,factor_slots=slots,signatures=frozenset(kept))
    return result


def explicit_fake(state,past,fakes,summary):
    if not fakes:return (((),F(1)),)
    rule=summary[fakes];rows=[]
    for choices in product(*rule['factor_slots']):
        tick()
        plan=tuple(r for r,q in choices);mass=prod((q for r,q in choices),start=F(1))
        if rule['signatures'] is None or sig(plan) in rule['signatures']:rows.append((plan,mass/rule['Z']))
    assert sum((q for plan,q in rows),F())==1
    return tuple(rows)


def enumerated_fake(state,past,fakes,weights,*,plausible=True):
    """Independent exhaustive reference, with its own denominator/filter."""
    from werewolf.seer_acquisition import SeerReport
    if len(fakes)>1:raise Undefined('multiple_fake_report_correlation_unselected')
    if not fakes:return (((),F(1)),)
    p=fakes[0];legal=[t for t in state.rosters[0] if t!=p]
    previously_reported=[r.target for r in past if r.player==p]
    targets=[t for t in legal if t not in previously_reported] or legal
    histories=[]
    for d,roster in enumerate(state.rosters,1):
        if p not in roster or any(r.player==p and r.acquired_day==d for r in past) or d==1 and state.initial_rule=='none':continue
        if not targets:raise Undefined('no_legal_fake_report_target')
        histories.append([(SeerReport(d,len(state.rosters),p,t,color),F(1,2*len(targets))) for t in targets for color in ('white','black')])
    possible=[h for h in state.hypotheses if weights.get(full(h),0) and h.roles[2]&(1<<(p-1))] if plausible else []
    options=[]
    for choice in product(*histories):
        tick()
        reports=tuple(r for r,q in choice);q=F(1)
        for r,chance in choice:q*=chance
        supported=not possible
        for h in possible:
            true=tuple(sorted((a.day,a.target,a.color) for a in h.acquisitions if a.player==p and not any(r.player==p and r.acquired_day==a.day for r in past)))
            proposed=tuple(sorted((r.acquired_day,r.target,r.color) for r in reports))
            if true==proposed:supported=True;break
        if supported:options.append((reports,q))
    total=sum((q for plan,q in options),F())
    if not total:raise Undefined('no_noncontradictory_fake_report')
    return tuple((plan,q/total) for plan,q in options)


def medium_joint(source):
    from werewolf.exact import MediumReport
    b=source.public;Q={full(h):h.mass for h in source.public_state.hypotheses}
    supplied={(r.day,r.reporter,r.target) for r in b.reports}
    ops=tuple(o for o in b.medium_opportunities if o[0]==b.day and o[1] in b.alive and o not in b.report_resolved and o not in supplied)
    # Closed claims have true or wolf medium claimants. Every random fake
    # instruction is selected before reading the world's actual medium truth.
    fakes=tuple(sorted({p for day,p,t in ops if any(h.roles[0]&(1<<(p-1)) for h in source.public_state.hypotheses)}))
    out=defaultdict(lambda:defaultdict(F))
    for colors in product(('white','black'),repeat=len(fakes)):
        tick()
        instructions=dict(zip(fakes,colors));chance=F(1,2**len(fakes))
        for h in source.public_state.hypotheses:
            reports=tuple(MediumReport(day,p,t,('black' if h.roles[0]&(1<<(t-1)) else 'white') if h.roles[1]&(1<<(p-1)) else instructions[p]) for day,p,t in ops)
            out[b.reports+reports][full(h)]+=h.mass*chance
    assert all(sum((rows.get(key,F()) for rows in out.values()),F())==q for key,q in Q.items())
    return dict(out)


def oracle(source,*,plausible=True):
    """Named joint enumeration; no production publication/weighting helpers."""
    state=source.public_state;b=source.public;past=source.past
    Q={full(h):h.mass for h in state.hypotheses};Qpi=defaultdict(F)
    for h in state.hypotheses:Qpi[projection(h)]+=h.mass
    if any(projection(h) not in Qpi for h in source.private.hypotheses):raise Undefined('information_set_report_likelihood_incomplete')
    if sum((h.mass for h in source.private.hypotheses),F())!=1:raise Undefined('information_set_report_likelihood_incomplete')
    joint=defaultdict(lambda:defaultdict(F));summaries=[];emissions=0
    for medium,weights in medium_joint(source).items():
        qm=sum(weights.values(),F());summaries.append((medium,qm));fake_rows={}
        for h in state.hypotheses:
            if full(h) not in weights:continue
            fakes=tuple(p for p in b.alive if b.claims[p-1]=='seer' and not h.roles[2]&(1<<(p-1)))
            truth=truth_plan(h,past,b.alive,b.claims,len(state.rosters))
            if fakes not in fake_rows:fake_rows[fakes]=enumerated_fake(state,past,fakes,weights,plausible=plausible)
            for fake,mass in fake_rows[fakes]:
                tick()
                event=(medium,past+tuple(sorted(truth+fake)))
                joint[event][full(h)]+=weights[full(h)]*mass;emissions+=1
    # Verify every Q fiber's row sum, not only the current viewer's mass.
    for key,q in Q.items():assert sum((rows.get(key,F()) for rows in joint.values()),F())==q
    result={}
    for event,rows in joint.items():
        probability=sum(rows.values(),F());Jpi=defaultdict(F)
        for (roles,acqs,guards,attacks),mass in rows.items():Jpi[roles,acqs]+=mass
        private={full(h):h.mass*Jpi.get(projection(h),F())/Qpi[projection(h)] for h in source.private.hypotheses}
        private={key:q for key,q in private.items() if q};mass=sum(private.values(),F())
        result[event]=dict(q=probability,Q=normalized(rows),p=mass,P=normalized(private) if mass else {})
    assert sum((r['p'] for r in result.values()),F())==1
    return result,dict(H=len(Q),medium_families=len(summaries),raw_emissions=emissions,public_vectors=len(result),positive_P_vectors=sum(r['p']>0 for r in result.values()),summaries=summaries)


def compact_validation(source,*,plausible=True):
    """Design candidate: validate full Q factor families, then P support.

    It returns only a row-stochasticity fact, never a conditional law/value.
    Caller still has to establish that its continuation is observation-invariant.
    """
    b=source.public;state=source.public_state;families=[]
    # Includes positive-Q medium families with zero probability under P.
    for medium,weights in medium_joint(source).items():
        rules=factor_check(state,source.past,b.alive,b.claims,normalized(weights),plausible=plausible);families.append((medium,rules))
    support={projection(h) for h in state.hypotheses}
    if any(projection(h) not in support for h in source.private.hypotheses) or sum((h.mass for h in source.private.hypotheses),F())!=1:
        raise Undefined('information_set_report_likelihood_incomplete')
    return families


def audit(node):
    source=node.read()
    from types import SimpleNamespace
    from .closed_full_tree_fixture import case
    from .cut_out_compact_terminal_fixture import independent_cold
    graph=SimpleNamespace(data=node._Node__calculation.data,engine=case(5,'single').engine)
    assert independent_cold(graph,node.export_request())==source
    e=node._Node__calculation._ClosedCalculation__engine
    plausible='noncontradictory' in e.strategy.fake_seer_policy
    expected,counts=oracle(source,plausible=plausible);compact_validation(source,plausible=plausible)
    # Read every public-Q row, including rows removed by the viewer condition.
    with node._Node__calculation._ClosedCalculation__kernel():public=e.morning(source.public,source.public_state,source.past)
    got={}
    for q,b,state,past in public:
        event=(b.reports,past);assert event not in got
        got[event]=dict(q=q,Q={full(h):h.mass for h in state.hypotheses})
    assert set(got)==set(expected)
    for key,row in got.items():assert row['q']==expected[key]['q'] and row['Q']==expected[key]['Q']
    private={(r.node.read().public.reports,r.node.read().past):r for r in node.reports()}
    assert set(private)=={key for key,row in expected.items() if row['p']}
    for key,row in private.items():
        assert row.public_probability==expected[key]['q'] and row.probability==expected[key]['p']
        assert {full(h):h.mass for h in row.node.read().private.hypotheses}==expected[key]['P']
    return expected,counts


def compiled_mass_probe(node):
    """Development-only candidate using CURRENT shared kernels/index.

    Independent oracle/coverage assertions belong here, not in a future
    production mass operation. No event/posterior or orbit is constructed.
    """
    from werewolf.exact import report_actions,random_report_outcomes
    from werewolf.morning_publications import compile_publications
    from werewolf.seer_future_uniform import FuturePending
    from werewolf.information_set_forecast import exchangeable_value
    c=node._Node__calculation;e=c._ClosedCalculation__engine;s=node.read();b=s.public
    if not (b.phase=='day' and len(b.alive)==3 and not b.initial_hunter_count and set(b.wolf_count_distribution)=={1}):
        raise Undefined('design_constant_terminal_domain_required')
    medium=random_report_outcomes(b) if report_actions(b) else ()
    rows=[];indices=[]
    for probability,board in ((o.probability,o.board) for o in medium) if medium else ((F(1),b),):
        public=e.project(s.public_state,board)
        kernel=compile_publications(public,s.past,b.alive,b.claims,fake_policy=e.strategy.fake_seer_policy,board=board)
        if isinstance(kernel,FuturePending):raise Undefined(kernel.reason)
        # These are DEVELOPMENT assertions, not proposed runtime proof scans.
        assert sum(len(hs) for d in kernel.indexed.values() for hs in d.values())==len(public.hypotheses)
        assert all(sum(chances.values(),F())==1 for chances in kernel.fake_chances.values())
        assert not kernel.events and not kernel.public_rows
        indices.append(dict(hypotheses=len(public.hypotheses),fake_plans=sum(len(v) for v in kernel.fake_chances.values()),built_event_laws=len(kernel.events)))
        rows.append((probability,board,public,s.past))
    weighted=e.push(s.public_state,s.private,tuple(rows))
    constant=exchangeable_value(3,1,'day',e.strategy)
    value=sum((mass*constant for mass,board,public,past,private in weighted),F())
    return value,dict(medium_families=len(rows),positive_P_medium_families=len(weighted),built_conditional_seer_event_laws=0,indices=indices)


def make(n,kind,day_target,night_target):
    from .closed_full_tree_fixture import case
    from werewolf.closed_calculation import ClosedCalculation
    c=ClosedCalculation(case(n,kind).data,grouped=True,aggregate_wolf=True,aggregate_reports=True)
    node=next(r.node for r in c.root.action(day_target) if r.node.read().public.winner is None)
    node=next(r.node for r in node.action(night_target) if r.node.read().public.winner is None)
    return c,node


def terminal_named(rows,alive):
    # Independent last-execution enumeration (one live wolf is a precondition).
    assert all((roles[0]&sum(1<<(p-1) for p in alive)).bit_count()==1 for roles,acqs,guards,attacks in rows)
    return {p:sum((mass*F(bool(key[0][0]&(1<<(p-1)))) for key,mass in rows.items()),F()) for p in alive}


def five_full_terminal_sum(node):
    """Independent named physical/report/execution sum, no solve/recurrence."""
    b=node.read().public
    assert len(b.alive)==5 and b.phase=='day' and set(b.wolf_count_distribution)=={1}
    stats=dict(first_targets=0,physical_edges=0,wolf_choices=0,terminal_executions=0,report_vectors=0)
    value=F();columns={}
    for target in b.alive:
        stats['first_targets']+=1;subtotal=F()
        for branch in node.action(target):
            stats['physical_edges']+=1
            child=branch.node.read().public
            if child.winner is not None:
                subtotal+=branch.probability*F(child.winner=='village');continue
            assert len(child.alive)==4 and child.phase=='night'
            choices=branch.node.wolf_choices();assert sum((c.mass for c in choices),F())==1
            for choice in choices:
                stats['wolf_choices']+=1
                for night in choice.node.action(choice.target):
                    stats['physical_edges']+=1;source=night.node.read()
                    assert len(source.public.alive)==3 and source.public.winner is None
                    rows,counts=oracle(source);stats['report_vectors']+=len(rows)
                    terminal=F()
                    for event,row in rows.items():
                        if not row['p']:continue
                        # Explicit final legal targets/role payoff, not 1/3.
                        for executed,payoff in terminal_named(row['P'],source.public.alive).items():
                            tick();stats['terminal_executions']+=1
                            terminal+=row['p']*payoff/len(source.public.alive)
                    subtotal+=branch.probability*choice.mass*night.probability*terminal
        columns[target]=subtotal;value+=subtotal/len(b.alive)
    return value,columns,stats


def count_design_reference(node):
    """Design theorem candidate, not a production route or supported API."""
    from werewolf.information_set_forecast import exchangeable_value
    from werewolf.by_dawn import HorizonValues
    from werewolf.exact import legal_targets
    s=node.read();b=s.public;e=node._Node__calculation._ClosedCalculation__engine;n=len(b.alive)
    # Study only retrospective private views; future interventions can fail
    # even though physical count values exist.
    from werewolf.seer_intervention import SeerObserver
    if isinstance(s.observer,SeerObserver) and s.observer.day>len(s.private.rosters):raise Undefined('design_prospective_observer_excluded')
    value=sum((h.mass*exchangeable_value(n,(h.roles[0]&b.alive_mask).bit_count(),b.phase,e.strategy) for h in s.private.hypotheses),F())
    columns={}
    for target in legal_targets(s.physical,e.rules,e.strategy):
        if b.phase=='day':
            columns[target]=sum((h.mass*exchangeable_value(n-1,(h.roles[0]&b.alive_mask).bit_count()-int(bool(h.roles[0]&(1<<(target-1)))),'night',e.strategy) for h in s.private.hypotheses),F())
        else:
            columns[target]=sum((h.mass*exchangeable_value(n-1,(h.roles[0]&b.alive_mask).bit_count(),'day',e.strategy) for h in s.private.hypotheses),F())
    return value,columns


def run():
    from werewolf.actor_information import PersonalInformation,WolfInformation
    from werewolf.calculation_budget import calculation_budget,budget_usage
    started=time.perf_counter();cases=[]
    with calculation_budget(250000,max_seconds=30):
        for kind,day in [('single',3),('dual',3),('three',4),('medium-pair',4)]:
            c,node=make(5,kind,day,5);h=next(h for h in node.read().private.hypotheses if h.roles[2]&1)
            views=[('public',node),('seer',node.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1]),('wolf',node.personal(WolfInformation.from_hypothesis(h))[1])]
            for view,n in views:
                rows,counts=audit(n);alive=n.read().public.alive
                values={event:sum(terminal_named(row['P'],alive).values(),F())/len(alive) for event,row in rows.items() if row['p']}
                expanded=sum((rows[event]['p']*v for event,v in values.items()),F());assert set(values.values())=={F(1,3)} and expanded==F(1,3)
                candidate,probe=compiled_mass_probe(n);assert candidate==expanded
                counts.pop('summaries');cases.append(dict(kind=kind,view=view,counts=counts,expanded=str(expanded),contracted=str(candidate),current_common_index_probe=probe,full_joint_oracle_equal=True))
        out=dict(status='verified',cases=cases,budget=budget_usage(),seconds=time.perf_counter()-started,production_changed=False)
    return out

def study():
    from .closed_full_tree_fixture import case
    from .cut_out_user_seven_uniform_preparation import comparison_game
    from werewolf.closed_calculation import ClosedCalculation,_forecast_scope
    from werewolf.board_flow import BoardData
    from werewolf.actor_information import PersonalInformation,WolfInformation
    from werewolf.calculation_budget import calculation_budget,budget_usage
    from unittest.mock import patch
    started=time.perf_counter()
    with calculation_budget(250000,max_seconds=30):
        result=run();complete=[]
        for kind in ('single','dual','three','medium-pair'):
            c=ClosedCalculation(case(5,kind).data,grouped=True,aggregate_wolf=True,aggregate_reports=True)
            h=next(h for h in c.root.read().private.hypotheses if h.roles[2]&1)
            for view,n in [('public',c.root),('seer',c.root.personal(PersonalInformation(1,'seer',tuple(a for a in h.acquisitions if a.player==1)))[1]),('wolf',c.root.personal(WolfInformation.from_hypothesis(h))[1])]:
                with patch.object(c._ClosedCalculation__engine,'solve',side_effect=AssertionError('independent reference calls solver')):
                    value,columns,stats=five_full_terminal_sum(n)
                proposed,proposed_columns=count_design_reference(n)
                actual=n.forecast()
                assert value==proposed==actual.village_win and columns==proposed_columns==dict(actual.action_values)
                complete.append(dict(kind=kind,view=view,value=str(value),columns={str(p):str(q) for p,q in columns.items()},named_physical_report_terminal_enumeration=stats,current_full_Forecast_values_equal=True))
        c=ClosedCalculation(BoardData.from_game(comparison_game()[1]),grouped=True,aggregate_wolf=True,aggregate_reports=True)
        _forecast_scope(c.root.read(),c._ClosedCalculation__engine)
        value,columns=count_design_reference(c.root)
        assert value==F(8,35)
        result.update(complete_five_player_integrals=complete,initial_seven_conditional_theorem_prediction=dict(value=str(value),columns={str(p):str(q) for p,q in columns.items()},actual_complete_seven_API_obtained=False,note='Mathematical prediction under stated full-law closure hypotheses; no production Forecast/Table returned or synthesized.'),budget=budget_usage(),seconds=time.perf_counter()-started)
        return result


def check_tests():
    import unittest,io
    from werewolf.calculation_budget import calculation_budget,budget_usage
    names=['tests.test_report_integral_design','tests.test_terminal_day_cut','tests.test_seven_initial_scope','tests.test_value_law_cache.ValueLawCacheTests.test_same_role_marginal_different_scan_history_cannot_share_input','tests.test_closed_full_tree.ClosedFullTreeTests.test_undefined_multiple_fake_joint_kernel_is_rejected_before_recursion','tests.test_closed_full_tree.ClosedFullTreeTests.test_missing_initial_declaration_is_not_synthesized_as_future_policy']
    stream=io.StringIO();started=time.perf_counter()
    with calculation_budget(250000,max_seconds=30):
        result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromNames(names))
        output=dict(status='verified' if result.wasSuccessful() else 'failed',tests=result.testsRun,test_output=stream.getvalue(),budget=budget_usage(),seconds=time.perf_counter()-started)
    return output


if __name__=='__main__':
    import sys
    print(json.dumps(check_tests() if sys.argv[1:2]==['tests'] else study()))
