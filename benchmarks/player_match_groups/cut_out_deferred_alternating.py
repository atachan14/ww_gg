"""Alternating fresh-worker comparison of eager/deferred diagnostic modes."""
import time
START=time.perf_counter()
import sys,os,json,threading,hashlib,statistics,subprocess
from pathlib import Path
from datetime import datetime,timezone


def fingerprint_rows(rows):
    from .cut_out_initial_publications import clean
    digest=hashlib.sha256();count=0
    for row in rows:
        digest.update(json.dumps(clean(row),sort_keys=True,separators=(',',':')).encode());digest.update(b'\n');count+=1
    return dict(rows=count,sha256=digest.hexdigest())


def worker(case,mode,repeat):
    from .cut_out_uniform_game_fixture import peak_bytes
    def watch():
        while True:
            if time.perf_counter()-START>120 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.05)
    threading.Thread(target=watch,daemon=True).start()
    from dataclasses import replace
    from types import SimpleNamespace
    from .cut_out_deferred_diagnostics import EagerSmallEngine,DeferredSmallEngine
    from .cut_out_model_a import adapt_model_a,adapt_six_model_a
    from .cut_out_saved_recipes import SavedCutOutGraph
    from .cut_out_uniform_game import evaluate
    from .cut_out_max_fixture import complete_table
    from .cut_out_live_medium_forecast import cold
    from .partitioned_match_groups import UnsupportedPartition
    from .cut_out_initial_publications import clean
    from werewolf.calculation_budget import calculation_budget
    from werewolf.board_future import same_role_board
    sys.path.insert(0,str(Path('tests').resolve()))
    from test_cut_out_model_a import cases
    from test_cut_out_morning import medium_spec
    from .cut_out_two_nights import spec as six_spec
    from werewolf.seer_acquisition import SeerReport
    imports=time.perf_counter()
    with calculation_budget(4000000,max_seconds=30):
        spec=cases(4)['single'] if case=='four' else medium_spec() if case=='five-medium' else replace(six_spec(),mediums=1,claims=('seer','medium','medium','latent','latent','latent'),reports=(SeerReport(1,1,1,4,'white'),))
        graph=SavedCutOutGraph((adapt_six_model_a if case=='six-medium' else adapt_model_a)(spec))
        root=graph.origin();prepared=time.perf_counter()
        result=evaluate(graph,engine_class=DeferredSmallEngine if mode=='deferred' else EagerSmallEngine,capture_terminal=True)
        if isinstance(result,UnsupportedPartition):raise RuntimeError(result.reason)
        forecast,engine=result;evaluated=time.perf_counter()
        table=complete_table(graph,forecast,None);formatted=time.perf_counter()
        # Same deterministic three depths, using distinct saved requests. No
        # terminal-tree replay or engine from the opposite mode is retained.
        requests=list({id(r):r for r in engine.board_sources.values()}.values())
        requests.sort(key=lambda r:(len(r.history),repr(r.facts),repr(tuple((type(op).__name__,getattr(op,'target',None),getattr(op,'observation',None)) for op in r.history))))
        selected=[requests[i] for i in sorted({0,len(requests)//2,len(requests)-1})]
        cold_rows=[]
        for request in selected:
            warm=request.roles();fresh=cold(SimpleNamespace(registry=graph),request)
            assert warm.public_state==fresh.public_state and warm.private==fresh.private
            assert warm.past==fresh.past and warm.observer==fresh.observer
            assert same_role_board(warm.public,fresh.public) and same_role_board(warm.physical,fresh.physical)
            cold_rows.append((warm.public,warm.public_state,warm.past,warm.private,warm.observer,warm.physical))
        cold_done=time.perf_counter();value_peak=peak_bytes()
        assert mode!='deferred' or engine.deferred_ledger.materialized==0
        diagnostics=lambda:{name:fingerprint_rows(getattr(engine,name)) for name in ('full_branch_records','terminal_records','branch_records')}
        first=diagnostics();opened=time.perf_counter();open_peak=peak_bytes()
        second=diagnostics();reopened=time.perf_counter();assert first==second
        repeat_peak=peak_bytes()
        signatures=dict(root=fingerprint_rows([(root.public,root.public_state,root.private,root.past)]),forecast=fingerprint_rows([forecast]),table=fingerprint_rows([table]),cold=fingerprint_rows(cold_rows),diagnostics=first)
    phases=dict(imports=imports-START,preprocessing=prepared-imports,Forecast=evaluated-prepared,Table=formatted-evaluated,representative_cold=cold_done-formatted,first_diagnostic_open=opened-cold_done,repeated_diagnostic_open=reopened-opened)
    row=dict(status='verified',case=case,mode=mode,repeat=repeat,signatures=signatures,phases=phases,
        preprocessing_through_full_result_and_cold_seconds=cold_done-START,
        through_first_open_seconds=opened-START,through_repeated_open_seconds=reopened-START,
        peak_through_result_and_cold_bytes=value_peak,peak_through_first_open_bytes=open_peak,peak_through_repeated_open_bytes=repeat_peak,
        post_fingerprint_peak_bytes=peak_bytes(),worker_seconds=time.perf_counter()-START,
        values=len(engine.values),actions=len(engine.scalar_actions),sources=len(engine.board_sources),
        retained_resolutions=len(engine.board_action_kernels),representative_cold_reads=len(cold_rows),
        diagnostic_first_repeat_equal=True,full_initial7_search=False,
        scope='one engine per fresh worker; complete Forecast/Table/3 representative cold then first/repeated diagnostic opens')
    print('RESULT_JSON '+json.dumps(row),flush=True)


def run():
    path=Path('benchmarks/player_match_groups/deferred-diagnostics-alternating-results.json')
    result=dict(status='running',recorded_utc=datetime.now(timezone.utc).isoformat(),runs=[],worker_calculation_limit_seconds=30,worker_wall_limit_seconds=120,worker_memory_limit_bytes=1500000000,
        order='four rounds per case: eager/deferred, deferred/eager, eager/deferred, deferred/eager',cases=['four','five-medium','six-medium'])
    for case in result['cases']:
        for repeat in range(1,5):
            for mode in (('eager','deferred') if repeat%2 else ('deferred','eager')):
                begin=time.perf_counter()
                proc=subprocess.run([sys.executable,'-B','-m',__spec__.name,case,mode,str(repeat)],capture_output=True,text=True,timeout=121)
                if proc.returncode:
                    result.update(status='unverified',failed=dict(case=case,mode=mode,repeat=repeat,returncode=proc.returncode,stdout=proc.stdout,stderr=proc.stderr));path.write_text(json.dumps(result,indent=2)+'\n');raise RuntimeError(result['failed'])
                row=json.loads(next(s[12:] for s in proc.stdout.splitlines() if s.startswith('RESULT_JSON ')));row['process_wall_seconds']=time.perf_counter()-begin
                result['runs'].append(row);path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:row[k] for k in ('case','mode','repeat','preprocessing_through_full_result_and_cold_seconds','through_repeated_open_seconds','peak_through_result_and_cold_bytes')}),flush=True)
    summary={}
    for case in result['cases']:
        rows=[r for r in result['runs'] if r['case']==case]
        assert all(r['signatures']==rows[0]['signatures'] for r in rows)
        summary[case]={mode:{key:dict(median=statistics.median(r[key] for r in rows if r['mode']==mode),min=min(r[key] for r in rows if r['mode']==mode),max=max(r[key] for r in rows if r['mode']==mode)) for key in ('preprocessing_through_full_result_and_cold_seconds','through_first_open_seconds','through_repeated_open_seconds','peak_through_result_and_cold_bytes','peak_through_repeated_open_bytes')} for mode in ('eager','deferred')}
    result.update(status='verified',summary=summary,all_mode_repeat_outputs_equal=True,total_workers=len(result['runs']))
    path.write_text(json.dumps(result,indent=2)+'\n');print('ALL_VERIFIED',flush=True)

if __name__=='__main__':
    if len(sys.argv)>1:worker(sys.argv[1],sys.argv[2],int(sys.argv[3]))
    else:run()
