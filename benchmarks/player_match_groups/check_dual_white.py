"""Actual input-path acceptance; entire validation unit bounded to 300s."""
import json,sys,time,threading
from pathlib import Path
from dataclasses import asdict,is_dataclass
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from benchmarks.player_match_groups.initial_white import initial_white_source
from benchmarks.player_match_groups.run import run
from benchmarks.board_b_benchmark import process_memory_peak
from werewolf.calculation_budget import calculation_budget
import werewolf.match_groups as matching
# Explicit isolated experiment only; committed seven-player gate stays fallback.
provisional='--provisional-seven'in sys.argv
if provisional:
    source=Path(matching.__file__).read_text(encoding='utf-8')
    exec(compile(source.replace('    if board.player_count>6:return False\n',''),matching.__file__,'exec'),matching.__dict__)
current=[None];phase=['prepare'];progress=[];stop=threading.Event();started=time.perf_counter()
original=matching.make_engine

def capture(*args,**kwargs):
    e=original(*args,**kwargs);current[0]=e;return e
matching.make_engine=capture

def serialize(value):return json.loads(json.dumps(value,default=lambda x:asdict(x)if is_dataclass(x)else str(x)))
def checkpoint():
    e=current[0];row=dict(phase=phase[0],seconds=time.perf_counter()-started,memory=process_memory_peak(),stats=dict(e.stats)if e else None,audited_batches=len(e.audits)if e else 0)
    progress.append(row)
    Path('benchmarks/player_match_groups/dual-white-progress.json').write_text(json.dumps(progress,indent=2),encoding='utf-8')
    print(json.dumps(row),flush=True)
def monitor():
    while not stop.wait(10):checkpoint()
thread=threading.Thread(target=monitor,daemon=True);thread.start();results=[]
try:
    with calculation_budget(4000000,max_seconds=300):
        before=json.loads(Path('benchmarks/player_match_groups/dual-white-before.json').read_text(encoding='utf-8'))
        for index,(n,w)in enumerate(((5,1),(6,2),(7,2))if provisional else ((5,1),(6,2))):
            prepared=initial_white_source(n,w,actors=(1,2));state,past=prepared[3:5]
            if n==7:
                phase[0]='7/2 baseline'
                reference=serialize(run(n,w,False,False,prepared=prepared,max_seconds=300,max_work=4000000))
                results.append(dict(phase='7/2 baseline',result=reference))
                Path('benchmarks/player_match_groups/dual-white-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
                if not reference['complete']:
                    checkpoint();raise RuntimeError('Seven-player baseline pending; no terminal equivalence claimed')
            else:reference=before[index]
            phase[0]=f'{n}/{w} independent audit'
            result=serialize(run(n,w,True,True,prepared=prepared,max_seconds=300,max_work=4000000))
            if not result['complete']:
                results.append(dict(phase=phase[0],result=result));Path('benchmarks/player_match_groups/dual-white-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8');checkpoint();raise RuntimeError('Audit pending; no terminal equivalence claimed')
            assert result['stats']['active']and result['stats']['audited_batches']>0
            assert(result['value'],result['table'])==(reference['value'],reference['table'])
            assert prepared[2].role_probability(3,'wolf')==0
            assert all(h.acquisitions[0].target==3 for h in state.hypotheses)
            results.append(dict(phase=phase[0],result=result,joint=serialize(state),past=serialize(past),board_worlds=serialize(prepared[2].worlds)))
            Path('benchmarks/player_match_groups/dual-white-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
            checkpoint()
finally:stop.set();thread.join()
print('complete total_seconds',time.perf_counter()-started,flush=True)
