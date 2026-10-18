"""Conditional exploratory initial7 comparison stopped at exactly3000 actions."""
import time
START=time.perf_counter()
import os,sys,json,threading,subprocess,statistics,hashlib
from pathlib import Path
from datetime import datetime,timezone


def worker(mode,repeat,output):
    from .cut_out_uniform_game_fixture import peak_bytes
    def watch():
        while True:
            if time.perf_counter()-START>9.7 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.025)
    threading.Thread(target=watch,daemon=True).start()
    from .cut_out_initial_publications import base,scope,clean,stats
    from .cut_out_deferred_diagnostics import DeferredInitialEngine
    from .cut_out_compact_terminal import CompactTerminalInitialEngine
    from .cut_out_initial_short_retention import retained
    from .cut_out_deferred_alternating import fingerprint_rows
    from werewolf.board_future import calculation_origin,remember
    from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded,budget_stop
    from werewolf.information_set_forecast import Pending
    class Reached(Exception):pass
    search_start=None
    class Probe:
        def act(self,b,s,past,target,private,observer,*,physical=None):
            value=super().act(b,s,past,target,private,observer,physical=physical)
            if len(self.scalar_actions)==3000 and not getattr(self,'_board_evidence_snapshot',False):
                self.fixed_time=time.perf_counter()-search_start;self.fixed_peak=peak_bytes()
                self.fixed_context=(b,s,past,private,observer,physical,target)
                raise Reached()
            return value
    class Off(Probe,DeferredInitialEngine):pass
    class On(Probe,CompactTerminalInitialEngine):pass
    row=dict(status='running',mode=mode,repeat=repeat,stop_goal_unique_actions=3000,calculation_limit_seconds=8,worker_limit_seconds=10,memory_limit_bytes=1500000000)
    path=Path(output);path.write_text(json.dumps(row,indent=2)+'\n')
    engine=None
    try:
        with calculation_budget(None,max_seconds=8):
            graph,w=base();source=scope(graph,w);engine=(On if mode=='on' else Off)(graph,witness=w);engine.capture_terminal=True
            row['root_signature']=fingerprint_rows([(source.public,source.public_state,source.private,source.past)])
            search_start=time.perf_counter();row['preparation_seconds']=search_start-START
            with calculation_origin(graph.data):
                remember(engine,graph.root,source);engine.solve(*source,physical=source.physical)
        row.update(status='unexpected_completion')
    except Reached:
        row.update(status='fixed_point_reached',search_seconds=engine.fixed_time,peak_at_fixed_point_bytes=engine.fixed_peak,context=clean(engine.fixed_context))
        row['context_sha256']=hashlib.sha256(json.dumps(row['context'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    except CalculationBudgetExceeded:row.update(status='unverified',stop=budget_stop())
    except Pending as error:row.update(status='unverified',reason=error.reason,first_refusal=clean(engine.first_refusal))
    if engine is not None:
        row.update(stats=stats(engine),retained=retained(engine),compact_actions=getattr(engine,'terminal_compact_actions',0))
        row['partial_memo_fingerprints']=dict(values=fingerprint_rows(engine.values.items()),actions=fingerprint_rows(engine.scalar_actions.items()))
    row.update(worker_seconds=time.perf_counter()-START,post_census_fingerprint_peak_bytes=peak_bytes(),initial_Forecast_Table_joint_branch_mass_cold_complete=False)
    path.write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({k:row[k] for k in ('status','mode','repeat','search_seconds','peak_at_fixed_point_bytes','worker_seconds') if k in row}),flush=True)


def run():
    finite=json.loads(Path('benchmarks/player_match_groups/compact-terminal-alternating-results.json').read_text())
    assert finite['status']=='verified' and finite['all_mode_repeat_contents_equal']
    # Preserve the original5% magnitude gate and its failure. Four positive
    # paired directions in BOTH cases, exact content equality, and no material
    # time/memory regression justify only this bounded exploratory measurement.
    for case in finite['cases']:
        assert finite['short_initial_gate_results'][case]['paired_Forecast_wins']==4
        s=finite['summary'][case]
        assert s['on']['phases']['Forecast']<s['off']['phases']['Forecast']
        assert all(s['on'][k]<=1.05*s['off'][k] for k in ('result_Table_cold_seconds','all_outputs_first_and_repeated_seconds','peak_through_result_cold_bytes','peak_after_all_outputs_bytes'))
    path=Path('benchmarks/player_match_groups/compact-terminal-initial3000-results.json')
    result=dict(status='running',recorded_utc=datetime.now(timezone.utc).isoformat(),order=['off','on','on','off'],runs=[],original_5pct_effect_gate_passed=finite['short_initial_eligible'],
        decision='Exploratory only: both cases4/4 paired Forecast improvements and no material endpoint regression;7-mid magnitude below prespecified5%, retained as limitation, no adoption/speedup conclusion')
    def save():path.write_text(json.dumps(result,indent=2)+'\n')
    save()
    for index,mode in enumerate(result['order']):
        repeat=1 if index<2 else 2;output='benchmarks/player_match_groups/compact-terminal-initial3000-'+mode+'-'+str(repeat)+'.json';begin=time.perf_counter()
        proc=subprocess.run([sys.executable,'-B','-m',__spec__.name,mode,str(repeat),output],capture_output=True,text=True,timeout=10)
        if proc.returncode:
            result.update(status='unverified',failure=dict(mode=mode,repeat=repeat,stdout=proc.stdout,stderr=proc.stderr));save();raise RuntimeError(result['failure'])
        row=json.loads(Path(output).read_text());row['process_wall_seconds']=time.perf_counter()-begin;result['runs'].append(row);save();print(proc.stdout,flush=True)
        if row['status']!='fixed_point_reached':result['status']='unverified';save();return
    first=result['runs'][0]
    assert all(r['stats']['actions']==3000 and (r['stats']['values'],r['stats']['generated'],r['context_sha256'],r['root_signature'],r['partial_memo_fingerprints'])==(first['stats']['values'],first['stats']['generated'],first['context_sha256'],first['root_signature'],first['partial_memo_fingerprints']) for r in result['runs'])
    result.update(status='matched_work_verified',initial_full_outputs_complete=False,
        summary={mode:{key:statistics.median(r[key] for r in result['runs'] if r['mode']==mode) for key in ('search_seconds','peak_at_fixed_point_bytes','worker_seconds')} for mode in ('off','on')})
    save();print('MATCHED_WORK_VERIFIED',flush=True)

if __name__=='__main__':
    if len(sys.argv)>1:worker(sys.argv[1],int(sys.argv[2]),sys.argv[3])
    else:run()
