"""Short matched3000 comparison for full immutable joint component sharing."""
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
    from .cut_out_compact_terminal import CompactTerminalInitialEngine
    from .cut_out_initial_publications import base,scope,stats,clean
    from .cut_out_immutable_joint_observation import census
    from .cut_out_deferred_alternating import fingerprint_rows
    from .cut_out_initial_short_retention import retained
    from werewolf.joint_value_sharing import share_joint_values,independent_joint_values
    from werewolf.board_future import calculation_origin,remember
    from werewolf.calculation_budget import calculation_budget,CalculationBudgetExceeded,budget_stop
    class Stop(Exception):pass
    start_search=None
    class Probe(CompactTerminalInitialEngine):
        def act(self,b,s,past,target,private,observer,*,physical=None):
            value=super().act(b,s,past,target,private,observer,physical=physical)
            if len(self.scalar_actions)==3000 and not getattr(self,'_board_evidence_snapshot',False):
                self.fixed_seconds=time.perf_counter()-start_search;self.fixed_peak=peak_bytes();self.fixed_context=(b,s,past,private,observer,physical,target);raise Stop()
            return value
    graph,w=base();source=scope(graph,w);engine=Probe(graph,witness=w);engine.capture_terminal=True
    row=dict(mode=mode,repeat=repeat,limits=dict(calculation_seconds=8,worker_seconds=10,bytes=1500000000),full_initial7_search=False)
    # Explicit scopes keep construction/evidence owner bound and close weak
    # lookup indices before retained-data census and independent fingerprints.
    try:
        with calculation_budget(None,max_seconds=8):
            with share_joint_values(graph) if mode=='on' else independent_joint_values() as pool:
                start_search=time.perf_counter()
                with calculation_origin(graph.data):remember(engine,graph.root,source);engine.solve(*source,physical=source.physical)
    except Stop:row.update(status='fixed_point_reached',search_seconds=engine.fixed_seconds,peak_at_fixed_point_bytes=engine.fixed_peak,context=clean(engine.fixed_context))
    except CalculationBudgetExceeded:row.update(status='unverified',reason=budget_stop())
    if mode=='on':row['pool']=dict(counters=dict(pool.counts),live_before_close=pool.closed_live_counts,indices_empty_after_close=not pool.records and not pool.hypotheses,owner_released=pool.owner is None)
    row.update(stats=stats(engine),retained=retained(engine),census=census(engine),partial_memo_fingerprints=dict(values=fingerprint_rows(engine.values.items()),actions=fingerprint_rows(engine.scalar_actions.items())))
    row['context_sha256']=hashlib.sha256(json.dumps(row['context'],sort_keys=True,separators=(',',':')).encode()).hexdigest()
    row.update(worker_seconds=time.perf_counter()-START,peak_after_census_bytes=peak_bytes())
    Path(output).write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({k:row[k] for k in ('mode','repeat','status','search_seconds','peak_at_fixed_point_bytes','worker_seconds')}),flush=True)


def run():
    path=Path('benchmarks/player_match_groups/immutable-joint-initial3000-results.json')
    result=dict(status='running',recorded_utc=datetime.now(timezone.utc).isoformat(),order=['off','on','on','off'],runs=[])
    def save():path.write_text(json.dumps(result,indent=2)+'\n')
    for index,mode in enumerate(result['order']):
        repeat=1 if index<2 else 2;output='benchmarks/player_match_groups/immutable-joint-initial3000-'+mode+'-'+str(repeat)+'.json';begin=time.perf_counter()
        proc=subprocess.run([sys.executable,'-B','-m',__spec__.name,mode,str(repeat),output],capture_output=True,text=True,timeout=10)
        if proc.returncode:result.update(status='unverified',failure=dict(stdout=proc.stdout,stderr=proc.stderr));save();raise RuntimeError(result['failure'])
        row=json.loads(Path(output).read_text());row['process_wall_seconds']=time.perf_counter()-begin;result['runs'].append(row);save();print(proc.stdout,flush=True)
        if row['status']!='fixed_point_reached':result['status']='unverified';save();return
    first=result['runs'][0]
    assert all(r['stats']['actions']==3000 and (r['stats']['values'],r['stats']['generated'],r['context_sha256'],r['partial_memo_fingerprints'])==(first['stats']['values'],first['stats']['generated'],first['context_sha256'],first['partial_memo_fingerprints']) for r in result['runs'])
    result.update(status='matched_work_verified',summary={mode:{key:statistics.median(r[key] for r in result['runs'] if r['mode']==mode) for key in ('search_seconds','peak_at_fixed_point_bytes','worker_seconds')} for mode in ('off','on')},initial_full_outputs_complete=False)
    save();print('MATCHED_WORK_VERIFIED',flush=True)

if __name__=='__main__':
    if len(sys.argv)>1:worker(sys.argv[1],int(sys.argv[2]),sys.argv[3])
    else:run()
