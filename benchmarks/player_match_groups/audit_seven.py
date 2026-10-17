"""One bounded missing audit, reusing the previously saved uncompressed result.

Run from repository root. Temporary gate exists only in this isolated process.
The oracle is separate and ungrouped, with its existing persistent engine caches.
No audit member, physical state or transport assertion is omitted.
"""
import json,sys,time,threading
from dataclasses import asdict,is_dataclass
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import werewolf.match_groups as matching
from benchmarks.board_b_benchmark import process_memory_peak
from werewolf.calculation_budget import budget_stop
source=Path(matching.__file__).read_text(encoding='utf-8')
assert '((5,1),(6,1),(6,2))' in source or '((5,1),(6,1),(6,2),(7,1))' in source
exec(compile(source.replace('((5,1),(6,1),(6,2))','((5,1),(6,1),(6,2),(7,1))'),matching.__file__,'exec'),matching.__dict__)
engines=[];original=matching.make_engine

def capture(*args,**kwargs):
    engine=original(*args,**kwargs);engines.append(engine);return engine
matching.make_engine=capture
from benchmarks.player_match_groups.run import run
started=time.perf_counter();finished=threading.Event();progress=[]

def snapshot(stage):
    row=dict(stage=stage,seconds=time.perf_counter()-started,memory=process_memory_peak())
    if engines:
        e=engines[0];o=e.audit_oracle
        row.update(stats=dict(e.stats),audited_batches=len(e.audits),oracle_stats=dict(o.stats),oracle_values=len(o.values),oracle_actions=o.expansions['actions'])
    progress.append(row)
    Path('benchmarks/player_match_groups/seven-audit-progress.json').write_text(json.dumps(progress,indent=2),encoding='utf-8')
    print(json.dumps(row),flush=True)

def monitor():
    while not finished.wait(10):snapshot('running')
thread=threading.Thread(target=monitor,daemon=True);thread.start()
try:
    result=run(7,1,True,True,max_seconds=300,max_work=4000000)
finally:
    finished.set();thread.join()
snapshot('complete' if result['complete'] else 'pending')
result=json.loads(json.dumps(result,default=lambda x:asdict(x)if is_dataclass(x)else str(x)))
result['budget_stop']=budget_stop()
Path('benchmarks/player_match_groups/seven-audit-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
reference=json.loads(Path('benchmarks/player_match_groups/seven-stage1-results.json').read_text(encoding='utf-8'))[0]
if result['complete']:
    assert reference['complete']
    assert (result['value'],result['table'])==(reference['value'],reference['table'])
    assert result['stats']['active'] and result['stats']['audited_batches']>0
    result['saved_uncompressed_full_table_equal']=True
Path('benchmarks/player_match_groups/seven-audit-result.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
print(json.dumps(dict(complete=result['complete'],seconds=result['seconds'],value=result.get('value'),stats=result['stats'],budget_stop=result['budget_stop'])),flush=True)
