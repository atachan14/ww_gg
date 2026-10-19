"""Current closed-generation entry; ordinary named evaluation is the oracle.

No issued ledger in the current route. Earlier ledger fixtures remain historical
regression/reference helpers and are no longer the selected experiment entry.
"""
import sys,json,time,statistics,subprocess,hashlib
from pathlib import Path
from collections import Counter
from contextlib import ExitStack
from datetime import datetime,timezone


def worker(case,diagnostic=False):
    from .cut_out_publication_orbit_value_fixture import make_role_filter_scope,tables
    from .cut_out_first_cycle_coverage import base
    from .cut_out_uniform_game_fixture import peak_bytes
    from .cut_out_compact_terminal_fixture import independent_cold
    from .cut_out_joint_night_forecast_fixture import moved_source
    from werewolf.closed_calculation import ClosedCalculation
    from werewolf.actor_information import PersonalInformation
    from werewolf.seer_intervention import SeerObserver
    from werewolf.board_future import same_role_board
    from werewolf import board_future
    from werewolf.seer_future_uniform import TrueScanState
    from werewolf.calculation_budget import calculation_budget
    from werewolf.joint_value_sharing import independent_joint_values
    from unittest.mock import patch
    counts=Counter();trace=[];readbacks=[];phases={}
    def wrap(stack,owner,name):
        original=getattr(owner,name)
        def call(*args,**kwargs):counts[name]+=1;return original(*args,**kwargs)
        stack.enter_context(patch.object(owner,name,call))
    before=peak_bytes();start=time.perf_counter()
    with ExitStack() as stack,calculation_budget(4000000,max_seconds=20),independent_joint_values():
        if diagnostic:
            from werewolf.acquisition_provenance import AcquisitionLedger,UniformAcquisitionCache
            stack.enter_context(patch.object(AcquisitionLedger,'__init__',side_effect=AssertionError('ledger instantiated')))
            stack.enter_context(patch.object(AcquisitionLedger,'_owner_current',side_effect=AssertionError('owner recheck')))
            stack.enter_context(patch.object(AcquisitionLedger,'_groups_record',side_effect=AssertionError('frame recheck')))
            stack.enter_context(patch.object(UniformAcquisitionCache,'__init__',side_effect=AssertionError('proof cache')))
            for owner,name in ((board_future.GeneratedBoard,'roles'),(board_future,'condition_recipe'),(TrueScanState,'__eq__'),(TrueScanState,'__hash__')):wrap(stack,owner,name)
        setup=time.perf_counter()
        graph=make_role_filter_scope().graph if case=='five-owner-night' else base()[0]
        phases['common_setup_seconds']=time.perf_counter()-setup
        begin=time.perf_counter();calculation=ClosedCalculation(graph.data,max_seconds=20);node=calculation.root
        phases['closed_open_seconds']=time.perf_counter()-begin
        def keep(node):
            s=node.read();trace.append((s.public,s.public_state,s.past,s.private,s.observer,s.physical));readbacks.append(node);return node
        def death(node,target):
            rows=node.action(target)
            for row in rows:keep(row.node)
            trace.append(tuple((r.probability,r.node.read().public.winner) for r in rows))
            return next(r.node for r in rows if r.node.read().public.winner is None)
        finite=time.perf_counter();owner=1 if case=='five-owner-night' else 2
        h=next(h for h in node.read().private.hypotheses if h.roles[2]&(1<<(owner-1)))
        known=tuple(a for a in h.acquisitions if a.player==owner)
        mass,node=node.personal(PersonalInformation(owner,'seer',known));trace.append(mass);keep(node)
        node=death(node,2 if owner==1 else 1)
        mass,node=node.personal(SeerObserver(owner,known,2,4 if owner==1 else 5));trace.append(mass);keep(node)
        for row in node.wolf_choices():trace.append((row.mass,row.target));keep(row.node)
        if case=='seven-owner-three':
            node=death(node,4);rows=node.reports()
            for row in rows:trace.append((row.public_probability,row.probability));keep(row.node)
            node=next(r.node for r in rows if any(v.reporter==3 and v.target==1 and v.color=='black' for v in r.node.read().public.reports)
                and any(v.player==2 and v.acquired_day==2 and v.target==5 and v.color=='white' for v in r.node.read().past))
            node=death(node,5);node=death(node,3);final=node.reports()
            for row in final:trace.append((row.public_probability,row.probability));keep(row.node)
        else:
            from werewolf.closed_calculation import ReportBranch
            from fractions import Fraction
            final=(ReportBranch(Fraction(1),Fraction(1),node),)
        phases['finite_common_kernels_seconds']=time.perf_counter()-finite
        solve=time.perf_counter()
        for row in final:
            result=row.node.forecast();trace.append((row.public_probability,row.probability,result,tables(row.node.read(),result)))
        phases['Forecast_Table_seconds']=time.perf_counter()-solve
        elapsed=time.perf_counter()-start;peak=peak_bytes();states=calculation.stats();states['readout_entries']=len(readbacks)
        digest=hashlib.sha256(repr(trace).encode('utf-8')).hexdigest()
    comparisons=0;symmetries=0
    if diagnostic:
        for node in readbacks:
            s=node.read();request=node.export_request();cold=independent_cold(graph,request)
            assert same_role_board(cold.public,s.public) and same_role_board(cold.physical,s.physical)
            assert (cold.public_state,cold.private,cold.past,cold.observer)==(s.public_state,s.private,s.past,s.observer);comparisons+=1
            for group in node.groups:
                for p in group[1:]:
                    m=list(range(1,s.public.player_count+1));m[group[0]-1],m[p-1]=p,group[0]
                    other=moved_source(s,tuple(m))
                    assert same_role_board(s.public,other.public) and same_role_board(s.physical,other.physical)
                    assert (s.public_state,s.private,s.past)==(other.public_state,other.private,other.past);symmetries+=1
    return dict(case=case,mode='closed',diagnostic=diagnostic,body_seconds=elapsed,phase_seconds=phases,
        process_peak_before_bytes=before,process_peak_working_set_bytes_until_timed_end=peak,states=states,
        semantic_digest=digest,instrumented_calls=dict(counts),cold_reads=comparisons,independent_group_generators=symmetries,
        ledger_required=False,initial7_value_search=False)


def audit():
    from .measure_shared_transition import worker as ordinary
    rows=[]
    for case in ('five-owner-night','seven-owner-three'):
        reference=ordinary(case,False,True);closed=worker(case,True)
        assert closed['semantic_digest']==reference['semantic_digest']
        for key in ('values','actions','expansions','acquired','mornings','publications','policies','resolution_cache','readout_entries'):
            assert closed['states'][key]==reference['states'][key]
        assert closed['states']['saved_sources']==0
        rows.append(dict(case=case,ordinary=reference,closed=closed,complete_named_results_equal=True))
    from .closed_saved_day_fixture import audit as saved_day_audit
    saved=saved_day_audit()
    result=dict(status='verified',saved_day=saved,cases=rows,scope='initial immutable uniform H0 group snapshot; typed owner/action/report/choice generation; Forecast at <=4 alive',ledger_required=False,full_initial7_search=False)
    Path('benchmarks/player_match_groups/closed-calculation-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],cases=[dict(case=r['case'],states=r['closed']['states'],cold_reads=r['closed']['cold_reads'],groups=r['closed']['independent_group_generators'],calls=r['closed']['instrumented_calls']) for r in rows])),flush=True)
    return result


def run(repeats=5):
    from .measure_shared_transition import __name__ as ordinary_module
    start=time.perf_counter();runs=[];diagnostics=[]
    for case in ('five-owner-night','seven-owner-three'):
        for i in range(repeats):
            for mode in (('ordinary','closed') if i%2==0 else ('closed','ordinary')):
                if time.perf_counter()-start>180:raise TimeoutError('closed comparison exceeded 180 seconds')
                module=ordinary_module if mode=='ordinary' else __name__
                args=[sys.executable,'-m',module,'worker',case]+(['0'] if mode=='ordinary' else [])
                begin=time.perf_counter();p=subprocess.run(args,capture_output=True,text=True,timeout=25,check=True)
                row=json.loads(p.stdout);row.update(mode=mode,repeat=i,process_wall_seconds=time.perf_counter()-begin);runs.append(row)
        for mode in ('ordinary','closed'):
            module=ordinary_module if mode=='ordinary' else __name__
            args=[sys.executable,'-m',module,'worker',case]+(['0','diagnostic'] if mode=='ordinary' else ['diagnostic'])
            p=subprocess.run(args,capture_output=True,text=True,timeout=25,check=True);row=json.loads(p.stdout);row['mode']=mode;diagnostics.append(row)
    summaries=[]
    for case in ('five-owner-night','seven-owner-three'):
        selected=[r for r in runs if r['case']==case]
        assert len({r['semantic_digest'] for r in selected+[d for d in diagnostics if d['case']==case]})==1
        summary=dict(case=case,complete_named_results_equal=True)
        for mode in ('ordinary','closed'):
            group=[r for r in selected if r['mode']==mode]
            assert all(r['states']==group[0]['states'] for r in group)
            summary[mode]=dict(body_seconds_median=statistics.median(r['body_seconds'] for r in group),
                body_seconds_min=min(r['body_seconds'] for r in group),body_seconds_max=max(r['body_seconds'] for r in group),
                compute_seconds_median=statistics.median(sum(v for k,v in r['phase_seconds'].items() if k!='common_setup_seconds') for r in group),
                process_wall_seconds_median=statistics.median(r['process_wall_seconds'] for r in group),
                peak_bytes_median=statistics.median(r['process_peak_working_set_bytes_until_timed_end'] for r in group),
                peak_bytes_max=max(r['process_peak_working_set_bytes_until_timed_end'] for r in group),states=group[0]['states'],
                calls=next(d['instrumented_calls'] for d in diagnostics if d['case']==case and d['mode']==mode))
        for key in ('values','actions','expansions','acquired','mornings','publications','policies','resolution_cache','readout_entries'):
            assert summary['ordinary']['states'][key]==summary['closed']['states'][key]
        summary['closed_over_ordinary_time']=summary['closed']['body_seconds_median']/summary['ordinary']['body_seconds_median'];summaries.append(summary)
    result=dict(status='verified',repeats=repeats,recorded_at_utc=datetime.now(timezone.utc).isoformat(),seconds=time.perf_counter()-start,
        summaries=summaries,runs=runs,diagnostics=diagnostics,method='same two completed tasks, alternating fresh processes, uninstrumented timings; independent cold/group checks separate',
        source_hashes={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in ('werewolf/closed_calculation.py','werewolf/board_future.py','werewolf/information_set_forecast.py')},
        scope_note='Common fixture setup is included; closed open reconstructs its own immutable root while the ordinary fixture has a prepared root. Oracle/cold/export work is untimed.',
        ledger_required=False,full_initial7_search=False)
    Path('benchmarks/player_match_groups/closed-calculation-performance-results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],summaries=summaries,seconds=result['seconds'])),flush=True);return result


if __name__=='__main__':
    if sys.argv[1:2]==['worker']:print(json.dumps(worker(sys.argv[2],len(sys.argv)>3)),flush=True)
    elif '--measure' in sys.argv:run()
    else:audit()
