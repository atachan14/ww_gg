"""DEVELOPMENT sparse positive-Q joint report traversal, no seven jobs."""
from collections import Counter
from contextlib import nullcontext
from fractions import Fraction as F
from itertools import product
from math import prod
from pathlib import Path
from unittest.mock import patch
from time import perf_counter
import hashlib,json
from werewolf.calculation_budget import calculation_budget,budget_usage,tick
from werewolf.board_future import kernel_calculation
from werewolf.morning_publications import CompiledPublications,_report_plans,future_publications
from werewolf.policy_choice import optimal_targets
from .max_structure_design import calculation
from .cut_out_publication_orbit_value_fixture import tables


def sparse_joint_rows(kernel,counts=None):
    """Accumulate all Q contributions to each literal complete event first."""
    events={}
    for fakes,truths in kernel.indexed.items():
        for truth,hypotheses in truths.items():
            for fake,chance in kernel.fake_chances[fakes].items():
                tick()
                if chance<=0:continue
                plans=tuple(sorted((*truth,*fake)))
                rows=None
                for h in hypotheses:
                    tick()
                    mass=h.mass*chance
                    if mass<=0:continue
                    if rows is None:rows=events.setdefault(plans,{})
                    fiber=(h.roles,h.acquisitions)
                    rows[fiber]=rows.get(fiber,F())+mass
                    if counts is not None:counts['positive_hypothesis_terms']+=1
                if rows is not None and counts is not None:counts['positive_component_plans']+=1
    if counts is not None:counts['positive_joint_events']+=len(events)
    return events


def sparse_moments(kernel,targets,*,incomplete):
    events=sparse_joint_rows(kernel);moments={};public_mass=F()
    for rows in events.values():
        tick(0)
        public={t:sum((mass for (roles,records),mass in rows.items() if roles[0]&(1<<(t-1))),F()) for t in targets}
        # MAX AFTER summing every hidden/fake-identity contribution to this event.
        public_mass+=sum(rows.values(),F())
        if not any(public.values()):continue
        chosen=optimal_targets(tuple(public.items()),maximize=True)
        for fiber,mass in rows.items():
            payoff=F(sum(bool(fiber[0][0]&(1<<(t-1))) for t in chosen),len(chosen))
            moments[fiber]=moments.get(fiber,F())+mass*payoff
    if public_mass!=1:raise incomplete()
    return tuple(moments.items())


def dense_joint_rows(kernel):
    """Independent Cartesian diagnostic, before any public normalization."""
    events={};candidates=0
    for selection in product(*(kernel.options[p] for p in kernel.reporters)):
        tick();candidates+=1;plans=tuple(zip(kernel.reporters,selection));rows={}
        for fakes,chances in kernel.fake_chances.items():
            chance=chances.get(tuple(pair for pair in plans if pair[0] in fakes),F())
            if not chance:continue
            truth=tuple(pair for pair in plans if pair[0] not in fakes)
            for h in kernel.indexed[fakes].get(truth,()):
                tick();mass=h.mass*chance
                if mass>0:
                    fiber=(h.roles,h.acquisitions);rows[fiber]=rows.get(fiber,F())+mass
        if rows:events[plans]=rows
    return events,candidates


def independent_joint_rows(kernel,*,fake_policy=('noncontradictory','uniform')):
    # Existing expanded generator, not the compiled index or its moments.
    generated=future_publications(kernel.state,kernel.past,kernel.board.alive,kernel.board.claims,fake_policy=fake_policy)
    return {_report_plans(row.reports,kernel.reporters):{(h.roles,h.acquisitions):row.probability*h.mass for h in row.state.hypotheses} for row in generated}


def run():
    measurements=[]
    original=CompiledPublications.terminal_execution_moments
    for kind in ('single','dual','three','medium-pair'):
        for view in ('public','seer','wolf'):
            for mode in ('dense','sparse'):
                with calculation_budget(250000,max_seconds=30),kernel_calculation():
                    c,n=calculation(kind,'baseline',view);used=[]
                    def measured(k,targets,*,incomplete):
                        used.append(k)
                        return (original if mode=='dense' else sparse_moments)(k,targets,incomplete=incomplete)
                    before=budget_usage()['work'];at=perf_counter()
                    with patch.object(CompiledPublications,'terminal_execution_moments',measured):f=n.forecast()
                    seconds=perf_counter()-at;work=budget_usage()['work']-before
                    counters=Counter()
                    # Diagnostics are separately charged AFTER the measured
                    # Forecast, inside the SAME original request budget.
                    diagnostic_start=budget_usage()['work']
                    for k in used:
                        sparse=sparse_joint_rows(k,counters);dense,proposed=dense_joint_rows(k)
                        assert sparse==dense
                        counters['cartesian_candidates']+=proposed
                        counters['zero_Q_candidates']+=proposed-len(sparse)
                    measurements.append({'kind':kind,'view':view,'mode':mode,'complete':True,'value':str(f.village_win),'forecast':repr(f),'table_sha256':hashlib.sha256(repr(tables(n.read(),f)).encode()).hexdigest(),'work':work,'seconds':seconds,'moment_build_calls':len(used),'diagnostic_counts':dict(counters),'diagnostic_work':budget_usage()['work']-diagnostic_start,'total_request_budget':budget_usage()})
    for i in range(0,len(measurements),2):
        a,b=measurements[i:i+2]
        assert (a['forecast'],a['table_sha256'])==(b['forecast'],b['table_sha256'])
    totals={mode:{'work':sum(r['work'] for r in measurements if r['mode']==mode),'seconds':sum(r['seconds'] for r in measurements if r['mode']==mode)} for mode in ('dense','sparse')}
    out={'scope':'DEVELOPMENT terminal moments only;12 complete five-player MAX public/private requests per mode. No seven, no named-event modification. Diagnostic dense/sparse row comparisons are charged separately within each same250000/30s budget. Timing is one instrumented sample, not a statistical guarantee.','totals':totals,'measurements':measurements,'source_sha256':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('benchmarks/player_match_groups/sparse_report_moments.py','werewolf/morning_publications.py','werewolf/grouped_forecast.py')}}
    Path('benchmarks/player_match_groups/sparse-report-moment-results.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'totals':totals,'pairs':[(measurements[i]['kind'],measurements[i]['view'],measurements[i]['work'],measurements[i+1]['work'],measurements[i]['diagnostic_counts']) for i in range(0,len(measurements),2)]}))

if __name__=='__main__':run()
