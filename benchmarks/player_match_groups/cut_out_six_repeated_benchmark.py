"""Isolated six-player2-case/3-mode repeats, identical Table + one cold label."""
import time
_MODULE_START=time.perf_counter()
import sys,os,json,threading,subprocess,hashlib,statistics
from pathlib import Path
from contextlib import ExitStack,contextmanager
from functools import wraps


@contextmanager
def group_clock(enabled):
    data=dict(seconds=0.,calls={},depth=0)
    if not enabled:
        yield data;return
    from unittest.mock import patch
    from .cut_out_uniform_game import CutOutUniformEngine
    from .cut_out_inherited_groups import InheritedGroupRegistry
    def timed(method,label):
        @wraps(method)
        def run(*args,**kwargs):
            outer=data['depth']==0;start=time.perf_counter() if outer else 0.
            data['depth']+=1;data['calls'][label]=data['calls'].get(label,0)+1
            try:return method(*args,**kwargs)
            finally:
                data['depth']-=1
                if outer:data['seconds']+=time.perf_counter()-start
        return run
    with ExitStack() as stack:
        for owner,names in ((InheritedGroupRegistry,('__init__','acquisition','action','publication','private_groups')),
                            (CutOutUniformEngine,('inherited_value_groups','legacy_large_groups'))):
            for name in names:stack.enter_context(patch.object(owner,name,timed(getattr(owner,name),owner.__name__+'.'+name)))
        yield data


def worker(case,mode,profile,launch):
    from .cut_out_uniform_game_fixture import peak_bytes
    watch_start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-watch_start>60 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    from dataclasses import replace
    from .cut_out_two_nights import spec
    from .cut_out_model_a import adapt_six_model_a
    from .cut_out_saved_recipes import SavedCutOutGraph
    from .cut_out_six_inherited import evaluate as new_evaluate
    from .cut_out_uniform_game import evaluate as old_evaluate
    from .cut_out_max_fixture import complete_table
    from .partitioned_match_groups import UnsupportedPartition
    from werewolf.seer_acquisition import SeerReport
    from werewolf.exact import action_outcomes
    from werewolf.board_future import ActionEvidence,kernel_snapshot,outcome_key,reconstruction_kernel_reuse
    from werewolf.calculation_budget import calculation_budget
    with group_clock(profile) as clock:
        ready=time.perf_counter();imports_peak=peak_bytes()
        source_spec=spec()
        if case=='medium':source_spec=replace(source_spec,mediums=1,claims=('seer','medium','medium','latent','latent','latent'),reports=(SeerReport(1,1,1,4,'white'),))
        source=SavedCutOutGraph(adapt_six_model_a(source_spec));root=source.origin();prior=time.perf_counter()
        before_group=clock['seconds']
        result=(new_evaluate(source) if mode=='new' else old_evaluate(source,official_reference=mode=='labelled'))
        if isinstance(result,UnsupportedPartition):raise AssertionError(result)
        forecast,engine=result;evaluated=time.perf_counter();eval_group=clock['seconds']-before_group
        assert not engine.capture_terminal and not engine.terminal_records
        table=complete_table(source,forecast,None);formatted=time.perf_counter()
        # Same literalP6 execution, conditional on a nonterminal observation.
        # This is one requested branch, not a traversal of all terminal labels.
        outcome=next(o for o in action_outcomes(root.physical,6,source_spec.rules,source_spec.strategy) if o.board.winner is None)
        request=source.root.child(ActionEvidence(kernel_snapshot(engine),6,outcome_key(outcome),False),
                                  (outcome.board.day,outcome.board.phase,outcome.board.alive))
        prepared=time.perf_counter();before_cold_group=clock['seconds']
        with calculation_budget(1000000,max_seconds=25),reconstruction_kernel_reuse(False):child=request.roles()
        restored=time.perf_counter();cold_group=clock['seconds']-before_cold_group
        assert child.public.history[-1].target==6 and child.public.winner is None
        assert request.origin is source.origin and len(child.public.history)==1
        group_seconds=clock['seconds'];cold_endpoint_peak=peak_bytes()
    # Full immutable weighted output fingerprints are emitted after the endpoint.
    def digest(value):return hashlib.sha256(repr(value).encode()).hexdigest()
    signatures=dict(root_public=digest(root.public_state),root_physical=digest(root.private),forecast=digest(forecast),table=digest(table),
        individual_branch=digest((child.public,child.public_state,child.past,child.private,child.observer,child.physical,outcome.probability)))
    phases=dict(startup_import_seconds=ready-launch,prior_and_initial_group_seconds=prior-ready,
        forecast_total_seconds=evaluated-prior,Table_seconds=formatted-evaluated,
        individual_branch_request_seconds=prepared-formatted,individual_branch_cold_seconds=restored-prepared)
    endpoint=restored-launch
    assert all(v>=0 for v in phases.values()) and abs(sum(phases.values())-endpoint)<.001
    row=dict(case=case,mode=mode,profile=profile,signatures=signatures,village_win=str(forecast.village_win),
        end_to_end_startup_to_cold_branch_seconds=endpoint,phases=phases,
        initial_group_subset_seconds=source.engine.stats.get('partition_seconds',0.),
        native_partial_group_counter_seconds=engine.costs['cut_out_seconds'],
        instrumented_group_seconds=(group_seconds if profile else None),
        instrumented_group_within_forecast_seconds=(eval_group if profile else None),
        instrumented_forecast_other_than_group_seconds=(evaluated-prior-eval_group if profile else None),
        instrumented_group_within_cold_seconds=(cold_group if profile else None),
        instrumented_group_calls=(clock['calls'] if profile else None),
        peak_working_set_bytes=cold_endpoint_peak,post_fingerprint_peak_working_set_bytes=peak_bytes(),post_import_peak_working_set_bytes=imports_peak,
        action_requests=engine.costs['action_requests'],action_evaluations=engine.costs['action_evaluations'],
        terminal_tree_materialized=False,individual_execution_target=6,branch_observation_probability=str(outcome.probability),
        scope='existing6 uniform two-night Forecast + complete public Table + one first-day literalP6 nonterminal cold branch',
        group_timing_note='group maintenance is an overlapping subset of forecast/cold, never additive; complete group clock only in separate profile samples')
    print('RESULT_JSON '+json.dumps(row),flush=True)


def summarize(rows):
    def stats(values):return dict(min=min(values),median=statistics.median(values),max=max(values))
    result={}
    for case in ('public','medium'):
        result[case]={}
        for mode in ('new','old-root','labelled'):
            selected=[r for r in rows if r['case']==case and r['mode']==mode and not r['profile']]
            result[case][mode]=dict(repeats=len(selected),end_to_end_seconds=stats([r['end_to_end_startup_to_cold_branch_seconds'] for r in selected]),
                process_wall_seconds=stats([r['process_wall_seconds'] for r in selected]),
                phases={k:stats([r['phases'][k] for r in selected]) for k in selected[0]['phases']},
                peak_working_set_bytes=stats([r['peak_working_set_bytes'] for r in selected]))
    return result


def main():
    if len(sys.argv)>1:return worker(sys.argv[1],sys.argv[2],sys.argv[3]=='profile',float(sys.argv[4]))
    from datetime import datetime,timezone
    start=time.monotonic();rows=[];logs=[];fingerprints={}
    def execute(case,mode,profile,repeat):
        remaining=300-(time.monotonic()-start)
        if remaining<=0:raise RuntimeError('300s overall deadline')
        launch=time.perf_counter()
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,case,mode,'profile' if profile else 'native',str(launch)],capture_output=True,text=True,timeout=min(60,remaining))
        wall=time.perf_counter()-launch;logs.append(run.stdout+run.stderr)
        if run.returncode:raise RuntimeError(logs[-1])
        r=json.loads(next(s[len('RESULT_JSON '):] for s in run.stdout.splitlines() if s.startswith('RESULT_JSON ')))
        r.update(repeat=repeat,process_wall_seconds=wall)
        expected=fingerprints.setdefault(case,r['signatures'])
        assert r['signatures']==expected,(case,mode,profile,'semantic output differs')
        rows.append(r)
    modes=('new','old-root','labelled')
    for case_index,case in enumerate(('public','medium')):
        for repeat in range(3):
            offset=(repeat+case_index)%3;order=modes[offset:]+modes[:offset]
            for mode in order:execute(case,mode,False,repeat+1)
            print('native '+case+' repeat '+str(repeat+1)+' matched',flush=True)
    for case in ('public','medium'):
        for mode in modes:execute(case,mode,True,1)
        print('separate profile '+case+' matched',flush=True)
    Path('.artifacts/six-repeated-benchmark.log').write_text('\n'.join(logs),encoding='utf-8')
    source_paths=['benchmarks/player_match_groups/cut_out_six_repeated_benchmark.py','benchmarks/player_match_groups/cut_out_six_inherited.py','benchmarks/player_match_groups/cut_out_uniform_game.py','benchmarks/player_match_groups/cut_out_inherited_groups.py']
    record=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),tested_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        cases=rows,summary=summarize(rows),all_outputs_equal_per_case=True,
        limits=dict(per_process_seconds=60,overall_seconds=300,peak_working_set_bytes=1500000000),
        total_driver_seconds=time.monotonic()-start,native_processes=18,separate_profile_processes=6,
        clock='Windows shared monotonic perf_counter; parent launch marker is passed to each child',
        memory_scope='primary peak is captured at cold endpoint before output fingerprints; later diagnostic peak recorded separately; Windows PeakWorkingSet is RSS-equivalent',
        interpretation='3 independent fresh-process samples per case/mode, rotated order. Native speed/RSS and instrumented maintenance profiles are separate. No cross-mode engine/cache memory sharing.',
        excluded='all terminal tree/reference assertions/full suite; no UI/server/deploy; no registry bridge implementation',
        source_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in source_paths})
    Path('benchmarks/player_match_groups/cut-out-six-repeated-benchmark-results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(total_driver_seconds=record['total_driver_seconds'],native_processes=18,separate_profile_processes=6)),flush=True)

if __name__=='__main__':main()
