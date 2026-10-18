"""Short initial7 partial-search comparison with a common completed-action point."""
import time
START=time.perf_counter()
import os,sys,json,threading,hashlib,subprocess,statistics
from pathlib import Path
from datetime import datetime,timezone


def retained(engine):
    from werewolf.exact import Board
    from werewolf.seer_future_uniform import TrueScanState
    # Identity census in named retained engine structures, not a whole-heap
    # estimate. Never iterate a deferred diagnostic view.
    refs=[v[0] for v in engine.board_key_hashes.values()]
    boards={id(v) for v in refs if isinstance(v,Board)}
    laws={id(v):v for v in refs if isinstance(v,TrueScanState)}
    for key in engine.board_sources:
        for v in key.values:
            if isinstance(v,Board):boards.add(id(v))
            if isinstance(v,TrueScanState):laws[id(v)]=v
    outcomes={}
    for acquired,rows in engine.board_action_kernels.values():
        for row in rows:outcomes[id(row)]=row
    for record in engine.full_branch_records if isinstance(engine.full_branch_records,list) else ():
        for row in record[3]:outcomes[id(row)]=row
    for row in outcomes.values():
        boards.add(id(row.board))
        if row.context is not None:boards.add(id(row.context))
    ops={id(op):op for request in engine.board_sources.values() for op in request.history}
    return dict(scope='identity census of hash/source keys, resolution and diagnostic outcomes, and source evidence histories; not entire heap',
        tracked_Board_objects=len(boards),tracked_joint_law_objects=len(laws),
        tracked_joint_hypothesis_objects=len({id(h) for law in laws.values() for h in law.hypotheses}),
        retained_resolution_entries=len(engine.board_action_kernels),retained_full_outcome_objects=len(outcomes),
        retained_diagnostic_outcome_references=sum(len(row[3]) for row in engine.full_branch_records) if isinstance(engine.full_branch_records,list) else 0,
        deferred_recipe_inputs=len(engine.deferred_ledger.inputs) if hasattr(engine,'deferred_ledger') else 0,
        deferred_materializations=engine.deferred_ledger.materialized if hasattr(engine,'deferred_ledger') else None,
        identity_hash_entries=len(engine.board_key_hashes),source_keys=len(engine.board_sources),
        unique_saved_request_objects=len({id(r) for r in engine.board_sources.values()}),unique_evidence_operations=len(ops),
        frozen_kernel_objects=len({id(op.engine) for op in ops.values() if hasattr(op,'engine')}))


def worker(mode,repeat,output):
    from .cut_out_uniform_game_fixture import peak_bytes
    def watch():
        while True:
            if time.perf_counter()-START>9.7 or peak_bytes()>1500000000:os._exit(124)
            time.sleep(.025)
    threading.Thread(target=watch,daemon=True).start()
    from .cut_out_initial_publications import base,scope,InitialPublicationEngine,stats,clean
    from .cut_out_deferred_diagnostics import DeferredInitialEngine
    from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded,budget_stop
    from werewolf.information_set_forecast import Pending
    from werewolf.board_future import calculation_origin,remember
    target=3000;search_started=None
    class Probe:
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs);self.fixed_point=None
        def act(self,b,s,past,target,private,observer,*,physical=None):
            value=super().act(b,s,past,target,private,observer,physical=physical)
            if self.fixed_point is None and len(self.scalar_actions)>=3000 and not getattr(self,'_board_evidence_snapshot',False):
                capture=time.perf_counter();peak=peak_bytes();context=clean((b,s,past,private,observer,physical,target))
                signature=hashlib.sha256(json.dumps(context,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                self.fixed_point=dict(completed_unique_scalar_actions=len(self.scalar_actions),search_seconds=capture-search_started,
                    startup_to_fixed_seconds=capture-START,peak_working_set_bytes=peak,context=context,context_sha256=signature,
                    values=len(self.values),generated_sources=len(self.board_sources),retained=retained(self))
                self.fixed_point['capture_seconds']=time.perf_counter()-capture
            return value
    class EagerProbe(Probe,InitialPublicationEngine):pass
    class DeferredProbe(Probe,DeferredInitialEngine):pass
    engine=None;row=dict(status='running',mode=mode,repeat=repeat,search_budget_seconds=8,worker_wall_limit_seconds=10,memory_limit_bytes=1500000000,fixed_completed_actions=target)
    Path(output).write_text(json.dumps(row,indent=2)+'\n')
    reason=None
    try:
        with calculation_budget(None,max_seconds=8):
            graph,w=base();source=scope(graph,w)
            engine=(DeferredProbe if mode=='deferred' else EagerProbe)(graph,witness=w);engine.capture_terminal=True
            search_started=time.perf_counter();row['preparation_seconds']=search_started-START
            with calculation_origin(graph.data):
                remember(engine,graph.root,source);engine.solve(*source,physical=source.physical)
    except CalculationBudgetExceeded:reason=budget_stop()
    except Pending as error:reason=error.reason;row['first_refusal']=engine.first_refusal
    stopped=time.perf_counter();peak=peak_bytes()
    row.update(status='partial_search',stop=reason,search_seconds=stopped-search_started,search_and_preparation_seconds=stopped-START,
        peak_at_search_stop_bytes=peak,stats=stats(engine),retained_at_stop=retained(engine),fixed_point=engine.fixed_point,
        semantic_outputs_complete=False,Forecast_Table_joint_branch_mass_representative_cold_complete=False)
    row['worker_seconds']=time.perf_counter()-START;row['peak_at_worker_end_bytes']=peak_bytes()
    Path(output).write_text(json.dumps(row,indent=2)+'\n')
    print('RESULT_JSON '+json.dumps({k:row[k] for k in ('status','mode','repeat','stop','worker_seconds','peak_at_search_stop_bytes')}),flush=True)


def run():
    path=Path('benchmarks/player_match_groups/initial7-short-retention-comparison.json')
    result=dict(status='running',recorded_utc=datetime.now(timezone.utc).isoformat(),order=['eager','deferred','deferred','eager'],runs=[],note='8-second calculation including preparation, each process <=10 seconds; no full completion or speedup claim')
    for index,mode in enumerate(result['order']):
        repeat=1 if index<2 else 2
        output='benchmarks/player_match_groups/initial7-short-'+mode+'-'+str(repeat)+'.json'
        begin=time.perf_counter()
        try:
            proc=subprocess.run([sys.executable,'-B','-m',__spec__.name,mode,str(repeat),output],capture_output=True,text=True,timeout=10)
            if proc.returncode:raise RuntimeError(str((proc.returncode,proc.stdout,proc.stderr)))
            row=json.loads(Path(output).read_text());row['process_wall_seconds']=time.perf_counter()-begin
        except (subprocess.TimeoutExpired,RuntimeError) as error:
            result.update(status='unverified',failure=dict(index=index,mode=mode,reason=str(error)));path.write_text(json.dumps(result,indent=2)+'\n');raise
        result['runs'].append(row);path.write_text(json.dumps(result,indent=2)+'\n');print(proc.stdout,flush=True)
    fixed=[r['fixed_point'] for r in result['runs']]
    assert all(p is not None and p['completed_unique_scalar_actions']==3000 for p in fixed)
    assert all((p['context_sha256'],p['values'],p['generated_sources'])==(fixed[0]['context_sha256'],fixed[0]['values'],fixed[0]['generated_sources']) for p in fixed)
    result.update(status='bounded_comparison_complete',fixed_branch_and_search_counts_equal=True,
        semantic_equivalence_scope='prior completed finite comparisons only; current initial7 search is incomplete')
    result['medians']={mode:dict(fixed_search_seconds=statistics.median(r['fixed_point']['search_seconds'] for r in result['runs'] if r['mode']==mode),
        fixed_peak_bytes=statistics.median(r['fixed_point']['peak_working_set_bytes'] for r in result['runs'] if r['mode']==mode),
        stopped_actions=statistics.median(r['stats']['actions'] for r in result['runs'] if r['mode']==mode),stopped_values=statistics.median(r['stats']['values'] for r in result['runs'] if r['mode']==mode),
        stopped_generated_sources=statistics.median(r['stats']['generated'] for r in result['runs'] if r['mode']==mode),stopped_peak_bytes=statistics.median(r['peak_at_search_stop_bytes'] for r in result['runs'] if r['mode']==mode)) for mode in ('eager','deferred')}
    path.write_text(json.dumps(result,indent=2)+'\n');print('FIXED_POINT_VERIFIED',flush=True)

if __name__=='__main__':
    if len(sys.argv)>1:worker(sys.argv[1],int(sys.argv[2]),sys.argv[3])
    else:run()
