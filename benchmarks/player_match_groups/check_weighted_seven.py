"""One finite seven-player joint-weight extension acceptance (<=300s total)."""
import json,sys,subprocess,time
from pathlib import Path
started=time.perf_counter();rows=[]
for enabled,audit in ((False,False),(True,True)):
    remaining=max(1,300-(time.perf_counter()-started))
    code="""import json,threading,time
from dataclasses import asdict,is_dataclass
from benchmarks.player_match_groups.run import run
from benchmarks.player_match_groups.weighted_joint import weighted_source
from benchmarks.board_b_benchmark import process_memory_peak
import werewolf.match_groups as m
engines=[];original=m.make_engine

def capture(*args,**kwargs):
 e=original(*args,**kwargs);engines.append(e);return e
m.make_engine=capture
stop=threading.Event()
def report():
 while not stop.wait(10):
  e=engines[0]if engines else None
  print(json.dumps(dict(progress=True,memory=process_memory_peak(),stats=e.stats if e else None,audited_batches=len(e.audits)if e else 0)),flush=True)
thread=threading.Thread(target=report,daemon=True);thread.start()
try:r=run(7,1,ENABLED,AUDIT,max_seconds=BUDGET,max_work=4000000,prepared=weighted_source(7,1,'point'))
finally:stop.set();thread.join()
print(json.dumps(r,default=lambda x:asdict(x)if is_dataclass(x)else str(x)),flush=True)
""".replace('ENABLED',repr(enabled)).replace('AUDIT',repr(audit)).replace('BUDGET',repr(remaining))
    process=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=remaining+10,check=True)
    lines=process.stdout.splitlines()
    Path(f'benchmarks/player_match_groups/weighted-seven-progress-{int(enabled)}.jsonl').write_text('\n'.join(lines[:-1])+'\n',encoding='utf-8')
    result=json.loads(lines[-1]);rows.append(result)
    Path('benchmarks/player_match_groups/weighted-seven-results.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    print({k:result.get(k)for k in ('complete','seconds','value','stats','memory')},flush=True)
    if not result['complete']:break
    assert (result['value'],result['table'])==(rows[0]['value'],rows[0]['table'])
print('stage_seconds',time.perf_counter()-started,flush=True)
