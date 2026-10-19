"""Fresh-process paired measurements of the existing shared experiment kernels.

No new evaluator. Timed children omit independent validation/instrumentation;
separate counted children do the same task and independent cold readbacks.
"""
import sys,json,time,subprocess,statistics,hashlib,platform
from datetime import datetime,timezone
from pathlib import Path
from dataclasses import replace
from fractions import Fraction as F
from collections import Counter
from contextlib import ExitStack


def worker(case,tracked,diagnostic=False):
    from .cut_out_publication_orbit_value_fixture import make_role_filter_scope,forecast,tables,same_role_board
    from .cut_out_publication_orbit_value import seed_structural
    from .cut_out_first_cycle_coverage import base
    from .cut_out_user_seven_source import ROOT_GROUPS
    from .cut_out_joint_night_forecast_fixture import moved_source
    from .cut_out_compact_terminal_fixture import independent_cold
    from .cut_out_uniform_game_fixture import peak_bytes
    from werewolf.actor_information import PersonalInformation
    from werewolf.seer_intervention import SeerObserver
    from werewolf.information_set_forecast import InformationSetForecast
    from werewolf.evaluation_branch import ActionInputs
    from werewolf.action_flow import resolve_action
    from werewolf.board_future import calculation_origin,remember
    from werewolf import board_future
    from werewolf.seer_future_uniform import TrueScanState
    from werewolf.calculation_budget import calculation_budget
    from werewolf.joint_value_sharing import independent_joint_values
    from unittest.mock import patch
    counts=Counter();trace=[];readbacks=[];phases={}
    def instrument(stack,owner,name):
        original=getattr(owner,name)
        def wrapped(*args,**kwargs):
            counts[name]+=1;return original(*args,**kwargs)
        stack.enter_context(patch.object(owner,name,wrapped))
    profiler=None
    if diagnostic:
        import cProfile
        profiler=cProfile.Profile();profiler.enable()
    before_peak=peak_bytes();start=time.perf_counter()
    with ExitStack() as stack,calculation_budget(4000000,max_seconds=20),independent_joint_values():
        if diagnostic:
            for owner,name in ((board_future.GeneratedBoard,'roles'),(board_future,'condition_recipe'),(TrueScanState,'__eq__'),(TrueScanState,'__hash__')):
                instrument(stack,owner,name)
        setup=time.perf_counter()
        if case=='five-owner-night':
            scope=make_role_filter_scope();graph=scope.graph;source=scope.source;request=scope.request
        else:
            graph,witness=base();source=graph.origin();request=graph.root
        e=InformationSetForecast(graph.engine.baseline.rules,graph.engine.baseline.strategy,exact_renaming=False,
            retire_uninformative_scans=False,track_acquisition_provenance=tracked)
        e.retain_joint_guard_history=True
        phases['common_setup_seconds']=time.perf_counter()-setup
        with calculation_origin(graph.data):
            audit=time.perf_counter()
            if tracked:
                if case=='five-owner-night':groups=seed_structural(scope).groups
                else:
                    groups=ROOT_GROUPS
                    for group in groups:
                        for p in group[1:]:
                            m=list(range(1,8));m[group[0]-1],m[p-1]=p,group[0]
                            other=moved_source(source,tuple(m))
                            assert same_role_board(source.public,other.public) and same_role_board(source.physical,other.physical)
                            assert (source.public_state,source.private,source.past)==(other.public_state,other.private,other.past)
                token=e.acquisition_provenance._register_audited_root(source.public,source,groups,(graph,graph.data),request=request)
                source=replace(source,provenance=token)
            source=replace(source,board_data=request);remember(e,request,source)
            phases['root_guarantee_and_registration_seconds']=time.perf_counter()-audit
            def keep(s):
                trace.append((s.public,s.public_state,s.past,s.private,s.observer,s.physical));readbacks.append(s)
                return s
            def death(s,target):
                payload=ActionInputs(s.public_state,s.past,s.private,s.observer,s.physical,provenance=s.provenance)
                ac,outs=resolve_action(s.public,payload,target,e.action_policy,terminal_payoffs=False)
                children=[(o.probability,keep(e.action_policy.project(s.public,ac,o,target))) for o in outs]
                trace.append(tuple((q,c.public.winner) for q,c in children))
                return next(c for q,c in children if c.public.winner is None)
            finite=time.perf_counter();owner=1 if case=='five-owner-night' else 2
            h=next(h for h in source.private.hypotheses if h.roles[2]&(1<<(owner-1)))
            known=tuple(a for a in h.acquisitions if a.player==owner)
            mass,source=e.personal_view(source,PersonalInformation(owner,'seer',known));trace.append(mass);keep(source)
            source=death(source,2 if owner==1 else 1)
            mass,source=e.personal_view(source,SeerObserver(owner,known,2,4 if owner==1 else 5));trace.append(mass);keep(source)
            choices=e.wolf_choices(source)
            for mass,c,target,proof in choices:trace.append((mass,target));keep(c)
            if case=='seven-owner-three':
                source=death(source,4)
                rows=e.report_children(source)
                for q,p,c in rows:trace.append((q,p));keep(c)
                source=next(c for q,p,c in rows if any(v.reporter==3 and v.target==1 and v.color=='black' for v in c.public.reports)
                    and any(v.player==2 and v.acquired_day==2 and v.target==5 and v.color=='white' for v in c.past))
                source=death(source,5);source=death(source,3)
                final=e.report_children(source)
                for q,p,c in final:trace.append((q,p));keep(c)
            else:final=((F(1),F(1),source),)
            phases['finite_common_kernels_seconds']=time.perf_counter()-finite
            solve=time.perf_counter()
            for q,p,c in final:
                result=forecast(e,c);trace.append((q,p,result,tables(c,result)))
            phases['Forecast_Table_seconds']=time.perf_counter()-solve
        elapsed=time.perf_counter()-start;peak=peak_bytes()
        if profiler is not None:profiler.disable()
        states=dict(values=len(e.values),actions=len(e.action_values),expansions=dict(e.expansions),
            acquired=len(e.acquired),mornings=len(e.mornings),publications=len(e.publication_values),
            policies=len(e.policies),saved_sources=len(e.board_sources),resolution_cache=len(e.board_action_kernels),readout_entries=len(readbacks))
        proof={} if e.acquisition_provenance is None else dict(e.acquisition_provenance.stats)
        # Full named semantics, including complete secret records. Provenance
        # and recipe carrier metadata are deliberately absent from the trace.
        digest=hashlib.sha256(repr(trace).encode('utf-8')).hexdigest()
    if diagnostic:
        for s in readbacks:
            cold=independent_cold(graph,s.board_data)
            assert same_role_board(cold.public,s.public) and same_role_board(cold.physical,s.physical)
            assert (cold.public_state,cold.private,cold.past,cold.observer)==(s.public_state,s.private,s.past,s.observer)
    group_shapes=[]
    if diagnostic and e.acquisition_provenance is not None:
        for source in readbacks:
            groups=e.acquisition_provenance.groups_for(source.provenance,source.public,source)
            live=() if groups is None else tuple(tuple(p for p in group if p in source.public.alive) for group in groups)
            group_shapes.append(dict(day=source.public.day,phase=source.public.phase,alive=len(source.public.alive),
                inherited=groups is not None,nontrivial_live_blocks=[len(g) for g in live if len(g)>1]))
    profiles=[]
    if profiler is not None:
        import pstats
        for (file,line,name),(cc,nc,tt,ct,callers) in pstats.Stats(profiler).stats.items():
            if file.endswith(('acquisition_provenance.py','board_future.py')) and (file.endswith('acquisition_provenance.py') or name in ('condition_recipe','register_origin','remember','roles','kernel_snapshot','reconstruct_information','reconstruct_child','reconstruct_publication')):
                profiles.append(dict(file=Path(file).name,function=name,calls=nc,self_seconds=tt,cumulative_seconds=ct))
    retained={} if e.acquisition_provenance is None else {k:len(v) for k,v in vars(e.acquisition_provenance).items() if isinstance(v,dict) or type(v).__name__=='WeakKeyDictionary'}
    return dict(diagnostic_group_shapes=group_shapes,profile=sorted(profiles,key=lambda r:r['self_seconds'],reverse=True),ledger_retained_entries=retained,case=case,tracked=tracked,diagnostic=diagnostic,body_seconds=elapsed,phase_seconds=phases,
        process_peak_working_set_bytes_until_timed_end=peak,process_peak_before_bytes=before_peak,
        states=states,proof_counts=proof,instrumented_calls=dict(counts),semantic_digest=digest,
        cold_reads=len(readbacks) if diagnostic else 0)


def run(repeats=5,*,output_path='benchmarks/player_match_groups/shared-transition-performance-boundary-results.json'):
    start=time.perf_counter();rows=[];diagnostics=[]
    for case in ('five-owner-night','seven-owner-three'):
        for i in range(repeats):
            for tracked in ((False,True) if i%2==0 else (True,False)):
                if time.perf_counter()-start>180:raise TimeoutError('bounded shared measurement exceeded 180 seconds')
                began=time.perf_counter()
                p=subprocess.run([sys.executable,'-m',__name__,'worker',case,str(int(tracked))],capture_output=True,text=True,timeout=25,check=True)
                row=json.loads(p.stdout);row.update(repeat=i,process_wall_seconds=time.perf_counter()-began);rows.append(row)
        for tracked in (False,True):
            p=subprocess.run([sys.executable,'-m',__name__,'worker',case,str(int(tracked)),'diagnostic'],capture_output=True,text=True,timeout=25,check=True)
            diagnostics.append(json.loads(p.stdout))
    summaries=[]
    for case in ('five-owner-night','seven-owner-three'):
        selected=[r for r in rows if r['case']==case]
        assert len({r['semantic_digest'] for r in selected+[r for r in diagnostics if r['case']==case]})==1
        result=dict(case=case,named_complete_results_equal=True)
        for tracked,label in ((False,'ordinary'),(True,'inherited')):
            group=[r for r in selected if r['tracked']==tracked]
            assert all(r['states']==group[0]['states'] for r in group)
            result[label]=dict(repeats=len(group),body_seconds_median=statistics.median(r['body_seconds'] for r in group),
                body_seconds_min=min(r['body_seconds'] for r in group),body_seconds_max=max(r['body_seconds'] for r in group),
                process_wall_seconds_median=statistics.median(r['process_wall_seconds'] for r in group),
                peak_working_set_bytes_median=statistics.median(r['process_peak_working_set_bytes_until_timed_end'] for r in group),
                peak_working_set_bytes_max=max(r['process_peak_working_set_bytes_until_timed_end'] for r in group),
                phase_seconds_median={k:statistics.median(r['phase_seconds'][k] for r in group) for k in group[0]['phase_seconds']},
                root_and_compute_seconds_median=statistics.median(sum(v for k,v in r['phase_seconds'].items() if k!='common_setup_seconds') for r in group),
                instrumented_calls=next(r['instrumented_calls'] for r in diagnostics if r['case']==case and r['tracked']==tracked),
                states=group[0]['states'],proof_counts=group[0]['proof_counts'])
        result['inherited_over_ordinary_time']=result['inherited']['body_seconds_median']/result['ordinary']['body_seconds_median']
        result['inherited_over_ordinary_peak']=result['inherited']['peak_working_set_bytes_median']/result['ordinary']['peak_working_set_bytes_median']
        result['paired_body_ratios']=[next(r['body_seconds'] for r in selected if r['repeat']==i and r['tracked'])/next(r['body_seconds'] for r in selected if r['repeat']==i and not r['tracked']) for i in range(repeats)]
        summaries.append(result)
    output=dict(python=sys.version,platform=platform.platform(),recorded_at_utc=datetime.now(timezone.utc).isoformat(),status='verified',repeats=repeats,seconds=time.perf_counter()-start,summaries=summaries,runs=rows,diagnostics=diagnostics,
        method='alternating paired fresh processes; uninstrumented timed work; separate counted/cold runs; setup/root audit/finite kernels/Forecast/Table included; digest and cold excluded from timed body and peak snapshot',
        baseline='same named task via ordinary common kernels; no artificial symmetry rechecks added to baseline; downstream group merges are not implemented by this path',
        memory='Windows process peak working set through timed end, including common imports and source setup; not Python heap or post-validation peak',
        full_initial7_search=False,MAX_evaluated=False)
    Path(output_path).write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=output['status'],summaries=summaries,seconds=output['seconds'])),flush=True)
    return output


def compare_boundary(reference_cwd,repeats=5):
    """Same-session old/current/ordinary runs; reference is a clean f930c44 tree."""
    root=Path.cwd();reference=Path(reference_cwd).resolve()
    if reference==root:raise ValueError('Separate reference checkout required')
    reference_sources={}
    for name in ('acquisition_provenance.py','board_future.py','information_set_forecast.py'):
        blob=subprocess.run(['git','show','f930c44:werewolf/'+name],cwd=root,capture_output=True,check=True).stdout
        actual=hashlib.sha256((reference/'werewolf'/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        if actual!=hashlib.sha256(blob.replace(b'\r\n',b'\n')).hexdigest():raise ValueError('Reference source differs from f930c44: '+name)
        reference_sources[name]=actual
    variants=(('ordinary',root,False),('before_inherited',reference,True),('optimized_inherited',root,True))
    start=time.perf_counter();rows=[];diagnostics=[]
    for case in ('five-owner-night','seven-owner-three'):
        for i in range(repeats):
            order=variants[i%3:]+variants[:i%3]
            for variant,cwd,tracked in order:
                if time.perf_counter()-start>180:raise TimeoutError('boundary comparison exceeded 180 seconds')
                began=time.perf_counter()
                child=subprocess.run([sys.executable,'-m',__name__,'worker',case,str(int(tracked))],cwd=cwd,capture_output=True,text=True,timeout=25,check=True)
                row=json.loads(child.stdout);row.update(variant=variant,repeat=i,process_wall_seconds=time.perf_counter()-began);rows.append(row)
        for variant,cwd,tracked in variants:
            child=subprocess.run([sys.executable,'-m',__name__,'worker',case,str(int(tracked)),'diagnostic'],cwd=cwd,capture_output=True,text=True,timeout=25,check=True)
            row=json.loads(child.stdout);row['variant']=variant;diagnostics.append(row)
    summaries=[]
    for case in ('five-owner-night','seven-owner-three'):
        selected=[r for r in rows if r['case']==case]
        assert len({r['semantic_digest'] for r in selected+[r for r in diagnostics if r['case']==case]})==1
        assert all(r['states']==selected[0]['states'] for r in selected)
        result=dict(case=case,named_results_equal=True,states_equal=True)
        for variant,cwd,tracked in variants:
            group=[r for r in selected if r['variant']==variant]
            diagnostic=next(r for r in diagnostics if r['case']==case and r['variant']==variant)
            result[variant]=dict(body_seconds_median=statistics.median(r['body_seconds'] for r in group),
                body_seconds_min=min(r['body_seconds'] for r in group),body_seconds_max=max(r['body_seconds'] for r in group),
                root_compute_seconds_median=statistics.median(sum(v for k,v in r['phase_seconds'].items() if k!='common_setup_seconds') for r in group),
                peak_bytes_median=statistics.median(r['process_peak_working_set_bytes_until_timed_end'] for r in group),
                peak_bytes_max=max(r['process_peak_working_set_bytes_until_timed_end'] for r in group),
                process_wall_seconds_median=statistics.median(r['process_wall_seconds'] for r in group),
                phase_seconds_median={k:statistics.median(r['phase_seconds'][k] for r in group) for k in group[0]['phase_seconds']},
                instrumented_calls=diagnostic['instrumented_calls'],
                validation_calls={name:sum(p['calls'] for p in diagnostic['profile'] if p['file']=='acquisition_provenance.py' and p['function']==name) for name in ('_groups_record','_owner_current','_same_references','_supported')},
                ledger_self_seconds=sum(p['self_seconds'] for p in diagnostic['profile'] if p['file']=='acquisition_provenance.py'),
                retained_entry_count=sum(n for k,n in diagnostic['ledger_retained_entries'].items() if k!='stats'),
                retained_entries=diagnostic['ledger_retained_entries'],states=group[0]['states'])
        result['optimized_over_ordinary']=result['optimized_inherited']['body_seconds_median']/result['ordinary']['body_seconds_median']
        result['optimized_over_before']=result['optimized_inherited']['body_seconds_median']/result['before_inherited']['body_seconds_median']
        summaries.append(result)
    sources={name:hashlib.sha256((root/'werewolf'/name).read_bytes()).hexdigest() for name in ('acquisition_provenance.py','board_future.py','information_set_forecast.py')}
    output=dict(status='verified',repeats=repeats,seconds=time.perf_counter()-start,reference_revision='f930c44',reference_cwd=str(reference),
        optimized_source_hashes=sources,reference_source_hashes_lf=reference_sources,runtime_acceleration_adopted=False,python=sys.version,platform=platform.platform(),recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        method='three rotating-order variants in fresh processes; same cases/task/timing boundaries as f930c44; diagnostic/profile/cold separate; no concurrent test load',
        summaries=summaries,runs=rows,diagnostics=diagnostics,full_initial7_search=False,scope_extended=False)
    Path('benchmarks/player_match_groups/shared-transition-performance-boundary-ab-results.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=output['status'],summaries=summaries,seconds=output['seconds'])),flush=True)
    return output


if __name__=='__main__':
    if sys.argv[1:2]==['worker']:print(json.dumps(worker(sys.argv[2],bool(int(sys.argv[3])),len(sys.argv)>4)),flush=True)
    else:run()
