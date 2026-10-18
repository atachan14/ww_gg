"""Revised16 correctness requests + three lightweight, separate e2e pairs."""
import time
_PROCESS_START=time.perf_counter()
import sys,os,json,threading,subprocess,hashlib
from pathlib import Path
from contextlib import ExitStack,contextmanager
from unittest.mock import patch


def watchdog():
    from .cut_out_uniform_game_fixture import peak_bytes
    start=time.monotonic()
    def watch():
        while True:
            if time.monotonic()-start>60 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.1)
    threading.Thread(target=watch,daemon=True).start()
    return peak_bytes


@contextmanager
def actual_path_monitor():
    # Load oracle aliases before installing any guards.
    from . import cut_out_candidate_context_fixture
    from .cut_out_uniform_game import CutOutUniformEngine
    from .cut_out_no_read_night_max import NoReadNightMaxEngine
    from .cut_out_active_report_max import ActiveReportMaxEngine
    from werewolf.information_set_forecast import InformationSetForecast
    stats=dict(guarded_entries=0,recursive_canonical_calls=0,recursive_CandidateRules_calls=0,root_rebuild_calls=0)
    def fail(kind):
        def blocked(*args,**kwargs):
            stats[kind]+=1
            raise AssertionError('forbidden in actual grouped path: '+kind)
        return blocked
    def guarded(method):
        def run(self,*args,**kwargs):
            if getattr(self,'inherited_groups',None) is None:return method(self,*args,**kwargs)
            stats['guarded_entries']+=1
            with ExitStack() as scope:
                scope.enter_context(patch('werewolf.exact_renaming.canonical_key',side_effect=fail('recursive_canonical_calls')))
                scope.enter_context(patch('werewolf.candidate_policy.canonical_key',side_effect=fail('recursive_canonical_calls')))
                scope.enter_context(patch('werewolf.candidate_policy.CandidateRules',side_effect=fail('recursive_CandidateRules_calls')))
                return method(self,*args,**kwargs)
        return run
    root_method=CutOutUniformEngine.legacy_large_groups
    def root(self,b,*args,**kwargs):
        if b.player_count in (4,5):return fail('root_rebuild_calls')()
        return root_method(self,b,*args,**kwargs)
    with ExitStack() as stack:
        for owner,name in ((CutOutUniformEngine,'act'),(CutOutUniformEngine,'solve'),
                           (CutOutUniformEngine,'wolf_policy'),(CutOutUniformEngine,'morning'),
                           (NoReadNightMaxEngine,'wolf_policy'),(ActiveReportMaxEngine,'wolf_policy')):
            stack.enter_context(patch.object(owner,name,guarded(getattr(owner,name))))
        stack.enter_context(patch.object(CutOutUniformEngine,'legacy_large_groups',root))
        yield stats
    assert stats['recursive_canonical_calls']==stats['recursive_CandidateRules_calls']==stats['root_rebuild_calls']==0


def named_worker(target):
    peak=watchdog()
    import unittest
    sys.path.insert(0,str(Path('tests').resolve()))
    suite=unittest.defaultTestLoader.loadTestsFromName(target)
    with actual_path_monitor() as stats:
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():raise SystemExit(1)
    print('RESULT_JSON '+json.dumps(dict(target=target,tests=result.testsRun,monitor=stats,
        worker_seconds=time.perf_counter()-_PROCESS_START,peak_working_set_bytes=peak())),flush=True)


def timing_worker(case,mode):
    peak=watchdog();begin=_PROCESS_START
    if case=='uniform4':
        from .cut_out_model_a import InitialModelASpec,adapt_model_a
        from .cut_out_saved_recipes import SavedCutOutGraph
        from .cut_out_uniform_game import evaluate
        from werewolf.exact import Rules
        from werewolf.seer_acquisition import SeerReport
        def build():return SavedCutOutGraph(adapt_model_a(InitialModelASpec(4,('seer','latent','latent','latent'),True,mediums=0,rules=Rules(initial_seer='random_white'),reports=(SeerReport(1,1,1,3,'white'),))))
    elif case=='seer5':
        from .cut_out_max_game import graph,evaluate
        def build():return graph(5,1,'max',fake_reports='max')
    else:
        from .cut_out_active_report_max import graph,evaluate
        def build():return graph(5,'random_white')
    from .cut_out_max_fixture import complete_table
    from .partitioned_match_groups import UnsupportedPartition
    from werewolf.board_future import ActionEvidence,reconstruction_kernel_reuse
    imported=time.perf_counter()
    source=build();root=source.origin();prior=time.perf_counter()
    result=evaluate(source,official_reference=mode=='old')
    if isinstance(result,UnsupportedPartition):raise AssertionError(result)
    forecast,engine=result;evaluated=time.perf_counter()
    table=complete_table(source,forecast,None);formatted=time.perf_counter()
    target=3 if case=='active5' else 2
    request=next(r for r in engine.board_sources.values() if len(r.history)==1
                 and isinstance(r.history[0],ActionEvidence) and r.history[0].target==target and r.facts[1]=='night')
    with reconstruction_kernel_reuse(False):child=request.roles()
    restored=time.perf_counter()
    # Semantic fingerprints are outside the timed endpoint. Full immutable
    # weighted public/private laws and past are included, never object IDs.
    def digest(value):return hashlib.sha256(repr(value).encode()).hexdigest()
    signature=dict(forecast=digest(forecast),table=digest(table),
        root_joint=digest(root.public_state),branch=digest((child.public,child.public_state,child.past,child.private,child.observer,child.physical)))
    print('RESULT_JSON '+json.dumps(dict(case=case,mode=mode,signature=signature,village_win=str(forecast.village_win),
        phases=dict(startup_and_import_seconds=imported-begin,constructed_prior_seconds=prior-imported,
            forecast_including_root_actions_horizons_seconds=evaluated-prior,table_seconds=formatted-evaluated,
            one_cold_branch_seconds=restored-formatted),worker_start_to_branch_seconds=restored-begin,
        phase_measurement='one fresh process, unmocked; startup begins at module import, parent process wall also recorded',
        branch_execution_target=target,peak_working_set_bytes=peak())),flush=True)


def main():
    if len(sys.argv)>1:
        if sys.argv[1]=='named':return named_worker(sys.argv[2])
        return timing_worker(sys.argv[2],sys.argv[3])
    from datetime import datetime,timezone
    start=time.monotonic();plan_path=Path('benchmarks/player_match_groups/integration-review-plan.json')
    plan=json.loads(plan_path.read_text(encoding='utf-8'));rows=[];logs=[];timings=[]
    def execute(args):
        remaining=270-(time.monotonic()-start)
        if remaining<=0:raise RuntimeError('shared270s deadline exhausted')
        begin=time.monotonic()
        run=subprocess.run([sys.executable,'-B','-m',__spec__.name,*args],capture_output=True,text=True,timeout=min(60,remaining))
        wall=time.monotonic()-begin;logs.append(run.stdout+run.stderr)
        if run.returncode:raise RuntimeError(logs[-1])
        row=json.loads(next(s[len('RESULT_JSON '):] for s in run.stdout.splitlines() if s.startswith('RESULT_JSON ')))
        row['fresh_process_wall_seconds']=wall
        return row
    for suite in plan['suites']:
        if suite['id'] not in plan['selected_suites']:continue
        for kind,target in suite['requests']:
            row=execute([kind,target]);row['suite']=suite['id'];rows.append(row)
            print('passed '+target.rsplit('.',1)[-1],flush=True)
    correctness_seconds=time.monotonic()-start
    for case in plan['timing_cases']:
        pair=[execute(['timing',case,mode]) for mode in ('new','old')]
        assert pair[0]['signature']==pair[1]['signature'],(case,pair)
        timings.append(dict(case=case,new=pair[0],old=pair[1],all_semantic_fingerprints_equal=True,
            old_over_new_process_wall_ratio=pair[1]['fresh_process_wall_seconds']/pair[0]['fresh_process_wall_seconds']))
        print('timed separate pair '+case,flush=True)
    Path('.artifacts/integration-checkpoint-final.log').write_text('\n'.join(logs),encoding='utf-8')
    record=dict(recorded_utc=datetime.now(timezone.utc).isoformat(),tested_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        correctness_requests=rows,correctness_tests=sum(r['tests'] for r in rows),correctness_suite_seconds=correctness_seconds,
        end_to_end_pairs=timings,total_driver_seconds=time.monotonic()-start,
        limits=dict(per_worker_seconds=60,overall_seconds=270,working_set_bytes=1500000000),
        scope='existing4/5 comparison only; no normal UI publication',
        interpretation='correctness suite is not product latency; e2e pairs are separate single unmocked cold-process samples, not a benchmark distribution',
        explicit_old_oracle='OfficialLabelledEngine and H1 read-control are intentional references outside actual-path monitor',
        no_heavy_measurement=True,full_project_suite_run=False,existing62_run=False)
    Path('benchmarks/player_match_groups/integration-checkpoint-results.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    plan.update(executed=True,numerical_code_changed=False,validation='revised16 executed; actual-path zero-call guards and three separate e2e pairs passed',
        execution_result='benchmarks/player_match_groups/integration-checkpoint-results.json')
    plan_path.write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(correctness_tests=record['correctness_tests'],correctness_suite_seconds=correctness_seconds,total_driver_seconds=record['total_driver_seconds'])),flush=True)

if __name__=='__main__':main()
