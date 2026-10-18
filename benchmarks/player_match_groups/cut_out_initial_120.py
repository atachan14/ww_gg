"""One authorized <=120s initial7 trial, then reference only after completion."""
import time
START=time.perf_counter()
import os,sys,json,threading,subprocess
from pathlib import Path
from datetime import datetime,timezone


def worker(kind):
    from .cut_out_initial_publications import (base,scope,InitialReferenceEngine,clean,stats,completed_evidence)
    from .cut_out_deferred_diagnostics import DeferredInitialEngine
    from .cut_out_initial_short_retention import retained
    from .cut_out_uniform_game_fixture import peak_bytes
    from werewolf.board_future import calculation_origin,remember
    from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded,budget_stop,budget_usage
    from werewolf.information_set_forecast import Pending
    from werewolf.model_a_public import horizon_for_action
    from werewolf.forecast_result import Forecast
    from .cut_out_max_fixture import complete_table
    path=Path('benchmarks/player_match_groups/initial7-120-'+kind+'-trial.json')
    engine=None;graph=None;source=None;last_live=START
    row=dict(status='running',kind=kind,diagnostics='deferred' if kind=='new' else 'eager',
        recorded_utc=datetime.now(timezone.utc).isoformat(),hard_wall_seconds=120,calculation_seconds=115,
        reserve_note='five seconds reserved for checkpoint persistence, retained-object census and process shutdown',memory_limit_bytes=1500000000,
        comparison_scope=dict(Forecast=False,Table=False,joint=False,branches=False,representative_cold=False))
    def atomic(value):
        tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,indent=2)+'\n');tmp.replace(path)
    def checkpoint():
        row.update(elapsed_seconds=time.perf_counter()-START,peak_working_set_bytes=peak_bytes(),stats=stats(engine) if engine is not None else {},
            last_exact_inputs=clean(getattr(engine,'last_exact_inputs',None)),first_refusal=clean(getattr(engine,'first_refusal',None)))
        atomic(row)
    atomic(row)
    def watch():
        while True:
            peak=peak_bytes()
            reason='memory_limit' if peak>1500000000 else 'hard_wall_guard' if time.perf_counter()-START>119.5 else None
            if reason:
                # Last atomic main-thread checkpoint is valid; do not census a
                # mutating engine from this emergency watchdog thread.
                safe=json.loads(path.read_text());safe.update(status='unverified',reason=reason,last_safe_checkpoint_seconds=safe.get('elapsed_seconds'),
                    elapsed_seconds=time.perf_counter()-START,peak_working_set_bytes=peak)
                atomic(safe);os._exit(124)
            time.sleep(.025)
    threading.Thread(target=watch,daemon=True).start()
    class Captured:
        def solve(self,b,s,past,private,observer,*,physical=None):
            nonlocal last_live
            if not getattr(self,'_board_evidence_snapshot',False):
                self.last_exact_inputs=(b,s,past,private,observer,physical)
                now=time.perf_counter()
                if now-last_live>15:
                    last_live=now;checkpoint()
                    print('PROGRESS '+json.dumps(dict(kind=kind,seconds=round(now-START,3),values=len(self.values),actions=len(self.scalar_actions),sources=len(self.board_sources))),flush=True)
            return super().solve(b,s,past,private,observer,physical=physical)
    class New(Captured,DeferredInitialEngine):pass
    class Reference(Captured,InitialReferenceEngine):pass
    try:
        with calculation_budget(None,max_seconds=115):
            graph,w=base();source=scope(graph,w);row['root_game']=graph.data.to_game();row['root_inputs']=clean(source)
            engine=New(graph,witness=w) if kind=='new' else Reference(graph);engine.capture_terminal=True
            checkpoint()
            with calculation_origin(graph.data):
                remember(engine,graph.root,source)
                row['stage']='initial_Forecast'
                value=engine.solve(*source,physical=source.physical)
                actions=tuple((p,engine.act(*source[:3],p,source.private,None,physical=source.physical)) for p in source.public.alive)
                dawn=tuple((p,horizon_for_action(engine,source.public,source.public_state,source.past,p,source.private)) for p in source.public.alive)
            forecast=Forecast(value,actions,dawn);row.update(forecast=clean(forecast),stage='Table')
            row['comparison_scope']['Forecast']=True;row['table']=clean(complete_table(graph,forecast,None));row['comparison_scope']['Table']=True
            row.update(status='forecast_completed_validation_pending',stage='full_evidence_validation');checkpoint()
            evidence=completed_evidence(engine,graph);row['evidence']=evidence
            row['comparison_scope'].update(joint=True,branches=True,representative_cold=True)
            row.update(status='completed',stage='complete',budget_usage=budget_usage())
    except CalculationBudgetExceeded:
        row.update(status='unverified',reason='calculation_time_limit',budget_stop=budget_stop())
    except Pending as error:row.update(status='unverified',reason=error.reason)
    except Exception as error:
        row.update(status='unverified',reason=type(error).__name__,detail=str(error))
    checkpoint()
    # Persist the exact stop before the potentially larger identity census.
    row['retained']=retained(engine) if engine is not None else {}
    row['diagnostic_materializations']=getattr(getattr(engine,'deferred_ledger',None),'materialized',None)
    row['worker_seconds_before_shutdown']=time.perf_counter()-START;checkpoint()
    print('RESULT_JSON '+json.dumps({k:row[k] for k in ('kind','status','reason','elapsed_seconds','peak_working_set_bytes') if k in row}),flush=True)


def main():
    path=Path('benchmarks/player_match_groups/initial7-120-comparison.json')
    result=dict(status='running',recorded_utc=datetime.now(timezone.utc).isoformat(),workers=[],full_initial_retry_count=1)
    def save():path.write_text(json.dumps(result,indent=2)+'\n')
    save()
    for kind in ('new','reference'):
        begin=time.perf_counter()
        try:
            proc=subprocess.run([sys.executable,'-B','-m',__spec__.name,kind],capture_output=True,text=True,timeout=120)
            info=json.loads(Path('benchmarks/player_match_groups/initial7-120-'+kind+'-trial.json').read_text())
            entry=dict(kind=kind,process_returncode=proc.returncode,process_wall_seconds=time.perf_counter()-begin,status=info['status'],reason=info.get('reason'),comparison_scope=info['comparison_scope'])
        except subprocess.TimeoutExpired as error:
            saved_path=Path('benchmarks/player_match_groups/initial7-120-'+kind+'-trial.json')
            saved=json.loads(saved_path.read_text()) if saved_path.exists() else {}
            entry=dict(kind=kind,status='unverified',reason='external_120s_timeout',process_wall_seconds=time.perf_counter()-begin,
                saved_status=saved.get('status'),saved_reason=saved.get('reason'),saved_elapsed_seconds=saved.get('elapsed_seconds'),
                comparison_scope=saved.get('comparison_scope'),note='worker was externally stopped; atomic checkpoint preserved before process exit')
        result['workers'].append(entry);save();print(json.dumps(entry),flush=True)
        if entry['status']!='completed':
            result.update(status='unverified',reason=entry.get('reason'),reference_executed=kind=='reference',note='No further attempt; incomplete new result cannot authorize reference worker')
            save();return
    new=json.loads(Path('benchmarks/player_match_groups/initial7-120-new-trial.json').read_text())
    old=json.loads(Path('benchmarks/player_match_groups/initial7-120-reference-trial.json').read_text())
    equal={name:new[name]==old[name] for name in ('forecast','table')}
    equal.update({name:new['evidence'][name]==old['evidence'][name] for name in ('joint','branches','terminals')})
    equal['representative_cold_each_validated']=bool(new['evidence']['representative_cold'] and old['evidence']['representative_cold'])
    result.update(status='verified' if all(equal.values()) else 'mismatch',comparison=equal,reference_executed=True)
    save();print('COMPARISON '+json.dumps(equal),flush=True)

if __name__=='__main__':
    if len(sys.argv)>1:worker(sys.argv[1])
    else:main()
